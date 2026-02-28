"""Isolation Forest anomaly detection (ROADMAP task 4.2).

Trains Isolation Forest on batch features (technician × month) to
detect anomalous batches — e.g. a technician with unusually low
pregnancy rate in a given month.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from .config import (
    ARTIFACTS_DIR,
    IFOREST_CONTAMINATION,
    IFOREST_MAX_SAMPLES,
    IFOREST_N_ESTIMATORS,
    SEED,
)

logger = logging.getLogger(__name__)


def train_isolation_forest(
    X: pd.DataFrame,
    batch_df: pd.DataFrame,
    contamination: float = IFOREST_CONTAMINATION,
    save_dir: Path = ARTIFACTS_DIR,
) -> tuple:
    """Train Isolation Forest on QC feature matrix.

    Parameters
    ----------
    X : Feature matrix (z-scored batch metrics)
    batch_df : Original batch DataFrame with metadata
    contamination : Expected anomaly fraction

    Returns
    -------
    model : Trained IsolationForest
    results_df : batch_df annotated with anomaly scores and labels
    """
    logger.info(f"Training Isolation Forest on {len(X)} samples, contamination={contamination}")

    model = IsolationForest(
        n_estimators=IFOREST_N_ESTIMATORS,
        max_samples=IFOREST_MAX_SAMPLES,
        contamination=contamination,
        random_state=SEED,
        n_jobs=-1,
    )

    model.fit(X)

    # Score all samples
    scores = model.decision_function(X.values)  # higher = more normal
    labels = model.predict(X.values)  # 1 = normal, -1 = anomaly

    results = batch_df.copy()
    results["anomaly_score"] = scores
    results["is_anomaly"] = labels == -1
    results["anomaly_severity"] = results["anomaly_score"].apply(_score_to_severity)

    n_anomalies = results["is_anomaly"].sum()
    logger.info(f"Detected {n_anomalies}/{len(results)} anomalous batches")

    # Save model
    save_dir.mkdir(parents=True, exist_ok=True)
    import joblib
    model_path = save_dir / "isolation_forest.joblib"
    joblib.dump(model, model_path)

    # Save metadata
    meta = {
        "type": "isolation_forest",
        "n_samples": len(X),
        "n_features": X.shape[1],
        "feature_names": list(X.columns),
        "contamination": contamination,
        "n_anomalies": int(n_anomalies),
        "anomaly_rate": round(float(n_anomalies / len(results)), 4),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with open(save_dir / "iforest_meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    return model, results


def score_new_batch(
    X_new: pd.DataFrame,
    model_dir: Path = ARTIFACTS_DIR,
) -> pd.DataFrame:
    """Score new batch data against trained Isolation Forest."""
    import joblib

    model_path = model_dir / "isolation_forest.joblib"
    if not model_path.exists():
        raise FileNotFoundError(f"No trained model at {model_path}")

    model = joblib.load(model_path)
    scores = model.decision_function(X_new.values)
    labels = model.predict(X_new.values)

    result = X_new.copy()
    result["anomaly_score"] = scores
    result["is_anomaly"] = labels == -1
    result["anomaly_severity"] = result["anomaly_score"].apply(_score_to_severity)

    return result


def _score_to_severity(score: float) -> str:
    """Map anomaly score to severity level.

    Isolation Forest scores: negative = more anomalous, positive = more normal.
    """
    if score < -0.3:
        return "critical"
    elif score < -0.1:
        return "warning"
    else:
        return "info"
