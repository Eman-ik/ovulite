"""Feature engineering — build canonical feature matrix from ET Data CSV.

Mirrors the vw_et_features database view but reads directly from CSV
for offline training. The prediction API uses the DB view at inference time.
"""

import re
from datetime import datetime

import numpy as np
import pandas as pd

from ml.config import (
    CATEGORICAL_FEATURES,
    DATA_CSV,
    LEAKAGE_COLUMNS,
    NUMERIC_FEATURES,
    TARGET_COL,
)

# ── CSV column mapping (raw CSV header → canonical name) ─────
_COL_MAP = {
    "# ET": "et_number",
    "ET Date": "et_date",
    "Customer ID": "customer_id",
    "ET Location": "farm_location",
    "Recipient ID (1st)": "recipient_tag",
    "Cow/Heifer": "cow_or_heifer",
    "BC Score": "bc_score",
    "CL Side": "cl_side",
    "CL measure (mm)": "cl_measure_mm",
    "Protocol": "protocol_name",
    "Fresh or Frozen": "fresh_or_frozen",
    "ET Tech": "technician_name",
    "ET assistant": "assistant_name",
    "Embryo Stage 4-8": "embryo_stage",
    "Embryo Grade": "embryo_grade",
    "Heat": "heat_observed",
    "Heat day": "heat_day",
    "1st PC date": "pc1_date",
    "1st PC Result": "pc1_result",
    "2nd PC date": "pc2_date",
    "2nd PC Result": "pc2_result",
    "Fetal Sexing": "fetal_sexing",
    "OPU Date": "opu_date",
    "Donor": "donor_tag",
    "Donor Breed": "donor_breed",
    "Donor BW EPD": "donor_bw_epd",
    "SIRE Name": "sire_name",
    "SIRE Breed": "sire_breed",
    "SIRE BW EPD": "sire_bw_epd",
    "Semen type": "semen_type",
    "BCScore": "bc_score_alt",  # duplicate column
}


def _parse_date(val: str) -> pd.Timestamp | None:
    """Parse M/D/YYYY or similar date strings, return None for dirty values."""
    if not val or val.strip() in (".", "", "nan", "None"):
        return None
    try:
        return pd.to_datetime(val, format="mixed", dayfirst=False)
    except Exception:
        return None


def _clean_dot(val):
    """Replace '.' sentinel with NaN."""
    if isinstance(val, str) and val.strip() == ".":
        return np.nan
    return val


def _normalize_semen_type(val):
    if pd.isna(val):
        return val
    val = str(val).strip()
    if re.search(r"pre.?sort", val, re.IGNORECASE):
        return "Sexed"
    return val


def _normalize_cl_side(val):
    if pd.isna(val):
        return val
    val = str(val).strip().title()
    if val in ("Left", "Right"):
        return val
    return np.nan


def _normalize_pc_result(val):
    if pd.isna(val):
        return val
    val = str(val).strip()
    mapping = {"P": "Pregnant", "O": "Open", "R": "Recheck"}
    return mapping.get(val, val)


def load_raw_csv(csv_path: str | None = None) -> pd.DataFrame:
    """Load and minimally clean the raw ET Data CSV."""
    path = csv_path or str(DATA_CSV)
    df = pd.read_csv(path, dtype=str)
    # Drop fully-empty rows
    df = df.dropna(how="all").reset_index(drop=True)
    return df


