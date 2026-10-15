"""Response schemas for the homepage dashboard endpoints (live-query, not cached)."""

from datetime import date
from datetime import date as Date
from typing import Optional

from pydantic import BaseModel


class SparklinePoint(BaseModel):
    bucket: str
    value: Optional[float] = None


class KpiItem(BaseModel):
    key: str
    label: str
    value: Optional[float] = None
    unit: str
    delta_pct: Optional[float] = None
    delta_direction: Optional[str] = None
    sparkline: list[SparklinePoint] = []
    comparison_label: str


class KpiResponse(BaseModel):
    kpis: list[KpiItem]
    date_from: date
    date_to: date


class FunnelStage(BaseModel):
    name: str
    value: int
    conversion_pct_from_previous: Optional[float] = None
    conversion_pct_from_first: Optional[float] = None
    # True where the stage above it counts a different set of animals, so a
    # conversion percentage between the two would be meaningless. The embryos
    # banked inside a date window are not the embryos transferred inside it,
    # which is how the funnel used to report a 243% conversion.
    cohort_break: bool = False
    cohort_note: Optional[str] = None


class OmittedFunnelStage(BaseModel):
    name: str
    reason: str


class FunnelResponse(BaseModel):
    stages: list[FunnelStage]
    omitted_stages: list[OmittedFunnelStage]


class TrendPoint(BaseModel):
    bucket_label: str
    value: Optional[float] = None
    n: int


class TrendResponse(BaseModel):
    metric: str
    granularity: str
    points: list[TrendPoint]


class OperationsResponse(BaseModel):
    opu_sessions_today: int
    ivf_batches_in_culture: int
    embryos_pending_grading: int
    transfers_scheduled_today: int
    pregnancy_checks_due: int
    predictions_pending_outcome: int
    estimated_fields: list[str]


class PipelineRow(BaseModel):
    stage: str
    entity_id: int
    label: str
    # Named Date in the import: a field called `date` would otherwise shadow the type here.
    date: Optional[Date] = None
    detail: Optional[str] = None


class AlertItem(BaseModel):
    severity: str
    title: str
    detail: str
    metric_key: str


class AlertsResponse(BaseModel):
    alerts: list[AlertItem]


class PerformanceRow(BaseModel):
    id: int
    label: str
    n_transfers: int
    pregnancy_rate: Optional[float] = None
    insufficient_data: bool = False


class PerformanceResponse(BaseModel):
    dimension: str
    rows: list[PerformanceRow]


class DataQualityRow(BaseModel):
    table: str
    field: str
    total: int
    missing: int
    missing_pct: float
    stale: bool


class DataQualityResponse(BaseModel):
    rows: list[DataQualityRow]


class HighRiskTransfer(BaseModel):
    transfer_id: int
    et_date: Optional[date] = None
    probability: float
    risk_band: Optional[str] = None
    predicted_at: str


class AISummaryResponse(BaseModel):
    pending_predictions_count: int
    high_risk_transfers: list[HighRiskTransfer]


class LabeledOption(BaseModel):
    id: int
    label: str


class DashboardFilterOptions(BaseModel):
    donors: list[LabeledOption]
    sires: list[LabeledOption]
    technicians: list[LabeledOption]
    protocols: list[LabeledOption]
    breeds: list[str]
    farm_locations: list[str]
    fresh_or_frozen: list[str]
