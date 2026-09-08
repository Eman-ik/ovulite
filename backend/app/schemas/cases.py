"""Pydantic schemas for the Case Records / Case Detail views.

A "case" is one ET Transfer viewed together with its full lineage (donor,
sire, recipient, embryo, protocol, technician) and any AI prediction made
for it — the read-only traceability view the frontend's Case Records page
needs. Every field here is sourced from real data; fields with no backing
data (e.g. no prediction was ever run) are returned as null rather than
fabricated.
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel


class CaseRecordResponse(BaseModel):
    id: str
    transfer_id: str
    case_date: date
    donor_tag: Optional[str] = None
    sire_name: Optional[str] = None
    recipient_tag: Optional[str] = None
    protocol_name: Optional[str] = None
    outcome: str  # "pregnant" | "open" | "recheck" | "pending"
    pregnancy_prediction_probability: Optional[float] = None
    actual_result: Optional[str] = None
    technician_name: Optional[str] = None
    embryo_grade: Optional[str] = None
    cl_size_mm: Optional[float] = None
    notes: Optional[str] = None
    follow_up_date: Optional[date] = None


class CaseDonorInfo(BaseModel):
    tag_id: Optional[str] = None
    breed: Optional[str] = None
    birth_weight_epd: Optional[float] = None


class CaseSireInfo(BaseModel):
    name: Optional[str] = None
    breed: Optional[str] = None
    semen_type: Optional[str] = None


class CaseRecipientInfo(BaseModel):
    tag_id: Optional[str] = None
    farm_location: Optional[str] = None
    cow_or_heifer: Optional[str] = None


class CasePregnancyPrediction(BaseModel):
    probability: float
    confidence_lower: Optional[float] = None
    confidence_upper: Optional[float] = None
    risk_band: Optional[str] = None
    model_version: Optional[str] = None


class CaseSimilarCase(BaseModel):
    transfer_id: str
    outcome: str
    prediction_accuracy: Optional[float] = None


class CaseDetailResponse(BaseModel):
    id: str
    transfer_id: str
    case_date: date
    outcome: str

    donor: CaseDonorInfo
    sire: CaseSireInfo
    recipient: CaseRecipientInfo

    embryo_stage: Optional[int] = None
    embryo_grade: Optional[str] = None
    cl_size_mm: Optional[float] = None
    fresh_or_frozen: Optional[str] = None

    protocol_name: Optional[str] = None
    technician_name: Optional[str] = None

    # Null when no prediction has ever been generated for this transfer.
    pregnancy_prediction: Optional[CasePregnancyPrediction] = None
    # Always null — grading predictions (POST /grade/embryo) are computed
    # on demand and never persisted, so there is no historical record to
    # show here. Not fabricated.
    grading_prediction: None = None

    qc_flags: list[str] = []
    qc_passed: bool = True

    actual_result: Optional[str] = None
    ultrasound_date: Optional[date] = None
    follow_up_notes: Optional[str] = None

    # Attributable clinical record events, newest first; legacy events are not fabricated.
    audit_trail: list[dict] = []

    similar_cases: list[CaseSimilarCase] = []