def build_feature_matrix(csv_path: str | None = None) -> pd.DataFrame:
    """Build the canonical feature matrix from raw CSV.

    Returns a DataFrame with:
    - All features from REQUIREMENTS §3.4
    - Binary target column (pregnancy_outcome: 1=Pregnant, 0=Open)
    - donor_tag for GroupKFold splitting
    - et_date for temporal splitting
    - transfer_id (et_number) for record tracking

    Rows with 'Recheck' or missing outcome are excluded.
    """
    raw = load_raw_csv(csv_path)

    # Rename columns to canonical names
    rename_map = {}
    for raw_col in raw.columns:
        canonical = _COL_MAP.get(raw_col.strip())
        if canonical:
            rename_map[raw_col] = canonical
    df = raw.rename(columns=rename_map)

    # Clean sentinel values
    for col in df.columns:
        df[col] = df[col].apply(_clean_dot)

    # Parse dates
    df["et_date"] = df["et_date"].apply(_parse_date)
    df["opu_date"] = df["opu_date"].apply(_parse_date)

    # Normalize categoricals
    df["cl_side"] = df["cl_side"].apply(_normalize_cl_side)
    df["semen_type"] = df["semen_type"].apply(_normalize_semen_type)
    df["pc1_result"] = df["pc1_result"].apply(_normalize_pc_result)

    # Numeric conversions
    for col in NUMERIC_FEATURES:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Derived features
    if "opu_date" in df.columns and "et_date" in df.columns:
        df["days_opu_to_et"] = (df["et_date"] - df["opu_date"]).dt.days
    else:
        df["days_opu_to_et"] = np.nan

    # BC missing flag
    df["bc_missing"] = df["bc_score"].isna().astype(int)

    # Use bc_score_alt as fallback if primary is missing
    if "bc_score_alt" in df.columns:
        mask = df["bc_score"].isna() & df["bc_score_alt"].notna()
        df.loc[mask, "bc_score"] = pd.to_numeric(
            df.loc[mask, "bc_score_alt"], errors="coerce"
        )

    # Binary target: Pregnant=1, Open=0; exclude Recheck and missing
    df = df[df["pc1_result"].isin(["Pregnant", "Open"])].copy()
    df[TARGET_COL] = (df["pc1_result"] == "Pregnant").astype(int)

    # Keep needed columns
    keep_cols = (
        NUMERIC_FEATURES
        + CATEGORICAL_FEATURES
        + ["bc_missing", TARGET_COL, "donor_tag", "et_date", "et_number"]
    )
    keep_cols = [c for c in keep_cols if c in df.columns]
    df = df[keep_cols].reset_index(drop=True)

    return df


def preprocess_for_model(
    df: pd.DataFrame,
    fit: bool = True,
    encoder_map: dict | None = None,
) -> tuple[np.ndarray, np.ndarray, list[str], dict]:
    """Convert feature DataFrame to numpy arrays ready for sklearn.

    Parameters
    ----------
    df : DataFrame with features + target
    fit : if True, compute encoding mappings; if False, use encoder_map
    encoder_map : pre-computed encoding mappings (for inference)

    Returns
    -------
    X : feature array (n_samples, n_features)
    y : target array (n_samples,)
    feature_names : list of feature column names after encoding
    encoder_map : encoding mappings for reuse at inference
    """
    if encoder_map is None:
        encoder_map = {}

    df = df.copy()
    feature_cols = []

    # Numeric features: impute median
    for col in NUMERIC_FEATURES:
        if col not in df.columns:
            df[col] = np.nan
        if fit:
            median_val = df[col].median()
            encoder_map[f"{col}_median"] = median_val
        else:
            median_val = encoder_map.get(f"{col}_median", 0)
        df[col] = df[col].fillna(median_val)
        feature_cols.append(col)

    # Binary flags
    if "bc_missing" in df.columns:
        feature_cols.append("bc_missing")
    else:
        df["bc_missing"] = 0
        feature_cols.append("bc_missing")

    # Categorical features: one-hot encoding
    for col in CATEGORICAL_FEATURES:
        if col not in df.columns:
            df[col] = "Unknown"
        df[col] = df[col].fillna("Unknown").astype(str)

        if fit:
            categories = sorted(df[col].unique().tolist())
            encoder_map[f"{col}_categories"] = categories
        else:
            categories = encoder_map.get(f"{col}_categories", [])

        for cat in categories:
            ohe_col = f"{col}__{cat}"
            df[ohe_col] = (df[col] == cat).astype(int)
            feature_cols.append(ohe_col)

    X = df[feature_cols].values.astype(np.float64)
    y = df[TARGET_COL].values.astype(int) if TARGET_COL in df.columns else np.zeros(len(df))
    return X, y, feature_cols, encoder_map
