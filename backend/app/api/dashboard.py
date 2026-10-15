"""Homepage dashboard API — live-queried KPIs, funnel, operations, alerts.

This is deliberately independent of the M6 Analytics module (`/analytics/*`),
which serves pre-generated static JSON with no filter support. Every endpoint
here queries the database directly so the homepage filter bar (date range,
farm, breed, donor, sire, embryologist, ET technician, protocol, fresh/frozen)
works live. Read-only calls into M4 (`ml.predict`) and M7 (`/qc/*`, called
directly by the frontend) are fine; this module does not modify either.

Every query is scoped by `current_user.organization_id`. Numbers that have no
underlying data are returned as `None`/empty, never fabricated as 0 or NaN.
"""

import math
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.api.transfers import _clean_pregnancy_result
from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.donor import Donor
from app.models.embryo import Embryo
from app.models.et_transfer import ETTransfer
from app.models.ivf_batch import IVFBatch
from app.models.opu_session import OPUSession
from app.models.prediction import Prediction
from app.models.protocol import Protocol
from app.models.sire import Sire
from app.models.technician import Technician
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.dashboard import (
    AISummaryResponse,
    AlertItem,
    AlertsResponse,
    DashboardFilterOptions,
    DataQualityResponse,
    DataQualityRow,
    FunnelResponse,
    FunnelStage,
    HighRiskTransfer,
    KpiItem,
    KpiResponse,
    LabeledOption,
    OmittedFunnelStage,
    OperationsResponse,
    PerformanceResponse,
    PerformanceRow,
    PipelineRow,
    SparklinePoint,
    TrendPoint,
    TrendResponse,
)

# Allow `import ml.predict` the same way predictions.py / qc.py already do.
_project_root = str(Path(__file__).resolve().parent.parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

router = APIRouter()

TRANSFERABLE_GRADES = (1, 2, 3)

# Upper edge of the shuffled-label null for this dataset's size, measured by
# permutation in ml/diagnose_split.py (null 0.501 ± 0.040, 95% range to 0.568).
# An AUC below this is not evidence of any learned signal.
AUC_CHANCE_CEILING = 0.57
DEFAULT_RANGE_DAYS = 90


# --------------------------------------------------------------------------
# Filters
# --------------------------------------------------------------------------

@dataclass
class DashboardFilterValues:
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    farm_location: Optional[str] = None
    breed: Optional[str] = None
    donor_id: Optional[int] = None
    sire_id: Optional[int] = None
    embryologist_id: Optional[int] = None
    technician_id: Optional[int] = None
    protocol_id: Optional[int] = None
    fresh_or_frozen: Optional[str] = None


def get_dashboard_filters(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    farm_location: Optional[str] = Query(None),
    breed: Optional[str] = Query(None),
    donor_id: Optional[int] = Query(None),
    sire_id: Optional[int] = Query(None),
    embryologist_id: Optional[int] = Query(None),
    technician_id: Optional[int] = Query(None),
    protocol_id: Optional[int] = Query(None),
    fresh_or_frozen: Optional[str] = Query(None),
) -> DashboardFilterValues:
    return DashboardFilterValues(
        date_from=date_from, date_to=date_to, farm_location=farm_location, breed=breed,
        donor_id=donor_id, sire_id=sire_id, embryologist_id=embryologist_id,
        technician_id=technician_id, protocol_id=protocol_id, fresh_or_frozen=fresh_or_frozen,
    )


def _latest_activity_date(db: Session, org_id: int) -> date:
    """Anchor for the default date range: the most recent ET transfer date on
    record, falling back to today's date if the organization has no transfers
    yet. Anchoring to wall-clock "today" would leave the homepage looking
    empty by default whenever the underlying dataset's most recent activity
    is months in the past (true for the current historical import).
    """
    latest = db.query(ETTransfer.et_date).filter(
        ETTransfer.organization_id == org_id
    ).order_by(ETTransfer.et_date.desc()).first()
    return latest[0] if latest else date.today()


def resolve_date_range(
    date_from: Optional[date], date_to: Optional[date], anchor: Optional[date] = None
) -> tuple[date, date]:
    if (date_from is None) != (date_to is None):
        raise HTTPException(400, "date_from and date_to must be provided together")
    if date_from is None:
        end = anchor or date.today()
        return end - timedelta(days=DEFAULT_RANGE_DAYS - 1), end
    if date_from > date_to:
        raise HTTPException(400, "date_from must be before date_to")
    return date_from, date_to


def previous_period(start: date, end: date) -> tuple[date, date]:
    length = (end - start).days + 1
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=length - 1)
    return prev_start, prev_end


def bucket_granularity(start: date, end: date) -> str:
    days = (end - start).days + 1
    if days <= 31:
        return "day"
    if days <= 180:
        return "week"
    return "month"


def _bucket_of(d: date, granularity: str) -> str:
    if granularity == "day":
        return d.isoformat()
    if granularity == "week":
        iso_year, iso_week, _ = d.isocalendar()
        return f"{iso_year}-W{iso_week:02d}"
    return f"{d.year}-{d.month:02d}"


def _ordered_buckets(start: date, end: date, granularity: str) -> list[str]:
    buckets: list[str] = []
    seen: set[str] = set()
    cur = start
    while cur <= end:
        b = _bucket_of(cur, granularity)
        if b not in seen:
            seen.add(b)
            buckets.append(b)
        cur += timedelta(days=1)
    return buckets


def _apply_breed(query, donor_id_col, db: Session, org_id: int, breed: Optional[str]):
    if breed:
        subq = db.query(Donor.donor_id).filter(Donor.organization_id == org_id, Donor.breed == breed)
        query = query.filter(donor_id_col.in_(subq))
    return query


# --------------------------------------------------------------------------
# Data fetchers — one per entity, shared by every endpoint below
# --------------------------------------------------------------------------

