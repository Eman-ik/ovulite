"""Outcome Tracking & Continuous Learning API endpoints (Module 7).

Provides:
- GET  /monitoring/metrics        — persisted rolling-metric history
- GET  /monitoring/drift          — current drift report (read-only)
- POST /monitoring/run            — run the pipeline and persist its results
- GET  /monitoring/retrain-jobs   — audit trail of retrain decisions
- POST /monitoring/retrain-jobs/{job_id}/acknowledge — mark a job reviewed

This complements, and does not replace, GET /predict/performance. That route
reports the *training-time holdout* metrics recorded in the deployed artifact.
This one measures the model's *live* behaviour against outcomes that have since
resolved, which is the only way calibration decay becomes visible.

Two adaptations from the upstream module:

1. Authorisation. Upstream used a `require_permission(...)` registry built for a
   three-role model (admin / technical_staff / viewer_researcher). This
   repository has six canonical roles and `require_role`, so the gates are
   expressed in those terms: reads are open to any authenticated user (matching
   /qc/*, /analytics/* and /predict/performance), while the two writes are
   restricted to admin and organization_admin (matching /qc/run and
   /analytics/run).

2. Tenancy. Predictions and transfers are organization-scoped here, so every
   query filters on the caller's organization. Upstream pooled all rows, which
   in this schema would compute one tenant's drift partly from another
   tenant's outcomes.
"""

