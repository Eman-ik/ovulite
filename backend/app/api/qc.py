"""Lab QC & Anomaly Detection API endpoints (ROADMAP tasks 4.5, 4.7).

Provides:
- GET  /qc/anomalies    — list detected anomalies with severity filters
- GET  /qc/charts        — EWMA + CUSUM control chart data for frontend
- GET  /qc/technicians   — per-technician QC statistics
- GET  /qc/summary       — pipeline overview stats
- POST /qc/run           — trigger QC pipeline execution
"""

import json
import logging
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.dependencies import get_current_user
from app.models.user import User

from app.schemas.qc import (
    ControlChartData,
    QCAlert,
    QCAlertsResponse,
    QCChartsResponse,
    QCSummary,
    TechnicianQCStats,
    TechnicianStatsResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Resolve repository root for both layouts:
# - Docker: /app/app/api/qc.py -> /app
# - Local:  <repo>/backend/app/api/qc.py -> <repo>
_base_root = Path(__file__).resolve().parents[2]
if (_base_root / "ml" / "analytics").exists():
    _project_root = _base_root
elif (_base_root.parent / "ml" / "analytics").exists():
    _project_root = _base_root.parent
else:
    _project_root = _base_root
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

_ARTIFACTS_DIR = _project_root / "ml" / "artifacts" / "qc"


def _load_artifact(filename: str) -> dict | list | None:
    """Load a JSON artifact from the QC artifacts directory."""
    path = _ARTIFACTS_DIR / filename
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def _normalize_qc_alert(raw: dict, default_metric: str | None = None) -> dict:
    """Normalize legacy/raw chart alerts into QCAlert-compatible shape."""
    metric_name = raw.get("metric") or default_metric or "unknown_metric"
    alert_type = raw.get("alert_type") or raw.get("type") or "chart_alert"

    # Backfill fields required by QCAlert from control-chart artifacts.
    return {
        "alert_type": alert_type,
        "entity_type": raw.get("entity_type") or "system_metric",
        "entity_id": str(raw.get("entity_id") or metric_name),
        "severity": raw.get("severity") or "warning",
        "metric": metric_name,
        "metric_value": raw.get("metric_value", raw.get("value")),
        "baseline_value": raw.get("baseline_value", raw.get("target")),
        "description": raw.get("description")
        or f"{alert_type} detected for {metric_name}",
        "period": raw.get("period"),
        "timestamp": raw.get("timestamp"),
    }


@router.get("/anomalies", response_model=QCAlertsResponse)
async def get_anomalies(
    severity: str | None = Query(None, description="Filter by severity: info, warning, critical"),
    limit: int = Query(100, ge=1, le=1000),
    _current_user: User = Depends(get_current_user),
):
    """List detected QC anomalies, optionally filtered by severity.

    Returns alerts from both Isolation Forest and control chart violations,
    sorted by severity (critical first) then by metric magnitude.
    """
    alerts_data = _load_artifact("qc_alerts.json")

    if alerts_data is None:
        # No pipeline run yet — run it on the fly
        try:
            from ml.qc.run_pipeline import run_qc_pipeline
            result = run_qc_pipeline()
            alerts_data = result["alerts"]
        except Exception as e:
            logger.exception("QC pipeline failed")
            raise HTTPException(503, f"QC pipeline not available: {e}")

    # Filter by severity
    if severity:
        alerts_data = [a for a in alerts_data if a.get("severity") == severity]

    # Limit
    alerts_data = alerts_data[:limit]

    # Count by severity
    critical = sum(1 for a in alerts_data if a.get("severity") == "critical")
    warning = sum(1 for a in alerts_data if a.get("severity") == "warning")
    info = sum(1 for a in alerts_data if a.get("severity") == "info")

    normalized_alerts = [
        _normalize_qc_alert(a) for a in alerts_data if isinstance(a, dict)
    ]

    return QCAlertsResponse(
        alerts=[QCAlert(**a) for a in normalized_alerts],
        total=len(normalized_alerts),
        critical_count=critical,
        warning_count=warning,
        info_count=info,
    )


@router.get("/charts", response_model=QCChartsResponse)
async def get_charts(
    metric: str | None = Query(None, description="Filter by metric name"),
    _current_user: User = Depends(get_current_user),
):
    """Get EWMA and CUSUM control chart data for visualization.

    Returns chart data for each monitored metric (pregnancy_rate,
    avg_cl_measure, avg_embryo_grade) with control limits and violations.
    """
    charts_data = _load_artifact("qc_charts.json")

    if charts_data is None:
        try:
            from ml.qc.run_pipeline import run_qc_pipeline
            result = run_qc_pipeline()
            charts_data = result["charts"]
        except Exception as e:
            logger.exception("QC pipeline failed")
            raise HTTPException(503, f"QC pipeline not available: {e}")

    # Build response
    chart_list = []
    all_metrics = list(charts_data.keys())

    for metric_name, data in charts_data.items():
        if metric and metric_name != metric:
            continue

        ewma_points = [EWMAPoint(**p) for p in data.get("ewma", []) if isinstance(p, dict)]
        cusum_points = [CUSUMPoint(**p) for p in data.get("cusum", []) if isinstance(p, dict)]
        normalized_alerts = [
            _normalize_qc_alert(a, default_metric=metric_name)
            for a in data.get("alerts", [])
            if isinstance(a, dict)
        ]
        alert_items = [QCAlert(**a) for a in normalized_alerts]

        chart_list.append(ControlChartData(
            metric=metric_name,
            periods=data.get("periods", []),
            ewma=ewma_points,
            cusum=cusum_points,
            alerts=alert_items,
        ))

    return QCChartsResponse(charts=chart_list, metrics=all_metrics)


# Import missing schema types used in the endpoint
from app.schemas.qc import CUSUMPoint, EWMAPoint


@router.get("/technicians", response_model=TechnicianStatsResponse)
async def get_technician_stats(_current_user: User = Depends(get_current_user)):
    """Get per-technician QC statistics.

    Returns transfer count, pregnancy rate, CL measure stats,
    and comparison to global mean for each technician.
    """
    try:
        # Prefer persisted pipeline output if available.
        stats_data = _load_artifact("qc_technicians.json")
        summary_data = _load_artifact("qc_summary.json")

        if isinstance(stats_data, list):
            techs = [
                TechnicianQCStats(
                    technician_name=row.get("technician_name", "Unknown"),
                    transfer_count=int(row.get("transfer_count", 0) or 0),
                    pregnancy_rate=_safe_float(row.get("pregnancy_rate")),
                    avg_cl_measure=_safe_float(row.get("avg_cl_measure")),
                    std_cl_measure=_safe_float(row.get("std_cl_measure")),
                    avg_embryo_grade=_safe_float(row.get("avg_embryo_grade")),
                    avg_bc_score=_safe_float(row.get("avg_bc_score")),
                    preg_rate_vs_mean=_safe_float(row.get("preg_rate_vs_mean")),
                )
                for row in stats_data
                if isinstance(row, dict)
            ]
            return TechnicianStatsResponse(
                technicians=techs,
                total=len(techs),
                global_pregnancy_rate=_safe_float(
                    summary_data.get("global_pregnancy_rate")
                    if isinstance(summary_data, dict)
                    else None
                ),
            )

        # Fallback: compute directly from ET dataset.
        from ml.qc.features import compute_technician_stats, load_et_data

        df = load_et_data()
        stats = compute_technician_stats(df)
        global_preg = float(df["pregnant"].mean()) if "pregnant" in df.columns else None

        techs = []
        for _, row in stats.iterrows():
            techs.append(TechnicianQCStats(
                technician_name=row["technician_name"],
                transfer_count=int(row["transfer_count"]),
                pregnancy_rate=_safe_float(row.get("pregnancy_rate")),
                avg_cl_measure=_safe_float(row.get("avg_cl_measure")),
                std_cl_measure=_safe_float(row.get("std_cl_measure")),
                avg_embryo_grade=_safe_float(row.get("avg_embryo_grade")),
                avg_bc_score=_safe_float(row.get("avg_bc_score")),
                preg_rate_vs_mean=_safe_float(row.get("preg_rate_vs_mean")),
            ))

        return TechnicianStatsResponse(
            technicians=techs,
            total=len(techs),
            global_pregnancy_rate=global_preg,
        )
    except Exception as e:
        logger.exception("Failed to compute technician stats")
        raise HTTPException(500, str(e))


@router.get("/summary", response_model=QCSummary)
async def get_summary(_current_user: User = Depends(get_current_user)):
    """Get QC pipeline summary statistics."""
    summary = _load_artifact("qc_summary.json")

    if summary is None:
        try:
            from ml.qc.run_pipeline import run_qc_pipeline
            result = run_qc_pipeline()
            summary = result["summary"]
        except Exception as e:
            logger.exception("QC pipeline failed")
            raise HTTPException(503, f"QC pipeline not available: {e}")

    return QCSummary(**summary)


@router.post("/run")
async def run_pipeline(
    with_synthetic: bool = Query(False),
    _current_user: User = Depends(get_current_user),
):
    """Trigger QC pipeline execution.

    Optionally inject synthetic anomalies for testing.
    Returns pipeline summary.
    """
    try:
        from ml.qc.run_pipeline import run_qc_pipeline
        result = run_qc_pipeline(with_synthetic=with_synthetic)
        return {
            "status": "complete",
            "summary": result["summary"],
            "alert_count": len(result["alerts"]),
        }
    except Exception as e:
        logger.exception("QC pipeline execution failed")
        raise HTTPException(500, f"Pipeline failed: {e}")


def _safe_float(val) -> float | None:
    """Convert a value to float, returning None for NaN/None."""
    import math
    if val is None:
        return None
    try:
        f = float(val)
        return None if math.isnan(f) else round(f, 4)
    except (TypeError, ValueError):
        return None
