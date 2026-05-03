"""Analytics pipeline runner — ties all analytics modules together.

Usage:
    python -m ml.analytics.run_analytics
"""

import argparse
import json
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _normalize_csv_columns(df: "pd.DataFrame") -> "pd.DataFrame":
    """Normalize CSV column names to internal format.
    
    Maps raw CSV headers to internal column names, handling:
    - Whitespace and special characters (parentheses, hyphens, etc)
    - Trailing spaces in column names
    - Duplicate columns (kept as-is for second occurrence)
    """
    col_map = {
        "CL measure (mm)": "cl_measure_mm",
        "CL Side": "cl_side",
        "ET Date": "et_date",
        "ET Tech": "technician_name",
        "Embryo Stage 4-8": "embryo_stage",
        "1st PC Result": "pc1_result",
        "BC Score": "bc_score",
        "BCScore": "bc_score",
        "Heat day": "heat_day",
        "Protocol": "protocol_name",
        "Fresh or Frozen": "fresh_or_frozen",
        "Donor Breed": "donor_breed",
        "Donor": "donor_tag",
        "SIRE Name": "sire_name",
        "SIRE Breed": "sire_breed",
        "SIRE BW EPD": "sire_bw_epd",
        "Customer ID": "customer_id",
        "CLIENT ": "client_id",
        "OPU Date": "opu_date",
        "Semen type": "semen_type",
        "Embryo Grade": "embryo_grade",
    }

    rename_map = {}
    seen_cols = set()
    for raw_col in df.columns:
        stripped = raw_col.strip()
        if stripped in col_map:
            internal_name = col_map[stripped]
            if internal_name not in seen_cols:
                rename_map[raw_col] = internal_name
                seen_cols.add(internal_name)
        else:
            clean = stripped.lower().replace(" ", "_").replace("(", "").replace(")", "").replace("-", "_")
            if clean not in seen_cols:
                rename_map[raw_col] = clean
                seen_cols.add(clean)

    return df.rename(columns=rename_map)


def load_et_data(csv_path: Path | None = None) -> "pd.DataFrame":
    """Load and prepare ET data for analytics."""
    import pandas as pd

    from ml.analytics.config import DATA_CSV

    path = csv_path or DATA_CSV
    if not path.exists():
        candidates = list(path.parent.glob("*ET Data*"))
        if candidates:
            path = candidates[0]
        else:
            raise FileNotFoundError(f"CSV not found at {path}")

    df = pd.read_csv(path, dtype=str)
    df = df.dropna(how="all").reset_index(drop=True)
    df = df.replace(".", None)

    # Normalize column names using centralized mapping
    df = _normalize_csv_columns(df)

    # Convert numeric columns after normalization
    for col in ["cl_measure_mm", "bc_score", "heat_day"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Ensure pregnant column
    if "pregnant" not in df.columns:
        if "pc1_result" in df.columns:
            df["pregnant"] = df["pc1_result"].fillna("").str.strip().str.upper().map(
                {"P": 1, "PREGNANT": 1, "O": 0, "OPEN": 0}
            )
        else:
            df["pregnant"] = None

    return df


def run_analytics(csv_path: Path | None = None, save_dir: Path | None = None) -> dict:
    """Run full analytics pipeline.

    Returns dict with all analytics results.
    """
    import pandas as pd

    from ml.analytics.biomarker_analysis import all_biomarker_sweetspots
    from ml.analytics.config import ARTIFACTS_DIR
    from ml.analytics.donor_analysis import breed_stats, donor_performance, donor_trends
    from ml.analytics.kpi import compute_kpis, ivf_funnel, monthly_kpi_trends
    from ml.analytics.protocol_analysis import (
        protocol_logistic_regression,
        protocol_pregnancy_rates,
        protocol_shap_importance,
    )

    if save_dir is None:
        save_dir = ARTIFACTS_DIR

    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("Analytics Pipeline: Loading data")

    df = load_et_data(csv_path)
    logger.info(f"Loaded {len(df)} ET records")

    # ── KPIs ──
    logger.info("Computing KPIs...")
    kpis = compute_kpis(df)
    monthly = monthly_kpi_trends(df)
    funnel = ivf_funnel(df)

    # ── Protocol Analysis ──
    logger.info("Protocol analysis...")
    protocol_rates = protocol_pregnancy_rates(df)
    protocol_lr = protocol_logistic_regression(df)
    protocol_shap = protocol_shap_importance(df)

    # ── Donor Analysis ──
    logger.info("Donor analysis...")
    donors = donor_performance(df)
    d_trends = donor_trends(df)
    breeds = breed_stats(df)

    # ── Biomarker Analysis ──
    logger.info("Biomarker sweet-spot analysis...")
    biomarkers = all_biomarker_sweetspots(df)

    # ── Save artifacts ──
    save_dir.mkdir(parents=True, exist_ok=True)

    results = {
        "kpis": kpis,
        "monthly_trends": monthly,
        "ivf_funnel": funnel,
        "protocol_rates": protocol_rates.to_dict(orient="records"),
        "protocol_regression": protocol_lr,
        "protocol_importance": protocol_shap,
        "donor_performance": donors.to_dict(orient="records"),
        "donor_trends": d_trends,
        "breed_stats": breeds.to_dict(orient="records"),
        "biomarkers": biomarkers,
    }

    for key, data in results.items():
        with open(save_dir / f"{key}.json", "w") as f:
            json.dump(data, f, indent=2, default=str)

    logger.info(f"Analytics artifacts saved to {save_dir}")
    logger.info("=" * 60)

    return results


def main():
    parser = argparse.ArgumentParser(description="Run Ovulite analytics pipeline")
    parser.add_argument("--csv", type=str, default=None, help="Path to ET Data CSV")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    )

    csv_path = Path(args.csv) if args.csv else None
    run_analytics(csv_path=csv_path)


if __name__ == "__main__":
    main()
