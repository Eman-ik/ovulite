"""Biomarker sweet-spot analysis (ROADMAP task 5.7).

CL size vs pregnancy rate curves, optimal ranges for biomarkers,
and dose-response style analysis for key numeric features.
"""

import logging

import numpy as np
import pandas as pd

from ml.analytics.config import CL_BIN_EDGES, CL_BIN_LABELS, MIN_SAMPLES_BIOMARKER

logger = logging.getLogger(__name__)


def cl_sweet_spot(df: pd.DataFrame) -> dict:
    """Analyze CL measure (mm) vs pregnancy rate.

    Returns
    -------
    dict with:
        bins: list of {range, n, pregnancy_rate, ci_lower, ci_upper}
        optimal_range: {lower, upper, pregnancy_rate}
        overall_rate: float
    """
    working = df.dropna(subset=["cl_measure_mm", "pregnant"]).copy()
    working["cl_bin"] = pd.cut(
        working["cl_measure_mm"].astype(float),
        bins=CL_BIN_EDGES,
        labels=CL_BIN_LABELS,
        right=False,
    )

    bins = []
    for label in CL_BIN_LABELS:
        subset = working[working["cl_bin"] == label]
        n = len(subset)
        if n < 3:
            continue
        rate = float(subset["pregnant"].mean())
        # Wilson CI
        z = 1.96
        denom = 1 + z**2 / n
        centre = (rate + z**2 / (2 * n)) / denom
        spread = z * np.sqrt((rate * (1 - rate) + z**2 / (4 * n)) / n) / denom
        bins.append({
            "range": label,
            "n": int(n),
            "pregnancy_rate": round(rate, 4),
            "ci_lower": round(max(0, centre - spread), 4),
            "ci_upper": round(min(1, centre + spread), 4),
        })

    # Find optimal range
    optimal = max(bins, key=lambda x: x["pregnancy_rate"]) if bins else None

    return {
        "bins": bins,
        "optimal_range": optimal,
        "overall_rate": round(float(working["pregnant"].mean()), 4) if len(working) > 0 else None,
        "total_records": len(working),
    }


def biomarker_analysis(df: pd.DataFrame, col: str, n_bins: int = 8) -> dict:
    """Generic biomarker vs pregnancy rate analysis using quantile bins.

    Parameters
    ----------
    df : DataFrame
    col : column name for the biomarker
    n_bins : number of quantile bins

    Returns
    -------
    dict with bins, optimal_bin, overall_rate
    """
    working = df.dropna(subset=[col, "pregnant"]).copy()
    if len(working) < MIN_SAMPLES_BIOMARKER:
        return {"error": f"Insufficient data for {col} ({len(working)} records)"}

    working["bin"] = pd.qcut(working[col].astype(float), q=n_bins, duplicates="drop")
    bins = []
    for interval, group in working.groupby("bin", observed=True):
        n = len(group)
        rate = float(group["pregnant"].mean())
        bins.append({
            "range": str(interval),
            "n": int(n),
            "pregnancy_rate": round(rate, 4),
            "mean_value": round(float(group[col].mean()), 2),
        })

    optimal = max(bins, key=lambda x: x["pregnancy_rate"]) if bins else None

    return {
        "biomarker": col,
        "bins": bins,
        "optimal_bin": optimal,
        "overall_rate": round(float(working["pregnant"].mean()), 4),
        "total_records": len(working),
    }


def all_biomarker_sweetspots(df: pd.DataFrame) -> dict:
    """Run sweet-spot analysis for all key biomarkers."""
    results = {
        "cl_measure": cl_sweet_spot(df),
    }

    for col in ["bc_score", "heat_day"]:
        if col in df.columns:
            results[col] = biomarker_analysis(df, col)

    return results
