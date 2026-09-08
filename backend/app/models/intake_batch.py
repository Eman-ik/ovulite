from datetime import datetime
from sqlalchemy import ForeignKey, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.models.mixins import OrganizationScopedMixin


class IntakeBatch(OrganizationScopedMixin, Base):
    __tablename__ = "intake_batches"
    batch_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    filename: Mapped[str] = mapped_column(String(200))
    raw_csv: Mapped[str] = mapped_column(Text)
    checksum: Mapped[str] = mapped_column(String(64))
    source_type: Mapped[str] = mapped_column(String(40))
    source_reference: Mapped[str] = mapped_column(String(1000))
    mapping: Mapped[dict] = mapped_column(JSON)
    report: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="preview")
    created_by: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    __table_args__ = (UniqueConstraint("organization_id", "checksum", name="uq_intake_org_checksum"),)


class TransferProvenance(OrganizationScopedMixin, Base):
    __tablename__ = "transfer_provenance"
    provenance_id: Mapped[int] = mapped_column(primary_key=True)
    transfer_id: Mapped[int] = mapped_column(ForeignKey("et_transfers.transfer_id"), unique=True)
    batch_id: Mapped[str] = mapped_column(String(36), ForeignKey("intake_batches.batch_id"), index=True)
    source_row: Mapped[int] = mapped_column()
    source_type: Mapped[str] = mapped_column(String(40))
