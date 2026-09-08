from sqlalchemy import ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.models.mixins import OrganizationScopedMixin


class LiteratureChunk(OrganizationScopedMixin, Base):
    __tablename__ = "literature_chunks"
    chunk_id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("literature_documents.document_id", ondelete="CASCADE"), index=True)
    passage_number: Mapped[int] = mapped_column()
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    embedding_model: Mapped[str] = mapped_column(String(200))
    embedding: Mapped[list] = mapped_column(JSON)
    __table_args__ = (UniqueConstraint("document_id", "passage_number", "embedding_model", name="uq_literature_chunk_model"),)
