"""In-vitro maturation of an oocyte cohort, between recovery and fertilisation.

A separate table rather than more columns on ``IVFBatch`` because IVM is its
own procedure with its own medium, incubator conditions and outcome, and
because one matured cohort can be split across more than one fertilisation.
Folding it into the IVF row would force those parameters to be repeated per
split and make them disagree the first time one copy was corrected.

``IVFBatch.mature_oocytes`` stays as the denormalised count the analytics and
dashboard paths already read — the same arrangement as ``pc1_result`` on
transfers. ``mature_oocytes_out`` here is the authoritative figure.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import OrganizationScopedMixin

if TYPE_CHECKING:
    from app.models.ivf_batch import IVFBatch
    from app.models.opu_session import OPUSession
    from app.models.technician import Technician


class IVMBatch(OrganizationScopedMixin, Base):
    __tablename__ = "ivm_batches"

    ivm_batch_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    opu_id: Mapped[int] = mapped_column(
        ForeignKey("opu_sessions.opu_id"), nullable=False, index=True
    )

    ivm_date: Mapped[Optional[date]] = mapped_column(Date)
    medium: Mapped[Optional[str]] = mapped_column(String(120))
    medium_lot: Mapped[Optional[str]] = mapped_column(String(60))
    incubation_hours: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    temperature_c: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 2))
    co2_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 2))
    o2_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 2))

    oocytes_in: Mapped[Optional[int]] = mapped_column(Integer)
    mature_oocytes_out: Mapped[Optional[int]] = mapped_column(Integer)

    embryologist_id: Mapped[Optional[int]] = mapped_column(ForeignKey("technicians.technician_id"))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    opu_session: Mapped["OPUSession"] = relationship(back_populates="ivm_batches")
    embryologist: Mapped[Optional["Technician"]] = relationship()
    ivf_batches: Mapped[list["IVFBatch"]] = relationship(back_populates="ivm_batch")

    __table_args__ = (
        # More matured than were put in is a data-entry error, not a result.
        CheckConstraint(
            "mature_oocytes_out IS NULL OR oocytes_in IS NULL OR mature_oocytes_out <= oocytes_in",
            name="ck_ivm_batches_mature_not_above_input",
        ),
        CheckConstraint("oocytes_in IS NULL OR oocytes_in >= 0", name="ck_ivm_batches_oocytes_in"),
        CheckConstraint(
            "incubation_hours IS NULL OR incubation_hours BETWEEN 0 AND 96",
            name="ck_ivm_batches_incubation_hours",
        ),
    )
