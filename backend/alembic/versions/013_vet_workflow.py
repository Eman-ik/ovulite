"""Veterinarian / ET workflow: recipient profiles, screening, diagnosis chain, calving.

Four changes, in dependency order:

1. ``recipients`` gains the animal profile the ET workflow needs (breed,
   birth_date, parity, reproductive status and history). Age is deliberately
   not a column — it is derived from birth_date so it cannot go stale.

2. ``recipient_evaluations`` records pre-transfer CL and uterine assessment
   against the *recipient*, so animals screened and rejected are captured.
   Hanging it off et_transfers would have made those rows impossible.

3. ``pregnancy_checks`` replaces the fixed pc1/pc2 pair with an open-ended
   chain (day 28 / 45 / 60 / whatever a programme adds), each with its own
   date, method and operator. This is what makes pregnancy *retention*
   measurable.

4. ``calving_records`` records the terminal outcome, making live birth rate
   computable for the first time.

**Backfill.** Existing ``pc1_date``/``pc1_result`` pairs are copied into
``pregnancy_checks`` so the new table is not empty on day one. ``pc2_*`` is
deliberately NOT backfilled: in this database its 7 non-null values are
integers (54, 17, 83, 85, 74, 46, 61), i.e. day counts written into a result
column, not pregnancy outcomes. Copying them would import known-bad data into
the new table's constrained ``result`` column.

``et_transfers.pc1_result`` is kept and stays maintained as the denormalised
view of the earliest check, because the dashboard, research, analytics and ML
feature paths all read it. It is not a second source of truth.
"""

import sqlalchemy as sa
from alembic import op

