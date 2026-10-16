"""Consolidate user roles to four: admin, embryologist, veterinarian, researcher.

The seven-value vocabulary was never seven jobs:

* organization_admin had exactly admin's permissions — a second word for one
  thing.
* et team is the ET dataset's spelling of veterinarian.
* viewer was researcher with the analysis screens switched off, which is not a
  role anyone does here.

Rows are remapped BEFORE the constraint is tightened, so no existing row can
violate it. The remap is the same mapping normalize_role() applies in
app/auth/dependencies.py, so a row and a token written before this migration
authorise exactly what they did before.

Downgrade restores the old constraint but does NOT restore the old values: the
remap is lossy (viewer and researcher are now indistinguishable). Downgrading
is for a schema rollback, not a data rollback.

Revision ID: 021_four_roles
Revises: 020_account_security
"""

from alembic import op

revision = "021_four_roles"
down_revision = "020_account_security"
branch_labels = None
depends_on = None

_REMAP = {
    "organization_admin": "admin",
    "et team": "veterinarian",
    "viewer": "researcher",
}

_OLD_ROLES = (
    "admin", "veterinarian", "embryologist", "viewer", "et team",
    "organization_admin", "researcher",
)
_NEW_ROLES = ("admin", "embryologist", "veterinarian", "researcher")


def _in(values) -> str:
    return ", ".join(f"'{v}'" for v in values)


def upgrade() -> None:
    op.drop_constraint("ck_users_role", "users", type_="check")

    for old, new in _REMAP.items():
        op.execute(f"UPDATE users SET role = '{new}' WHERE role = '{old}'")
        op.execute(f"UPDATE organization_memberships SET role = '{new}' WHERE role = '{old}'")

    op.create_check_constraint("ck_users_role", "users", f"role IN ({_in(_NEW_ROLES)})")


def downgrade() -> None:
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.create_check_constraint("ck_users_role", "users", f"role IN ({_in(_OLD_ROLES)})")
