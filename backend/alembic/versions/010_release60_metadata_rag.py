"""Canonical case snapshots, attributable audit events and literature vector index."""
from alembic import op
import sqlalchemy as sa

revision = "010_release60_metadata_rag"
down_revision = "009_canonical_intake"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("case_metadata",
        sa.Column("transfer_id", sa.Integer(), sa.ForeignKey("et_transfers.transfer_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.organization_id"), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False), sa.Column("source_type", sa.String(40), nullable=False),
        sa.Column("source_reference", sa.String(1000), nullable=False), sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_by", sa.String(100), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_case_metadata_organization_id", "case_metadata", ["organization_id"])
    op.create_table("case_audit",
        sa.Column("audit_id", sa.Integer(), primary_key=True), sa.Column("transfer_id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.organization_id"), nullable=False),
        sa.Column("action", sa.String(40), nullable=False), sa.Column("actor", sa.String(100), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_case_audit_organization_id", "case_audit", ["organization_id"])
    op.create_index("ix_case_audit_transfer_id", "case_audit", ["transfer_id"])
    op.create_table("literature_chunks",
        sa.Column("chunk_id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.organization_id"), nullable=False),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("literature_documents.document_id", ondelete="CASCADE"), nullable=False),
        sa.Column("passage_number", sa.Integer(), nullable=False), sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False), sa.Column("embedding_model", sa.String(200), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=False),
        sa.UniqueConstraint("document_id", "passage_number", "embedding_model", name="uq_literature_chunk_model"))
    op.create_index("ix_literature_chunks_organization_id", "literature_chunks", ["organization_id"])
    op.create_index("ix_literature_chunks_document_id", "literature_chunks", ["document_id"])


def downgrade():
    op.drop_table("literature_chunks")
    op.drop_table("case_audit")
    op.drop_table("case_metadata")
