"""Laboratory workflow: oocyte grading, IVM, semen identity, culture timeline, embryo status.

Completes the embryologist's path — OPU -> oocyte -> IVM -> IVF -> cleavage ->
blastocyst -> grade -> freeze/transfer — which previously existed only as
aggregate counts on ``ivf_batches``, every one of which is null in this
database.

Five changes:

1. ``opu_sessions`` gains oocyte quality as counts per grade (A/B/C/degenerate)
   rather than a row per oocyte. COCs are graded in a dish and tallied; twenty
   rows carrying only a grade would add storage without adding information.

2. ``ivm_batches`` records maturation as its own procedure — medium, lot,
   incubation hours, temperature, CO2/O2, in/out counts. Separate from
   ``ivf_batches`` because one matured cohort can be split across several
   fertilisations, and folding it in would repeat those parameters per split.

3. ``ivf_batches`` gains semen identity and fertilisation parameters, plus a
   link to the IVM batch it drew from.

4. ``embryo_observations`` records the culture timeline: one look per embryo
   per day, with stage, grade, morphology and whether it arrested. ``Embryo``
   carries only the final state, which cannot say when the embryo got there.

5. ``embryos`` gains a ``status`` lifecycle.

6. ``donors`` gains the animal profile, mirroring the recipient work in
   migration 013: birth date (age is derived, never stored), parity,
   reproductive status and history.

**On semen type.** ``ivf_batches`` is the correct home for it: at least one
sire here — Mr Karu Manso 800 — is used with both conventional and sexed
straws, so ``sires.semen_type`` (which is populated) cannot describe an
individual insemination. Checked against the source data, semen type is
consistent within all 117 IVF batches, so per-batch storage loses nothing.

This migration deliberately does NOT backfill it. Deriving it from
``sires.semen_type`` was tried and is only 86.2% accurate — 57 of 414
transfers get the wrong value — and it manufactures a difference that is not
there: the sire-derived version reports Sexed at 22.7% against Conventional
28.4%, where the per-transfer source says 29.5% against 28.5%, i.e. no effect
at all. Shipping a 5.7 pp gap that is an artefact of the approximation would
be worse than shipping nothing.

The real values live in the ingest CSV, and a migration should not depend on a
data file that may not exist on another machine. ``scripts/backfill_semen_type.py``
does that separately and verifies every row it writes.

``embryos.status`` is backfilled to 'Transferred' for every embryo that has a
transfer. In this dataset that is all 489 of them, because it is an embryo
*transfer* dataset — so the column has no variance today and is worth nothing
analytically until embryos are entered through the lab workflow and some are
frozen, assigned or discarded. It is populated anyway so the lifecycle starts
from a true statement rather than from null.
"""

import sqlalchemy as sa
from alembic import op

revision = "015_lab_workflow"
down_revision = "014_synchronization_scheduling"
branch_labels = None
depends_on = None

EMBRYO_STATUSES = "('In Culture', 'Transferable', 'Frozen', 'Assigned', 'Transferred', 'Discarded')"


