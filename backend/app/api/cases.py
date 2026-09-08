"""Case Records / Case Detail API — a read-only traceability view over ET
transfers and their full lineage, used by the frontend's Case Records and
Case Detail pages. No new data model: everything here is computed by
joining existing entities (ET Transfer, Donor, Sire, Recipient, Protocol,
Technician, Prediction). Fields with no real backing data (a grading
prediction history, an audit log) are returned as null/empty rather than
fabricated — see schemas/cases.py for what each field means and why.
"""

import math
import json
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.api.transfers import _clean_pregnancy_result
from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.embryo import Embryo
from app.models.et_transfer import ETTransfer
from app.models.prediction import Prediction
from app.models.user import User
from app.models.case_metadata import CaseAudit
from app.schemas.cases import (
    CaseDetailResponse,
    CaseDonorInfo,
    CasePregnancyPrediction,
    CaseRecipientInfo,
    CaseRecordResponse,
    CaseSimilarCase,
    CaseSireInfo,
)
from app.schemas.common import PaginatedResponse

router = APIRouter()

_OUTCOME_MAP = {"Pregnant": "pregnant", "Open": "open", "Recheck": "recheck"}
# A prediction is "low confidence" for QC-flagging purposes when it sits
# close to a coin flip either way, not just on the low end.
_LOW_CONFIDENCE_BAND = (0.35, 0.65)


def _outcome_for(transfer: ETTransfer) -> str:
    cleaned = _clean_pregnancy_result(transfer.pc1_result)
    return _OUTCOME_MAP.get(cleaned, "pending")


def _with_joins(db: Session):
    return db.query(ETTransfer).options(
        joinedload(ETTransfer.embryo).joinedload(Embryo.donor),
        joinedload(ETTransfer.embryo).joinedload(Embryo.sire),
        joinedload(ETTransfer.recipient),
        joinedload(ETTransfer.technician),
        joinedload(ETTransfer.protocol),
    )


def _latest_prediction(db: Session, org_id: int, transfer_id: int) -> Optional[Prediction]:
    return (
        db.query(Prediction)
        .filter(Prediction.organization_id == org_id, Prediction.transfer_id == transfer_id)
        .order_by(Prediction.predicted_at.desc())
        .first()
    )


def _to_case_record(t: ETTransfer, prediction: Optional[Prediction]) -> CaseRecordResponse:
    donor_tag = t.embryo.donor.tag_id if t.embryo and t.embryo.donor else None
    sire_name = t.embryo.sire.name if t.embryo and t.embryo.sire else None
    cleaned = _clean_pregnancy_result(t.pc1_result)
    return CaseRecordResponse(
        id=str(t.transfer_id),
        transfer_id=str(t.transfer_id),
        case_date=t.et_date,
        donor_tag=donor_tag,
        sire_name=sire_name,
        recipient_tag=t.recipient.tag_id if t.recipient else None,
        protocol_name=t.protocol.name if t.protocol else None,
        outcome=_outcome_for(t),
        pregnancy_prediction_probability=float(prediction.probability) if prediction else None,
        actual_result=cleaned,
        technician_name=t.technician.name if t.technician else None,
        embryo_grade=str(t.embryo.grade) if t.embryo and t.embryo.grade is not None else None,
        cl_size_mm=float(t.cl_measure_mm) if t.cl_measure_mm is not None else None,
        notes=None,  # ETTransfer has no notes column — honestly always empty.
        follow_up_date=t.pc2_date,
    )


