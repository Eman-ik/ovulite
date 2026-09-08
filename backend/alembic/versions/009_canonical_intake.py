"""Persist mapped import batches and transfer provenance."""
from alembic import op
import sqlalchemy as sa

revision = "009_canonical_intake"
down_revision = "008_literature_documents"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("intake_batches",
        sa.Column("batch_id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.organization_id"), nullable=False),
        sa.Column("filename", sa.String(200), nullable=False),
        sa.Column("raw_csv", sa.Text(), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("source_type", sa.String(40), nullable=False),
        sa.Column("source_reference", sa.String(1000), nullable=False),
        sa.Column("mapping", sa.JSON(), nullable=False),
        sa.Column("report", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_by", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "checksum", name="uq_intake_org_checksum"))
    op.create_index("ix_intake_batches_organization_id", "intake_batches", ["organization_id"])
    op.create_table("transfer_provenance",
        sa.Column("provenance_id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.organization_id"), nullable=False),
        sa.Column("transfer_id", sa.Integer(), sa.ForeignKey("et_transfers.transfer_id"), nullable=False, unique=True),
        sa.Column("batch_id", sa.String(36), sa.ForeignKey("intake_batches.batch_id"), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(40), nullable=False))
    op.create_index("ix_transfer_provenance_organization_id", "transfer_provenance", ["organization_id"])
    op.create_index("ix_transfer_provenance_batch_id", "transfer_provenance", ["batch_id"])


def downgrade():
    op.drop_table("transfer_provenance")
    op.drop_table("intake_batches")
