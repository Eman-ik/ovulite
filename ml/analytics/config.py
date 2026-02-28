"""Analytics configuration — paths, column mappings, and defaults."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ML_DIR = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = ML_DIR / "artifacts" / "analytics"
DATA_CSV = PROJECT_ROOT / "docs" / "dataset" / "ET Summary - ET Data.csv"

# Pregnancy record CSVs (client reports)
PREG_CSVS = list((PROJECT_ROOT / "docs" / "dataset").glob("*Pregnancy Record*"))

# Minimum samples for reliable stats
MIN_SAMPLES_PROTOCOL = 10
MIN_SAMPLES_DONOR = 5
MIN_SAMPLES_TECHNICIAN = 10
MIN_SAMPLES_BIOMARKER = 20

# CL measure bins (mm) for sweet-spot analysis
CL_BIN_EDGES = [0, 10, 15, 18, 20, 22, 25, 30, 50]
CL_BIN_LABELS = ["<10", "10-15", "15-18", "18-20", "20-22", "22-25", "25-30", "30+"]

# Biomarker metrics to analyze
BIOMARKER_COLS = ["cl_measure_mm", "bc_score", "heat_day"]

SEED = 42
