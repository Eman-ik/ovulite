"""QC module configuration."""

from pathlib import Path

# ── Paths ─────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ML_DIR = Path(__file__).resolve().parent.parent
QC_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = ML_DIR / "artifacts" / "qc"
DATA_CSV = PROJECT_ROOT / "docs" / "dataset" / "ET Summary - ET Data.csv"

# ── Random seed ──────────────────────────────────────────
SEED = 42

# ── Isolation Forest ─────────────────────────────────────
IFOREST_CONTAMINATION = 0.10  # expected anomaly rate 10%
IFOREST_N_ESTIMATORS = 200
IFOREST_MAX_SAMPLES = "auto"

# ── EWMA parameters ─────────────────────────────────────
EWMA_SPAN = 10  # smoothing span (number of periods)
EWMA_LAMBDA = 0.2  # smoothing weight for EWMA
EWMA_SIGMA_MULTIPLIER = 3.0  # control limit at 3σ

# ── CUSUM parameters ────────────────────────────────────
CUSUM_TARGET = 0.0  # target mean (set from data)
CUSUM_ALLOWANCE = 0.5  # slack / allowance (k)
CUSUM_THRESHOLD = 5.0  # decision interval (h)

# ── Alert severities ────────────────────────────────────
SEVERITY_LEVELS = ["info", "warning", "critical"]

# ── QC feature grouping ─────────────────────────────────
TECHNICIAN_METRICS = [
    "pregnancy_rate",
    "avg_cl_measure",
    "transfer_count",
    "avg_embryo_grade",
]

TEMPORAL_METRICS = [
    "monthly_pregnancy_rate",
    "monthly_transfer_count",
    "monthly_avg_cl",
]

# ── Minimum sample sizes ────────────────────────────────
MIN_TECH_TRANSFERS = 5  # minimum transfers for technician stats
MIN_MONTHLY_RECORDS = 3  # minimum records in a month to compute metric
