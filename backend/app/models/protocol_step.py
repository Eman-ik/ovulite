"""One scheduled treatment in a synchronization protocol.

The template. ``protocols`` previously held only a name — and the names in
this database (``CIDR+GnRH+PGF+GnRH``) encode which drugs are used but not
*when*, so the schedule cannot be recovered from them. These rows have to be
entered by the veterinarian; Ovulite does not guess them, because an invented
treatment day is a clinical instruction, not a cosmetic default.

``day_offset`` is days from the enrollment's start date, zero-based:
``due_date = enrollment.start_date + day_offset``. A protocol a vet writes as
"Day 1 GnRH, Day 7 PGF" is stored as offsets 0 and 6. Zero-based is chosen so
the arithmetic is the same everywhere it appears — a 1-based column invites a
``start_date + day_number`` off-by-one at every call site.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import OrganizationScopedMixin

if TYPE_CHECKING:
    from app.models.protocol import Protocol
    from app.models.protocol_log import ProtocolLog


class ProtocolStep(OrganizationScopedMixin, Base):
    __tablename__ = "protocol_steps"

    step_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    protocol_id: Mapped[int] = mapped_column(
        ForeignKey("protocols.protocol_id"), nullable=False, index=True
    )

    day_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    step_name: Mapped[str] = mapped_column(String(100), nullable=False)
    drug_name: Mapped[Optional[str]] = mapped_column(String(100))
    dosage: Mapped[Optional[str]] = mapped_column(String(50))
    route: Mapped[Optional[str]] = mapped_column(String(30))

    # Marks the step at which transfer is scheduled, so the board can show
    # "eligible for ET" without hard-coding a step name.
    is_transfer_day: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    protocol: Mapped["Protocol"] = relationship(back_populates="steps")
    logs: Mapped[list["ProtocolLog"]] = relationship(back_populates="step")

    __table_args__ = (
        # Two treatments legitimately fall on the same day (the double PGF in
        # several of these protocols), so the day alone is not unique — the
        # day plus the step name is.
        UniqueConstraint(
            "protocol_id", "day_offset", "step_name", name="uq_protocol_steps_protocol_day_name"
        ),
        # Negative offsets are allowed: some programmes record a pre-treatment
        # examination before day 0. A cap keeps a typo from generating a
        # schedule years out.
        CheckConstraint("day_offset BETWEEN -30 AND 365", name="ck_protocol_steps_day_offset"),
    )
