"""System-wide audit trail for auth events and privileged changes.

FR-M1-05 / NFR-SEC-06. ``case_audit`` already covers edits to one case but
cannot answer "who logged in", "who changed a role", or "who deployed a
model", which is what an audit is for.

``actor_user_id`` and ``organization_id`` are both nullable on purpose: a
failed login against an unknown username has neither, and that is precisely
the event most worth recording. Forcing either would mean inventing a value
or dropping the row.

No backfill: nothing before this migration was observed, and inventing
history is the one thing an audit trail must never do.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "016_audit_events"
down_revision = "015_lab_workflow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("audit_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("outcome", sa.String(20), nullable=False, server_default="success"),
        sa.Column("actor_user_id", sa.Integer()),
        sa.Column("actor_label", sa.String(150)),
        sa.Column("actor_role", sa.String(40)),
        sa.Column("organization_id", sa.Integer()),
        sa.Column("target_type", sa.String(60)),
        sa.Column("target_id", sa.String(60)),
        sa.Column("ip_address", sa.String(64)),
        sa.Column("user_agent", sa.String(300)),
        sa.Column("request_id", sa.String(64)),
        sa.Column("detail", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("message", sa.Text()),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.user_id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.organization_id"]),
    )
    op.create_index("ix_audit_events_occurred_at", "audit_events", ["occurred_at"])
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_events_actor_user_id", "audit_events", ["actor_user_id"])
    op.create_index("ix_audit_events_organization_id", "audit_events", ["organization_id"])
    op.create_index("ix_audit_events_target_type", "audit_events", ["target_type"])
    op.create_index("ix_audit_events_request_id", "audit_events", ["request_id"])
    # The two queries an audit actually gets.
    op.create_index("ix_audit_events_org_time", "audit_events", ["organization_id", "occurred_at"])
    op.create_index("ix_audit_events_actor_time", "audit_events", ["actor_user_id", "occurred_at"])


def downgrade() -> None:
    op.drop_table("audit_events")
