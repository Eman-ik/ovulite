"""Add the researcher/data-analyst role to the users role vocabulary.

Ovulite's four operational roles are admin, embryologist, veterinarian and
researcher. The first three already existed; `researcher` is the read-only
analysis role that owns advanced analytics, model evaluation and exports.

`role` is guarded by a CHECK constraint rather than an enum type, so widening
it is a constraint swap.
"""

from alembic import op

revision = "012_researcher_role"
down_revision = "011_intake_governance"
branch_labels = None
depends_on = None

_ROLES_WITH_RESEARCHER = (
    "role IN ('admin', 'veterinarian', 'embryologist', 'viewer', "
    "'et team', 'organization_admin', 'researcher')"
)
_ROLES_WITHOUT_RESEARCHER = (
    "role IN ('admin', 'veterinarian', 'embryologist', 'viewer', "
    "'et team', 'organization_admin')"
)


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("ck_users_role", type_="check")
        batch_op.create_check_constraint("ck_users_role", _ROLES_WITH_RESEARCHER)


def downgrade() -> None:
    # Researchers have no clinical write access, so there is nothing to
    # reassign — but the constraint cannot be narrowed while rows still use
    # the role, so demote them to viewer (the nearest read-only equivalent).
    op.execute("UPDATE users SET role = 'viewer' WHERE role = 'researcher'")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("ck_users_role", type_="check")
        batch_op.create_check_constraint("ck_users_role", _ROLES_WITHOUT_RESEARCHER)