revision = "013_vet_workflow"
down_revision = "012_researcher_role"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Recipient profile ──
    with op.batch_alter_table("recipients") as batch_op:
        batch_op.add_column(sa.Column("breed", sa.String(100)))
        batch_op.add_column(sa.Column("birth_date", sa.Date()))
        batch_op.add_column(sa.Column("parity", sa.Integer()))
        batch_op.add_column(sa.Column("reproductive_status", sa.String(30)))
        batch_op.add_column(sa.Column("reproductive_disorders", sa.Text()))
        batch_op.add_column(sa.Column("previous_ai_count", sa.Integer()))
        batch_op.add_column(sa.Column("previous_et_count", sa.Integer()))
        batch_op.create_check_constraint("ck_recipients_parity_non_negative", "parity >= 0")
        batch_op.create_check_constraint(
            "ck_recipients_reproductive_status",
            "reproductive_status IN ('Cycling', 'Anestrus', 'Pregnant', 'Open', 'Culled')",
        )

    # ── 2. Pre-transfer screening ──
    op.create_table(
        "recipient_evaluations",
        sa.Column("evaluation_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("recipient_id", sa.Integer(), nullable=False),
        sa.Column("evaluation_date", sa.Date(), nullable=False),
        sa.Column("technician_id", sa.Integer()),
        sa.Column("cl_present", sa.Boolean()),
        sa.Column("cl_side", sa.String(10)),
        sa.Column("cl_diameter_mm", sa.Numeric(5, 2)),
        sa.Column("cl_quality", sa.String(10)),
        sa.Column("follicle_count", sa.Integer()),
        sa.Column("largest_follicle_mm", sa.Numeric(5, 2)),
        sa.Column("uterine_tone", sa.String(10)),
        sa.Column("progesterone_ng_ml", sa.Numeric(6, 3)),
        sa.Column("body_condition_score", sa.Numeric(3, 1)),
        sa.Column("eligibility", sa.String(20)),
        sa.Column("notes", sa.Text()),
        sa.Column("transfer_id", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.organization_id"]),
        sa.ForeignKeyConstraint(["recipient_id"], ["recipients.recipient_id"]),
        sa.ForeignKeyConstraint(["technician_id"], ["technicians.technician_id"]),
        sa.ForeignKeyConstraint(["transfer_id"], ["et_transfers.transfer_id"]),
        sa.CheckConstraint(
            "eligibility IN ('Excellent', 'Acceptable', 'Not Recommended')",
            name="ck_recipient_evaluations_eligibility",
        ),
        sa.CheckConstraint(
            "cl_quality IN ('Good', 'Fair', 'Poor')", name="ck_recipient_evaluations_cl_quality"
        ),
        sa.CheckConstraint(
            "uterine_tone IN ('Good', 'Fair', 'Poor')", name="ck_recipient_evaluations_uterine_tone"
        ),
        sa.CheckConstraint(
            "cl_side IN ('Left', 'Right')", name="ck_recipient_evaluations_cl_side"
        ),
    )
    op.create_index("ix_recipient_evaluations_organization_id", "recipient_evaluations", ["organization_id"])
    op.create_index("ix_recipient_evaluations_recipient_id", "recipient_evaluations", ["recipient_id"])
    op.create_index("ix_recipient_evaluations_transfer_id", "recipient_evaluations", ["transfer_id"])

    # ── 3. Pregnancy diagnosis chain ──
    op.create_table(
        "pregnancy_checks",
        sa.Column("check_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("transfer_id", sa.Integer(), nullable=False),
        sa.Column("check_date", sa.Date(), nullable=False),
        sa.Column("days_post_transfer", sa.Integer()),
        sa.Column("result", sa.String(20), nullable=False),
        sa.Column("method", sa.String(30)),
        sa.Column("technician_id", sa.Integer()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.organization_id"]),
        sa.ForeignKeyConstraint(["transfer_id"], ["et_transfers.transfer_id"]),
        sa.ForeignKeyConstraint(["technician_id"], ["technicians.technician_id"]),
        sa.CheckConstraint(
            "result IN ('Pregnant', 'Open', 'Recheck', 'Lost')", name="ck_pregnancy_checks_result"
        ),
        sa.CheckConstraint(
            "method IN ('Ultrasound', 'Rectal Palpation', 'Blood Test', 'Other')",
            name="ck_pregnancy_checks_method",
        ),
        sa.UniqueConstraint("transfer_id", "check_date", name="uq_pregnancy_checks_transfer_date"),
    )
    op.create_index("ix_pregnancy_checks_organization_id", "pregnancy_checks", ["organization_id"])
    op.create_index("ix_pregnancy_checks_transfer_id", "pregnancy_checks", ["transfer_id"])

    # ── 4. Calving ──
    op.create_table(
        "calving_records",
        sa.Column("calving_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("transfer_id", sa.Integer(), nullable=False),
        sa.Column("calving_date", sa.Date(), nullable=False),
        sa.Column("outcome", sa.String(20), nullable=False),
        sa.Column("calf_sex", sa.String(10)),
        sa.Column("calf_weight_kg", sa.Numeric(5, 2)),
        sa.Column("gestation_days", sa.Integer()),
        sa.Column("assisted", sa.Boolean()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.organization_id"]),
        sa.ForeignKeyConstraint(["transfer_id"], ["et_transfers.transfer_id"]),
        sa.CheckConstraint(
            "outcome IN ('Live Birth', 'Stillbirth', 'Abortion')", name="ck_calving_records_outcome"
        ),
        sa.CheckConstraint(
            "calf_sex IN ('Male', 'Female', 'Unknown')", name="ck_calving_records_calf_sex"
        ),
        sa.UniqueConstraint("transfer_id", name="uq_calving_records_transfer"),
    )
    op.create_index("ix_calving_records_organization_id", "calving_records", ["organization_id"])
    op.create_index("ix_calving_records_transfer_id", "calving_records", ["transfer_id"])

    # ── Backfill pc1 only. See module docstring for why pc2 is excluded. ──
    op.execute(
        """
        INSERT INTO pregnancy_checks
            (organization_id, transfer_id, check_date, days_post_transfer, result, notes)
        SELECT
            t.organization_id,
            t.transfer_id,
            t.pc1_date,
            CASE WHEN t.et_date IS NOT NULL THEN (t.pc1_date - t.et_date) END,
            CASE lower(trim(t.pc1_result))
                WHEN 'pregnant' THEN 'Pregnant'
                WHEN 'p'        THEN 'Pregnant'
                WHEN 'positive' THEN 'Pregnant'
                WHEN 'open'     THEN 'Open'
                WHEN 'o'        THEN 'Open'
                WHEN 'negative' THEN 'Open'
                WHEN 'recheck'  THEN 'Recheck'
                WHEN 'pending'  THEN 'Recheck'
            END,
            'Backfilled from et_transfers.pc1_result by migration 013'
        FROM et_transfers t
        WHERE t.pc1_date IS NOT NULL
          AND lower(trim(t.pc1_result)) IN
              ('pregnant', 'p', 'positive', 'open', 'o', 'negative', 'recheck', 'pending')
        """
    )


def downgrade() -> None:
    op.drop_table("calving_records")
    op.drop_table("pregnancy_checks")
    op.drop_table("recipient_evaluations")
    with op.batch_alter_table("recipients") as batch_op:
        batch_op.drop_constraint("ck_recipients_reproductive_status", type_="check")
        batch_op.drop_constraint("ck_recipients_parity_non_negative", type_="check")
        for column in (
            "previous_et_count",
            "previous_ai_count",
            "reproductive_disorders",
            "reproductive_status",
            "parity",
            "birth_date",
            "breed",
        ):
            batch_op.drop_column(column)
