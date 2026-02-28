"""Reproductive KPI computations (ROADMAP task 5.4).

Pregnancy rates, embryo utilization, IVF funnel metrics,
and time-series trends.
"""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def compute_kpis(df: pd.DataFrame) -> dict:
    """Compute core reproductive KPIs from ET data.

    Returns dict with all key performance indicators.
    """
    total = len(df)
    with_outcome = df["pregnant"].notna().sum()
    pregnant = int(df["pregnant"].sum()) if "pregnant" in df.columns else 0
    open_count = int(with_outcome - pregnant)

    # Pregnancy rate
    preg_rate = round(float(pregnant / with_outcome), 4) if with_outcome > 0 else None

    # Embryo utilization
    unique_embryos = df["embryo_id"].nunique() if "embryo_id" in df.columns else None
    embryo_utilization = round(total / unique_embryos, 2) if unique_embryos and unique_embryos > 0 else None

    # Temporal range
    dates = pd.to_datetime(df["et_date"])
    date_range = {
        "first": str(dates.min().date()) if len(dates) > 0 else None,
        "last": str(dates.max().date()) if len(dates) > 0 else None,
        "span_months": int((dates.max() - dates.min()).days / 30.44) if len(dates) > 1 else 0,
    }

    # Entity counts
    entity_counts = {
        "donors": int(df["donor_tag"].nunique()) if "donor_tag" in df.columns else 0,
        "recipients": int(df["recipient_tag"].nunique()) if "recipient_tag" in df.columns else 0,
        "technicians": int(df["technician_name"].nunique()) if "technician_name" in df.columns else 0,
        "protocols": int(df["protocol_name"].nunique()) if "protocol_name" in df.columns else 0,
        "sires": int(df["sire_name"].nunique()) if "sire_name" in df.columns else 0,
    }

    # Fresh vs frozen
    fresh_frozen = {}
    if "fresh_or_frozen" in df.columns:
        for ff_type, group in df.groupby("fresh_or_frozen"):
            n = len(group)
            n_preg = int(group["pregnant"].sum())
            fresh_frozen[str(ff_type)] = {
                "n": n,
                "pregnant": n_preg,
                "rate": round(n_preg / n, 4) if n > 0 else None,
            }

    return {
        "total_transfers": total,
        "with_outcome": int(with_outcome),
        "pregnant": pregnant,
        "open": open_count,
        "pregnancy_rate": preg_rate,
        "embryo_utilization": embryo_utilization,
        "unique_embryos": unique_embryos,
        "date_range": date_range,
        "entity_counts": entity_counts,
        "fresh_vs_frozen": fresh_frozen,
    }


def monthly_kpi_trends(df: pd.DataFrame) -> list[dict]:
    """Compute monthly KPI trends.

    Returns list of {month, n_transfers, n_pregnant, pregnancy_rate, avg_cl}.
    """
    df = df.copy()
    df["month"] = pd.to_datetime(df["et_date"]).dt.to_period("M").astype(str)

    monthly = df.groupby("month").agg(
        n_transfers=("pregnant", "count"),
        n_pregnant=("pregnant", "sum"),
        avg_cl=("cl_measure_mm", "mean"),
    ).reset_index()

    monthly["pregnancy_rate"] = monthly["n_pregnant"] / monthly["n_transfers"]
    monthly["avg_cl"] = monthly["avg_cl"].round(1)
    monthly["pregnancy_rate"] = monthly["pregnancy_rate"].round(4)

    return monthly.to_dict(orient="records")


def ivf_funnel(df: pd.DataFrame) -> list[dict]:
    """Compute IVF funnel stages.

    Returns list of {stage, count, rate_from_previous}.
    """
    total = len(df)
    with_embryo = df["embryo_id"].notna().sum() if "embryo_id" in df.columns else total
    with_cl = df["cl_measure_mm"].notna().sum() if "cl_measure_mm" in df.columns else total
    transferred = total  # all records are transfers
    with_outcome = int(df["pregnant"].notna().sum())
    pregnant = int(df["pregnant"].sum())

    funnel = [
        {"stage": "Embryos Available", "count": int(with_embryo)},
        {"stage": "CL Verified", "count": int(with_cl)},
        {"stage": "Transferred", "count": transferred},
        {"stage": "Outcome Recorded", "count": with_outcome},
        {"stage": "Pregnant", "count": pregnant},
    ]

    # Compute conversion rates
    for i in range(1, len(funnel)):
        prev = funnel[i - 1]["count"]
        funnel[i]["rate_from_previous"] = (
            round(funnel[i]["count"] / prev, 4) if prev > 0 else None
        )
    funnel[0]["rate_from_previous"] = 1.0

    return funnel
