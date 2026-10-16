"""Account security: lockout, password reset, forced change, signup approval.

Adds the columns behind the hardened /auth routes:

* ``failed_login_count`` / ``locked_until`` — too many wrong passwords locks
  the account for a while (the SRS asked for this; nothing implemented it).
* ``reset_token`` / ``reset_token_expires`` — forgot-password. Only the
  SHA-256 of the token is ever stored.
* ``pending_approval`` / ``approved_by`` / ``approved_at`` — self-registered
  accounts cannot log in until an admin approves them. This closes a real
  hole: before this, ``POST /auth/register`` was unauthenticated and took the
  role straight from the request body, so anyone who could reach the API could
  create themselves an admin account and use it.
* ``must_change_password`` / ``password_changed_at`` — temporary passwords
  must be replaced; changing a password also ends sessions opened with the old
  one.
* ``sessions_revoked_at`` — "log out everywhere".

Deliberately NOT ported from upstream, which has these in the same migration:

* The role CHECK constraint is left alone. Upstream moved to three roles
  (admin / technical_staff / viewer_researcher); this deployment has six and
  ``ck_users_role`` already lists them.
* No ``uq_users_single_admin`` index. Upstream allows exactly one admin row;
  here admins are per-organization, so that index would make a second
  organization impossible to administer.
* No ``audit_events`` table — 016_audit_events already created a richer one.

The backfill only flags a bootstrap admin that has never been used. Several
demo accounts in this deployment share one documented password, and flagging
all of them would lock every demo login behind a password-change screen.
Rotating those is a deliberate operational step, not a migration side effect.

Revision ID: 020_account_security
Revises: 019_monitoring
"""

import sqlalchemy as sa
from alembic import op

revision = "020_account_security"
down_revision = "019_monitoring"
branch_labels = None
depends_on = None


_COLUMNS = (
    ("failed_login_count", sa.Column("failed_login_count", sa.Integer(), nullable=False, server_default="0")),
    ("locked_until", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True)),
    ("reset_token", sa.Column("reset_token", sa.String(255), nullable=True)),
    ("reset_token_expires", sa.Column("reset_token_expires", sa.DateTime(timezone=True), nullable=True)),
    ("pending_approval", sa.Column("pending_approval", sa.Boolean(), nullable=False, server_default=sa.false())),
    ("approved_by", sa.Column("approved_by", sa.String(100), nullable=True)),
    ("approved_at", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True)),
    ("must_change_password", sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false())),
    ("password_changed_at", sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True)),
    ("sessions_revoked_at", sa.Column("sessions_revoked_at", sa.DateTime(timezone=True), nullable=True)),
)


def upgrade() -> None:
    for _name, column in _COLUMNS:
        op.add_column("users", column)

    # A reset token is looked up by its hash on every reset attempt.
    op.create_index("ix_users_reset_token", "users", ["reset_token"])

    # Only an unused bootstrap admin. An admin that has logged in is a real
    # account whose password is the operator's business, and the other seeded
    # demo logins are left alone on purpose (see the note above).
    op.execute(
        "UPDATE users SET must_change_password = true "
        "WHERE username = 'admin' AND last_login IS NULL"
    )


def downgrade() -> None:
    op.drop_index("ix_users_reset_token", table_name="users")
    for name, _column in reversed(_COLUMNS):
        op.drop_column("users", name)
