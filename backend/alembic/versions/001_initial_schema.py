"""Initial schema — 12 tables + canonical ET features view

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-02-26

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── donors ──
    op.create_table(
        "donors",
        sa.Column("donor_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("tag_id", sa.String(50), nullable=False, unique=True),
        sa.Column("breed", sa.String(100)),
        sa.Column("birth_weight_epd", sa.Numeric(6, 2)),
        sa.Column("notes", sa.Text),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # ── sires ──
    op.create_table(
        "sires",
        sa.Column("sire_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("breed", sa.String(100)),
        sa.Column("birth_weight_epd", sa.Numeric(6, 2)),
        sa.Column("semen_type", sa.String(50)),
        sa.Column("notes", sa.Text),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "semen_type IN ('Conventional', 'Sexed', 'Unknown')",
            name="ck_sires_semen_type",
        ),
    )

    # ── recipients ──
    op.create_table(
        "recipients",
        sa.Column(
            "recipient_id", sa.Integer, primary_key=True, autoincrement=True
        ),
        sa.Column("tag_id", sa.String(50), nullable=False),
        sa.Column("farm_location", sa.String(200)),
        sa.Column("cow_or_heifer", sa.String(20)),
        sa.Column("notes", sa.Text),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "cow_or_heifer IN ('Cow', 'Heifer')",
            name="ck_recipients_cow_or_heifer",
        ),
    )

    # ── technicians ──
    op.create_table(
        "technicians",
        sa.Column(
            "technician_id", sa.Integer, primary_key=True, autoincrement=True
        ),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("role", sa.String(50), server_default="ET Technician"),
        sa.Column("active", sa.Boolean, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # ── protocols ──
    op.create_table(
        "protocols",
        sa.Column(
            "protocol_id", sa.Integer, primary_key=True, autoincrement=True
        ),
        sa.Column("name", sa.String(200), nullable=False, unique=True),
        sa.Column("description", sa.Text),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # ── embryos ──
    op.create_table(
        "embryos",
        sa.Column("embryo_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "donor_id", sa.Integer, sa.ForeignKey("donors.donor_id")
        ),
        sa.Column(
            "sire_id", sa.Integer, sa.ForeignKey("sires.sire_id")
        ),
        sa.Column("opu_date", sa.Date),
        sa.Column("stage", sa.Integer),
        sa.Column("grade", sa.Integer),
        sa.Column("fresh_or_frozen", sa.String(20)),
        sa.Column("cane_number", sa.String(50)),
        sa.Column("freezing_date", sa.Date),
        sa.Column("ai_grade", sa.Integer),
        sa.Column("ai_viability", sa.Numeric(5, 4)),
        sa.Column("notes", sa.Text),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("stage BETWEEN 1 AND 9", name="ck_embryos_stage"),
        sa.CheckConstraint("grade BETWEEN 1 AND 4", name="ck_embryos_grade"),
        sa.CheckConstraint(
            "fresh_or_frozen IN ('Fresh', 'Frozen')",
            name="ck_embryos_fresh_or_frozen",
        ),
    )

    # ── et_transfers ──
    op.create_table(
        "et_transfers",
        sa.Column(
            "transfer_id", sa.Integer, primary_key=True, autoincrement=True
        ),
        sa.Column("et_number", sa.Integer),
        sa.Column("lab", sa.String(50)),
        sa.Column("satellite", sa.String(50)),
        sa.Column("customer_id", sa.String(50)),
        sa.Column("et_date", sa.Date, nullable=False),
        sa.Column("farm_location", sa.String(200)),
        sa.Column(
            "recipient_id",
            sa.Integer,
            sa.ForeignKey("recipients.recipient_id"),
        ),
        sa.Column("bc_score", sa.Numeric(4, 2)),
        sa.Column("cl_side", sa.String(10)),
        sa.Column("cl_measure_mm", sa.Numeric(5, 1)),
        sa.Column(
            "protocol_id",
            sa.Integer,
            sa.ForeignKey("protocols.protocol_id"),
        ),
        sa.Column("heat_observed", sa.Boolean),
        sa.Column("heat_day", sa.Integer),
        sa.Column(
            "embryo_id", sa.Integer, sa.ForeignKey("embryos.embryo_id")
        ),
        sa.Column(
            "technician_id",
            sa.Integer,
            sa.ForeignKey("technicians.technician_id"),
        ),
        sa.Column("assistant_name", sa.String(100)),
        sa.Column("pc1_date", sa.Date),
        sa.Column("pc1_result", sa.String(20)),
        sa.Column("pc2_date", sa.Date),
        sa.Column("pc2_result", sa.String(20)),
        sa.Column("fetal_sexing", sa.String(20)),
        sa.Column("days_in_pregnancy", sa.Integer),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "pc1_result IN ('Pregnant', 'Open', 'Recheck') OR pc1_result IS NULL",
            name="ck_et_transfers_pc1_result",
        ),
    )

    # ── embryo_images ──
    op.create_table(
        "embryo_images",
        sa.Column("image_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "embryo_id", sa.Integer, sa.ForeignKey("embryos.embryo_id")
        ),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("file_hash", sa.String(64)),
        sa.Column("width_px", sa.Integer),
        sa.Column("height_px", sa.Integer),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column("notes", sa.Text),
    )

    # ── protocol_logs ──
    op.create_table(
        "protocol_logs",
        sa.Column("log_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "transfer_id",
            sa.Integer,
            sa.ForeignKey("et_transfers.transfer_id"),
        ),
        sa.Column(
            "protocol_id",
            sa.Integer,
            sa.ForeignKey("protocols.protocol_id"),
        ),
        sa.Column("step_name", sa.String(100)),
        sa.Column("step_date", sa.Date),
        sa.Column("drug_name", sa.String(100)),
        sa.Column("dosage", sa.String(50)),
        sa.Column("notes", sa.Text),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # ── predictions ──
    op.create_table(
        "predictions",
        sa.Column(
            "prediction_id", sa.Integer, primary_key=True, autoincrement=True
        ),
        sa.Column(
            "transfer_id",
            sa.Integer,
            sa.ForeignKey("et_transfers.transfer_id"),
        ),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("model_version", sa.String(50)),
        sa.Column("probability", sa.Numeric(5, 4), nullable=False),
        sa.Column("confidence_lower", sa.Numeric(5, 4)),
        sa.Column("confidence_upper", sa.Numeric(5, 4)),
        sa.Column("risk_band", sa.String(20)),
        sa.Column("shap_json", sa.JSON),
        sa.Column(
            "predicted_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # ── anomalies ──
    op.create_table(
        "anomalies",
        sa.Column(
            "anomaly_id", sa.Integer, primary_key=True, autoincrement=True
        ),
        sa.Column("anomaly_type", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(50)),
        sa.Column("entity_id", sa.String(100)),
        sa.Column("severity", sa.String(20)),
        sa.Column("description", sa.Text),
        sa.Column("metric_value", sa.Numeric(8, 4)),
        sa.Column("baseline_value", sa.Numeric(8, 4)),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # ── users ──
    op.create_table(
        "users",
        sa.Column("user_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(100), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50)),
        sa.Column("full_name", sa.String(200)),
        sa.Column("email", sa.String(200)),
        sa.Column("active", sa.Boolean, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column("last_login", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "role IN ('admin', 'veterinarian', 'embryologist', 'viewer')",
            name="ck_users_role",
        ),
    )

    # ── Canonical ET features view (from REQUIREMENTS.md §2.2) ──
    op.execute("""
        CREATE VIEW vw_et_features AS
        SELECT
            t.transfer_id,
            t.et_date,
            t.farm_location,

            -- Recipient features
            r.tag_id            AS recipient_tag,
            r.cow_or_heifer,
            t.bc_score,
            t.cl_side,
            t.cl_measure_mm,
            t.heat_observed,
            t.heat_day,

            -- Protocol
            p.name              AS protocol_name,

            -- Embryo features
            e.stage             AS embryo_stage,
            e.grade             AS embryo_grade,
            e.fresh_or_frozen,
            e.opu_date,
            (t.et_date - e.opu_date) AS days_opu_to_et,

            -- Donor features
            d.tag_id            AS donor_tag,
            d.breed             AS donor_breed,
            d.birth_weight_epd  AS donor_bw_epd,

            -- Sire features
            s.name              AS sire_name,
            s.breed             AS sire_breed,
            s.birth_weight_epd  AS sire_bw_epd,
            s.semen_type,

            -- Staff
            tech.name           AS technician_name,
            t.assistant_name,

            -- Target (exclude from features during training!)
            t.pc1_result        AS pregnancy_outcome

        FROM et_transfers t
        LEFT JOIN recipients r   ON t.recipient_id  = r.recipient_id
        LEFT JOIN embryos e      ON t.embryo_id     = e.embryo_id
        LEFT JOIN donors d       ON e.donor_id      = d.donor_id
        LEFT JOIN sires s        ON e.sire_id       = s.sire_id
        LEFT JOIN protocols p    ON t.protocol_id   = p.protocol_id
        LEFT JOIN technicians tech ON t.technician_id = tech.technician_id;
    """)


def downgrade() -> None:
    # Drop view first (references tables)
    op.execute("DROP VIEW IF EXISTS vw_et_features;")

    # Drop tables in reverse FK order
    op.drop_table("users")
    op.drop_table("anomalies")
    op.drop_table("predictions")
    op.drop_table("protocol_logs")
    op.drop_table("embryo_images")
    op.drop_table("et_transfers")
    op.drop_table("embryos")
    op.drop_table("protocols")
    op.drop_table("technicians")
    op.drop_table("recipients")
    op.drop_table("sires")
    op.drop_table("donors")
