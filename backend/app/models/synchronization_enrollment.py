"""A recipient placed on a synchronization protocol, starting on a date.

This is the row that turns a protocol template into an actual schedule: each
``ProtocolStep`` becomes a due date of ``start_date + step.day_offset``. The
schedule itself is never stored — materialising it would mean rewriting every
enrollment's rows whenever a protocol's steps are corrected, and the two would
drift apart the first time that was missed.

Enrollment hangs off the *recipient*, not a transfer, for the same reason
``recipient_evaluations`` does: most animals are synchronised, and only some
go on to receive an embryo. Tying synchronisation to a transfer would erase
every animal that was prepared and not used, which is precisely the
denominator "how many did we synchronise to get this many transfers?" needs.
"""

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, Date, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import OrganizationScopedMixin

if TYPE_CHECKING:
    from app.models.et_transfer import ETTransfer
    from app.models.protocol import Protocol
    from app.models.protocol_log import ProtocolLog
    from app.models.recipient import Recipient
    from app.models.technician import Technician

# "Withdrawn" covers an animal pulled mid-protocol (illness, a missed
# treatment); "Completed" means the schedule ran to its end whether or not a
# transfer resulted. Keeping them distinct is what makes drop-out visible.
ENROLLMENT_STATUSES = ("Active", "Completed", "Withdrawn")


class SynchronizationEnrollment(OrganizationScopedMixin, Base):
    __tablename__ = "synchronization_enrollments"

    enrollment_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    recipient_id: Mapped[int] = mapped_column(
        ForeignKey("recipients.recipient_id"), nullable=False, index=True
    )
    protocol_id: Mapped[int] = mapped_column(
        ForeignKey("protocols.protocol_id"), nullable=False, index=True
    )

    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="Active")
    withdrawn_reason: Mapped[Optional[str]] = mapped_column(Text)

    technician_id: Mapped[Optional[int]] = mapped_column(ForeignKey("technicians.technician_id"))

    # Set when the enrollment results in a transfer. Null on an active
    # enrollment, and on one that finished without a transfer.
    transfer_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("et_transfers.transfer_id"), index=True
    )

    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    recipient: Mapped["Recipient"] = relationship(back_populates="enrollments")
    protocol: Mapped["Protocol"] = relationship(back_populates="enrollments")
    technician: Mapped[Optional["Technician"]] = relationship()
    transfer: Mapped[Optional["ETTransfer"]] = relationship(back_populates="enrollments")
    logs: Mapped[list["ProtocolLog"]] = relationship(
        back_populates="enrollment", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('Active', 'Completed', 'Withdrawn')",
            name="ck_synchronization_enrollments_status",
        ),
    )
