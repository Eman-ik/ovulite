from decimal import Decimal
from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Numeric, CheckConstraint, Date, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import OrganizationScopedMixin

if TYPE_CHECKING:
    from app.models.embryo import Embryo
    from app.models.ivm_batch import IVMBatch
    from app.models.opu_session import OPUSession
    from app.models.sire import Sire
    from app.models.technician import Technician


class IVFBatch(OrganizationScopedMixin, Base):
    """A single laboratory IVF production cycle from one OPU session's oocytes.

    Backfilled rows (see migration 006) are grouped from historical embryo
    records by (opu_id, sire_id). Lab-level counts (oocytes used, cleaved,
    blastocysts) are unknown for those and left null rather than fabricated —
    cleavage_rate/blastocyst_rate are only computed when counts exist.
    """

    __tablename__ = "ivf_batches"

    ivf_batch_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    opu_id: Mapped[int] = mapped_column(ForeignKey("opu_sessions.opu_id"), nullable=False)
    sire_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sires.sire_id"))
    ivf_date: Mapped[Optional[date]] = mapped_column(Date)
    oocytes_used: Mapped[Optional[int]] = mapped_column(Integer)
    mature_oocytes: Mapped[Optional[int]] = mapped_column(Integer)
    cleaved_embryos: Mapped[Optional[int]] = mapped_column(Integer)
    blastocysts: Mapped[Optional[int]] = mapped_column(Integer)
    degenerated_embryos: Mapped[Optional[int]] = mapped_column(Integer)
    culture_media: Mapped[Optional[str]] = mapped_column(String(100))
    embryologist_id: Mapped[Optional[int]] = mapped_column(ForeignKey("technicians.technician_id"))
    # The matured cohort this fertilisation drew from. Nullable because IVM
    # was not recorded separately before migration 015.
    ivm_batch_id: Mapped[Optional[int]] = mapped_column(ForeignKey("ivm_batches.ivm_batch_id"), index=True)

    # Semen identity belongs to the insemination, not the bull: at least one
    # sire in this dataset is used with both conventional and sexed straws,
    # so Sire.semen_type cannot describe an individual batch.
    semen_type: Mapped[Optional[str]] = mapped_column(String(20))
    semen_batch: Mapped[Optional[str]] = mapped_column(String(60))
    sperm_concentration: Mapped[Optional[str]] = mapped_column(String(40))
    fertilization_medium: Mapped[Optional[str]] = mapped_column(String(120))
    fertilization_hours: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))

    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    opu_session: Mapped["OPUSession"] = relationship(back_populates="ivf_batches")
    ivm_batch: Mapped[Optional["IVMBatch"]] = relationship(back_populates="ivf_batches")
    sire: Mapped[Optional["Sire"]] = relationship()
    embryologist: Mapped[Optional["Technician"]] = relationship()
    embryos: Mapped[list["Embryo"]] = relationship(back_populates="ivf_batch")

    __table_args__ = (
        CheckConstraint(
            "semen_type IS NULL OR semen_type IN ('Conventional', 'Sexed')",
            name="ck_ivf_batches_semen_type",
        ),
    )
