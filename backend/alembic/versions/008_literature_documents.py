"""Add an organization-scoped literature corpus."""
from alembic import op
import sqlalchemy as sa

revision = "008_literature_documents"
down_revision = "007_sire_recipient_uniqueness"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("literature_documents",
        sa.Column("document_id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.organization_id"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("authors", sa.String(1000), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("source_url", sa.String(2000), nullable=False),
        sa.Column("source_kind", sa.String(30), nullable=False),
        sa.Column("rights", sa.String(1000), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("created_by", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "checksum", name="uq_literature_org_checksum"))
    op.create_index("ix_literature_documents_organization_id", "literature_documents", ["organization_id"])


def downgrade():
    op.drop_table("literature_documents")
