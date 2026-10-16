"""Model performance tracking (Module 7 — Outcome Tracking & Continuous Learning).

Stores rolling performance snapshots (Brier score, ROC-AUC, PR-AUC, win-rate)
for a given model version over a given evaluation window, so drift can be
detected by comparing a new snapshot against recent history.

Rows are organization-scoped. A snapshot summarises one organization's own
resolved outcomes, so pooling them across tenants would both leak clinical
performance between organizations and make the per-day snapshot ambiguous
about whose data it describes.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import OrganizationScopedMixin


class ModelMetric(OrganizationScopedMixin, Base):
    __tablename__ = "model_metrics"

    metric_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    window_label: Mapped[Optional[str]] = mapped_column(String(20))  # e.g. "7d", "30d"

    brier_score: Mapped[Optional[Decimal]] = mapped_column()
    roc_auc: Mapped[Optional[Decimal]] = mapped_column()
    pr_auc: Mapped[Optional[Decimal]] = mapped_column()
    win_rate: Mapped[Optional[Decimal]] = mapped_column()
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    metric_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # The API updates one snapshot per (org, model, window, day) in place.
    # Without this constraint a concurrent second run inserts a duplicate and
    # the drift baseline silently double-counts that day.
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "model_version",
            "window_label",
            "metric_date",
            name="uq_model_metrics_org_version_window_date",
        ),
    )
