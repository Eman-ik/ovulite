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

from fastapi import APIRouter, HTTPException, Query

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

# Add project root to sys.path so ml package is importable
_project_root = Path(__file__).resolve().parent.parent.parent.parent
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


@router.get("/anomalies", response_model=QCAlertsResponse)
async def get_anomalies(
    severity: str | None = Query(None, description="Filter by severity: info, warning, critical"),
    limit: int = Query(100, ge=1, le=1000),
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

    return QCAlertsResponse(
        alerts=[QCAlert(**a) for a in alerts_data],
        total=len(alerts_data),
        critical_count=critical,
        warning_count=warning,
        info_count=info,
    )


@router.get("/charts", response_model=QCChartsResponse)
async def get_charts(
    metric: str | None = Query(None, description="Filter by metric name"),
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
        alert_items = [QCAlert(**a) for a in data.get("alerts", []) if isinstance(a, dict)]

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
async def get_technician_stats():
    """Get per-technician QC statistics.

    Returns transfer count, pregnancy rate, CL measure stats,
    and comparison to global mean for each technician.
    """
    try:
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
async def get_summary():
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
async def run_pipeline(with_synthetic: bool = Query(False)):
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
