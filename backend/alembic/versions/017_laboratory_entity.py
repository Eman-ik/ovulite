"""Promote the free-text site name to a Laboratory entity.

``farm_location`` was a ``String(200)`` repeated on ``et_transfers``,
``opu_sessions`` and ``recipients``, which meant a site had no identity: it could
not carry an address or a contact, could not be renamed without a three-table
UPDATE, and every per-site analysis was a GROUP BY on a string that nothing
stopped from drifting ("DZF" vs "DZF " vs "dzf").

This adds ``laboratories`` and a nullable ``laboratory_id`` on each of the three
tables, backfilled from the distinct values already present. The original text
columns are kept: they are the imported source record, and dropping them would
destroy the only evidence of what a row originally said. New writes should set
``laboratory_id``.

``uq_recipients_org_tag_id_farm`` spans ``farm_location``, so it is rebuilt
against ``laboratory_id`` — otherwise the same tag at the same site could be
inserted twice once callers stop writing the text column.

Revision ID: 017_laboratory_entity
Revises: 016_audit_events
"""

import sqlalchemy as sa
from alembic import op

revision = "017_laboratory_entity"
down_revision = "016_audit_events"
branch_labels = None
depends_on = None

SCOPED = ("et_transfers", "opu_sessions", "recipients")


def upgrade() -> None:
    op.create_table(
        "laboratories",
        sa.Column("laboratory_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=True),
        sa.Column("site_type", sa.String(length=20), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("country", sa.String(length=120), nullable=True),
        sa.Column("contact_name", sa.String(length=200), nullable=True),
        sa.Column("contact_phone", sa.String(length=50), nullable=True),
        sa.Column("contact_email", sa.String(length=200), nullable=True),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.organization_id"]),
        sa.PrimaryKeyConstraint("laboratory_id"),
        sa.UniqueConstraint("organization_id", "name", name="uq_laboratories_org_name"),
        sa.CheckConstraint(
            "site_type IS NULL OR site_type IN ('Laboratory', 'Satellite', 'Farm', 'Customer')",
            name="ck_laboratories_site_type",
        ),
    )
    op.create_index("ix_laboratories_organization_id", "laboratories", ["organization_id"])

    for table in SCOPED:
        op.add_column(table, sa.Column("laboratory_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            f"fk_{table}_laboratory_id", table, "laboratories",
            ["laboratory_id"], ["laboratory_id"],
        )
        op.create_index(f"ix_{table}_laboratory_id", table, ["laboratory_id"])

    # ── Backfill ──
    # Every distinct non-blank site name already recorded, from all three tables
    # plus the transfer's lab/satellite/customer columns, becomes a row. Names
    # are trimmed so trailing whitespace does not create a duplicate site.
    op.execute(
        """
        INSERT INTO laboratories (organization_id, name, site_type, notes)
        SELECT DISTINCT organization_id, btrim(name), 'Laboratory',
               'Created from imported free-text site names by migration 017.'
        FROM (
            SELECT organization_id, farm_location AS name FROM et_transfers
            UNION SELECT organization_id, farm_location FROM opu_sessions
            UNION SELECT organization_id, farm_location FROM recipients
            UNION SELECT organization_id, lab FROM et_transfers
            UNION SELECT organization_id, satellite FROM et_transfers
            UNION SELECT organization_id, customer_id FROM et_transfers
        ) AS sources
        WHERE name IS NOT NULL AND btrim(name) <> ''
        ON CONFLICT (organization_id, name) DO NOTHING
        """
    )

    for table in SCOPED:
        op.execute(
            f"""
            UPDATE {table} AS t
            SET laboratory_id = l.laboratory_id
            FROM laboratories AS l
            WHERE l.organization_id = t.organization_id
              AND l.name = btrim(t.farm_location)
              AND t.farm_location IS NOT NULL
            """
        )

    # The recipient uniqueness rule has to follow the same move, or the pair
    # (tag, site) stops being enforced once callers write only laboratory_id.
    op.drop_constraint("uq_recipients_org_tag_id_farm", "recipients", type_="unique")
    op.create_unique_constraint(
        "uq_recipients_org_tag_lab", "recipients",
        ["organization_id", "tag_id", "laboratory_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_recipients_org_tag_lab", "recipients", type_="unique")
    op.create_unique_constraint(
        "uq_recipients_org_tag_id_farm", "recipients",
        ["organization_id", "tag_id", "farm_location"],
    )
    for table in SCOPED:
        op.drop_index(f"ix_{table}_laboratory_id", table_name=table)
        op.drop_constraint(f"fk_{table}_laboratory_id", table, type_="foreignkey")
        op.drop_column(table, "laboratory_id")
    op.drop_index("ix_laboratories_organization_id", table_name="laboratories")
    op.drop_table("laboratories")
