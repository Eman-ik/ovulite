"""Synchronization scheduling: protocol step templates and recipient enrollments.

``protocols`` held only a name. The names in this database
(``CIDR+GnRH+PGF+GnRH``) say which drugs a protocol uses but not on which
days, so no schedule can be derived from them — ``protocol_steps`` starts
empty and is filled in by the veterinarian. Seeding a guessed day schedule
would be fabricating a clinical instruction.

``synchronization_enrollments`` places a recipient on a protocol from a start
date. The resulting schedule is computed on read as
``start_date + step.day_offset`` and never stored: materialising it would
require rewriting every enrollment whenever a protocol's steps were
corrected, and the copies would silently drift.

``protocol_logs`` gains ``enrollment_id`` and ``step_id``. It previously
hung off ``transfer_id`` alone, which meant a treatment could only be recorded
for an animal that went on to receive an embryo — losing every recipient that
was synchronised and not used. That column is kept so existing callers still
work; the table has no rows today, so nothing needs migrating into the new
shape.
"""

import sqlalchemy as sa
from alembic import op

revision = "014_synchronization_scheduling"
down_revision = "013_vet_workflow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "protocol_steps",
        sa.Column("step_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("protocol_id", sa.Integer(), nullable=False),
        sa.Column("day_offset", sa.Integer(), nullable=False),
        sa.Column("step_name", sa.String(100), nullable=False),
        sa.Column("drug_name", sa.String(100)),
        sa.Column("dosage", sa.String(50)),
        sa.Column("route", sa.String(30)),
        sa.Column("is_transfer_day", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.organization_id"]),
        sa.ForeignKeyConstraint(["protocol_id"], ["protocols.protocol_id"]),
        sa.UniqueConstraint(
            "protocol_id", "day_offset", "step_name", name="uq_protocol_steps_protocol_day_name"
        ),
        sa.CheckConstraint("day_offset BETWEEN -30 AND 365", name="ck_protocol_steps_day_offset"),
    )
    op.create_index("ix_protocol_steps_organization_id", "protocol_steps", ["organization_id"])
    op.create_index("ix_protocol_steps_protocol_id", "protocol_steps", ["protocol_id"])

    op.create_table(
        "synchronization_enrollments",
        sa.Column("enrollment_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("recipient_id", sa.Integer(), nullable=False),
        sa.Column("protocol_id", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="Active"),
        sa.Column("withdrawn_reason", sa.Text()),
        sa.Column("technician_id", sa.Integer()),
        sa.Column("transfer_id", sa.Integer()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.organization_id"]),
        sa.ForeignKeyConstraint(["recipient_id"], ["recipients.recipient_id"]),
        sa.ForeignKeyConstraint(["protocol_id"], ["protocols.protocol_id"]),
        sa.ForeignKeyConstraint(["technician_id"], ["technicians.technician_id"]),
        sa.ForeignKeyConstraint(["transfer_id"], ["et_transfers.transfer_id"]),
        sa.CheckConstraint(
            "status IN ('Active', 'Completed', 'Withdrawn')",
            name="ck_synchronization_enrollments_status",
        ),
    )
    op.create_index(
        "ix_synchronization_enrollments_organization_id", "synchronization_enrollments", ["organization_id"]
    )
    op.create_index(
        "ix_synchronization_enrollments_recipient_id", "synchronization_enrollments", ["recipient_id"]
    )
    op.create_index(
        "ix_synchronization_enrollments_protocol_id", "synchronization_enrollments", ["protocol_id"]
    )
    op.create_index(
        "ix_synchronization_enrollments_transfer_id", "synchronization_enrollments", ["transfer_id"]
    )

    with op.batch_alter_table("protocol_logs") as batch_op:
        batch_op.add_column(sa.Column("enrollment_id", sa.Integer()))
        batch_op.add_column(sa.Column("step_id", sa.Integer()))
        batch_op.create_foreign_key(
            "fk_protocol_logs_enrollment_id",
            "synchronization_enrollments",
            ["enrollment_id"],
            ["enrollment_id"],
        )
        batch_op.create_foreign_key(
            "fk_protocol_logs_step_id", "protocol_steps", ["step_id"], ["step_id"]
        )
    op.create_index("ix_protocol_logs_enrollment_id", "protocol_logs", ["enrollment_id"])
    op.create_index("ix_protocol_logs_step_id", "protocol_logs", ["step_id"])


def downgrade() -> None:
    op.drop_index("ix_protocol_logs_step_id", table_name="protocol_logs")
    op.drop_index("ix_protocol_logs_enrollment_id", table_name="protocol_logs")
    with op.batch_alter_table("protocol_logs") as batch_op:
        batch_op.drop_constraint("fk_protocol_logs_step_id", type_="foreignkey")
        batch_op.drop_constraint("fk_protocol_logs_enrollment_id", type_="foreignkey")
        batch_op.drop_column("step_id")
        batch_op.drop_column("enrollment_id")

    op.drop_table("synchronization_enrollments")
    op.drop_table("protocol_steps")
