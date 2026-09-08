"""Immutable intake revisions and organization-scoped external embryo identities."""
from alembic import op
import sqlalchemy as sa

revision = "011_intake_governance"
down_revision = "010_release60_metadata_rag"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("embryo_identifiers",
        sa.Column("identifier_id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.organization_id"), nullable=False),
        sa.Column("identifier", sa.String(100), nullable=False),
        sa.Column("embryo_id", sa.Integer(), sa.ForeignKey("embryos.embryo_id"), nullable=False, unique=True),
        sa.UniqueConstraint("organization_id", "identifier", name="uq_embryo_identifier_org"))
    op.create_index("ix_embryo_identifiers_organization_id", "embryo_identifiers", ["organization_id"])
    op.create_table("intake_revisions",
        sa.Column("revision_id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.organization_id"), nullable=False),
        sa.Column("batch_id", sa.String(36), sa.ForeignKey("intake_batches.batch_id"), nullable=False),
        sa.Column("actor", sa.String(100), nullable=False), sa.Column("state", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_intake_revisions_organization_id", "intake_revisions", ["organization_id"])
    op.create_index("ix_intake_revisions_batch_id", "intake_revisions", ["batch_id"])


def downgrade():
    op.drop_table("intake_revisions")
    op.drop_table("embryo_identifiers")
