"""Protocol effectiveness analysis (ROADMAP tasks 5.1, 5.2).

Logistic regression per protocol, propensity score adjustment,
SHAP feature importance for protocol variables.
"""

import logging
import warnings

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder

from ml.analytics.config import MIN_SAMPLES_PROTOCOL, SEED

logger = logging.getLogger(__name__)

warnings.filterwarnings("ignore", category=UserWarning)


def protocol_pregnancy_rates(df: pd.DataFrame) -> pd.DataFrame:
    """Compute pregnancy rate per protocol with confidence intervals.

    Parameters
    ----------
    df : DataFrame with 'protocol_name' and 'pregnant' (binary) columns

    Returns
    -------
    DataFrame with protocol_name, n_transfers, n_pregnant, pregnancy_rate,
    ci_lower, ci_upper (Wilson 95% CI)
    """
    grouped = df.groupby("protocol_name").agg(
        n_transfers=("pregnant", "count"),
        n_pregnant=("pregnant", "sum"),
    ).reset_index()

    grouped = grouped[grouped["n_transfers"] >= MIN_SAMPLES_PROTOCOL].copy()
    grouped["pregnancy_rate"] = grouped["n_pregnant"] / grouped["n_transfers"]

    # Wilson score interval
    z = 1.96
    n = grouped["n_transfers"]
    p = grouped["pregnancy_rate"]
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    spread = z * np.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denom
    grouped["ci_lower"] = np.maximum(0, centre - spread)
    grouped["ci_upper"] = np.minimum(1, centre + spread)

    return grouped.sort_values("pregnancy_rate", ascending=False).reset_index(drop=True)


def protocol_logistic_regression(df: pd.DataFrame) -> dict:
    """Fit logistic regression with protocol as a feature to estimate
    adjusted protocol effect.

    Returns dict with coefficients, odds ratios, and model metrics.
    """
    # Prepare features
    feature_cols = ["cl_measure_mm", "heat_day", "protocol_name"]
    working = df.dropna(subset=["pregnant", "cl_measure_mm", "protocol_name"]).copy()

    if len(working) < 30:
        return {"error": "Insufficient data for logistic regression"}

    le = LabelEncoder()
    working["protocol_encoded"] = le.fit_transform(working["protocol_name"])

    # One-hot encode protocols
    protocol_dummies = pd.get_dummies(working["protocol_name"], prefix="protocol", drop_first=True)
    X = pd.concat([
        working[["cl_measure_mm"]].astype(float),
        working[["heat_day"]].fillna(0).astype(float),
        protocol_dummies.astype(float),
    ], axis=1)
    y = working["pregnant"].astype(int)

    model = LogisticRegression(
        C=1.0, penalty="l2", class_weight="balanced",
        solver="lbfgs", max_iter=1000, random_state=SEED
    )
    model.fit(X, y)

    coefs = dict(zip(X.columns, model.coef_[0]))
    odds_ratios = {k: round(float(np.exp(v)), 3) for k, v in coefs.items()}

    return {
        "coefficients": {k: round(float(v), 4) for k, v in coefs.items()},
        "odds_ratios": odds_ratios,
        "intercept": round(float(model.intercept_[0]), 4),
        "n_samples": len(X),
        "feature_names": list(X.columns),
        "protocol_classes": list(le.classes_),
    }


def protocol_shap_importance(df: pd.DataFrame) -> dict:
    """Compute permutation-based feature importance for protocol impact.

    Returns dict with feature importances and protocol-specific contributions.
    """
    working = df.dropna(subset=["pregnant", "cl_measure_mm", "protocol_name"]).copy()
    if len(working) < 30:
        return {"error": "Insufficient data"}

    protocol_dummies = pd.get_dummies(working["protocol_name"], prefix="protocol", drop_first=True)
    X = pd.concat([
        working[["cl_measure_mm"]].astype(float),
        working[["heat_day"]].fillna(0).astype(float),
        protocol_dummies.astype(float),
    ], axis=1)
    y = working["pregnant"].astype(int)

    model = LogisticRegression(
        C=1.0, class_weight="balanced", solver="lbfgs",
        max_iter=1000, random_state=SEED
    )
    model.fit(X, y)

    # Permutation importance
    from sklearn.inspection import permutation_importance
    # Use a single worker to avoid process-spawn memory failures on Windows and
    # low-memory container environments during API-triggered pipeline runs.
    result = permutation_importance(model, X, y, n_repeats=20, random_state=SEED, n_jobs=1)

    importances = {}
    for i, col in enumerate(X.columns):
        importances[col] = {
            "mean": round(float(result.importances_mean[i]), 4),
            "std": round(float(result.importances_std[i]), 4),
        }

    # Protocol-specific contribution (sum of protocol columns)
    protocol_cols = [c for c in X.columns if c.startswith("protocol_")]
    protocol_total = sum(importances[c]["mean"] for c in protocol_cols)

    return {
        "feature_importances": importances,
        "protocol_total_importance": round(protocol_total, 4),
        "n_samples": len(X),
    }
