"""A physical site: the lab, a satellite collection point, or a client farm.

Replaces the free-text ``farm_location`` that used to be repeated on
``et_transfers``, ``opu_sessions`` and ``recipients``. Those text columns are
still there and still hold what the import said, because that is the source
record; ``laboratory_id`` is what new writes and every per-site analysis should
use.

``site_type`` distinguishes the roles a site plays without needing three tables:
the same organisation's "DZF" is both the laboratory and, for most transfers,
the customer.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, CheckConstraint, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import OrganizationScopedMixin

if TYPE_CHECKING:
    from app.models.et_transfer import ETTransfer
    from app.models.opu_session import OPUSession
    from app.models.recipient import Recipient

SITE_TYPES = ("Laboratory", "Satellite", "Farm", "Customer")


class Laboratory(OrganizationScopedMixin, Base):
    __tablename__ = "laboratories"

    laboratory_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(32))
    site_type: Mapped[Optional[str]] = mapped_column(String(20))

    address: Mapped[Optional[str]] = mapped_column(Text)
    city: Mapped[Optional[str]] = mapped_column(String(120))
    country: Mapped[Optional[str]] = mapped_column(String(120))

    contact_name: Mapped[Optional[str]] = mapped_column(String(200))
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50))
    contact_email: Mapped[Optional[str]] = mapped_column(String(200))

    # Deactivated rather than deleted: a site with history behind it cannot be
    # removed without orphaning transfers, so it is hidden from pickers instead.
    active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    transfers: Mapped[list["ETTransfer"]] = relationship(back_populates="laboratory")
    opu_sessions: Mapped[list["OPUSession"]] = relationship(back_populates="laboratory")
    recipients: Mapped[list["Recipient"]] = relationship(back_populates="laboratory")

    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_laboratories_org_name"),
        CheckConstraint(
            "site_type IS NULL OR site_type IN ('Laboratory', 'Satellite', 'Farm', 'Customer')",
            name="ck_laboratories_site_type",
        ),
    )
