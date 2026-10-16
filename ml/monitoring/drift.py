"""Drift detection for the pregnancy-prediction ensemble.

Two independent drift signals, matched to the Module 7 spec:
  1) Population drift — Kolmogorov-Smirnov test comparing the feature
     distribution of the current window against a historical baseline.
  2) Performance drift — current rolling metrics vs. a rolling baseline
     built from recent history (Brier increase / ROC-AUC decrease beyond
     a threshold).
"""

import logging

import pandas as pd
from scipy.stats import ks_2samp

from ml.monitoring.config import (
    BRIER_DRIFT_DELTA,
    KS_ALPHA,
    POPULATION_DRIFT_FEATURES,
    ROC_AUC_DRIFT_DELTA,
)

logger = logging.getLogger(__name__)


def detect_population_drift(
    df_current: pd.DataFrame,
    df_baseline: pd.DataFrame,
    feature_cols: list[str] | None = None,
) -> tuple[bool, dict]:
    """Two-sample Kolmogorov-Smirnov test per feature.

    Returns (drift_detected, details) where details maps feature name to
    {ks_stat, p_value} for every feature with p < KS_ALPHA.
    """
    feature_cols = feature_cols or POPULATION_DRIFT_FEATURES
    drift_detected = False
    details: dict = {}

    for feature in feature_cols:
        if feature not in df_current.columns or feature not in df_baseline.columns:
            continue
        cur = df_current[feature].dropna()
        base = df_baseline[feature].dropna()
        if len(cur) < 5 or len(base) < 5:
            # Too few points for a meaningful KS test — skip, don't fabricate a signal.
            continue
        stat, p_value = ks_2samp(base, cur)
        if p_value < KS_ALPHA:
            drift_detected = True
            details[feature] = {
                "ks_stat": round(float(stat), 4),
                "p_value": round(float(p_value), 6),
            }

    return drift_detected, details


def detect_performance_drift(
    current_metrics: dict,
    historical_metrics: list[dict],
    window: int = 30,
) -> tuple[bool, dict]:
    """Compare current Brier/ROC-AUC to a rolling historical baseline.

    `historical_metrics` is a list of prior `compute_rolling_metrics()`
    outputs (most recent last), typically loaded from the `model_metrics`
    table. Entries with status != 'ok' are ignored for baseline purposes.
    """
    usable = [
        m for m in historical_metrics[-window:]
        if m.get("status") == "ok" and m.get("brier_score") is not None
    ]

    if len(usable) < 3:
        return False, {"message": "Insufficient history to establish a baseline."}

    baseline_brier = sum(m["brier_score"] for m in usable) / len(usable)
    roc_vals = [m["roc_auc"] for m in usable if m.get("roc_auc") is not None]
    baseline_roc_auc = sum(roc_vals) / len(roc_vals) if roc_vals else None

    if current_metrics.get("status") != "ok":
        return False, {"message": "Current window metrics not computable; skipping performance-drift check."}

    current_brier = current_metrics["brier_score"]
    current_roc_auc = current_metrics.get("roc_auc")

    brier_threshold = baseline_brier + BRIER_DRIFT_DELTA
    brier_drifted = current_brier is not None and current_brier > brier_threshold

    roc_drifted = False
    if baseline_roc_auc is not None and current_roc_auc is not None:
        roc_threshold = baseline_roc_auc - ROC_AUC_DRIFT_DELTA
        roc_drifted = current_roc_auc < roc_threshold

    drifted = brier_drifted or roc_drifted

    details = {
        "baseline_brier": round(baseline_brier, 4),
        "current_brier": current_brier,
        "brier_drifted": brier_drifted,
        "baseline_roc_auc": round(baseline_roc_auc, 4) if baseline_roc_auc is not None else None,
        "current_roc_auc": current_roc_auc,
        "roc_auc_drifted": roc_drifted,
        "baseline_window_size": len(usable),
    }

    return drifted, details
