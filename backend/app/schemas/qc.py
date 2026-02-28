"""Pydantic schemas for Lab QC & Anomaly Detection API."""

from pydantic import BaseModel, Field


class QCAlert(BaseModel):
    """A single QC alert."""
    alert_type: str = Field(..., description="Alert source: isolation_forest, ewma_violation, cusum_shift")
    entity_type: str = Field(..., description="What entity: technician_batch, system_metric")
    entity_id: str = Field(..., description="Entity identifier")
    severity: str = Field(..., description="info, warning, or critical")
    metric: str
    metric_value: float | None = None
    baseline_value: float | None = None
    description: str = ""
    period: str | None = None
    timestamp: str | None = None


class QCAlertsResponse(BaseModel):
    """Response for GET /qc/anomalies."""
    alerts: list[QCAlert]
    total: int
    critical_count: int = 0
    warning_count: int = 0
    info_count: int = 0


class EWMAPoint(BaseModel):
    """Single point on an EWMA chart."""
    value: float
    ewma: float
    target: float
    ucl: float
    lcl: float
    out_of_control: bool


class CUSUMPoint(BaseModel):
    """Single point on a CUSUM chart."""
    value: float
    cusum_pos: float
    cusum_neg: float
    threshold_pos: float
    threshold_neg: float
    shift_detected: bool
    shift_direction: str


class ControlChartData(BaseModel):
    """Data for a single metric's control charts."""
    metric: str
    periods: list[str]
    ewma: list[EWMAPoint]
    cusum: list[CUSUMPoint]
    alerts: list[QCAlert]


class QCChartsResponse(BaseModel):
    """Response for GET /qc/charts."""
    charts: list[ControlChartData]
    metrics: list[str]


class TechnicianQCStats(BaseModel):
    """QC statistics for a single technician."""
    technician_name: str
    transfer_count: int
    pregnancy_rate: float | None
    avg_cl_measure: float | None
    std_cl_measure: float | None
    avg_embryo_grade: float | None
    avg_bc_score: float | None
    preg_rate_vs_mean: float | None


class TechnicianStatsResponse(BaseModel):
    """Response for GET /qc/technicians."""
    technicians: list[TechnicianQCStats]
    total: int
    global_pregnancy_rate: float | None


class QCSummary(BaseModel):
    """QC pipeline summary."""
    total_records: int
    total_batches: int
    anomalous_batches: int
    anomaly_rate: float
    chart_alerts: int
    total_alerts: int
    technicians_analyzed: int
    protocols_analyzed: int
    months_analyzed: int
