"""Donor performance analytics (ROADMAP task 5.5).

Per-donor success rates, trends over time, and breed-level statistics.
"""

import logging

import numpy as np
import pandas as pd

from ml.analytics.config import MIN_SAMPLES_DONOR

logger = logging.getLogger(__name__)


def donor_performance(df: pd.DataFrame) -> pd.DataFrame:
    """Compute per-donor pregnancy rates and performance metrics.

    Returns DataFrame with donor_tag, breed, n_transfers, n_pregnant,
    pregnancy_rate, avg_cl, first_date, last_date, active_months.
    """
    grouped = df.groupby("donor_tag").agg(
        breed=("donor_breed", "first"),
        n_transfers=("pregnant", "count"),
        n_pregnant=("pregnant", "sum"),
        avg_cl=("cl_measure_mm", "mean"),
        first_date=("et_date", "min"),
        last_date=("et_date", "max"),
    ).reset_index()

    grouped = grouped[grouped["n_transfers"] >= MIN_SAMPLES_DONOR].copy()
    grouped["pregnancy_rate"] = grouped["n_pregnant"] / grouped["n_transfers"]

    # Active months
    grouped["active_months"] = (
        (pd.to_datetime(grouped["last_date"]) - pd.to_datetime(grouped["first_date"]))
        .dt.days / 30.44
    ).round(0).astype(int)

    grouped["avg_cl"] = grouped["avg_cl"].round(1)

    return grouped.sort_values("pregnancy_rate", ascending=False).reset_index(drop=True)


def donor_trends(df: pd.DataFrame, top_n: int = 10) -> dict:
    """Compute monthly pregnancy rate trends for top N donors.

    Returns dict mapping donor_tag -> list of {month, pregnancy_rate, n_transfers}.
    """
    df = df.copy()
    df["month"] = pd.to_datetime(df["et_date"]).dt.to_period("M").astype(str)

    # Get top N most active donors
    top_donors = (
        df.groupby("donor_tag")["pregnant"]
        .count()
        .nlargest(top_n)
        .index.tolist()
    )

    trends = {}
    for donor in top_donors:
        donor_data = df[df["donor_tag"] == donor]
        monthly = donor_data.groupby("month").agg(
            n_transfers=("pregnant", "count"),
            n_pregnant=("pregnant", "sum"),
        ).reset_index()
        monthly["pregnancy_rate"] = monthly["n_pregnant"] / monthly["n_transfers"]
        trends[donor] = monthly.to_dict(orient="records")

    return trends


def breed_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Compute pregnancy rates by donor breed."""
    grouped = df.groupby("donor_breed").agg(
        n_transfers=("pregnant", "count"),
        n_pregnant=("pregnant", "sum"),
        avg_cl=("cl_measure_mm", "mean"),
    ).reset_index()

    grouped = grouped[grouped["n_transfers"] >= MIN_SAMPLES_DONOR].copy()
    grouped["pregnancy_rate"] = grouped["n_pregnant"] / grouped["n_transfers"]
    grouped["avg_cl"] = grouped["avg_cl"].round(1)

    return grouped.sort_values("pregnancy_rate", ascending=False).reset_index(drop=True)
