"""Pregnancy diagnoses over the life of a transfer.

A child table rather than more ``pc3_result``/``pc4_result`` columns on
``et_transfers``: the number of checks is open-ended (day 28, 45, 60, and
whatever a programme adds), and each carries its own date, method and
operator. Widening the parent row for each new checkpoint would lose all of
that and require a migration every time practice changes.

Separating the checks is what makes *pregnancy retention* measurable —
pregnant at day 28 but open at day 60 is a loss, which a single pc1 column
cannot express and which the funnel previously had to leave blank.

``et_transfers.pc1_result`` stays as the maintained denormalised view of the
earliest check, because the dashboard, research, analytics and ML feature
paths all read it. The write path here keeps it in sync; it is not a second
source of truth.
"""

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, Date, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import OrganizationScopedMixin

if TYPE_CHECKING:
    from app.models.et_transfer import ETTransfer
    from app.models.technician import Technician

# "Recheck" is a real clinical outcome (inconclusive, re-examine), distinct
# from a missing result. "Lost" records a pregnancy confirmed earlier and
# absent now — the event pregnancy retention is built from.
CHECK_RESULTS = ("Pregnant", "Open", "Recheck", "Lost")
CHECK_METHODS = ("Ultrasound", "Rectal Palpation", "Blood Test", "Other")


class PregnancyCheck(OrganizationScopedMixin, Base):
    __tablename__ = "pregnancy_checks"

    check_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    transfer_id: Mapped[int] = mapped_column(
        ForeignKey("et_transfers.transfer_id"), nullable=False, index=True
    )
    check_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Stored rather than derived from check_date - et_date so that a check
    # recorded against a transfer with a missing et_date is still usable, and
    # so historical rows keep the offset they were actually scheduled at.
    days_post_transfer: Mapped[Optional[int]] = mapped_column()

    result: Mapped[str] = mapped_column(String(20), nullable=False)
    method: Mapped[Optional[str]] = mapped_column(String(30))
    technician_id: Mapped[Optional[int]] = mapped_column(ForeignKey("technicians.technician_id"))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    transfer: Mapped["ETTransfer"] = relationship(back_populates="pregnancy_checks")
    technician: Mapped[Optional["Technician"]] = relationship()

    __table_args__ = (
        CheckConstraint(
            "result IN ('Pregnant', 'Open', 'Recheck', 'Lost')",
            name="ck_pregnancy_checks_result",
        ),
        CheckConstraint(
            "method IN ('Ultrasound', 'Rectal Palpation', 'Blood Test', 'Other')",
            name="ck_pregnancy_checks_method",
        ),
        # One diagnosis per transfer per day. Re-examining the same animal
        # twice in one day is a correction, not a second data point.
        UniqueConstraint("transfer_id", "check_date", name="uq_pregnancy_checks_transfer_date"),
    )
