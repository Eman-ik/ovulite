"""Synthetic predictions + outcomes for testing/demoing Module 7.

Mirrors ml/qc/synthetic.py's approach: the real `predictions` table will be
sparse until the system has been in clinical use for a while, so this lets
the monitoring pipeline, API, and dashboard be exercised end-to-end with a
clearly-labeled synthetic batch instead of failing silently or faking a
"real" result.
"""

import numpy as np
import pandas as pd

from ml.monitoring.config import SEED


def generate_synthetic_predictions(
    n_baseline: int = 120,
    n_current: int = 40,
    inject_drift: bool = False,
    seed: int = SEED,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate a synthetic baseline window and current window of
    (probability, actual_outcome, cl_measure_mm, heat_day) rows.

    If inject_drift is True, the current window's calibration and feature
    distribution are shifted so detect_performance_drift/detect_population_drift
    should fire — useful for verifying the pipeline actually detects drift.
    """
    rng = np.random.default_rng(seed)

    def _make_window(n: int, shift: float = 0.0, feature_shift: float = 0.0) -> pd.DataFrame:
        true_prob = np.clip(rng.beta(2, 3, size=n) + shift, 0.02, 0.98)
        outcome = rng.binomial(1, true_prob)
        # Model's predicted probability: true_prob + noise (well-calibrated in baseline,
        # miscalibrated/noisier in the drifted current window).
        noise_scale = 0.25 if shift else 0.12
        pred_prob = np.clip(true_prob + rng.normal(0, noise_scale, size=n), 0.01, 0.99)
        cl_measure = rng.normal(18 + feature_shift, 3, size=n)
        heat_day = rng.integers(4, 9, size=n).astype(float)
        return pd.DataFrame({
            "probability": pred_prob,
            "actual_outcome": outcome,
            "cl_measure_mm": cl_measure,
            "heat_day": heat_day,
        })

    df_baseline = _make_window(n_baseline)
    if inject_drift:
        df_current = _make_window(n_current, shift=-0.15, feature_shift=4.0)
    else:
        df_current = _make_window(n_current)

    return df_baseline, df_current
