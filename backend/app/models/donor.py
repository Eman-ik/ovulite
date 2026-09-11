from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, Integer, CheckConstraint, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import OrganizationScopedMixin

if TYPE_CHECKING:
    from app.models.embryo import Embryo
    from app.models.opu_session import OPUSession


class Donor(OrganizationScopedMixin, Base):
    __tablename__ = "donors"

    donor_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tag_id: Mapped[str] = mapped_column(String(50), nullable=False)
    breed: Mapped[Optional[str]] = mapped_column(String(100))
    birth_weight_epd: Mapped[Optional[Decimal]] = mapped_column()
    # Date of birth rather than an age column, for the same reason as
    # Recipient: a stored age is wrong the day after it is written.
    birth_date: Mapped[Optional[date]] = mapped_column(Date)
    parity: Mapped[Optional[int]] = mapped_column(Integer)
    reproductive_status: Mapped[Optional[str]] = mapped_column(String(30))
    reproductive_history: Mapped[Optional[str]] = mapped_column(Text)

    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    embryos: Mapped[list["Embryo"]] = relationship(back_populates="donor")
    opu_sessions: Mapped[list["OPUSession"]] = relationship(back_populates="donor")

    @property
    def age_years(self) -> float | None:
        """Age today, derived so it cannot go stale."""
        if self.birth_date is None:
            return None
        return round((date.today() - self.birth_date).days / 365.25, 1)

    __table_args__ = (
        # tag_id is unique per organization, not globally — two organizations
        # may each have their own donor tagged e.g. "D1".
        UniqueConstraint("organization_id", "tag_id", name="uq_donors_org_tag_id"),
    )
