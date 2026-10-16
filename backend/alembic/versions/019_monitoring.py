"""Model monitoring and retrain decisions (Module 7).

Two tables behind /monitoring:

``model_metrics`` holds one rolling-performance snapshot per organization, per
model version, per evaluation window, per day — Brier, ROC-AUC, PR-AUC and
win-rate measured over predictions whose outcome has since resolved. Drift is
detected by comparing a new snapshot against recent history, so the history is
the point: these rows accumulate and are never pruned by the application.

``retrain_jobs`` is the decision log. When drift is detected the API records
*why*, and an admin acknowledges it. Nothing retrains automatically — the row
exists so a retrain is traceable to the evidence that prompted it.

Both are organization-scoped. The snapshots summarise one organization's own
outcomes, so pooling them would leak clinical performance between tenants and
make a daily snapshot ambiguous about whose data it describes.

The unique constraint on model_metrics matters: the API updates the day's row
in place, so without it two concurrent runs insert duplicates and that day is
double-counted in the baseline the drift check compares against.

Revision ID: 019_monitoring
Revises: 018_embryo_ai_assessment
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "019_monitoring"
down_revision = "018_embryo_ai_assessment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_metrics",
        sa.Column("metric_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=False),
        sa.Column("window_label", sa.String(length=20), nullable=True),
        sa.Column("brier_score", sa.Numeric(6, 4), nullable=True),
        sa.Column("roc_auc", sa.Numeric(6, 4), nullable=True),
        sa.Column("pr_auc", sa.Numeric(6, 4), nullable=True),
        sa.Column("win_rate", sa.Numeric(6, 4), nullable=True),
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.organization_id"]),
        sa.PrimaryKeyConstraint("metric_id"),
        sa.UniqueConstraint(
            "organization_id",
            "model_version",
            "window_label",
            "metric_date",
            name="uq_model_metrics_org_version_window_date",
        ),
    )
    op.create_index("ix_model_metrics_organization_id", "model_metrics", ["organization_id"])
    # The drift baseline reads the most recent snapshots for one org and model
    # version, ordered by date.
    op.create_index(
        "ix_model_metrics_org_version_date",
        "model_metrics",
        ["organization_id", "model_version", "metric_date"],
    )

    op.create_table(
        "retrain_jobs",
        sa.Column("job_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="PENDING"),
        sa.Column("triggered_by", sa.String(length=20), nullable=False, server_default="AUTO"),
        sa.Column("drift_details", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("model_version", sa.String(length=100), nullable=True),
        sa.Column("artifact_path", sa.String(length=500), nullable=True),
        sa.Column("triggered_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.organization_id"]),
        sa.PrimaryKeyConstraint("job_id"),
        sa.CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'COMPLETE', 'FAILED')",
            name="ck_retrain_jobs_status",
        ),
        sa.CheckConstraint(
            "triggered_by IN ('AUTO', 'MANUAL')",
            name="ck_retrain_jobs_triggered_by",
        ),
    )
    op.create_index("ix_retrain_jobs_organization_id", "retrain_jobs", ["organization_id"])
    # The rate limit looks up the newest open job for one org and model version.
    op.create_index(
        "ix_retrain_jobs_org_version_status",
        "retrain_jobs",
        ["organization_id", "model_version", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_retrain_jobs_org_version_status", table_name="retrain_jobs")
    op.drop_index("ix_retrain_jobs_organization_id", table_name="retrain_jobs")
    op.drop_table("retrain_jobs")
    op.drop_index("ix_model_metrics_org_version_date", table_name="model_metrics")
    op.drop_index("ix_model_metrics_organization_id", table_name="model_metrics")
    op.drop_table("model_metrics")
