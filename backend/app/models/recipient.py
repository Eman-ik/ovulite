from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import OrganizationScopedMixin

if TYPE_CHECKING:
    from app.models.laboratory import Laboratory
    from app.models.et_transfer import ETTransfer
    from app.models.recipient_evaluation import RecipientEvaluation
    from app.models.synchronization_enrollment import SynchronizationEnrollment


class Recipient(OrganizationScopedMixin, Base):
    __tablename__ = "recipients"

    recipient_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tag_id: Mapped[str] = mapped_column(String(50), nullable=False)
    # Kept as the imported source record. New writes set laboratory_id;
    # see app/models/laboratory.py.
    farm_location: Mapped[Optional[str]] = mapped_column(String(200))
    laboratory_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("laboratories.laboratory_id"), index=True
    )
    cow_or_heifer: Mapped[Optional[str]] = mapped_column(String(20))

    # ── Animal profile ──
    breed: Mapped[Optional[str]] = mapped_column(String(100))

    # Date of birth rather than an age column: a stored age is wrong the day
    # after it is written. Age is derived on read (see `age_years`).
    birth_date: Mapped[Optional[date]] = mapped_column(Date)

    # Completed calvings. 0 is meaningful (a heifer), so this is not nullable
    # -as-zero — null means "not recorded".
    parity: Mapped[Optional[int]] = mapped_column(Integer)

    reproductive_status: Mapped[Optional[str]] = mapped_column(String(30))
    reproductive_disorders: Mapped[Optional[str]] = mapped_column(Text)

    previous_ai_count: Mapped[Optional[int]] = mapped_column(Integer)
    previous_et_count: Mapped[Optional[int]] = mapped_column(Integer)

    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    laboratory: Mapped[Optional["Laboratory"]] = relationship(back_populates="recipients")
    transfers: Mapped[list["ETTransfer"]] = relationship(back_populates="recipient")
    evaluations: Mapped[list["RecipientEvaluation"]] = relationship(
        back_populates="recipient", cascade="all, delete-orphan"
    )
    enrollments: Mapped[list["SynchronizationEnrollment"]] = relationship(
        back_populates="recipient", cascade="all, delete-orphan"
    )

    @property
    def age_years(self) -> float | None:
        """Age today, derived from birth_date so it cannot go stale."""
        if self.birth_date is None:
            return None
        return round((date.today() - self.birth_date).days / 365.25, 1)

    __table_args__ = (
        CheckConstraint(
            "cow_or_heifer IN ('Cow', 'Heifer')",
            name="ck_recipients_cow_or_heifer",
        ),
        CheckConstraint("parity >= 0", name="ck_recipients_parity_non_negative"),
        CheckConstraint(
            "reproductive_status IN ('Cycling', 'Anestrus', 'Pregnant', 'Open', 'Culled')",
            name="ck_recipients_reproductive_status",
        ),
        # tag_id is unique per organization AND farm, not org-wide — the same
        # tag number is legitimately reused for a different physical animal
        # at a different farm (see scripts/ingest_et_data.py's
        # get_or_create_recipient, which has always matched this way).
        UniqueConstraint(
            "organization_id", "tag_id", "laboratory_id", name="uq_recipients_org_tag_lab"
        ),
    )
