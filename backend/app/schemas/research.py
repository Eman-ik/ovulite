"""Schemas for the researcher/data-analyst comparative analyses.

Every rate on this surface is reported with the denominator it was computed
from, and rates below the minimum sample size are returned as ``None`` with
``insufficient_data`` set rather than as a misleadingly precise percentage.
"""

from pydantic import BaseModel


class RateCell(BaseModel):
    """A proportion with its denominator and a Wilson 95% interval."""

    n: int
    """Records in the group (the denominator)."""
    successes: int
    rate_pct: float | None
    """None when n is below the minimum sample size."""
    ci_low_pct: float | None
    ci_high_pct: float | None
    insufficient_data: bool


class DonorSireCell(RateCell):
    donor_id: int
    donor_tag: str
    sire_id: int
    sire_name: str


class DonorSireResponse(BaseModel):
    min_sample_size: int
    donors: list[str]
    """Donor tags present in the matrix, ordered by total transfers."""
    sires: list[str]
    cells: list[DonorSireCell]
    overall: RateCell
    """The org-wide rate, so a cell can be read against a baseline."""
    note: str


class ProtocolComparisonRow(RateCell):
    protocol_id: int
    protocol_name: str
    is_baseline: bool
    """True for the protocol with the largest sample, used as the comparator."""
    diff_vs_baseline_pp: float | None
    """Percentage-point difference from the baseline protocol."""
    p_value: float | None
    """Two-proportion z-test against the baseline. None for the baseline row."""
    significant_at_05: bool | None


class ProtocolComparisonResponse(BaseModel):
    min_sample_size: int
    baseline_protocol: str | None
    rows: list[ProtocolComparisonRow]
    note: str


class FactorLevel(RateCell):
    label: str


class OutcomeFactor(BaseModel):
    key: str
    label: str
    levels: list[FactorLevel]
    available: bool
    """False when the field has no usable variation in this dataset."""
    unavailable_reason: str | None


class OutcomeFactorsResponse(BaseModel):
    min_sample_size: int
    factors: list[OutcomeFactor]
    overall: RateCell
