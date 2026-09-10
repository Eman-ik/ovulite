"""The terminal outcome of a transfer.

Kept separate from ``pregnancy_checks`` because calving is a different kind of
event: a check observes an ongoing state and may be repeated, whereas calving
happens once and ends the pregnancy. Folding both into one table would mean a
``result`` column whose allowed values depend on a type discriminator, and a
"latest check" query that has to know to exclude the terminal row.

This is the table that makes **live birth rate** computable. Until it has
rows, the reproductive funnel's final stage stays explicitly "not tracked"
rather than showing a fabricated zero.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import OrganizationScopedMixin

if TYPE_CHECKING:
    from app.models.et_transfer import ETTransfer

# Abortion and stillbirth are recorded distinctly: both end the pregnancy
# without a live calf, but they fail at different stages and have different
# causes, so collapsing them would hide which one a programme has.
CALVING_OUTCOMES = ("Live Birth", "Stillbirth", "Abortion")
CALF_SEXES = ("Male", "Female", "Unknown")


class CalvingRecord(OrganizationScopedMixin, Base):
    __tablename__ = "calving_records"

    calving_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    transfer_id: Mapped[int] = mapped_column(
        ForeignKey("et_transfers.transfer_id"), nullable=False, index=True
    )
    calving_date: Mapped[date] = mapped_column(Date, nullable=False)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)

    calf_sex: Mapped[Optional[str]] = mapped_column(String(10))
    calf_weight_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    gestation_days: Mapped[Optional[int]] = mapped_column()
    assisted: Mapped[Optional[bool]] = mapped_column()
    notes: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    transfer: Mapped["ETTransfer"] = relationship(back_populates="calving_record")

    __table_args__ = (
        CheckConstraint(
            "outcome IN ('Live Birth', 'Stillbirth', 'Abortion')",
            name="ck_calving_records_outcome",
        ),
        CheckConstraint(
            "calf_sex IN ('Male', 'Female', 'Unknown')",
            name="ck_calving_records_calf_sex",
        ),
        # A transfer produces at most one calving event. Twins are recorded on
        # the single row (notes/weight); a second row would double-count the
        # transfer in every rate that uses this table as a denominator.
        UniqueConstraint("transfer_id", name="uq_calving_records_transfer"),
    )
