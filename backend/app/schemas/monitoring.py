"""Pydantic schemas for Outcome Tracking & Continuous Learning (Module 7)."""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class RollingMetrics(BaseModel):
    """Result of compute_rolling_metrics() for one evaluation window."""
    status: str = Field(..., description="ok, insufficient_data, or single_class")
    message: str | None = None
    sample_size: int
    brier_score: float | None = None
    roc_auc: float | None = None
    pr_auc: float | None = None
    win_rate: float | None = None


class ModelMetricOut(BaseModel):
    """A single persisted model_metrics row."""
    metric_id: int
    model_version: str
    window_label: str | None = None
    brier_score: float | None = None
    roc_auc: float | None = None
    pr_auc: float | None = None
    win_rate: float | None = None
    sample_size: int
    metric_date: date
    created_at: datetime

    model_config = {"from_attributes": True}


class ModelMetricsResponse(BaseModel):
    """Response for GET /monitoring/metrics."""
    metrics: list[ModelMetricOut]
    total: int
    latest: RollingMetrics | None = None


class DriftReport(BaseModel):
    """Response for GET /monitoring/drift and POST /monitoring/run."""
    model_version: str
    current_metrics: RollingMetrics
    performance_drift_detected: bool
    performance_drift_details: dict[str, Any]
    population_drift_detected: bool
    population_drift_details: dict[str, Any]
    drift_detected: bool
    retrain_recommended: bool
    # Id of the open (PENDING/RUNNING) retrain job, or of the one just created.
    retrain_job_id: int | None = None
    # Why drift did NOT produce a new retrain job (rate limit / open job).
    retrain_suppressed_reason: str | None = None
    # True only for POST /monitoring/run; GET /monitoring/drift never writes.
    persisted: bool = False


class RetrainJobOut(BaseModel):
    """A single persisted retrain_jobs row."""
    job_id: int
    reason: str
    status: str
    triggered_by: str
    drift_details: dict[str, Any] | None = None
    model_version: str | None = None
    artifact_path: str | None = None
    triggered_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class RetrainJobsResponse(BaseModel):
    """Response for GET /monitoring/retrain-jobs."""
    jobs: list[RetrainJobOut]
    total: int
