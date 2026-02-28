"""Analytics Dashboard API endpoints (ROADMAP Phase 5).

Provides:
- GET /analytics/kpis        — core reproductive KPIs
- GET /analytics/trends       — monthly KPI trends
- GET /analytics/funnel       — IVF funnel stages
- GET /analytics/protocols    — protocol pregnancy rates
- GET /analytics/protocols/regression  — logistic regression results
- GET /analytics/protocols/importance  — SHAP/permutation importance
- GET /analytics/donors       — per-donor performance
- GET /analytics/donors/trends — donor monthly trends
- GET /analytics/breeds       — breed-level stats
- GET /analytics/biomarkers   — CL/BC/heat_day sweet-spot analysis
- POST /analytics/run         — trigger analytics pipeline
"""

import json
import logging
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from app.schemas.analytics import (
    BiomarkersResponse,
    BiomarkerResult,
    BreedStatsResponse,
    DonorStatsResponse,
    DonorTrendsResponse,
    FunnelResponse,
    FunnelStage,
    KPIResponse,
    MonthlyTrend,
    ProtocolImportance,
    ProtocolRatesResponse,
    ProtocolRegression,
)

logger = logging.getLogger(__name__)
router = APIRouter()

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

_ARTIFACTS_DIR = _project_root / "ml" / "artifacts" / "analytics"


def _load_artifact(filename: str):
    """Load a JSON artifact from analytics artifacts directory."""
    path = _ARTIFACTS_DIR / filename
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def _ensure_data():
    """Run analytics pipeline if no artifacts exist."""
    if not _ARTIFACTS_DIR.exists() or not any(_ARTIFACTS_DIR.iterdir()):
        try:
            from ml.analytics.run_analytics import run_analytics
            run_analytics()
        except Exception as e:
            logger.exception("Analytics pipeline failed")
            raise HTTPException(503, f"Analytics pipeline not available: {e}")


# ── KPIs ─────────────────────────────────────────────────

@router.get("/kpis", response_model=KPIResponse)
async def get_kpis():
    """Get core reproductive KPIs."""
    _ensure_data()
    data = _load_artifact("kpis.json")
    if data is None:
        raise HTTPException(404, "KPI data not available")
    return KPIResponse(**data)


@router.get("/trends", response_model=list[MonthlyTrend])
async def get_trends():
    """Get monthly KPI trends."""
    _ensure_data()
    data = _load_artifact("monthly_trends.json")
    if data is None:
        raise HTTPException(404, "Trend data not available")
    return [MonthlyTrend(**d) for d in data]


@router.get("/funnel", response_model=FunnelResponse)
async def get_funnel():
    """Get IVF funnel metrics."""
    _ensure_data()
    data = _load_artifact("ivf_funnel.json")
    if data is None:
        raise HTTPException(404, "Funnel data not available")
    return FunnelResponse(stages=[FunnelStage(**s) for s in data])


# ── Protocol Analysis ────────────────────────────────────

@router.get("/protocols", response_model=ProtocolRatesResponse)
async def get_protocol_rates():
    """Get pregnancy rates per protocol with confidence intervals."""
    _ensure_data()
    data = _load_artifact("protocol_rates.json")
    if data is None:
        raise HTTPException(404, "Protocol data not available")
    return ProtocolRatesResponse(protocols=data, total=len(data))


@router.get("/protocols/regression", response_model=ProtocolRegression)
async def get_protocol_regression():
    """Get logistic regression results for protocol effectiveness."""
    _ensure_data()
    data = _load_artifact("protocol_regression.json")
    if data is None:
        raise HTTPException(404, "Regression data not available")
    return ProtocolRegression(**data)


@router.get("/protocols/importance", response_model=ProtocolImportance)
async def get_protocol_importance():
    """Get permutation importance for protocol features."""
    _ensure_data()
    data = _load_artifact("protocol_importance.json")
    if data is None:
        raise HTTPException(404, "Importance data not available")
    return ProtocolImportance(**data)


# ── Donor Analysis ───────────────────────────────────────

@router.get("/donors", response_model=DonorStatsResponse)
async def get_donor_stats():
    """Get per-donor pregnancy rates and performance metrics."""
    _ensure_data()
    data = _load_artifact("donor_performance.json")
    if data is None:
        raise HTTPException(404, "Donor data not available")
    return DonorStatsResponse(donors=data, total=len(data))


@router.get("/donors/trends", response_model=DonorTrendsResponse)
async def get_donor_trends():
    """Get monthly pregnancy rate trends for top donors."""
    _ensure_data()
    data = _load_artifact("donor_trends.json")
    if data is None:
        raise HTTPException(404, "Donor trend data not available")
    return DonorTrendsResponse(trends=data)


@router.get("/breeds", response_model=BreedStatsResponse)
async def get_breed_stats():
    """Get pregnancy rates by donor breed."""
    _ensure_data()
    data = _load_artifact("breed_stats.json")
    if data is None:
        raise HTTPException(404, "Breed data not available")
    return BreedStatsResponse(breeds=data, total=len(data))


# ── Biomarker Analysis ───────────────────────────────────

@router.get("/biomarkers", response_model=BiomarkersResponse)
async def get_biomarkers():
    """Get biomarker sweet-spot analysis (CL, BC score, heat day)."""
    _ensure_data()
    data = _load_artifact("biomarkers.json")
    if data is None:
        raise HTTPException(404, "Biomarker data not available")

    result = {}
    for key in ["cl_measure", "bc_score", "heat_day"]:
        if key in data and data[key]:
            result[key] = BiomarkerResult(**data[key])

    return BiomarkersResponse(**result)


# ── Pipeline Trigger ─────────────────────────────────────

@router.post("/run")
async def run_pipeline():
    """Trigger full analytics pipeline execution."""
    try:
        from ml.analytics.run_analytics import run_analytics
        result = run_analytics()
        return {
            "status": "complete",
            "total_transfers": result["kpis"]["total_transfers"],
            "protocols_analyzed": len(result["protocol_rates"]),
            "donors_analyzed": len(result["donor_performance"]),
        }
    except Exception as e:
        logger.exception("Analytics pipeline failed")
        raise HTTPException(500, f"Pipeline failed: {e}")