def upgrade() -> None:
    # ── 1. Oocyte grading on the recovery session ──
    with op.batch_alter_table("opu_sessions") as batch_op:
        batch_op.add_column(sa.Column("grade_a_oocytes", sa.Integer()))
        batch_op.add_column(sa.Column("grade_b_oocytes", sa.Integer()))
        batch_op.add_column(sa.Column("grade_c_oocytes", sa.Integer()))
        batch_op.add_column(sa.Column("degenerated_oocytes", sa.Integer()))
        batch_op.add_column(sa.Column("oocyte_morphology_notes", sa.Text()))

    # ── 2. IVM ──
    op.create_table(
        "ivm_batches",
        sa.Column("ivm_batch_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("opu_id", sa.Integer(), nullable=False),
        sa.Column("ivm_date", sa.Date()),
        sa.Column("medium", sa.String(120)),
        sa.Column("medium_lot", sa.String(60)),
        sa.Column("incubation_hours", sa.Numeric(5, 2)),
        sa.Column("temperature_c", sa.Numeric(4, 2)),
        sa.Column("co2_percent", sa.Numeric(4, 2)),
        sa.Column("o2_percent", sa.Numeric(4, 2)),
        sa.Column("oocytes_in", sa.Integer()),
        sa.Column("mature_oocytes_out", sa.Integer()),
        sa.Column("embryologist_id", sa.Integer()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.organization_id"]),
        sa.ForeignKeyConstraint(["opu_id"], ["opu_sessions.opu_id"]),
        sa.ForeignKeyConstraint(["embryologist_id"], ["technicians.technician_id"]),
        sa.CheckConstraint(
            "mature_oocytes_out IS NULL OR oocytes_in IS NULL OR mature_oocytes_out <= oocytes_in",
            name="ck_ivm_batches_mature_not_above_input",
        ),
        sa.CheckConstraint("oocytes_in IS NULL OR oocytes_in >= 0", name="ck_ivm_batches_oocytes_in"),
        sa.CheckConstraint(
            "incubation_hours IS NULL OR incubation_hours BETWEEN 0 AND 96",
            name="ck_ivm_batches_incubation_hours",
        ),
    )
    op.create_index("ix_ivm_batches_organization_id", "ivm_batches", ["organization_id"])
    op.create_index("ix_ivm_batches_opu_id", "ivm_batches", ["opu_id"])

    # ── 3. Semen identity and fertilisation parameters ──
    with op.batch_alter_table("ivf_batches") as batch_op:
        batch_op.add_column(sa.Column("ivm_batch_id", sa.Integer()))
        batch_op.add_column(sa.Column("semen_type", sa.String(20)))
        batch_op.add_column(sa.Column("semen_batch", sa.String(60)))
        batch_op.add_column(sa.Column("sperm_concentration", sa.String(40)))
        batch_op.add_column(sa.Column("fertilization_medium", sa.String(120)))
        batch_op.add_column(sa.Column("fertilization_hours", sa.Numeric(5, 2)))
        batch_op.create_foreign_key(
            "fk_ivf_batches_ivm_batch_id", "ivm_batches", ["ivm_batch_id"], ["ivm_batch_id"]
        )
        batch_op.create_check_constraint(
            "ck_ivf_batches_semen_type", "semen_type IS NULL OR semen_type IN ('Conventional', 'Sexed')"
        )
    op.create_index("ix_ivf_batches_ivm_batch_id", "ivf_batches", ["ivm_batch_id"])

    # ── 4. Culture timeline ──
    op.create_table(
        "embryo_observations",
        sa.Column("observation_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("embryo_id", sa.Integer(), nullable=False),
        sa.Column("observation_date", sa.Date(), nullable=False),
        sa.Column("day_number", sa.Integer(), nullable=False),
        sa.Column("stage", sa.Integer()),
        sa.Column("grade", sa.Integer()),
        sa.Column("morphology", sa.Text()),
        sa.Column("is_arrested", sa.Boolean()),
        sa.Column("cell_count", sa.Integer()),
        sa.Column("expansion_diameter_um", sa.Numeric(6, 2)),
        sa.Column("embryologist_id", sa.Integer()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.organization_id"]),
        sa.ForeignKeyConstraint(["embryo_id"], ["embryos.embryo_id"]),
        sa.ForeignKeyConstraint(["embryologist_id"], ["technicians.technician_id"]),
        sa.UniqueConstraint("embryo_id", "day_number", name="uq_embryo_observations_embryo_day"),
        sa.CheckConstraint("day_number BETWEEN 0 AND 12", name="ck_embryo_observations_day_number"),
        sa.CheckConstraint("stage IS NULL OR stage BETWEEN 1 AND 9", name="ck_embryo_observations_stage"),
        sa.CheckConstraint("grade IS NULL OR grade BETWEEN 1 AND 4", name="ck_embryo_observations_grade"),
    )
    op.create_index("ix_embryo_observations_organization_id", "embryo_observations", ["organization_id"])
    op.create_index("ix_embryo_observations_embryo_id", "embryo_observations", ["embryo_id"])

    # ── 5. Donor profile, mirroring recipients in migration 013 ──
    with op.batch_alter_table("donors") as batch_op:
        batch_op.add_column(sa.Column("birth_date", sa.Date()))
        batch_op.add_column(sa.Column("parity", sa.Integer()))
        batch_op.add_column(sa.Column("reproductive_status", sa.String(30)))
        batch_op.add_column(sa.Column("reproductive_history", sa.Text()))
        batch_op.create_check_constraint("ck_donors_parity_non_negative", "parity >= 0")

    # ── 6. Embryo lifecycle ──
    with op.batch_alter_table("embryos") as batch_op:
        batch_op.add_column(sa.Column("status", sa.String(20)))
        batch_op.add_column(sa.Column("discarded_reason", sa.Text()))
        batch_op.create_check_constraint(
            "ck_embryos_status", f"status IS NULL OR status IN {EMBRYO_STATUSES}"
        )

    # ── Backfills ──
    # semen_type is intentionally left null here — see the module docstring.
    op.execute(
        """
        UPDATE embryos e
        SET status = 'Transferred'
        WHERE EXISTS (SELECT 1 FROM et_transfers t WHERE t.embryo_id = e.embryo_id)
        """
    )
    # Anything left with freezing evidence but no transfer is still in store.
    op.execute(
        """
        UPDATE embryos
        SET status = 'Frozen'
        WHERE status IS NULL
          AND (freezing_date IS NOT NULL OR cane_number IS NOT NULL)
        """
    )


def downgrade() -> None:
    with op.batch_alter_table("embryos") as batch_op:
        batch_op.drop_constraint("ck_embryos_status", type_="check")
        batch_op.drop_column("discarded_reason")
        batch_op.drop_column("status")

    op.drop_table("embryo_observations")

    op.drop_index("ix_ivf_batches_ivm_batch_id", table_name="ivf_batches")
    with op.batch_alter_table("ivf_batches") as batch_op:
        batch_op.drop_constraint("ck_ivf_batches_semen_type", type_="check")
        batch_op.drop_constraint("fk_ivf_batches_ivm_batch_id", type_="foreignkey")
        for column in (
            "fertilization_hours",
            "fertilization_medium",
            "sperm_concentration",
            "semen_batch",
            "semen_type",
            "ivm_batch_id",
        ):
            batch_op.drop_column(column)

    with op.batch_alter_table("donors") as batch_op:
        batch_op.drop_constraint("ck_donors_parity_non_negative", type_="check")
        for column in ("reproductive_history", "reproductive_status", "parity", "birth_date"):
            batch_op.drop_column(column)

    op.drop_table("ivm_batches")

    with op.batch_alter_table("opu_sessions") as batch_op:
        for column in (
            "oocyte_morphology_notes",
            "degenerated_oocytes",
            "grade_c_oocytes",
            "grade_b_oocytes",
            "grade_a_oocytes",
        ):
            batch_op.drop_column(column)