import logging
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import ADMIN_ROLES, ANALYST_ROLES, get_current_user, require_role
from app.database import get_db
from app.models.et_transfer import ETTransfer
from app.models.model_metric import ModelMetric
from app.models.prediction import Prediction
from app.models.retrain_job import RetrainJob
from app.models.user import User
from app.schemas.monitoring import (
    DriftReport,
    ModelMetricOut,
    ModelMetricsResponse,
    RetrainJobOut,
    RetrainJobsResponse,
    RollingMetrics,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Resolve repository root for both layouts (matches app/api/qc.py convention):
# - Docker: /app/app/api/monitoring.py -> /app
# - Local:  <repo>/backend/app/api/monitoring.py -> <repo>
_base_root = Path(__file__).resolve().parents[2]
if (_base_root / "ml" / "monitoring").exists():
    _project_root = _base_root
elif (_base_root.parent / "ml" / "monitoring").exists():
    _project_root = _base_root.parent
else:
    _project_root = _base_root
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

DEFAULT_MODEL_VERSION = "pregnancy_ensemble"

# Running the pipeline and closing a retrain job are both platform-operations
# actions, gated the same way as POST /qc/run and POST /analytics/run.
PIPELINE_ADMIN_ROLES = ADMIN_ROLES


def _load_resolved_predictions(
    db: Session,
    organization_id: int,
    since: datetime | None = None,
    until: datetime | None = None,
):
    """Join predictions -> et_transfers to get (probability, actual_outcome,
    cl_measure_mm, heat_day) for predictions whose outcome is now resolved.

    'Recheck' and NULL outcomes are excluded (not a resolved binary label).
    ``since`` is inclusive, ``until`` exclusive.
    """
    import pandas as pd

    query = (
        select(
            Prediction.probability,
            ETTransfer.pc1_result,
            ETTransfer.cl_measure_mm,
            ETTransfer.heat_day,
            Prediction.predicted_at,
        )
        .join(ETTransfer, Prediction.transfer_id == ETTransfer.transfer_id)
        .where(
            ETTransfer.pc1_result.in_(["Pregnant", "Open"]),
            Prediction.organization_id == organization_id,
        )
    )
    if since is not None:
        query = query.where(Prediction.predicted_at >= since)
    if until is not None:
        query = query.where(Prediction.predicted_at < until)

    rows = db.execute(query).all()
    if not rows:
        return pd.DataFrame(columns=["probability", "actual_outcome", "cl_measure_mm", "heat_day"])

    df = pd.DataFrame(rows, columns=["probability", "pc1_result", "cl_measure_mm", "heat_day", "predicted_at"])
    df["probability"] = df["probability"].astype(float)
    df["actual_outcome"] = (df["pc1_result"] == "Pregnant").astype(int)
    # cl_measure_mm and heat_day are nullable, and the KS test needs floats.
    # astype(float) raises on None, so coerce instead and let drift.py's
    # dropna() decide whether enough points remain for a meaningful test.
    df["cl_measure_mm"] = pd.to_numeric(df["cl_measure_mm"], errors="coerce")
    df["heat_day"] = pd.to_numeric(df["heat_day"], errors="coerce")
    return df


def _count_resolved_predictions(db: Session, organization_id: int, since: datetime | None) -> int:
    """How many predictions with a resolved outcome were made after `since`."""
    query = (
        select(func.count())
        .select_from(Prediction)
        .join(ETTransfer, Prediction.transfer_id == ETTransfer.transfer_id)
        .where(
            ETTransfer.pc1_result.in_(["Pregnant", "Open"]),
            Prediction.organization_id == organization_id,
        )
    )
    if since is not None:
        query = query.where(Prediction.predicted_at > since)
    return int(db.execute(query).scalar() or 0)


def _load_historical_metrics(
    db: Session,
    organization_id: int,
    model_version: str,
    limit: int = 30,
    before: date | None = None,
) -> list[dict]:
    """The most recent `limit` saved snapshots, oldest first.

    ``before`` excludes snapshots dated on/after that day, so today's own
    snapshot is never part of the baseline it is compared against.
    """
    q = db.query(ModelMetric).filter(
        ModelMetric.organization_id == organization_id,
        ModelMetric.model_version == model_version,
    )
    if before is not None:
        q = q.filter(ModelMetric.metric_date < before)
    rows = q.order_by(ModelMetric.metric_date.desc()).limit(limit).all()
    rows = list(reversed(rows))
    return [
        {
            "status": "ok",
            "brier_score": float(r.brier_score) if r.brier_score is not None else None,
            "roc_auc": float(r.roc_auc) if r.roc_auc is not None else None,
            "pr_auc": float(r.pr_auc) if r.pr_auc is not None else None,
            "win_rate": float(r.win_rate) if r.win_rate is not None else None,
        }
        for r in rows
        if r.brier_score is not None
    ]


_OPEN_JOB_STATUSES = ("PENDING", "RUNNING")


def _open_retrain_job(db: Session, organization_id: int, model_version: str) -> RetrainJob | None:
    return (
        db.query(RetrainJob)
        .filter(
            RetrainJob.organization_id == organization_id,
            RetrainJob.model_version == model_version,
            RetrainJob.status.in_(_OPEN_JOB_STATUSES),
        )
        .order_by(RetrainJob.job_id.desc())
        .first()
    )


def _run_pipeline(
    db: Session,
    organization_id: int,
    model_version: str = DEFAULT_MODEL_VERSION,
    persist: bool = False,
) -> dict:
    """Compute the drift report.

    persist=False (GET /monitoring/drift): pure read. Nothing is written to
    the database or to disk -- opening the dashboard must not create rows.

    persist=True (POST /monitoring/run): additionally saves today's metric
    snapshot (one row per day, updated in place) and, if drift is detected,
    creates a retrain job subject to the rate limit below.
    """
    from ml.monitoring.config import (
        BASELINE_WINDOW_DAYS,
        CURRENT_WINDOW_DAYS,
        MIN_NEW_LABELS_FOR_RETRAIN,
    )
    from ml.monitoring.run_monitoring import run_monitoring_pipeline

    now = datetime.now(timezone.utc)
    current_since = now - timedelta(days=CURRENT_WINDOW_DAYS)
    baseline_since = now - timedelta(days=BASELINE_WINDOW_DAYS)

    df_current = _load_resolved_predictions(db, organization_id, since=current_since)
    # The baseline is the period BEFORE the current window, so the recent data
    # is not partly compared against itself (which would hide population drift).
    df_baseline = _load_resolved_predictions(
        db, organization_id, since=baseline_since, until=current_since
    )

    historical_metrics = _load_historical_metrics(
        db, organization_id, model_version, before=date.today()
    )

    result = run_monitoring_pipeline(
        df_current=df_current,
        df_baseline=df_baseline,
        historical_metrics=historical_metrics or None,
        model_version=model_version,
        save_artifact=persist,
    )
    result["persisted"] = persist
    result["retrain_suppressed_reason"] = None

    open_job = _open_retrain_job(db, organization_id, model_version)
    result["retrain_job_id"] = open_job.job_id if open_job else None

    if not persist:
        return result

    # ── Persist today's snapshot: one row per (org, model, window, day) ──
    cm = result["current_metrics"]
    if cm.get("status") == "ok":
        window_label = f"{CURRENT_WINDOW_DAYS}d"
        metric_row = (
            db.query(ModelMetric)
            .filter(
                ModelMetric.organization_id == organization_id,
                ModelMetric.model_version == model_version,
                ModelMetric.window_label == window_label,
                ModelMetric.metric_date == date.today(),
            )
            .first()
        )
        if metric_row is None:
            metric_row = ModelMetric(
                organization_id=organization_id,
                model_version=model_version,
                window_label=window_label,
                metric_date=date.today(),
            )
            db.add(metric_row)
        metric_row.brier_score = cm["brier_score"]
        metric_row.roc_auc = cm["roc_auc"]
        metric_row.pr_auc = cm["pr_auc"]
        metric_row.win_rate = cm["win_rate"]
        metric_row.sample_size = cm["sample_size"]
        db.commit()

    # ── Retrain job, with the rate limit from the spec (BR-9) ──
    rj = result.get("retrain_job")
    if rj:
        if open_job is not None:
            result["retrain_suppressed_reason"] = (
                f"Retrain job #{open_job.job_id} is still {open_job.status}; no duplicate created."
            )
        else:
            last_job = (
                db.query(RetrainJob)
                .filter(
                    RetrainJob.organization_id == organization_id,
                    RetrainJob.model_version == model_version,
                )
                .order_by(RetrainJob.job_id.desc())
                .first()
            )
            new_labels = _count_resolved_predictions(
                db, organization_id, last_job.triggered_at if last_job else None
            )
            if last_job is not None and new_labels < MIN_NEW_LABELS_FOR_RETRAIN:
                result["retrain_suppressed_reason"] = (
                    f"Only {new_labels} new labelled outcomes since retrain job #{last_job.job_id} "
                    f"(need {MIN_NEW_LABELS_FOR_RETRAIN}); no new job created."
                )
            else:
                job = RetrainJob(
                    organization_id=organization_id,
                    reason=rj["reason"],
                    status=rj["status"],
                    triggered_by=rj["triggered_by"],
                    drift_details=rj["drift_details"],
                    model_version=rj["model_version"],
                    artifact_path=rj["artifact_path"],
                )
                db.add(job)
                db.commit()
                db.refresh(job)
                result["retrain_job_id"] = job.job_id

    return result


def _to_report(result: dict) -> DriftReport:
    return DriftReport(
        model_version=result["model_version"],
        current_metrics=RollingMetrics(**result["current_metrics"]),
        performance_drift_detected=result["performance_drift_detected"],
        performance_drift_details=result["performance_drift_details"],
        population_drift_detected=result["population_drift_detected"],
        population_drift_details=result["population_drift_details"],
        drift_detected=result["drift_detected"],
        retrain_recommended=result["retrain_recommended"],
        retrain_job_id=result.get("retrain_job_id"),
        retrain_suppressed_reason=result.get("retrain_suppressed_reason"),
        persisted=bool(result.get("persisted", False)),
    )


def _require_org(current_user: User) -> int:
    if current_user.organization_id is None:
        raise HTTPException(403, "User is not assigned to an organization")
    return current_user.organization_id


def _guarded_pipeline(db: Session, organization_id: int, model_version: str, persist: bool) -> dict:
    """Run the pipeline, turning its two distinct failure modes into distinct
    HTTP statuses.

    The pipeline needs pandas/scikit-learn/scipy, which this repository keeps in
    ml/requirements.txt and does not install into the slim backend image. A
    missing optional dependency is a 503 — the feature is not available in this
    deployment — not a 500 suggesting the computation itself went wrong.
    """
    try:
        return _run_pipeline(db, organization_id, model_version, persist=persist)
    except ImportError as e:
        logger.warning("Monitoring unavailable, ML dependencies missing: %s", e)
        raise HTTPException(
            503,
            "Model monitoring needs the ML dependencies in ml/requirements.txt "
            f"(pandas, scikit-learn, scipy), which are not installed here: {e}",
        )
    except Exception as e:
        logger.exception("Monitoring pipeline failed")
        raise HTTPException(500, f"Monitoring pipeline failed: {e}")


@router.get("/metrics", response_model=ModelMetricsResponse)
async def get_metrics(
    model_version: str = Query(DEFAULT_MODEL_VERSION),
    limit: int = Query(90, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*ANALYST_ROLES)),
):
    """Return persisted rolling-metric history for a model version."""
    organization_id = _require_org(current_user)
    rows = (
        db.query(ModelMetric)
        .filter(
            ModelMetric.organization_id == organization_id,
            ModelMetric.model_version == model_version,
        )
        .order_by(ModelMetric.metric_date.desc())
        .limit(limit)
        .all()
    )
    metrics_out = [ModelMetricOut.model_validate(r) for r in rows]

    latest = None
    if rows:
        r = rows[0]
        latest = RollingMetrics(
            status="ok",
            sample_size=r.sample_size,
            brier_score=float(r.brier_score) if r.brier_score is not None else None,
            roc_auc=float(r.roc_auc) if r.roc_auc is not None else None,
            pr_auc=float(r.pr_auc) if r.pr_auc is not None else None,
            win_rate=float(r.win_rate) if r.win_rate is not None else None,
        )

    return ModelMetricsResponse(metrics=metrics_out, total=len(metrics_out), latest=latest)