def _fetch_opu(db: Session, org_id: int, f: DashboardFilterValues, start: date, end: date) -> list[OPUSession]:
    q = db.query(OPUSession).options(joinedload(OPUSession.donor)).filter(
        OPUSession.organization_id == org_id,
        OPUSession.opu_date >= start,
        OPUSession.opu_date <= end,
    )
    if f.farm_location:
        q = q.filter(OPUSession.farm_location == f.farm_location)
    if f.donor_id:
        q = q.filter(OPUSession.donor_id == f.donor_id)
    if f.embryologist_id:
        q = q.filter(OPUSession.technician_id == f.embryologist_id)
    q = _apply_breed(q, OPUSession.donor_id, db, org_id, f.breed)
    return q.all()


def _fetch_ivf(db: Session, org_id: int, f: DashboardFilterValues, start: date, end: date) -> list[IVFBatch]:
    q = db.query(IVFBatch).join(OPUSession, IVFBatch.opu_id == OPUSession.opu_id).filter(
        IVFBatch.organization_id == org_id,
        IVFBatch.ivf_date.isnot(None),
        IVFBatch.ivf_date >= start,
        IVFBatch.ivf_date <= end,
    )
    if f.farm_location:
        q = q.filter(OPUSession.farm_location == f.farm_location)
    if f.donor_id:
        q = q.filter(OPUSession.donor_id == f.donor_id)
    if f.sire_id:
        q = q.filter(IVFBatch.sire_id == f.sire_id)
    if f.embryologist_id:
        q = q.filter(IVFBatch.embryologist_id == f.embryologist_id)
    q = _apply_breed(q, OPUSession.donor_id, db, org_id, f.breed)
    return q.all()


def _fetch_embryos(db: Session, org_id: int, f: DashboardFilterValues, start: date, end: date) -> list[Embryo]:
    q = db.query(Embryo).options(joinedload(Embryo.donor)).filter(
        Embryo.organization_id == org_id,
        Embryo.opu_date.isnot(None),
        Embryo.opu_date >= start,
        Embryo.opu_date <= end,
    )
    if f.donor_id:
        q = q.filter(Embryo.donor_id == f.donor_id)
    if f.sire_id:
        q = q.filter(Embryo.sire_id == f.sire_id)
    if f.fresh_or_frozen:
        q = q.filter(Embryo.fresh_or_frozen == f.fresh_or_frozen)
    q = _apply_breed(q, Embryo.donor_id, db, org_id, f.breed)
    return q.all()


def _fetch_transfers(db: Session, org_id: int, f: DashboardFilterValues, start: date, end: date) -> list[ETTransfer]:
    q = db.query(ETTransfer).options(
        joinedload(ETTransfer.embryo).joinedload(Embryo.donor),
        joinedload(ETTransfer.embryo).joinedload(Embryo.sire),
        joinedload(ETTransfer.protocol),
        joinedload(ETTransfer.technician),
    ).filter(
        ETTransfer.organization_id == org_id,
        ETTransfer.et_date >= start,
        ETTransfer.et_date <= end,
    )
    if f.farm_location:
        q = q.filter(ETTransfer.farm_location == f.farm_location)
    if f.technician_id:
        q = q.filter(ETTransfer.technician_id == f.technician_id)
    if f.protocol_id:
        q = q.filter(ETTransfer.protocol_id == f.protocol_id)
    if f.fresh_or_frozen:
        subq = db.query(Embryo.embryo_id).filter(
            Embryo.organization_id == org_id, Embryo.fresh_or_frozen == f.fresh_or_frozen
        )
        q = q.filter(ETTransfer.embryo_id.in_(subq))
    if f.donor_id or f.sire_id or f.breed:
        embryo_q = db.query(Embryo.embryo_id).filter(Embryo.organization_id == org_id)
        if f.donor_id:
            embryo_q = embryo_q.filter(Embryo.donor_id == f.donor_id)
        if f.sire_id:
            embryo_q = embryo_q.filter(Embryo.sire_id == f.sire_id)
        embryo_q = _apply_breed(embryo_q, Embryo.donor_id, db, org_id, f.breed)
        q = q.filter(ETTransfer.embryo_id.in_(embryo_q))
    return q.all()


# --------------------------------------------------------------------------
# Aggregation helpers
# --------------------------------------------------------------------------

def _sum_field(rows, field: str) -> Optional[float]:
    vals = [getattr(r, field) for r in rows if getattr(r, field) is not None]
    return float(sum(vals)) if vals else None


