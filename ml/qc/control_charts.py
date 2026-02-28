"""EWMA and CUSUM control charts (ROADMAP task 4.3).

Implements:
- EWMA (Exponentially Weighted Moving Average) for detecting gradual drift
- CUSUM (Cumulative Sum) for detecting persistent shifts
Both are standard SPC (Statistical Process Control) techniques.
"""

import logging

import numpy as np
import pandas as pd

from .config import (
    CUSUM_ALLOWANCE,
    CUSUM_THRESHOLD,
    EWMA_LAMBDA,
    EWMA_SIGMA_MULTIPLIER,
)

logger = logging.getLogger(__name__)


def compute_ewma(
    series: pd.Series,
    lam: float = EWMA_LAMBDA,
    sigma_mult: float = EWMA_SIGMA_MULTIPLIER,
) -> pd.DataFrame:
    """Compute EWMA control chart for a time-ordered metric series.

    Parameters
    ----------
    series : Time-ordered metric values (e.g. monthly pregnancy rate)
    lam : EWMA smoothing factor (0 < λ ≤ 1)
    sigma_mult : Control limit multiplier (typically 3 for 3σ)

    Returns
    -------
    DataFrame with columns:
        value, ewma, ucl (upper control limit), lcl (lower control limit),
        out_of_control (bool)
    """
    values = series.dropna().values.astype(float)
    n = len(values)
    if n < 3:
        return pd.DataFrame()

    target = np.mean(values)
    sigma = np.std(values, ddof=1)

    ewma = np.zeros(n)
    ewma[0] = values[0]

    for i in range(1, n):
        ewma[i] = lam * values[i] + (1 - lam) * ewma[i - 1]

    # Control limits widen with time then stabilize
    ucl = np.zeros(n)
    lcl = np.zeros(n)
    for i in range(n):
        # Asymptotic EWMA variance
        factor = (lam / (2 - lam)) * (1 - (1 - lam) ** (2 * (i + 1)))
        limit = sigma_mult * sigma * np.sqrt(factor)
        ucl[i] = target + limit
        lcl[i] = target - limit

    result = pd.DataFrame({
        "value": values,
        "ewma": ewma,
        "target": target,
        "ucl": ucl,
        "lcl": lcl,
        "out_of_control": (ewma > ucl) | (ewma < lcl),
    })

    return result


def compute_cusum(
    series: pd.Series,
    target: float | None = None,
    allowance: float = CUSUM_ALLOWANCE,
    threshold: float = CUSUM_THRESHOLD,
) -> pd.DataFrame:
    """Compute CUSUM control chart for detecting mean shifts.

    Two-sided CUSUM: tracks both upward and downward shifts.

    Parameters
    ----------
    series : Time-ordered metric values
    target : Target mean (default: series mean)
    allowance : Slack value k (in units of σ)
    threshold : Decision interval h (in units of σ)

    Returns
    -------
    DataFrame with columns:
        value, cusum_pos, cusum_neg, threshold_pos, threshold_neg,
        shift_detected (bool), shift_direction (str)
    """
    values = series.dropna().values.astype(float)
    n = len(values)
    if n < 3:
        return pd.DataFrame()

    if target is None:
        target = np.mean(values)

    sigma = np.std(values, ddof=1)
    if sigma == 0:
        sigma = 1e-6  # avoid division by zero

    k = allowance * sigma
    h = threshold * sigma

    # Standardize
    cusum_pos = np.zeros(n)  # detects upward shift
    cusum_neg = np.zeros(n)  # detects downward shift

    for i in range(n):
        deviation = values[i] - target
        cusum_pos[i] = max(0, (cusum_pos[i - 1] if i > 0 else 0) + deviation - k)
        cusum_neg[i] = max(0, (cusum_neg[i - 1] if i > 0 else 0) - deviation - k)

    result = pd.DataFrame({
        "value": values,
        "cusum_pos": cusum_pos,
        "cusum_neg": cusum_neg,
        "threshold_pos": h,
        "threshold_neg": h,
        "shift_up": cusum_pos > h,
        "shift_down": cusum_neg > h,
    })

    result["shift_detected"] = result["shift_up"] | result["shift_down"]
    result["shift_direction"] = "none"
    result.loc[result["shift_up"], "shift_direction"] = "up"
    result.loc[result["shift_down"], "shift_direction"] = "down"
    result.loc[result["shift_up"] & result["shift_down"], "shift_direction"] = "both"

    return result


def build_control_charts(monthly_df: pd.DataFrame) -> dict:
    """Build EWMA + CUSUM charts for all key monthly metrics.

    Parameters
    ----------
    monthly_df : Output of compute_monthly_metrics()

    Returns
    -------
    dict keyed by metric name, each containing:
        {metric: {ewma: DataFrame, cusum: DataFrame, alerts: list}}
    """
    metrics = ["pregnancy_rate", "avg_cl_measure", "avg_embryo_grade"]
    charts = {}

    for metric in metrics:
        if metric not in monthly_df.columns:
            continue

        series = monthly_df[metric].dropna()
        if len(series) < 3:
            logger.warning(f"Skipping {metric}: only {len(series)} data points")
            continue

        ewma_df = compute_ewma(series)
        cusum_df = compute_cusum(series)

        # Generate alerts from control chart violations
        alerts = []

        # EWMA alerts
        ewma_violations = ewma_df[ewma_df["out_of_control"]]
        for idx, row in ewma_violations.iterrows():
            direction = "above UCL" if row["ewma"] > row["ucl"] else "below LCL"
            alerts.append({
                "type": "ewma_violation",
                "metric": metric,
                "period_index": int(idx),
                "period": monthly_df["period"].iloc[idx] if "period" in monthly_df.columns else str(idx),
                "value": round(float(row["value"]), 4),
                "ewma": round(float(row["ewma"]), 4),
                "direction": direction,
                "severity": "warning",
            })

        # CUSUM alerts
        cusum_violations = cusum_df[cusum_df["shift_detected"]]
        for idx, row in cusum_violations.iterrows():
            alerts.append({
                "type": "cusum_shift",
                "metric": metric,
                "period_index": int(idx),
                "period": monthly_df["period"].iloc[idx] if "period" in monthly_df.columns else str(idx),
                "value": round(float(row["value"]), 4),
                "shift_direction": row["shift_direction"],
                "severity": "critical" if row["shift_direction"] == "both" else "warning",
            })

        charts[metric] = {
            "ewma": ewma_df,
            "cusum": cusum_df,
            "alerts": alerts,
            "periods": monthly_df["period"].tolist() if "period" in monthly_df.columns else list(range(len(series))),
        }

    return charts
