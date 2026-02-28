"""QC feature engineering (ROADMAP task 4.1).

Computes technician-level, protocol-level, temporal, and batch-level
quality metrics from ET transfer data for anomaly detection.
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from .config import DATA_CSV, MIN_MONTHLY_RECORDS, MIN_TECH_TRANSFERS, SEED

logger = logging.getLogger(__name__)


def load_et_data(csv_path: Path | None = None) -> pd.DataFrame:
    """Load and clean ET transfer data for QC analysis."""
    path = csv_path or DATA_CSV
    df = pd.read_csv(str(path), dtype=str)
    df = df.dropna(how="all").reset_index(drop=True)

    # Parse key columns
    df["et_number"] = pd.to_numeric(df.get("# ET"), errors="coerce")
    df["embryo_stage"] = pd.to_numeric(df.get("Embryo Stage 4-8"), errors="coerce")
    df["embryo_grade"] = pd.to_numeric(df.get("Embryo Grade"), errors="coerce")
    df["cl_measure_mm"] = pd.to_numeric(df.get("CL Measure (mm)"), errors="coerce")
    df["bc_score"] = pd.to_numeric(df.get("BCScore"), errors="coerce")
    df["heat_day"] = pd.to_numeric(df.get("Heat Day"), errors="coerce")

    # Categorical
    df["technician_name"] = df.get("ET Tech", pd.Series(dtype=str)).fillna("Unknown").str.strip()
    df["protocol_name"] = df.get("Protocol", pd.Series(dtype=str)).fillna("Unknown").str.strip()
    df["donor_breed"] = df.get("Donor Breed", pd.Series(dtype=str)).fillna("Unknown").str.strip()
    df["fresh_or_frozen"] = df.get("Fresh or Frozen", pd.Series(dtype=str)).fillna("Unknown").str.strip()
    df["customer_id"] = df.get("Customer ID", pd.Series(dtype=str)).fillna("Unknown").str.strip()
    df["semen_type"] = df.get("Semen Type", pd.Series(dtype=str)).fillna("Unknown").str.strip()
    df["cl_side"] = df.get("CL Side", pd.Series(dtype=str)).fillna("Unknown").str.strip()

    # Outcome
    pc1_raw = df.get("1st PC Result", pd.Series(dtype=str)).fillna("")
    df["pregnant"] = pc1_raw.str.strip().map(
        {"Pregnant": 1, "P": 1, "Open": 0, "O": 0, "Recheck": np.nan, "R": np.nan}
    )

    # Dates
    df["et_date"] = pd.to_datetime(df.get("ET Date"), errors="coerce", dayfirst=True)
    df["year_month"] = df["et_date"].dt.to_period("M")

    return df


# ═══════════════════════════════════════════════════════════
# Technician-level features (Task 4.1)
# ═══════════════════════════════════════════════════════════

def compute_technician_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Compute per-technician quality metrics.

    Returns DataFrame with columns:
        technician_name, transfer_count, pregnancy_rate, avg_cl_measure,
        avg_embryo_grade, avg_bc_score, std_cl_measure, pct_heat_observed
    """
    grouped = df.groupby("technician_name")

    stats = pd.DataFrame({
        "transfer_count": grouped.size(),
        "pregnancy_rate": grouped["pregnant"].mean(),
        "avg_cl_measure": grouped["cl_measure_mm"].mean(),
        "std_cl_measure": grouped["cl_measure_mm"].std(),
        "avg_embryo_grade": grouped["embryo_grade"].mean(),
        "avg_bc_score": grouped["bc_score"].mean(),
        "avg_heat_day": grouped["heat_day"].mean(),
    }).reset_index()

    # Filter out technicians with too few transfers
    stats = stats[stats["transfer_count"] >= MIN_TECH_TRANSFERS].copy()

    # Derived ratios
    global_preg_rate = df["pregnant"].mean()
    stats["preg_rate_vs_mean"] = stats["pregnancy_rate"] - global_preg_rate

    return stats


