"""Retraining job audit trail (Module 7 — Outcome Tracking & Continuous Learning).

A row is created whenever drift detection recommends retraining the
pregnancy-prediction ensemble. This is a reproducible LOG of the decision,
not an AutoML system — the actual retrain script is still launched by hand
(ml/train_pipeline.py); POST /monitoring/retrain-jobs/{id}/acknowledge only
records that a human picked the decision up.

Rows are organization-scoped: the drift that triggered the job was measured
over one organization's outcomes, so the decision belongs to that tenant.
"""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import OrganizationScopedMixin


class RetrainJob(OrganizationScopedMixin, Base):
    __tablename__ = "retrain_jobs"

    job_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING"
    )  # PENDING, RUNNING, COMPLETE, FAILED
    triggered_by: Mapped[str] = mapped_column(
        String(20), nullable=False, default="AUTO"
    )  # AUTO (drift) or MANUAL
    drift_details: Mapped[Optional[Any]] = mapped_column(JSON)
    model_version: Mapped[Optional[str]] = mapped_column(String(100))
    artifact_path: Mapped[Optional[str]] = mapped_column(String(500))

    triggered_at: Mapped[datetime] = mapped_column(server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
