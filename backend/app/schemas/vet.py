"""Schemas for the veterinarian / ET workflow.

Every optional field is genuinely optional: a vet records what they observed,
and an unrecorded finding stays null rather than being defaulted to something
that reads as an observation.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field

Eligibility = Literal["Excellent", "Acceptable", "Not Recommended"]
Quality = Literal["Good", "Fair", "Poor"]
Side = Literal["Left", "Right"]
CheckResult = Literal["Pregnant", "Open", "Recheck", "Lost"]
CheckMethod = Literal["Ultrasound", "Rectal Palpation", "Blood Test", "Other"]
CalvingOutcome = Literal["Live Birth", "Stillbirth", "Abortion"]
CalfSex = Literal["Male", "Female", "Unknown"]


# ── Recipient evaluation ─────────────────────────────────


class RecipientEvaluationBase(BaseModel):
    evaluation_date: date
    technician_id: Optional[int] = None
    cl_present: Optional[bool] = None
    cl_side: Optional[Side] = None
    cl_diameter_mm: Optional[Decimal] = Field(default=None, ge=0, le=60)
    cl_quality: Optional[Quality] = None
    follicle_count: Optional[int] = Field(default=None, ge=0, le=100)
    largest_follicle_mm: Optional[Decimal] = Field(default=None, ge=0, le=60)
    uterine_tone: Optional[Quality] = None
    progesterone_ng_ml: Optional[Decimal] = Field(default=None, ge=0, le=100)
    body_condition_score: Optional[Decimal] = Field(default=None, ge=1, le=5)
    eligibility: Optional[Eligibility] = None
    notes: Optional[str] = None
    transfer_id: Optional[int] = None


class RecipientEvaluationCreate(RecipientEvaluationBase):
    pass


class RecipientEvaluationUpdate(BaseModel):
    evaluation_date: Optional[date] = None
    technician_id: Optional[int] = None
    cl_present: Optional[bool] = None
    cl_side: Optional[Side] = None
    cl_diameter_mm: Optional[Decimal] = Field(default=None, ge=0, le=60)
    cl_quality: Optional[Quality] = None
    follicle_count: Optional[int] = Field(default=None, ge=0, le=100)
    largest_follicle_mm: Optional[Decimal] = Field(default=None, ge=0, le=60)
    uterine_tone: Optional[Quality] = None
    progesterone_ng_ml: Optional[Decimal] = Field(default=None, ge=0, le=100)
    body_condition_score: Optional[Decimal] = Field(default=None, ge=1, le=5)
    eligibility: Optional[Eligibility] = None
    notes: Optional[str] = None
    transfer_id: Optional[int] = None


class RecipientEvaluationResponse(RecipientEvaluationBase):
    evaluation_id: int
    recipient_id: int
    recipient_tag: Optional[str] = None
    technician_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Pregnancy check ──────────────────────────────────────


class PregnancyCheckBase(BaseModel):
    check_date: date
    result: CheckResult
    method: Optional[CheckMethod] = None
    technician_id: Optional[int] = None
    notes: Optional[str] = None


class PregnancyCheckCreate(PregnancyCheckBase):
    pass


class PregnancyCheckUpdate(BaseModel):
    check_date: Optional[date] = None
    result: Optional[CheckResult] = None
    method: Optional[CheckMethod] = None
    technician_id: Optional[int] = None
    notes: Optional[str] = None


class PregnancyCheckResponse(PregnancyCheckBase):
    check_id: int
    transfer_id: int
    days_post_transfer: Optional[int] = None
    technician_name: Optional[str] = None
    implausible_offset: bool = False
    """True when days_post_transfer falls outside 0-120 — a check dated before
    its own transfer, or improbably long after it. Surfaced rather than
    silently corrected, because it signals a date-entry error upstream."""
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Calving ──────────────────────────────────────────────


class CalvingRecordBase(BaseModel):
    calving_date: date
    outcome: CalvingOutcome
    calf_sex: Optional[CalfSex] = None
    calf_weight_kg: Optional[Decimal] = Field(default=None, ge=0, le=120)
    gestation_days: Optional[int] = Field(default=None, ge=150, le=330)
    assisted: Optional[bool] = None
    notes: Optional[str] = None


class CalvingRecordCreate(CalvingRecordBase):
    pass


class CalvingRecordUpdate(BaseModel):
    calving_date: Optional[date] = None
    outcome: Optional[CalvingOutcome] = None
    calf_sex: Optional[CalfSex] = None
    calf_weight_kg: Optional[Decimal] = Field(default=None, ge=0, le=120)
    gestation_days: Optional[int] = Field(default=None, ge=150, le=330)
    assisted: Optional[bool] = None
    notes: Optional[str] = None


class CalvingRecordResponse(CalvingRecordBase):
    calving_id: int
    transfer_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Outcome chain (read model) ───────────────────────────


class TransferOutcomeChain(BaseModel):
    """The full clinical history of one transfer, in order."""

    transfer_id: int
    et_date: Optional[date]
    recipient_tag: Optional[str]
    checks: list[PregnancyCheckResponse]
    calving: Optional[CalvingRecordResponse]
    current_status: str
    """Derived from the latest check plus any calving record."""


class RetentionStage(BaseModel):
    label: str
    n: int
    """Transfers with a diagnosis at this stage."""
    pregnant: int
    rate_pct: float | None
    retained_from_previous_pct: float | None


class RetentionResponse(BaseModel):
    stages: list[RetentionStage]
    live_birth_tracked: bool
    """False while calving_records is empty — the funnel then says so instead
    of reporting a live birth rate of zero."""
    live_birth: Optional[RetentionStage] = None
    note: str