def _rate(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    if not numerator and numerator != 0:
        return None
    if not denominator:
        return None
    return round(float(numerator) / float(denominator) * 100, 1)


def _sum_sparkline(rows, date_field: str, value_field: str, start: date, end: date, granularity: str):
    buckets = _ordered_buckets(start, end, granularity)
    sums = {b: 0.0 for b in buckets}
    for r in rows:
        d = getattr(r, date_field)
        if d is None:
            continue
        b = _bucket_of(d, granularity)
        if b not in sums:
            continue
        v = getattr(r, value_field)
        if v is not None:
            sums[b] += float(v)
    return [{"bucket": b, "value": sums[b]} for b in buckets]


def _ratio_sum_sparkline(rows, date_field: str, num_field: str, den_field: str, start: date, end: date, granularity: str):
    buckets = _ordered_buckets(start, end, granularity)
    num = {b: 0.0 for b in buckets}
    den = {b: 0.0 for b in buckets}
    for r in rows:
        d = getattr(r, date_field)
        if d is None:
            continue
        b = _bucket_of(d, granularity)
        if b not in den:
            continue
        dv = getattr(r, den_field)
        if dv is None:
            continue
        den[b] += float(dv)
        nv = getattr(r, num_field)
        if nv is not None:
            num[b] += float(nv)
    return [{"bucket": b, "value": (round(num[b] / den[b] * 100, 1) if den[b] else None)} for b in buckets]


def _pregnancy_rate_sparkline(transfers: list[ETTransfer], start: date, end: date, granularity: str):
    buckets = _ordered_buckets(start, end, granularity)
    num = {b: 0 for b in buckets}
    den = {b: 0 for b in buckets}
    for t in transfers:
        if t.et_date is None:
            continue
        b = _bucket_of(t.et_date, granularity)
        if b not in den:
            continue
        cleaned = _clean_pregnancy_result(t.pc1_result)
        if cleaned is None:
            continue
        den[b] += 1
        if cleaned == "Pregnant":
            num[b] += 1
    return [{"bucket": b, "value": (round(num[b] / den[b] * 100, 1) if den[b] else None)} for b in buckets]


def _build_kpi(key, label, value, prev_value, unit, comparison_label, sparkline_raw) -> KpiItem:
    # For "percent" KPIs (rates), delta_pct is the percentage-POINT difference
    # (e.g. 34.5% -> 17.5% is a -17.0 point move), not a relative percent
    # change — a rate can't sensibly "increase by 97%". For "count" KPIs,
    # delta_pct is a relative percent change, since raw counts have no
    # natural point scale.
    delta_pct = None
    direction = None
    if value is not None and prev_value is not None:
        if unit == "percent":
            delta_pct = round(value - prev_value, 1)
            direction = "up" if delta_pct > 0.05 else "down" if delta_pct < -0.05 else "flat"
        elif prev_value != 0:
            delta_pct = round((value - prev_value) / abs(prev_value) * 100, 1)
            direction = "up" if delta_pct > 0.05 else "down" if delta_pct < -0.05 else "flat"
        elif value > 0:
            direction = "up"
    return KpiItem(
        key=key, label=label, value=value, unit=unit,
        delta_pct=delta_pct, delta_direction=direction,
        sparkline=[SparklinePoint(bucket=p["bucket"], value=p["value"]) for p in sparkline_raw],
        comparison_label=comparison_label,
    )


def _model_auc_and_version():
    try:
        from ml.predict import get_predictor
        predictor = get_predictor()
        metadata = predictor.metadata or {}
        best_key = metadata.get("best_model")
        auc = None
        if best_key and best_key in metadata.get("models", {}):
            auc = metadata["models"][best_key].get("holdout_metrics", {}).get("roc_auc")
        return auc, predictor.version
    except Exception:
        return None, None


def _compute_operations(db: Session, org_id: int, f: DashboardFilterValues) -> dict:
    today = date.today()

    opu_today_q = db.query(OPUSession).filter(
        OPUSession.organization_id == org_id, OPUSession.opu_date == today,
    )
    if f.farm_location:
        opu_today_q = opu_today_q.filter(OPUSession.farm_location == f.farm_location)
    if f.embryologist_id:
        opu_today_q = opu_today_q.filter(OPUSession.technician_id == f.embryologist_id)

    culture_start = today - timedelta(days=7)
    ivf_culture_q = db.query(IVFBatch).join(OPUSession, IVFBatch.opu_id == OPUSession.opu_id).filter(
        IVFBatch.organization_id == org_id,
        IVFBatch.ivf_date.isnot(None),
        IVFBatch.ivf_date >= culture_start,
        IVFBatch.ivf_date <= today,
        IVFBatch.blastocysts.is_(None),
    )
    if f.farm_location:
        ivf_culture_q = ivf_culture_q.filter(OPUSession.farm_location == f.farm_location)
    if f.embryologist_id:
        ivf_culture_q = ivf_culture_q.filter(IVFBatch.embryologist_id == f.embryologist_id)

    grading_start = today - timedelta(days=14)
    embryo_grading_q = db.query(Embryo).filter(
        Embryo.organization_id == org_id,
        Embryo.grade.is_(None),
        Embryo.opu_date.isnot(None),
        Embryo.opu_date >= grading_start,
        Embryo.opu_date <= today,
    )

    transfers_today_q = db.query(ETTransfer).filter(
        ETTransfer.organization_id == org_id, ETTransfer.et_date == today,
    )
    if f.farm_location:
        transfers_today_q = transfers_today_q.filter(ETTransfer.farm_location == f.farm_location)
    if f.technician_id:
        transfers_today_q = transfers_today_q.filter(ETTransfer.technician_id == f.technician_id)

    pc_due_start = today - timedelta(days=60)
    pc_due_end = today - timedelta(days=30)
    pc_due_q = db.query(ETTransfer).filter(
        ETTransfer.organization_id == org_id,
        ETTransfer.pc1_result.is_(None),
        ETTransfer.et_date >= pc_due_start,
        ETTransfer.et_date <= pc_due_end,
    )
    if f.technician_id:
        pc_due_q = pc_due_q.filter(ETTransfer.technician_id == f.technician_id)

    pending_predictions = db.query(Prediction).filter(
        Prediction.organization_id == org_id, Prediction.actual_outcome.is_(None),
    ).count()

    return {
        "opu_sessions_today": opu_today_q.count(),
        "ivf_batches_in_culture": ivf_culture_q.count(),
        "embryos_pending_grading": embryo_grading_q.count(),
        "transfers_scheduled_today": transfers_today_q.count(),
        "pregnancy_checks_due": pc_due_q.count(),
        "predictions_pending_outcome": pending_predictions,
    }


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------

@router.get("/filters", response_model=DashboardFilterOptions)
def get_filter_options(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    org_id = current_user.organization_id
    donors = db.query(Donor).filter(Donor.organization_id == org_id).order_by(Donor.tag_id).all()
    sires = db.query(Sire).filter(Sire.organization_id == org_id).order_by(Sire.name).all()
    technicians = db.query(Technician).filter(Technician.organization_id == org_id).order_by(Technician.name).all()
    protocols = db.query(Protocol).filter(Protocol.organization_id == org_id).order_by(Protocol.name).all()
    breeds = [
        row[0] for row in db.query(Donor.breed).filter(
            Donor.organization_id == org_id, Donor.breed.isnot(None)
        ).distinct().all()
    ]
    farms = [
        row[0] for row in db.query(ETTransfer.farm_location).filter(
            ETTransfer.organization_id == org_id, ETTransfer.farm_location.isnot(None)
        ).distinct().all()
    ]
    return DashboardFilterOptions(
        donors=[LabeledOption(id=d.donor_id, label=d.tag_id) for d in donors],
        sires=[LabeledOption(id=s.sire_id, label=s.name) for s in sires],
        technicians=[LabeledOption(id=t.technician_id, label=t.name) for t in technicians],
        protocols=[LabeledOption(id=p.protocol_id, label=p.name) for p in protocols],
        breeds=sorted(breeds),
        farm_locations=sorted(farms),
        fresh_or_frozen=["Fresh", "Frozen"],
    )


@router.get("/kpis", response_model=KpiResponse)
def get_kpis(
    filters: DashboardFilterValues = Depends(get_dashboard_filters),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = current_user.organization_id
    start, end = resolve_date_range(filters.date_from, filters.date_to, anchor=_latest_activity_date(db, org_id))
    prev_start, prev_end = previous_period(start, end)
    granularity = bucket_granularity(start, end)
    comparison_label = f"vs {prev_start.isoformat()} – {prev_end.isoformat()}"

    opu_rows = _fetch_opu(db, org_id, filters, start, end)
    opu_prev = _fetch_opu(db, org_id, filters, prev_start, prev_end)
    ivf_rows = _fetch_ivf(db, org_id, filters, start, end)
    ivf_prev = _fetch_ivf(db, org_id, filters, prev_start, prev_end)
    embryo_rows = _fetch_embryos(db, org_id, filters, start, end)
    embryo_prev = _fetch_embryos(db, org_id, filters, prev_start, prev_end)
    transfer_rows = _fetch_transfers(db, org_id, filters, start, end)
    transfer_prev = _fetch_transfers(db, org_id, filters, prev_start, prev_end)

    kpis: list[KpiItem] = []

    # 1. Oocytes recovered
    kpis.append(_build_kpi(
        "oocytes_recovered", "Oocytes Recovered",
        _sum_field(opu_rows, "oocytes_recovered"), _sum_field(opu_prev, "oocytes_recovered"),
        "count", comparison_label,
        _sum_sparkline(opu_rows, "opu_date", "oocytes_recovered", start, end, granularity),
    ))

    # 2. Maturation rate
    kpis.append(_build_kpi(
        "maturation_rate", "Maturation Rate",
        _rate(_sum_field(ivf_rows, "mature_oocytes"), _sum_field(ivf_rows, "oocytes_used")),
        _rate(_sum_field(ivf_prev, "mature_oocytes"), _sum_field(ivf_prev, "oocytes_used")),
        "percent", comparison_label,
        _ratio_sum_sparkline(ivf_rows, "ivf_date", "mature_oocytes", "oocytes_used", start, end, granularity),
    ))

    # 3. Cleavage rate
    kpis.append(_build_kpi(
        "cleavage_rate", "Cleavage Rate",
        _rate(_sum_field(ivf_rows, "cleaved_embryos"), _sum_field(ivf_rows, "mature_oocytes")),
        _rate(_sum_field(ivf_prev, "cleaved_embryos"), _sum_field(ivf_prev, "mature_oocytes")),
        "percent", comparison_label,
        _ratio_sum_sparkline(ivf_rows, "ivf_date", "cleaved_embryos", "mature_oocytes", start, end, granularity),
    ))

    # 4. Blastocyst rate
    kpis.append(_build_kpi(
        "blastocyst_rate", "Blastocyst Rate",
        _rate(_sum_field(ivf_rows, "blastocysts"), _sum_field(ivf_rows, "cleaved_embryos")),
        _rate(_sum_field(ivf_prev, "blastocysts"), _sum_field(ivf_prev, "cleaved_embryos")),
        "percent", comparison_label,
        _ratio_sum_sparkline(ivf_rows, "ivf_date", "blastocysts", "cleaved_embryos", start, end, granularity),
    ))

    # 5. Transferable embryos (grade 1-3; grade 4 = degenerate, excluded)
    transferable_now = sum(1 for e in embryo_rows if e.grade in TRANSFERABLE_GRADES)
    transferable_prev = sum(1 for e in embryo_prev if e.grade in TRANSFERABLE_GRADES)
    kpis.append(_build_kpi(
        "transferable_embryos", "Transferable Embryos", float(transferable_now), float(transferable_prev),
        "count", comparison_label,
        _count_sparkline(
            [e for e in embryo_rows if e.grade in TRANSFERABLE_GRADES], "opu_date", start, end, granularity
        ),
    ))

    # 6. Transfers completed
    kpis.append(_build_kpi(
        "transfers_completed", "Transfers Completed",
        float(len(transfer_rows)), float(len(transfer_prev)),
        "count", comparison_label,
        _count_sparkline(transfer_rows, "et_date", start, end, granularity),
    ))

    # 7. Pregnancy rate
    def _preg_rate(transfers: list[ETTransfer]) -> Optional[float]:
        cleaned = [_clean_pregnancy_result(t.pc1_result) for t in transfers]
        checked = [c for c in cleaned if c is not None]
        if not checked:
            return None
        return round(sum(1 for c in checked if c == "Pregnant") / len(checked) * 100, 1)

    kpis.append(_build_kpi(
        "pregnancy_rate", "Pregnancy Rate",
        _preg_rate(transfer_rows), _preg_rate(transfer_prev),
        "percent", comparison_label,
        _pregnancy_rate_sparkline(transfer_rows, start, end, granularity),
    ))

    # 8. AI model metric (not date-scoped — the model is a single global artifact).
    #
    # Reported as discrimination above chance, not as "accuracy". ROC-AUC has a
    # floor of 0.5, so rendering it as a bare percentage invites reading 48.8%
    # as "about half right" when it actually means "no better than guessing".
    # A permutation test (ml/diagnose_split.py) puts the current artifact
    # squarely inside the shuffled-label null, so the label says so outright
    # rather than implying a number that is merely low.
    auc, version = _model_auc_and_version()
    pending_predictions = db.query(Prediction).filter(
        Prediction.organization_id == org_id, Prediction.actual_outcome.is_(None)
    ).count()
    if auc is None:
        value, label, note = None, "Model Discrimination", "no model loaded"
    else:
        value = round((auc - 0.5) * 200, 1)  # 0.5 AUC -> 0%, 1.0 AUC -> 100%
        label = "Model Discrimination (vs chance)"
        note = (
            f"AUC {auc:.3f} — not distinguishable from chance"
            if auc < AUC_CHANCE_CEILING
            else f"AUC {auc:.3f}"
        )
    kpis.append(KpiItem(
        key="model_auc", label=label,
        value=value,
        unit="percent", delta_pct=None, delta_direction=None, sparkline=[],
        comparison_label=(
            f"{note} · {version or 'no version'} · {pending_predictions} predictions pending outcome"
        ),
    ))

    return KpiResponse(kpis=kpis, date_from=start, date_to=end)


def _count_sparkline(rows, date_field: str, start: date, end: date, granularity: str):
    buckets = _ordered_buckets(start, end, granularity)
    counts = {b: 0 for b in buckets}
    for r in rows:
        d = getattr(r, date_field)
        if d is None:
            continue
        b = _bucket_of(d, granularity)
        if b in counts:
            counts[b] += 1
    return [{"bucket": b, "value": float(counts[b])} for b in buckets]


def _count_live_births(
    db: Session, org_id: int, f: DashboardFilterValues, start: date, end: date
) -> int:
    """Live births among transfers made inside the window.

    Counted against the transfer's own date, not the calving date, so the stage
    stays on the same cohort as the transfer and pregnancy stages above it.
    """
    from app.models.calving_record import CalvingRecord

    transfer_ids = [t.transfer_id for t in _fetch_transfers(db, org_id, f, start, end)]
    if not transfer_ids:
        return 0
    return (
        db.query(CalvingRecord)
        .filter(
            CalvingRecord.organization_id == org_id,
            CalvingRecord.transfer_id.in_(transfer_ids),
            CalvingRecord.outcome == "Live Birth",
        )
        .count()
    )


@router.get("/funnel", response_model=FunnelResponse)
def get_funnel(
    filters: DashboardFilterValues = Depends(get_dashboard_filters),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = current_user.organization_id
    start, end = resolve_date_range(filters.date_from, filters.date_to, anchor=_latest_activity_date(db, org_id))

    opu_rows = _fetch_opu(db, org_id, filters, start, end)
    ivf_rows = _fetch_ivf(db, org_id, filters, start, end)
    embryo_rows = _fetch_embryos(db, org_id, filters, start, end)
    transfer_rows = _fetch_transfers(db, org_id, filters, start, end)

    oocytes_recovered = int(_sum_field(opu_rows, "oocytes_recovered") or 0)
    mature = int(_sum_field(ivf_rows, "mature_oocytes") or 0)
    cleaved = int(_sum_field(ivf_rows, "cleaved_embryos") or 0)
    blastocysts = int(_sum_field(ivf_rows, "blastocysts") or 0)
    transferable = sum(1 for e in embryo_rows if e.grade in TRANSFERABLE_GRADES)
    transfers = len(transfer_rows)
    cleaned_pc1 = [_clean_pregnancy_result(t.pc1_result) for t in transfer_rows]
    pregnancies = sum(1 for c in cleaned_pc1 if c == "Pregnant")
    ongoing = sum(
        1 for t in transfer_rows
        if _clean_pregnancy_result(t.pc1_result) == "Pregnant"
        and _clean_pregnancy_result(t.pc2_result) == "Pregnant"
    )

    live_births = _count_live_births(db, org_id, filters, start, end)

    # The first five stages follow one cohort of oocytes through the lab. The
    # transfer stages follow a different set of animals: an embryo banked in
    # this window is usually transferred in a later one, and a transfer in this
    # window usually used an embryo banked earlier. Carrying a percentage across
    # that boundary produced the 243% "conversion" this funnel used to show.
    COHORT_NOTE = (
        "Different cohort: embryos banked in this window are not the embryos "
        "transferred in it, so lab output and transfer counts are not a conversion."
    )
    raw_stages: list[tuple[str, int, bool]] = [
        ("Oocytes Recovered", oocytes_recovered, False),
        ("Mature Oocytes", mature, False),
        ("Cleaved Embryos", cleaved, False),
        ("Blastocysts", blastocysts, False),
        ("Transferable Embryos", transferable, False),
        ("Transfers", transfers, True),
        ("Pregnancies", pregnancies, False),
        ("Ongoing Pregnancies", ongoing, False),
        ("Live Births", live_births, False),
    ]
    first_value = raw_stages[0][1] or None
    prev_value: Optional[int] = None
    cohort_first: Optional[int] = first_value
    stages: list[FunnelStage] = []
    for name, value, is_break in raw_stages:
        if is_break:
            cohort_first = value or None
        stages.append(FunnelStage(
            name=name, value=value,
            conversion_pct_from_previous=None if is_break else _rate(value, prev_value),
            conversion_pct_from_first=_rate(value, cohort_first),
            cohort_break=is_break,
            cohort_note=COHORT_NOTE if is_break else None,
        ))
        prev_value = value

    return FunnelResponse(stages=stages, omitted_stages=[])


@router.get("/trends", response_model=TrendResponse)
def get_trends(
    metric: str = Query(..., pattern="^(pregnancy_rate|cleavage_rate|blastocyst_rate|maturation_rate)$"),
    granularity: str | None = Query(None, pattern="^(day|week|month)$"),
    filters: DashboardFilterValues = Depends(get_dashboard_filters),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = current_user.organization_id
    start, end = resolve_date_range(filters.date_from, filters.date_to, anchor=_latest_activity_date(db, org_id))
    # Drill-down/up: the caller may pick the bucket size; otherwise it follows the range.
    if granularity is None:
        granularity = bucket_granularity(start, end)
    elif granularity == "day" and (end - start).days + 1 > 366:
        raise HTTPException(status_code=422, detail="Daily points need a range of a year or less.")
    buckets = _ordered_buckets(start, end, granularity)

    if metric == "pregnancy_rate":
        transfers = _fetch_transfers(db, org_id, filters, start, end)
        num = {b: 0 for b in buckets}
        den = {b: 0 for b in buckets}
        for t in transfers:
            if t.et_date is None:
                continue
            b = _bucket_of(t.et_date, granularity)
            if b not in den:
                continue
            cleaned = _clean_pregnancy_result(t.pc1_result)
            if cleaned is None:
                continue
            den[b] += 1
            if cleaned == "Pregnant":
                num[b] += 1
        points = [
            TrendPoint(bucket_label=b, value=(round(num[b] / den[b] * 100, 1) if den[b] else None), n=den[b])
            for b in buckets
        ]
    else:
        field_map = {
            "maturation_rate": ("mature_oocytes", "oocytes_used"),
            "cleavage_rate": ("cleaved_embryos", "mature_oocytes"),
            "blastocyst_rate": ("blastocysts", "cleaved_embryos"),
        }
        num_field, den_field = field_map[metric]
        ivf_rows = _fetch_ivf(db, org_id, filters, start, end)
        num = {b: 0.0 for b in buckets}
        den = {b: 0.0 for b in buckets}
        for r in ivf_rows:
            if r.ivf_date is None:
                continue
            b = _bucket_of(r.ivf_date, granularity)
            if b not in den:
                continue
            dv = getattr(r, den_field)
            if dv is None:
                continue
            den[b] += float(dv)
            nv = getattr(r, num_field)
            if nv is not None:
                num[b] += float(nv)
        points = [
            TrendPoint(bucket_label=b, value=(round(num[b] / den[b] * 100, 1) if den[b] else None), n=int(den[b]))
            for b in buckets
        ]

    return TrendResponse(metric=metric, granularity=granularity, points=points)


@router.get("/operations", response_model=OperationsResponse)
def get_operations(
    filters: DashboardFilterValues = Depends(get_dashboard_filters),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ops = _compute_operations(db, current_user.organization_id, filters)
    return OperationsResponse(
        **ops,
        estimated_fields=["ivf_batches_in_culture", "embryos_pending_grading", "pregnancy_checks_due"],
    )


@router.get("/pipeline", response_model=PaginatedResponse[PipelineRow])
def get_pipeline(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    filters: DashboardFilterValues = Depends(get_dashboard_filters),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = current_user.organization_id
    today = date.today()
    rows: list[PipelineRow] = []

    opu_today_q = db.query(OPUSession).options(joinedload(OPUSession.donor)).filter(
        OPUSession.organization_id == org_id, OPUSession.opu_date == today,
    )
    if filters.farm_location:
        opu_today_q = opu_today_q.filter(OPUSession.farm_location == filters.farm_location)
    if filters.embryologist_id:
        opu_today_q = opu_today_q.filter(OPUSession.technician_id == filters.embryologist_id)
    for o in opu_today_q.all():
        rows.append(PipelineRow(
            stage="opu", entity_id=o.opu_id, label=o.donor.tag_id if o.donor else f"OPU #{o.opu_id}",
            date=o.opu_date, detail="OPU session today",
        ))

    culture_start = today - timedelta(days=7)
    ivf_q = db.query(IVFBatch).options(
        joinedload(IVFBatch.opu_session).joinedload(OPUSession.donor)
    ).join(OPUSession, IVFBatch.opu_id == OPUSession.opu_id).filter(
        IVFBatch.organization_id == org_id, IVFBatch.ivf_date.isnot(None),
        IVFBatch.ivf_date >= culture_start, IVFBatch.ivf_date <= today, IVFBatch.blastocysts.is_(None),
    )
    if filters.farm_location:
        ivf_q = ivf_q.filter(OPUSession.farm_location == filters.farm_location)
    if filters.embryologist_id:
        ivf_q = ivf_q.filter(IVFBatch.embryologist_id == filters.embryologist_id)
    for b in ivf_q.all():
        donor_tag = b.opu_session.donor.tag_id if b.opu_session and b.opu_session.donor else None
        rows.append(PipelineRow(
            stage="ivf", entity_id=b.ivf_batch_id,
            label=f"IVF batch — {donor_tag or b.ivf_batch_id}",
            date=b.ivf_date, detail="In culture (estimated)",
        ))

    grading_start = today - timedelta(days=14)
    embryo_q = db.query(Embryo).options(joinedload(Embryo.donor)).filter(
        Embryo.organization_id == org_id, Embryo.grade.is_(None),
        Embryo.opu_date.isnot(None), Embryo.opu_date >= grading_start, Embryo.opu_date <= today,
    )
    if filters.donor_id:
        embryo_q = embryo_q.filter(Embryo.donor_id == filters.donor_id)
    for e in embryo_q.all():
        rows.append(PipelineRow(
            stage="grading", entity_id=e.embryo_id,
            label=e.donor.tag_id if e.donor else f"Embryo #{e.embryo_id}",
            date=e.opu_date, detail="Pending grading (estimated)",
        ))

    transfers_today_q = db.query(ETTransfer).filter(
        ETTransfer.organization_id == org_id, ETTransfer.et_date == today,
    )
    if filters.farm_location:
        transfers_today_q = transfers_today_q.filter(ETTransfer.farm_location == filters.farm_location)
    if filters.technician_id:
        transfers_today_q = transfers_today_q.filter(ETTransfer.technician_id == filters.technician_id)
    for t in transfers_today_q.all():
        rows.append(PipelineRow(
            stage="transfer_scheduled", entity_id=t.transfer_id, label=f"Transfer #{t.transfer_id}",
            date=t.et_date, detail="Scheduled today",
        ))

    pc_due_start = today - timedelta(days=60)
    pc_due_end = today - timedelta(days=30)
    pc_due_q = db.query(ETTransfer).filter(
        ETTransfer.organization_id == org_id, ETTransfer.pc1_result.is_(None),
        ETTransfer.et_date >= pc_due_start, ETTransfer.et_date <= pc_due_end,
    )
    if filters.technician_id:
        pc_due_q = pc_due_q.filter(ETTransfer.technician_id == filters.technician_id)
    for t in pc_due_q.all():
        rows.append(PipelineRow(
            stage="pending_pc", entity_id=t.transfer_id, label=f"Transfer #{t.transfer_id}",
            date=t.et_date, detail="Pregnancy check due (estimated)",
        ))

    rows.sort(key=lambda r: r.date or date.min, reverse=True)
    total = len(rows)
    start_idx = (page - 1) * page_size
    page_rows = rows[start_idx: start_idx + page_size]
    return PaginatedResponse(
        items=page_rows, total=total, page=page, page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/alerts", response_model=AlertsResponse)
def get_alerts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    org_id = current_user.organization_id
    today = date.today()
    last_start, last_end = today - timedelta(days=29), today
    prior_start, prior_end = last_start - timedelta(days=30), last_start - timedelta(days=1)
    empty_filters = DashboardFilterValues()

    last_transfers = _fetch_transfers(db, org_id, empty_filters, last_start, last_end)
    prior_transfers = _fetch_transfers(db, org_id, empty_filters, prior_start, prior_end)

    def _preg(transfers: list[ETTransfer]) -> tuple[Optional[float], int]:
        cleaned = [_clean_pregnancy_result(t.pc1_result) for t in transfers]
        checked = [c for c in cleaned if c is not None]
        if not checked:
            return None, 0
        return round(sum(1 for c in checked if c == "Pregnant") / len(checked) * 100, 1), len(checked)

    last_rate, last_n = _preg(last_transfers)
    prior_rate, prior_n = _preg(prior_transfers)

    alerts: list[AlertItem] = []
    if last_rate is not None and prior_rate is not None and last_n >= 10 and prior_n >= 10:
        drop = prior_rate - last_rate
        if drop >= 10:
            alerts.append(AlertItem(
                severity="critical", title="Pregnancy rate has dropped sharply",
                detail=f"Pregnancy rate fell from {prior_rate}% to {last_rate}% over the last 30 days ({drop:.1f} point drop, n={last_n}).",
                metric_key="pregnancy_rate",
            ))
        elif drop >= 5:
            alerts.append(AlertItem(
                severity="warning", title="Pregnancy rate is trending down",
                detail=f"Pregnancy rate fell from {prior_rate}% to {last_rate}% over the last 30 days ({drop:.1f} point drop, n={last_n}).",
                metric_key="pregnancy_rate",
            ))

    last_ivf = _fetch_ivf(db, org_id, empty_filters, last_start, last_end)
    prior_ivf = _fetch_ivf(db, org_id, empty_filters, prior_start, prior_end)
    last_b_num, last_b_den = _sum_field(last_ivf, "blastocysts"), _sum_field(last_ivf, "cleaved_embryos")
    prior_b_num, prior_b_den = _sum_field(prior_ivf, "blastocysts"), _sum_field(prior_ivf, "cleaved_embryos")
    last_b_rate = _rate(last_b_num, last_b_den)
    prior_b_rate = _rate(prior_b_num, prior_b_den)
    if (
        last_b_rate is not None and prior_b_rate is not None
        and (last_b_den or 0) >= 20 and (prior_b_den or 0) >= 20
    ):
        drop = prior_b_rate - last_b_rate
        if drop >= 8:
            alerts.append(AlertItem(
                severity="warning", title="Blastocyst conversion is declining",
                detail=f"Blastocyst rate fell from {prior_b_rate}% to {last_b_rate}% over the last 30 days.",
                metric_key="blastocyst_rate",
            ))

    ops = _compute_operations(db, org_id, empty_filters)
    if ops["pregnancy_checks_due"] > 15:
        alerts.append(AlertItem(
            severity="warning", title="Pregnancy-check backlog building up",
            detail=f"{ops['pregnancy_checks_due']} transfers are due for a pregnancy check (estimated).",
            metric_key="pregnancy_checks_due",
        ))
    if ops["predictions_pending_outcome"] > 25:
        alerts.append(AlertItem(
            severity="info", title="Predictions awaiting outcome",
            detail=f"{ops['predictions_pending_outcome']} predictions have no recorded outcome yet.",
            metric_key="predictions_pending_outcome",
        ))

    severity_order = {"critical": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda a: severity_order[a.severity])
    return AlertsResponse(alerts=alerts)


@router.get("/performance", response_model=PerformanceResponse)
def get_performance(
    dimension: str = Query(..., pattern="^(donor|sire|protocol|technician)$"),
    limit: int = Query(10, ge=1, le=50),
    filters: DashboardFilterValues = Depends(get_dashboard_filters),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = current_user.organization_id
    start, end = resolve_date_range(filters.date_from, filters.date_to, anchor=_latest_activity_date(db, org_id))
    transfers = _fetch_transfers(db, org_id, filters, start, end)

    groups: dict[int, list[ETTransfer]] = defaultdict(list)
    labels: dict[int, str] = {}
    for t in transfers:
        key: Optional[int] = None
        label: Optional[str] = None
        if dimension == "donor":
            if t.embryo and t.embryo.donor_id:
                key = t.embryo.donor_id
                label = t.embryo.donor.tag_id if t.embryo.donor else None
        elif dimension == "sire":
            if t.embryo and t.embryo.sire_id:
                key = t.embryo.sire_id
                label = t.embryo.sire.name if t.embryo.sire else None
        elif dimension == "protocol":
            if t.protocol_id:
                key = t.protocol_id
                label = t.protocol.name if t.protocol else None
        else:
            if t.technician_id:
                key = t.technician_id
                label = t.technician.name if t.technician else None
        if key is None:
            continue
        groups[key].append(t)
        labels[key] = label or f"#{key}"

    rows: list[PerformanceRow] = []
    for key, items in groups.items():
        cleaned = [_clean_pregnancy_result(t.pc1_result) for t in items]
        checked = [c for c in cleaned if c is not None]
        insufficient = len(checked) < 5
        rate = None if insufficient else round(sum(1 for c in checked if c == "Pregnant") / len(checked) * 100, 1)
        rows.append(PerformanceRow(
            id=key, label=labels[key], n_transfers=len(items),
            pregnancy_rate=rate, insufficient_data=insufficient,
        ))
    # Select the most relevant rows by transfer volume, but DISPLAY them
    # grouped by label type (numeric-tagged donors/sires first in numeric
    # order, then name-tagged ones alphabetically) rather than interleaved
    # by transfer count — mixed numeric/alpha tags in one rank-ordered list
    # read as inconsistent even though the underlying tags are legitimate.
    rows.sort(key=lambda r: r.n_transfers, reverse=True)
    top_rows = rows[:limit]
    top_rows.sort(key=_natural_label_key)
    return PerformanceResponse(dimension=dimension, rows=top_rows)


def _natural_label_key(row: PerformanceRow) -> tuple:
    match = re.match(r"^(\d+)", row.label)
    if match:
        return (0, int(match.group(1)), row.label)
    return (1, 0, row.label.lower())


def _dq_row(table: str, field: str, total: int, missing: int, stale: bool) -> DataQualityRow:
    pct = round(missing / total * 100, 1) if total else 0.0
    return DataQualityRow(table=table, field=field, total=total, missing=missing, missing_pct=pct, stale=stale)


@router.get("/data-quality", response_model=DataQualityResponse)
def get_data_quality(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    org_id = current_user.organization_id
    stale_cutoff = date.today() - timedelta(days=45)
    rows: list[DataQualityRow] = []

    total_transfers = db.query(ETTransfer).filter(ETTransfer.organization_id == org_id).count()
    missing_pc1_stale = db.query(ETTransfer).filter(
        ETTransfer.organization_id == org_id, ETTransfer.pc1_result.is_(None), ETTransfer.et_date <= stale_cutoff,
    ).count()
    rows.append(_dq_row("et_transfers", "pc1_result", total_transfers, missing_pc1_stale, stale=True))

    total_embryos = db.query(Embryo).filter(Embryo.organization_id == org_id).count()
    missing_grade = db.query(Embryo).filter(Embryo.organization_id == org_id, Embryo.grade.is_(None)).count()
    rows.append(_dq_row("embryos", "grade", total_embryos, missing_grade, stale=False))

    missing_ff = db.query(Embryo).filter(
        Embryo.organization_id == org_id, Embryo.fresh_or_frozen.is_(None)
    ).count()
    rows.append(_dq_row("embryos", "fresh_or_frozen", total_embryos, missing_ff, stale=False))

    total_opu = db.query(OPUSession).filter(OPUSession.organization_id == org_id).count()
    missing_tech = db.query(OPUSession).filter(
        OPUSession.organization_id == org_id, OPUSession.technician_id.is_(None)
    ).count()
    rows.append(_dq_row("opu_sessions", "technician_id", total_opu, missing_tech, stale=False))

    missing_protocol = db.query(ETTransfer).filter(
        ETTransfer.organization_id == org_id, ETTransfer.protocol_id.is_(None)
    ).count()
    rows.append(_dq_row("et_transfers", "protocol_id", total_transfers, missing_protocol, stale=False))

    return DataQualityResponse(rows=rows)


@router.get("/ai-summary", response_model=AISummaryResponse)
def get_ai_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    org_id = current_user.organization_id
    pending = db.query(Prediction).filter(
        Prediction.organization_id == org_id, Prediction.actual_outcome.is_(None)
    ).count()

    high_risk = (
        db.query(Prediction)
        .options(joinedload(Prediction.transfer))
        .join(ETTransfer, Prediction.transfer_id == ETTransfer.transfer_id)
        .filter(
            Prediction.organization_id == org_id,
            ETTransfer.pc1_result.is_(None),
            Prediction.risk_band == "High",
        )
        .order_by(Prediction.predicted_at.desc())
        .limit(10)
        .all()
    )
    items = [
        HighRiskTransfer(
            transfer_id=p.transfer_id,
            et_date=p.transfer.et_date if p.transfer else None,
            probability=float(p.probability),
            risk_band=p.risk_band,
            predicted_at=p.predicted_at.isoformat(),
        )
        for p in high_risk if p.transfer_id is not None
    ]
    return AISummaryResponse(pending_predictions_count=pending, high_risk_transfers=items)
