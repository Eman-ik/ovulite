"""Schemas for the laboratory workflow.

Counts on the lab board are exact where the data supports it and flagged
``is_estimated`` where they are inferred from dates rather than recorded
directly — the same discipline the vet board uses.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field

EmbryoStatus = Literal[
    "In Culture", "Transferable", "Frozen", "Assigned", "Transferred", "Discarded"
]


# ── IVM ──────────────────────────────────────────────────


class IVMBatchBase(BaseModel):
    ivm_date: Optional[date] = None
    medium: Optional[str] = None
    medium_lot: Optional[str] = None
    incubation_hours: Optional[Decimal] = Field(default=None, ge=0, le=96)
    temperature_c: Optional[Decimal] = Field(default=None, ge=30, le=42)
    co2_percent: Optional[Decimal] = Field(default=None, ge=0, le=20)
    o2_percent: Optional[Decimal] = Field(default=None, ge=0, le=100)
    oocytes_in: Optional[int] = Field(default=None, ge=0, le=500)
    mature_oocytes_out: Optional[int] = Field(default=None, ge=0, le=500)
    embryologist_id: Optional[int] = None
    notes: Optional[str] = None


class IVMBatchCreate(IVMBatchBase):
    pass


class IVMBatchUpdate(IVMBatchBase):
    pass


class IVMBatchResponse(IVMBatchBase):
    ivm_batch_id: int
    opu_id: int
    embryologist_name: Optional[str] = None
    maturation_rate_pct: Optional[float] = None
    """out/in as a percentage. None when either count is missing — a rate
    without its denominator is not interpretable."""

    model_config = {"from_attributes": True}


# ── Culture timeline ─────────────────────────────────────


class EmbryoObservationBase(BaseModel):
    observation_date: date
    day_number: int = Field(ge=0, le=12)
    stage: Optional[int] = Field(default=None, ge=1, le=9)
    grade: Optional[int] = Field(default=None, ge=1, le=4)
    morphology: Optional[str] = None
    is_arrested: Optional[bool] = None
    cell_count: Optional[int] = Field(default=None, ge=0, le=500)
    expansion_diameter_um: Optional[Decimal] = Field(default=None, ge=0, le=500)
    embryologist_id: Optional[int] = None
    notes: Optional[str] = None


class EmbryoObservationCreate(EmbryoObservationBase):
    pass


class EmbryoObservationUpdate(BaseModel):
    observation_date: Optional[date] = None
    stage: Optional[int] = Field(default=None, ge=1, le=9)
    grade: Optional[int] = Field(default=None, ge=1, le=4)
    morphology: Optional[str] = None
    is_arrested: Optional[bool] = None
    cell_count: Optional[int] = Field(default=None, ge=0, le=500)
    expansion_diameter_um: Optional[Decimal] = Field(default=None, ge=0, le=500)
    embryologist_id: Optional[int] = None
    notes: Optional[str] = None


class EmbryoObservationResponse(EmbryoObservationBase):
    observation_id: int
    embryo_id: int
    stage_label: Optional[str] = None
    embryologist_name: Optional[str] = None

    model_config = {"from_attributes": True}


class EmbryoTimeline(BaseModel):
    embryo_id: int
    donor_tag: Optional[str]
    sire_name: Optional[str]
    status: Optional[str]
    final_stage: Optional[int]
    final_grade: Optional[int]
    fresh_or_frozen: Optional[str]
    observations: list[EmbryoObservationResponse]
    transfer_id: Optional[int]
    note: str


# ── Inventory ────────────────────────────────────────────


class InventoryRow(BaseModel):
    embryo_id: int
    donor_tag: Optional[str]
    sire_name: Optional[str]
    opu_date: Optional[date]
    stage: Optional[int]
    grade: Optional[int]
    fresh_or_frozen: Optional[str]
    cane_number: Optional[str]
    freezing_date: Optional[date]
    status: Optional[str]
    transfer_id: Optional[int]
    observation_count: int


class InventorySummary(BaseModel):
    status: Optional[str]
    count: int


class InventoryResponse(BaseModel):
    rows: list[InventoryRow]
    total: int
    page: int
    page_size: int
    summary: list[InventorySummary]
    note: str


class StatusChange(BaseModel):
    status: EmbryoStatus
    discarded_reason: Optional[str] = None


# ── Lab board ────────────────────────────────────────────


class LabCount(BaseModel):
    key: str
    label: str
    count: int
    is_estimated: bool = False
    basis: str


class WorkflowStage(BaseModel):
    label: str
    count: int | None
    """None when the underlying field is entirely unrecorded — distinct from
    a genuine zero."""
    unavailable_reason: Optional[str] = None


class LabBoardResponse(BaseModel):
    as_of: date
    counts: list[LabCount]
    workflow: list[WorkflowStage]
    note: str


class IVMBatchWithSession(IVMBatchResponse):
    donor_tag: Optional[str] = None
    opu_date: Optional[date] = None


class OocyteGradeSummary(BaseModel):
    opu_id: int
    donor_tag: Optional[str]
    opu_date: date
    oocytes_recovered: Optional[int]
    grade_a_oocytes: Optional[int]
    grade_b_oocytes: Optional[int]
    grade_c_oocytes: Optional[int]
    degenerated_oocytes: Optional[int]
    graded_total: int
    ungraded: Optional[int]
    ivm_batches: list[IVMBatchResponse]
    created_at: Optional[datetime] = None


class OocyteGradeUpdate(BaseModel):
    """Just the grade tally — see the endpoint for why this is not a full PUT."""

    grade_a_oocytes: Optional[int] = Field(default=None, ge=0, le=200)
    grade_b_oocytes: Optional[int] = Field(default=None, ge=0, le=200)
    grade_c_oocytes: Optional[int] = Field(default=None, ge=0, le=200)
    degenerated_oocytes: Optional[int] = Field(default=None, ge=0, le=200)
    oocyte_morphology_notes: Optional[str] = None
