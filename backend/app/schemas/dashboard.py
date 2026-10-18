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
    # None means "not in this role's view" (the server omits it), not zero.
    opu_sessions_today: Optional[int] = None
    ivf_batches_in_culture: Optional[int] = None
    embryos_pending_grading: Optional[int] = None
    transfers_scheduled_today: Optional[int] = None
    pregnancy_checks_due: Optional[int] = None
    predictions_pending_outcome: Optional[int] = None
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
    # Every high-risk transfer without a pregnancy check, not just the rows listed.
    high_risk_total: int
    # Probability at or above which a prediction is banded High (ml/config.py).
    high_risk_threshold: float
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


# --- Programme charts (GET /dashboard/charts) -------------------------------
# Rates are fractions (0-1), not percentages. A rate is None when the group has
# no transfers with a recorded outcome. Every rate uses n_with_outcome as its
# denominator; n_transfers counts all transfers in the group.


class GalleryGroup(BaseModel):
    n_with_outcome: int
    pregnant: int
    rate: Optional[float] = None


class GalleryKpis(BaseModel):
    pregnant: int
    open: int
    with_outcome: int
    total_transfers: int
    fresh_vs_frozen: dict[str, GalleryGroup]


class GalleryTrendRow(BaseModel):
    month: str
    n_transfers: int
    n_with_outcome: int
    n_pregnant: int
    pregnancy_rate: Optional[float] = None


class GalleryProtocolRow(BaseModel):
    protocol_id: Optional[int] = None
    protocol_name: str
    n_transfers: int
    n_with_outcome: int
    n_pregnant: int
    pregnancy_rate: Optional[float] = None
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None


class GalleryBreedRow(BaseModel):
    donor_breed: str
    n_transfers: int
    n_with_outcome: int
    n_pregnant: int
    pregnancy_rate: Optional[float] = None


class GalleryDonorRow(BaseModel):
    donor_id: Optional[int] = None
    donor_tag: str
    breed: Optional[str] = None
    n_transfers: int
    n_with_outcome: int
    n_pregnant: int
    pregnancy_rate: Optional[float] = None


class GalleryBinRow(BaseModel):
    range: str
    n_transfers: int
    n_with_outcome: int
    n_pregnant: int
    pregnancy_rate: Optional[float] = None
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None


class ChartsResponse(BaseModel):
    start: Optional[Date] = None
    end: Optional[Date] = None
    kpis: GalleryKpis
    trends: list[GalleryTrendRow]
    protocols: list[GalleryProtocolRow]
    breeds: list[GalleryBreedRow]
    donors: list[GalleryDonorRow]
    bins: list[GalleryBinRow]
