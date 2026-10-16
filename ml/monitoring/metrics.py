"""Rolling performance metrics for the pregnancy-prediction ensemble.

Per the Module 7 spec: Brier score, ROC-AUC, PR-AUC and a simple win-rate,
computed over a window of {prediction, actual_outcome} pairs where the
outcome is now known (i.e. et_transfers.pc1_result is 'Pregnant' or 'Open').
'Recheck' outcomes are excluded — they are not a resolved binary label.
"""

import logging

import numpy as np
import pandas as pd
from sklearn.metrics import (
    auc,
    brier_score_loss,
    precision_recall_curve,
    roc_auc_score,
)

from ml.monitoring.config import MIN_SAMPLES_FOR_METRICS

logger = logging.getLogger(__name__)


def compute_rolling_metrics(df_predictions: pd.DataFrame) -> dict:
    """Compute Brier score, ROC-AUC, PR-AUC and win-rate for a batch of
    resolved predictions.

    Parameters
    ----------
    df_predictions : DataFrame with columns ['probability', 'actual_outcome']
        probability: float in [0, 1] — the model's predicted P(pregnant)
        actual_outcome: int {0, 1} — the resolved ground-truth outcome

    Returns
    -------
    dict with brier_score, roc_auc, pr_auc, win_rate, sample_size, and
    a `status` field ('ok' | 'insufficient_data' | 'single_class') so
    callers can render an honest message instead of a bogus number.
    """
    working = df_predictions.dropna(subset=["probability", "actual_outcome"]).copy()
    n = len(working)

    if n < MIN_SAMPLES_FOR_METRICS:
        return {
            "status": "insufficient_data",
            "message": (
                f"Only {n} resolved predictions available "
                f"(need >= {MIN_SAMPLES_FOR_METRICS}). Metrics not computed."
            ),
            "sample_size": n,
            "brier_score": None,
            "roc_auc": None,
            "pr_auc": None,
            "win_rate": None,
        }

    y_true = working["actual_outcome"].astype(int).to_numpy()
    y_prob = working["probability"].astype(float).clip(0, 1).to_numpy()

    if len(np.unique(y_true)) < 2:
        # ROC-AUC/PR-AUC are undefined with a single class present.
        win_rate = float((np.round(y_prob) == y_true).mean())
        return {
            "status": "single_class",
            "message": "All resolved outcomes are the same class this window; "
            "ROC-AUC/PR-AUC undefined.",
            "sample_size": n,
            "brier_score": round(float(brier_score_loss(y_true, y_prob)), 4),
            "roc_auc": None,
            "pr_auc": None,
            "win_rate": round(win_rate, 4),
        }

    brier = brier_score_loss(y_true, y_prob)
    roc_auc_val = roc_auc_score(y_true, y_prob)
    precision, recall, _ = precision_recall_curve(y_true, y_prob)
    pr_auc_val = auc(recall, precision)
    win_rate = float((np.round(y_prob) == y_true).mean())

    return {
        "status": "ok",
        "message": None,
        "sample_size": n,
        "brier_score": round(float(brier), 4),
        "roc_auc": round(float(roc_auc_val), 4),
        "pr_auc": round(float(pr_auc_val), 4),
        "win_rate": round(win_rate, 4),
    }