@router.get("/drift", response_model=DriftReport)
async def get_drift(
    model_version: str = Query(DEFAULT_MODEL_VERSION),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*ANALYST_ROLES)),
):
    """Compute the current drift report WITHOUT writing anything.

    Always fresh (no stale cache), but strictly read-only: a GET must be safe
    to repeat. Saving the metric snapshot and creating a retrain job happen
    only in POST /monitoring/run, which is role-gated.
    """
    organization_id = _require_org(current_user)
    return _to_report(_guarded_pipeline(db, organization_id, model_version, persist=False))


@router.post("/run", response_model=DriftReport)
async def run_pipeline(
    model_version: str = Query(DEFAULT_MODEL_VERSION),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*PIPELINE_ADMIN_ROLES)),
):
    """Run the outcome-tracking pipeline and persist its results: today's
    metric snapshot and, if drift is detected and the rate limit allows it,
    a retrain job."""
    organization_id = _require_org(current_user)
    return _to_report(_guarded_pipeline(db, organization_id, model_version, persist=True))


@router.get("/retrain-jobs", response_model=RetrainJobsResponse)
async def get_retrain_jobs(
    status: str | None = Query(None, description="Filter by status: PENDING, RUNNING, COMPLETE, FAILED"),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*ANALYST_ROLES)),
):
    """Audit trail of retrain decisions (Module 7 continuous-learning log)."""
    organization_id = _require_org(current_user)
    q = db.query(RetrainJob).filter(RetrainJob.organization_id == organization_id)
    if status:
        q = q.filter(RetrainJob.status == status)
    rows = q.order_by(RetrainJob.triggered_at.desc()).limit(limit).all()
    jobs = [RetrainJobOut.model_validate(r) for r in rows]
    return RetrainJobsResponse(jobs=jobs, total=len(jobs))


@router.post("/retrain-jobs/{job_id}/acknowledge", response_model=RetrainJobOut)
async def acknowledge_retrain_job(
    job_id: int,
    new_status: str = Query("RUNNING", description="RUNNING, COMPLETE, or FAILED"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*PIPELINE_ADMIN_ROLES)),
):
    """Mark a retrain job as reviewed/actioned by a human."""
    if new_status not in {"RUNNING", "COMPLETE", "FAILED"}:
        raise HTTPException(400, "new_status must be one of RUNNING, COMPLETE, FAILED")

    organization_id = _require_org(current_user)
    job = (
        db.query(RetrainJob)
        .filter(RetrainJob.job_id == job_id, RetrainJob.organization_id == organization_id)
        .first()
    )
    if job is None:
        raise HTTPException(404, "Retrain job not found")

    job.status = new_status
    if new_status in {"COMPLETE", "FAILED"}:
        job.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    return RetrainJobOut.model_validate(job)
