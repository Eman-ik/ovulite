"""Pre-transfer assessment of a recipient.

Deliberately hangs off ``recipients``, not ``et_transfers``. CL and uterine
findings are recorded to decide *whether* to transfer, so tying them to a
transfer would make every screened-and-rejected animal unrecordable — and
those are exactly the rows needed to measure how well screening works.
``transfer_id`` is set afterwards only when the evaluation led to a transfer.

``eligibility`` stores the veterinarian's own judgement. Ovulite deliberately
does not compute it: the local data shows only a weak, non-monotone
relationship between CL diameter and outcome (14-15.8 mm is the best band at
36.4%, but 16-17.5 mm falls back to 26.4% on n=72), which is not a basis for
an automated classifier. Recording the human decision instead leaves open the
more useful question — whether that judgement predicts outcome at all.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
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
    from app.models.et_transfer import ETTransfer
    from app.models.recipient import Recipient
    from app.models.technician import Technician

ELIGIBILITY_VALUES = ("Excellent", "Acceptable", "Not Recommended")
QUALITY_VALUES = ("Good", "Fair", "Poor")


class RecipientEvaluation(OrganizationScopedMixin, Base):
    __tablename__ = "recipient_evaluations"

    evaluation_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    recipient_id: Mapped[int] = mapped_column(
        ForeignKey("recipients.recipient_id"), nullable=False, index=True
    )
    evaluation_date: Mapped[date] = mapped_column(Date, nullable=False)
    technician_id: Mapped[Optional[int]] = mapped_column(ForeignKey("technicians.technician_id"))

    # ── Corpus luteum ──
    cl_present: Mapped[Optional[bool]] = mapped_column(Boolean)
    cl_side: Mapped[Optional[str]] = mapped_column(String(10))
    cl_diameter_mm: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    cl_quality: Mapped[Optional[str]] = mapped_column(String(10))

    # ── Ovarian and uterine findings ──
    follicle_count: Mapped[Optional[int]] = mapped_column(Integer)
    largest_follicle_mm: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    uterine_tone: Mapped[Optional[str]] = mapped_column(String(10))

    # Optional lab value; most programmes will not have it for every animal.
    progesterone_ng_ml: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 3))

    body_condition_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 1))

    eligibility: Mapped[Optional[str]] = mapped_column(String(20))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Set only if this evaluation resulted in a transfer. Null means the animal
    # was assessed and not used — a row that is meaningless to lose.
    transfer_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("et_transfers.transfer_id"), index=True
    )

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    recipient: Mapped["Recipient"] = relationship(back_populates="evaluations")
    technician: Mapped[Optional["Technician"]] = relationship()
    transfer: Mapped[Optional["ETTransfer"]] = relationship(back_populates="evaluations")

    __table_args__ = (
        CheckConstraint(
            "eligibility IN ('Excellent', 'Acceptable', 'Not Recommended')",
            name="ck_recipient_evaluations_eligibility",
        ),
        CheckConstraint(
            "cl_quality IN ('Good', 'Fair', 'Poor')",
            name="ck_recipient_evaluations_cl_quality",
        ),
        CheckConstraint(
            "uterine_tone IN ('Good', 'Fair', 'Poor')",
            name="ck_recipient_evaluations_uterine_tone",
        ),
        CheckConstraint(
            "cl_side IN ('Left', 'Right')",
            name="ck_recipient_evaluations_cl_side",
        ),
    )
