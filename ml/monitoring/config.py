"""Outcome Tracking & Continuous Learning module configuration.

Module 7 per 'Ovulite Modules 4, 5, 7 — n8n Automation & Data Design':
weekly rolling-metric computation + drift detection + retrain-job logging.
"""

from pathlib import Path

# ── Paths ─────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ML_DIR = Path(__file__).resolve().parent.parent
MONITORING_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = ML_DIR / "artifacts" / "monitoring"

# No DATA_CSV here: the pipeline reads resolved predictions out of the
# database via app.api.monitoring, never off a CSV, so the upstream
# `ml.data_source.get_et_data_csv()` import was both unused and unavailable
# in this repository.

SEED = 42

# ── Rolling windows ──────────────────────────────────────
CURRENT_WINDOW_DAYS = 30   # "recent" evaluation window
BASELINE_WINDOW_DAYS = 180  # history used to build the baseline for drift checks
MIN_SAMPLES_FOR_METRICS = 10  # below this, metrics are unreliable (small-N warning)

# ── Performance drift thresholds ─────────────────────────
# A model is considered drifted if current Brier rises above baseline + delta,
# OR current ROC-AUC falls below baseline - delta.
BRIER_DRIFT_DELTA = 0.05
ROC_AUC_DRIFT_DELTA = 0.05

# ── Population drift (Kolmogorov-Smirnov) ────────────────
KS_ALPHA = 0.05  # significance level
POPULATION_DRIFT_FEATURES = ["cl_measure_mm", "heat_day"]

# ── Retrain trigger ───────────────────────────────────────
# Requires this many *new* labeled outcomes since the last retrain job
# before auto-retrain is allowed to fire again (avoids retrain spam).
MIN_NEW_LABELS_FOR_RETRAIN = 20
