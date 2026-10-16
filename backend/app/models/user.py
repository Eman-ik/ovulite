from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, false, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    organization_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("organizations.organization_id")
    )
    username: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Optional[str]] = mapped_column(String(50))
    full_name: Mapped[Optional[str]] = mapped_column(String(200))
    email: Mapped[Optional[str]] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(Boolean, server_default="true")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    last_login: Mapped[Optional[datetime]] = mapped_column()

    # ── Account security (migration 020) ──────────────────────────────────
    # Brute-force protection: too many wrong passwords locks the account for a
    # while. Counted per account; app/api/auth.py adds a per-IP ceiling, since
    # a lockout on one account does not stop one client walking through many.
    failed_login_count: Mapped[int] = mapped_column(Integer, server_default="0", default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column()

    # Forgot-password. Only the SHA-256 of the token is stored, so a leaked
    # row cannot be used to reset anyone's password.
    reset_token: Mapped[Optional[str]] = mapped_column(String(255))
    reset_token_expires: Mapped[Optional[datetime]] = mapped_column()

    # Self-registered accounts wait for an admin before they can log in.
    pending_approval: Mapped[bool] = mapped_column(Boolean, server_default=false(), default=False)
    approved_by: Mapped[Optional[str]] = mapped_column(String(100))
    approved_at: Mapped[Optional[datetime]] = mapped_column()

    # Temporary passwords: the user must choose their own before anything else
    # answers. password_changed_at also ends sessions opened with the old one.
    must_change_password: Mapped[bool] = mapped_column(Boolean, server_default=false(), default=False)
    password_changed_at: Mapped[Optional[datetime]] = mapped_column()

    # "Log out everywhere": every token issued before this moment is refused.
    # Set by logout-all, by refresh-token reuse detection, and by deactivation.
    sessions_revoked_at: Mapped[Optional[datetime]] = mapped_column()

    organization = relationship("Organization", back_populates="users")
    memberships = relationship("OrganizationMembership", back_populates="user")

    @property
    def sessions_valid_after(self) -> Optional[datetime]:
        """Tokens issued before this instant are no longer accepted.

        The later of the last password change and the last explicit session
        revocation. Compared naive-to-naive because SQLite and Postgres differ
        on whether they hand back tzinfo.
        """
        stamps = [t for t in (self.password_changed_at, self.sessions_revoked_at) if t is not None]
        return max(stamps, key=lambda t: t.replace(tzinfo=None)) if stamps else None

    __table_args__ = (
        CheckConstraint(
            "role IN ('admin', 'embryologist', 'veterinarian', 'researcher')",
            name="ck_users_role",
        ),
    )
