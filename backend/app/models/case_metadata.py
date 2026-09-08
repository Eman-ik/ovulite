"""Versioned canonical case metadata; does not alter protected model features."""
from datetime import datetime
from sqlalchemy import ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.models.mixins import OrganizationScopedMixin


class CaseMetadata(OrganizationScopedMixin, Base):
    __tablename__ = "case_metadata"
    transfer_id: Mapped[int] = mapped_column(ForeignKey("et_transfers.transfer_id", ondelete="CASCADE"), primary_key=True)
    data: Mapped[dict] = mapped_column(JSON)
    source_type: Mapped[str] = mapped_column(String(40))
    source_reference: Mapped[str] = mapped_column(String(1000))
    version: Mapped[int] = mapped_column(default=1)
    updated_by: Mapped[str] = mapped_column(String(100))
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class CaseAudit(OrganizationScopedMixin, Base):
    __tablename__ = "case_audit"
    audit_id: Mapped[int] = mapped_column(primary_key=True)
    transfer_id: Mapped[int] = mapped_column(index=True)
    action: Mapped[str] = mapped_column(String(40))
    actor: Mapped[str] = mapped_column(String(100))
    details: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