@router.get("/", response_model=PaginatedResponse[CaseRecordResponse])
def list_cases(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: Optional[str] = None,
    outcome: Optional[str] = None,
    protocol: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List ET transfers as case records, with their joined lineage."""
    org_id = current_user.organization_id
    q = _with_joins(db).filter(ETTransfer.organization_id == org_id)
    if date_from is not None:
        q = q.filter(ETTransfer.et_date >= date_from)
    if date_to is not None:
        q = q.filter(ETTransfer.et_date <= date_to)
    transfers = q.order_by(ETTransfer.et_date.desc(), ETTransfer.transfer_id.desc()).all()

    if search:
        needle = search.strip().lower()
        def _matches(t: ETTransfer) -> bool:
            haystack = [
                str(t.transfer_id),
                str(t.et_number) if t.et_number is not None else "",
                str(t.embryo_id) if t.embryo_id is not None else "",
                t.embryo.sire.name if t.embryo and t.embryo.sire else "",
                t.embryo.donor.tag_id if t.embryo and t.embryo.donor else "",
                t.recipient.tag_id if t.recipient else "",
            ]
            return any(needle in (h or "").lower() for h in haystack)
        transfers = [t for t in transfers if _matches(t)]

    if outcome:
        transfers = [t for t in transfers if _outcome_for(t) == outcome.lower()]

    if protocol:
        needle = protocol.strip().lower()
        transfers = [t for t in transfers if t.protocol and needle in t.protocol.name.lower()]

    total = len(transfers)
    start = (page - 1) * page_size
    page_transfers = transfers[start:start + page_size]

    # Keep only the latest prediction per transfer (rows are sorted oldest
    # to newest below, so the last assignment per key wins).
    latest_by_transfer: dict[int, Prediction] = {}
    for p in sorted(
        db.query(Prediction).filter(
            Prediction.organization_id == org_id,
            Prediction.transfer_id.in_([t.transfer_id for t in page_transfers]),
        ),
        key=lambda p: p.predicted_at,
    ):
        if p.transfer_id is not None:
            latest_by_transfer[p.transfer_id] = p

    items = [_to_case_record(t, latest_by_transfer.get(t.transfer_id)) for t in page_transfers]
    return PaginatedResponse(
        items=items, total=total, page=page, page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/{transfer_id}", response_model=CaseDetailResponse)
def get_case_detail(transfer_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    org_id = current_user.organization_id
    t = _with_joins(db).filter(
        ETTransfer.transfer_id == transfer_id, ETTransfer.organization_id == org_id
    ).first()
    if not t:
        raise HTTPException(status_code=404, detail="Case not found")

    donor = t.embryo.donor if t.embryo else None
    sire = t.embryo.sire if t.embryo else None
    cleaned = _clean_pregnancy_result(t.pc1_result)

    prediction = _latest_prediction(db, org_id, transfer_id)
    pregnancy_prediction = None
    if prediction:
        pregnancy_prediction = CasePregnancyPrediction(
            probability=float(prediction.probability),
            confidence_lower=float(prediction.confidence_lower) if prediction.confidence_lower is not None else None,
            confidence_upper=float(prediction.confidence_upper) if prediction.confidence_upper is not None else None,
            risk_band=prediction.risk_band,
            model_version=prediction.model_version,
        )

    # Simple, honest per-case QC flags — real conditions checked directly
    # against this case's own data, not the aggregate QC pipeline (Module 7
    # produces technician/batch-level anomalies, not per-transfer ones).
    qc_flags: list[str] = []
    if t.cl_measure_mm is None:
        qc_flags.append("Missing CL measurement")
    if not t.embryo or t.embryo.grade is None:
        qc_flags.append("Missing embryo grade")
    if not t.technician_id:
        qc_flags.append("Missing technician")
    if not t.protocol_id:
        qc_flags.append("Missing protocol")
    if prediction and _LOW_CONFIDENCE_BAND[0] <= float(prediction.probability) <= _LOW_CONFIDENCE_BAND[1]:
        qc_flags.append("Low-confidence pregnancy prediction")
    if prediction and prediction.is_ood:
        qc_flags.append("Prediction flagged as outside the model's training experience")

    # Similar cases: other transfers sharing this case's donor+sire pairing,
    # most recent first. "Prediction accuracy" is only computed where both
    # a stored prediction and a resolved actual outcome exist — how close
    # the predicted probability was to the true binary result (1.0 = spot
    # on). Never fabricated for cases with no prediction or no outcome yet.
    similar_cases: list[CaseSimilarCase] = []
    if t.embryo and t.embryo.donor_id and t.embryo.sire_id:
        similar_q = (
            _with_joins(db)
            .join(Embryo, ETTransfer.embryo_id == Embryo.embryo_id)
            .filter(
                ETTransfer.organization_id == org_id,
                ETTransfer.transfer_id != transfer_id,
                Embryo.donor_id == t.embryo.donor_id,
                Embryo.sire_id == t.embryo.sire_id,
            )
            .order_by(ETTransfer.et_date.desc())
            .limit(5)
        )
        for other in similar_q.all():
            other_cleaned = _clean_pregnancy_result(other.pc1_result)
            other_prediction = _latest_prediction(db, org_id, other.transfer_id)
            accuracy = None
            if other_prediction and other_cleaned in ("Pregnant", "Open"):
                actual_binary = 1.0 if other_cleaned == "Pregnant" else 0.0
                accuracy = round(1.0 - abs(float(other_prediction.probability) - actual_binary), 3)
            similar_cases.append(CaseSimilarCase(
                transfer_id=str(other.transfer_id),
                outcome=_outcome_for(other),
                prediction_accuracy=accuracy,
            ))

    return CaseDetailResponse(
        id=str(t.transfer_id),
        transfer_id=str(t.transfer_id),
        case_date=t.et_date,
        outcome=_outcome_for(t),
        donor=CaseDonorInfo(
            tag_id=donor.tag_id if donor else None,
            breed=donor.breed if donor else None,
            birth_weight_epd=float(donor.birth_weight_epd) if donor and donor.birth_weight_epd is not None else None,
        ),
        sire=CaseSireInfo(
            name=sire.name if sire else None,
            breed=sire.breed if sire else None,
            semen_type=sire.semen_type if sire else None,
        ),
        recipient=CaseRecipientInfo(
            tag_id=t.recipient.tag_id if t.recipient else None,
            farm_location=t.recipient.farm_location if t.recipient else None,
            cow_or_heifer=t.recipient.cow_or_heifer if t.recipient else None,
        ),
        embryo_stage=t.embryo.stage if t.embryo else None,
        embryo_grade=str(t.embryo.grade) if t.embryo and t.embryo.grade is not None else None,
        cl_size_mm=float(t.cl_measure_mm) if t.cl_measure_mm is not None else None,
        fresh_or_frozen=t.embryo.fresh_or_frozen if t.embryo else None,
        protocol_name=t.protocol.name if t.protocol else None,
        technician_name=t.technician.name if t.technician else None,
        pregnancy_prediction=pregnancy_prediction,
        grading_prediction=None,
        qc_flags=qc_flags,
        qc_passed=len(qc_flags) == 0,
        actual_result=cleaned,
        ultrasound_date=t.pc1_date,
        follow_up_notes=None,
        audit_trail=[{"timestamp": row.created_at.isoformat(), "action": row.action, "user": row.actor,
                      "details": json.dumps(row.details, default=str)} for row in db.query(CaseAudit).filter_by(
                          transfer_id=transfer_id, organization_id=org_id).order_by(CaseAudit.audit_id.desc()).limit(100)],
        similar_cases=similar_cases,
    )
