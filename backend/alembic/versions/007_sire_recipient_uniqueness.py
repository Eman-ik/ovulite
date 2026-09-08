"""Add per-organization uniqueness for sires.name; per-org+farm for
recipients.tag_id.

Migration 005 made donors.tag_id/technicians.name/protocols.name unique
per-organization but missed sires and recipients — those two entities had
no uniqueness constraint at all (not even the old global one). sires.name
had no duplicates, so it gets the same UNIQUE(organization_id, name)
treatment as donors/technicians/protocols.

recipients.tag_id is different: scripts/ingest_et_data.py's
get_or_create_recipient() has always matched on tag_id **+ farm_location**
("Recipients may share tag IDs across farms" — its own comment), because
the same tag number can legitimately be reused for a different physical
animal at a different farm. 10 tag_id values were initially found
"duplicated" within the same org and mistakenly merged as if they were an
import bug — but every one of those pairs' transfers turned out to span
two different farm_locations, confirming the cross-farm reuse is real, not
a duplicate. The merge was reverted (split back into separate recipient
rows, transfers re-pointed to whichever row matches their own
farm_location) before this migration adds the *correct* constraint:
UNIQUE(organization_id, tag_id, farm_location) — matching the import
script's actual matching key, not a stricter org-wide one that would have
broken legitimate cross-farm tag reuse going forward.

Revision ID: 007_sire_recipient_uniqueness
Revises: 006_opu_ivf_batch
"""

import sqlalchemy as sa
from alembic import op

revision = "007_sire_recipient_uniqueness"
down_revision = "006_opu_ivf_batch"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_sires_org_name", "sires", ["organization_id", "name"]
    )
    op.create_unique_constraint(
        "uq_recipients_org_tag_id_farm",
        "recipients",
        ["organization_id", "tag_id", "farm_location"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_recipients_org_tag_id_farm", "recipients", type_="unique")
    op.drop_constraint("uq_sires_org_name", "sires", type_="unique")
