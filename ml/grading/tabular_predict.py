"""Serve the tabular grader: raw image bytes in, calibrated grade out.

Why this replaces the CNN on ``POST /grade/embryo``
---------------------------------------------------
Measured on the same held-out 72 images, identical split:

    tabular (this)   accuracy 0.597   macro-F1 0.564   Grade-2 recall 0.385
    EfficientNet-B0  accuracy 0.542   macro-F1 0.475   Grade-2 recall 0.192
    majority class   accuracy 0.403

Cross-validated on 407 images it scores 0.587 +/- 0.041, which is the number to
quote — the 72-image test figure carries a +/-0.11 interval either way.

It is also ~30x faster than a CNN forward pass on CPU, and its inputs are named
quantities a veterinarian can be shown: inner-cell-mass area and eccentricity,
trophectoderm texture, grey-level spread.

The important property is that ``ml/grading/morphometrics.py`` computes the
features both at training time and here, so there is no train/serve skew. The
model never sees a number produced by a different pipeline.

What it will not do
-------------------
It predicts IETS grade and nothing else. It does not predict pregnancy, and its
output must never be fed to the pregnancy model: the grading label is
independent of transfer outcome, so joining them would manufacture circular
leakage.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np

from .config import PROJECT_ROOT
from .morphometrics import BlastocystNotFound, extract_features_from_bytes

logger = logging.getLogger(__name__)

ARTIFACT_DIR = PROJECT_ROOT / "ml" / "artifacts" / "grading" / "tabular_extracted_v1"

CLASS_LABELS = {
    1: "Grade 1 (excellent/good)",
    2: "Grade 2 (fair)",
    3: "Grade 3 (poor)",
}


class TabularGradeClassifier:
    """Loads the fitted model and its feature order, and grades an image."""

    def __init__(self, artifact_dir: Path = ARTIFACT_DIR):
        import joblib

        model_path = artifact_dir / "model.joblib"
        metadata_path = artifact_dir / "metadata.json"
        if not model_path.exists():
            raise FileNotFoundError(
                f"Tabular grader not found at {model_path}. Train it with: "
                "python -m ml.grading.train_tabular_grading --features extracted"
            )

        bundle = joblib.load(model_path)
        self.model = bundle["model"]
        # Column order is part of the artifact. Rebuilding it from the extractor
        # would silently reorder features if either list ever changes.
        self.features: list[str] = bundle["features"]
        self.metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.version = self.metadata.get("trained_at", "unknown")
        self.selected_model = self.metadata.get("selected_model", "unknown")

        metrics = self.metadata.get("test_metrics", {})
        cv = self.metadata.get("cv_results", {}).get(self.selected_model, {})
        logger.info(
            "Tabular grader %s (%s): test acc %.3f, CV %.3f +/- %.3f",
            self.version, self.selected_model,
            metrics.get("accuracy", float("nan")),
            cv.get("cv_accuracy_mean", float("nan")),
            cv.get("cv_accuracy_std", float("nan")),
        )

    def predict(self, image_bytes: bytes) -> dict:
        """Grade one image. Raises BlastocystNotFound if nothing is locatable."""
        features = extract_features_from_bytes(image_bytes)

        row = np.array([[features[name] for name in self.features]], dtype=np.float64)
        probabilities = self.model.predict_proba(row)[0]
        predicted_index = int(np.argmax(probabilities))
        grade = predicted_index + 1

        return {
            "predicted_grade": grade,
            "predicted_label": CLASS_LABELS[grade],
            "confidence": float(probabilities[predicted_index]),
            "probabilities": [
                {"grade": i + 1, "label": CLASS_LABELS[i + 1], "probability": float(p)}
                for i, p in enumerate(probabilities)
            ],
            "features": features,
        }

    def accuracy_summary(self) -> dict:
        metrics = self.metadata.get("test_metrics", {})
        cv = self.metadata.get("cv_results", {}).get(self.selected_model, {})
        return {
            "cv_accuracy": cv.get("cv_accuracy_mean"),
            "cv_accuracy_std": cv.get("cv_accuracy_std"),
            "test_accuracy": metrics.get("accuracy"),
            "test_macro_f1": metrics.get("macro_f1"),
            "n_test": self.metadata.get("split", {}).get("test"),
        }


_classifier: TabularGradeClassifier | None = None


def get_tabular_classifier() -> TabularGradeClassifier:
    global _classifier
    if _classifier is None:
        _classifier = TabularGradeClassifier()
    return _classifier


__all__ = [
    "BlastocystNotFound",
    "TabularGradeClassifier",
    "get_tabular_classifier",
]
