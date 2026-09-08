"""Organization-owned, attributable evidence for Literature Intelligence."""
from datetime import datetime

from sqlalchemy import String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import OrganizationScopedMixin


class LiteratureDocument(OrganizationScopedMixin, Base):
    __tablename__ = "literature_documents"

    document_id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    authors: Mapped[str] = mapped_column(String(1000))
    year: Mapped[int] = mapped_column()
    source_url: Mapped[str] = mapped_column(String(2000))
    source_kind: Mapped[str] = mapped_column(String(30))
    rights: Mapped[str] = mapped_column(String(1000))
    content: Mapped[str] = mapped_column(Text)
    checksum: Mapped[str] = mapped_column(String(64))
    created_by: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (UniqueConstraint("organization_id", "checksum", name="uq_literature_org_checksum"),)
