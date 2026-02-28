"""Pydantic schemas for Analytics API (Phase 5)."""

from pydantic import BaseModel, Field


# ── KPIs ─────────────────────────────────────────────────

class DateRange(BaseModel):
    first: str | None = None
    last: str | None = None
    span_months: int = 0


class EntityCounts(BaseModel):
    donors: int = 0
    recipients: int = 0
    technicians: int = 0
    protocols: int = 0
    sires: int = 0


class FreshFrozenStats(BaseModel):
    n: int
    pregnant: int
    rate: float | None = None


class KPIResponse(BaseModel):
    total_transfers: int
    with_outcome: int
    pregnant: int
    open: int
    pregnancy_rate: float | None
    embryo_utilization: float | None
    unique_embryos: int | None
    date_range: DateRange
    entity_counts: EntityCounts
    fresh_vs_frozen: dict[str, FreshFrozenStats] = {}


class MonthlyTrend(BaseModel):
    month: str
    n_transfers: int
    n_pregnant: int
    pregnancy_rate: float
    avg_cl: float | None = None


class FunnelStage(BaseModel):
    stage: str
    count: int
    rate_from_previous: float | None = None


class FunnelResponse(BaseModel):
    stages: list[FunnelStage]


# ── Protocol Analysis ────────────────────────────────────

class ProtocolRate(BaseModel):
    protocol_name: str
    n_transfers: int
    n_pregnant: int
    pregnancy_rate: float
    ci_lower: float
    ci_upper: float


class ProtocolRatesResponse(BaseModel):
    protocols: list[ProtocolRate]
    total: int


class ProtocolRegression(BaseModel):
    coefficients: dict[str, float] = {}
    odds_ratios: dict[str, float] = {}
    intercept: float = 0.0
    n_samples: int = 0
    feature_names: list[str] = []
    protocol_classes: list[str] = []
    error: str | None = None


class FeatureImportance(BaseModel):
    mean: float
    std: float


class ProtocolImportance(BaseModel):
    feature_importances: dict[str, FeatureImportance] = {}
    protocol_total_importance: float = 0.0
    n_samples: int = 0
    error: str | None = None


# ── Donor Analysis ───────────────────────────────────────

class DonorStats(BaseModel):
    donor_tag: str
    breed: str | None = None
    n_transfers: int
    n_pregnant: int
    pregnancy_rate: float
    avg_cl: float | None = None
    first_date: str | None = None
    last_date: str | None = None
    active_months: int = 0


class DonorStatsResponse(BaseModel):
    donors: list[DonorStats]
    total: int


class DonorTrendPoint(BaseModel):
    month: str
    n_transfers: int
    n_pregnant: int
    pregnancy_rate: float


class DonorTrendsResponse(BaseModel):
    trends: dict[str, list[DonorTrendPoint]]


class BreedStat(BaseModel):
    donor_breed: str
    n_transfers: int
    n_pregnant: int
    pregnancy_rate: float
    avg_cl: float | None = None


class BreedStatsResponse(BaseModel):
    breeds: list[BreedStat]
    total: int


# ── Biomarker Analysis ───────────────────────────────────

class BiomarkerBin(BaseModel):
    range: str
    n: int
    pregnancy_rate: float
    ci_lower: float | None = None
    ci_upper: float | None = None
    mean_value: float | None = None


class BiomarkerResult(BaseModel):
    biomarker: str | None = None
    bins: list[BiomarkerBin]
    optimal_range: BiomarkerBin | None = None
    optimal_bin: BiomarkerBin | None = None
    overall_rate: float | None = None
    total_records: int = 0
    error: str | None = None


class BiomarkersResponse(BaseModel):
    cl_measure: BiomarkerResult | None = None
    bc_score: BiomarkerResult | None = None
    heat_day: BiomarkerResult | None = None
