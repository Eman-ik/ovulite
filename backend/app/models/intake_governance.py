from datetime import datetime
from sqlalchemy import ForeignKey, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.models.mixins import OrganizationScopedMixin


class EmbryoIdentifier(OrganizationScopedMixin, Base):
    __tablename__ = "embryo_identifiers"
    identifier_id: Mapped[int] = mapped_column(primary_key=True)
    identifier: Mapped[str] = mapped_column(String(100))
    embryo_id: Mapped[int] = mapped_column(ForeignKey("embryos.embryo_id"), unique=True)
    __table_args__ = (UniqueConstraint("organization_id", "identifier", name="uq_embryo_identifier_org"),)


class IntakeRevision(OrganizationScopedMixin, Base):
    __tablename__ = "intake_revisions"
    revision_id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[str] = mapped_column(String(36), ForeignKey("intake_batches.batch_id"), index=True)
    actor: Mapped[str] = mapped_column(String(100))
    state: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