# ═══════════════════════════════════════════════════════════
# Protocol-level features
# ═══════════════════════════════════════════════════════════

def compute_protocol_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Compute per-protocol quality metrics."""
    grouped = df.groupby("protocol_name")

    stats = pd.DataFrame({
        "transfer_count": grouped.size(),
        "pregnancy_rate": grouped["pregnant"].mean(),
        "avg_cl_measure": grouped["cl_measure_mm"].mean(),
        "avg_embryo_grade": grouped["embryo_grade"].mean(),
    }).reset_index()

    stats = stats[stats["transfer_count"] >= MIN_TECH_TRANSFERS].copy()

    global_preg_rate = df["pregnant"].mean()
    stats["preg_rate_vs_mean"] = stats["pregnancy_rate"] - global_preg_rate

    return stats


# ═══════════════════════════════════════════════════════════
# Temporal features (Task 4.1)
# ═══════════════════════════════════════════════════════════

def compute_monthly_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Compute monthly aggregated QC metrics for control charts.

    Returns DataFrame indexed by year_month with columns:
        transfer_count, pregnancy_rate, avg_cl_measure, avg_embryo_grade,
        avg_bc_score, std_cl_measure
    """
    valid = df.dropna(subset=["year_month"]).copy()
    grouped = valid.groupby("year_month")

    monthly = pd.DataFrame({
        "transfer_count": grouped.size(),
        "pregnancy_rate": grouped["pregnant"].mean(),
        "avg_cl_measure": grouped["cl_measure_mm"].mean(),
        "std_cl_measure": grouped["cl_measure_mm"].std(),
        "avg_embryo_grade": grouped["embryo_grade"].mean(),
        "avg_bc_score": grouped["bc_score"].mean(),
    }).reset_index()

    # Filter months with too few records
    monthly = monthly[monthly["transfer_count"] >= MIN_MONTHLY_RECORDS].copy()
    monthly = monthly.sort_values("year_month").reset_index(drop=True)

    # Convert period to string for JSON serialization
    monthly["period"] = monthly["year_month"].astype(str)

    return monthly


# ═══════════════════════════════════════════════════════════
# Batch-level features (for per-technician-per-month analysis)
# ═══════════════════════════════════════════════════════════

def compute_batch_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute technician × month batch features for Isolation Forest.

    Each row = one technician in one month.

    Returns DataFrame with columns:
        technician_name, period, transfer_count, pregnancy_rate,
        avg_cl_measure, avg_embryo_grade, z_pregnancy_rate, z_cl_measure
    """
    valid = df.dropna(subset=["year_month"]).copy()
    grouped = valid.groupby(["technician_name", "year_month"])

    batch = pd.DataFrame({
        "transfer_count": grouped.size(),
        "pregnancy_rate": grouped["pregnant"].mean(),
        "avg_cl_measure": grouped["cl_measure_mm"].mean(),
        "avg_embryo_grade": grouped["embryo_grade"].mean(),
    }).reset_index()

    batch = batch[batch["transfer_count"] >= 2].copy()

    # Z-score normalization against global stats
    for col in ["pregnancy_rate", "avg_cl_measure", "avg_embryo_grade"]:
        mean = batch[col].mean()
        std = batch[col].std()
        if std > 0:
            batch[f"z_{col}"] = (batch[col] - mean) / std
        else:
            batch[f"z_{col}"] = 0.0

    batch["period"] = batch["year_month"].astype(str)

    return batch


def build_qc_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Build the full QC feature matrix for Isolation Forest input.

    Uses batch features (technician × month) with z-scored metrics.
    """
    batch = compute_batch_features(df)

    feature_cols = [
        "z_pregnancy_rate",
        "z_avg_cl_measure",
        "z_avg_embryo_grade",
        "transfer_count",
    ]

    # Fill NaN with 0 for model input
    X = batch[feature_cols].fillna(0.0)

    return X, batch
