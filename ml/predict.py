"""Inference helper — load trained model and predict for new inputs."""

import json
import logging
from pathlib import Path

import joblib
import numpy as np

from ml.config import ARTIFACTS_DIR, get_risk_band
from ml.train_pipeline import compute_confidence_interval

logger = logging.getLogger(__name__)


class PregnancyPredictor:
    """Stateful predictor that loads a trained model version and serves predictions."""

    def __init__(self, version: str | None = None):
        """Load model artifacts for the given version (or latest)."""
        if version:
            self.artifact_dir = ARTIFACTS_DIR / version
            self._validate_artifact_dir(self.artifact_dir)
        else:
            self.artifact_dir = self._resolve_latest_valid_artifact_dir()

        self.version = self.artifact_dir.name
        logger.info("Loading model artifacts from %s", self.artifact_dir)

        # Load encoder map
        self.encoder_map = joblib.load(self.artifact_dir / "encoder_map.joblib")

        # Load feature names
        with open(self.artifact_dir / "feature_names.json") as f:
            self.feature_names = json.load(f)

        # Load metadata to find best model
        with open(self.artifact_dir / "metadata.json") as f:
            self.metadata = json.load(f)

        best_key = self.metadata.get("best_model", "logistic")

        # Load model (try calibrated first, then raw)
        model_path = self.artifact_dir / f"{best_key}_model.joblib"
        if not model_path.exists():
            # Fallback to any available model
            for fname in ("logistic_model.joblib", "xgboost_model.joblib", "tabpfn_model.joblib"):
                candidate = self.artifact_dir / fname
                if candidate.exists():
                    model_path = candidate
                    break
        if not model_path.exists():
            raise FileNotFoundError(
                f"No trained model file found under {self.artifact_dir}. "
                "Expected one of: logistic_model.joblib, xgboost_model.joblib, tabpfn_model.joblib"
            )

        self.model = joblib.load(model_path)
        self.model_name = self.metadata.get("models", {}).get(best_key, {}).get("name", best_key)
        logger.info("Loaded model: %s (version: %s)", self.model_name, self.version)

    @staticmethod
    def _validate_artifact_dir(path: Path) -> None:
        required = ["encoder_map.joblib", "feature_names.json", "metadata.json"]
        missing = [name for name in required if not (path / name).exists()]
        if missing:
            raise FileNotFoundError(
                f"Model artifact directory is incomplete: {path}. Missing files: {', '.join(missing)}"
            )

    @classmethod
    def _resolve_latest_valid_artifact_dir(cls) -> Path:
        if not ARTIFACTS_DIR.exists():
            raise FileNotFoundError(f"No model artifacts found in {ARTIFACTS_DIR}")

        versions = [p for p in ARTIFACTS_DIR.iterdir() if p.is_dir() and p.name.startswith("v")]
        versions = sorted(versions, key=lambda p: p.stat().st_mtime)
        for candidate in reversed(versions):
            try:
                cls._validate_artifact_dir(candidate)
                return candidate
            except FileNotFoundError:
                continue

        raise FileNotFoundError(
            f"No complete model artifact set found in {ARTIFACTS_DIR}. "
            "Run training to generate versioned artifacts."
        )

    def predict(self, features: dict) -> dict:
        """Generate pregnancy prediction for a single transfer.

        Parameters
        ----------
        features : dict with canonical feature names as keys

        Returns
        -------
        dict with probability, confidence_lower, confidence_upper, risk_band, shap_values
        """
        import pandas as pd

        from ml.config import CATEGORICAL_FEATURES, NUMERIC_FEATURES
        from ml.features import preprocess_for_model

        # Build a single-row DataFrame
        row = {}
        for col in NUMERIC_FEATURES:
            val = features.get(col)
            row[col] = float(val) if val is not None else np.nan
        for col in CATEGORICAL_FEATURES:
            row[col] = features.get(col, "Unknown")

        row["bc_missing"] = 1 if (features.get("bc_score") is None or pd.isna(features.get("bc_score"))) else 0
        row["pregnancy_outcome"] = 0  # dummy, won't be used

        df = pd.DataFrame([row])

        X, _, _, _ = preprocess_for_model(df, fit=False, encoder_map=self.encoder_map)

        # Predict probability
        prob = float(self.model.predict_proba(X)[:, 1][0])

        # Confidence interval
        ci_lower, ci_upper = compute_confidence_interval(np.array([prob]))
        ci_lo = float(ci_lower[0])
        ci_hi = float(ci_upper[0])

        # Risk band
        band = get_risk_band(prob)

        # SHAP values for this prediction
        shap_dict = self._compute_shap_single(X)

        return {
            "probability": round(prob, 4),
            "confidence_lower": round(ci_lo, 4),
            "confidence_upper": round(ci_hi, 4),
            "risk_band": band,
            "model_name": self.model_name,
            "model_version": self.version,
            "shap_values": shap_dict,
        }

    def _compute_shap_single(self, X: np.ndarray) -> dict:
        """Compute SHAP contribution for a single prediction."""
        try:
            import shap

            explainer = shap.Explainer(self.model.predict_proba, X, feature_names=self.feature_names)
            sv = explainer(X)
            if len(sv.shape) == 3:
                vals = sv.values[0, :, 1]
            else:
                vals = sv.values[0]

            contributions = sorted(
                zip(self.feature_names, vals.tolist()),
                key=lambda x: abs(x[1]),
                reverse=True,
            )
            return {
                "base_value": float(sv.base_values[0][1]) if len(sv.base_values.shape) > 1 else float(sv.base_values[0]),
                "contributions": contributions[:15],
            }
        except Exception as exc:
            logger.warning("SHAP failed for single prediction: %s", exc)
            return {"base_value": 0, "contributions": []}


# Module-level singleton (lazy loaded)
_predictor: PregnancyPredictor | None = None


def get_predictor(version: str | None = None) -> PregnancyPredictor:
    """Get or lazy-load the singleton predictor."""
    global _predictor
    if _predictor is None or (version and _predictor.version != version):
        _predictor = PregnancyPredictor(version=version)
    return _predictor
