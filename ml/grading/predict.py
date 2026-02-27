"""Embryo grading inference (singleton predictor for API use).

Loads trained grading model and provides:
- Grade prediction (3-class: High/Medium/Low viability)
- Viability probability
- Grad-CAM heatmap generation
"""

import io
import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

try:
    import torch

    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

from .config import ARTIFACTS_DIR, NUM_GRADES

GRADE_LABELS = {0: "Low", 1: "Medium", 2: "High"}


class EmbryoGrader:
    """Singleton embryo grading predictor.

    Usage::

        grader = EmbryoGrader.get_instance()
        result = grader.grade(image_bytes, metadata)
    """

    _instance = None

    def __init__(self, model_dir: Path = ARTIFACTS_DIR):
        if not HAS_TORCH:
            raise ImportError("PyTorch is required for embryo grading")

        from .models import EmbryoGradingModel, GradCAM
        from .preprocessing import GradingDataset

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model_dir = model_dir
        self.model = None
        self.grad_cam = None
        self._loaded = False

        # Categorical vocabs from training
        self._breed_vocab = dict(GradingDataset._breed_vocab) if GradingDataset._breed_vocab else {}
        self._tech_vocab = dict(GradingDataset._tech_vocab) if GradingDataset._tech_vocab else {}
        self._ff_vocab = dict(GradingDataset._ff_vocab) if GradingDataset._ff_vocab else {"Fresh": 1, "Frozen": 2}

    @classmethod
    def get_instance(cls, model_dir: Path = ARTIFACTS_DIR) -> "EmbryoGrader":
        if cls._instance is None:
            cls._instance = cls(model_dir)
        return cls._instance

    def _load_model(self):
        """Lazy-load the trained model."""
        if self._loaded:
            return

        from .models import EmbryoGradingModel, GradCAM

        model_path = self.model_dir / "grading_model.pt"

        if not model_path.exists():
            logger.warning(f"No grading model found at {model_path}, using untrained model")
            self.model = EmbryoGradingModel(n_grades=NUM_GRADES, freeze_backbone=False).to(self.device)
        else:
            self.model = EmbryoGradingModel(n_grades=NUM_GRADES, freeze_backbone=False).to(self.device)
            state = torch.load(model_path, map_location=self.device, weights_only=True)
            self.model.load_state_dict(state)
            logger.info(f"Loaded grading model from {model_path}")

        self.model.eval()
        self.grad_cam = GradCAM(self.model)
        self._loaded = True

    def _prepare_metadata(self, metadata: dict | None):
        """Convert raw metadata dict to model-ready tensors."""
        if metadata is None:
            metadata = {}

        numeric = torch.tensor([
            float(metadata.get("embryo_stage", 6.0)),
            float(metadata.get("embryo_grade", 1.0)),
        ], dtype=torch.float32).unsqueeze(0).to(self.device)

        categorical = {
            "donor_breed": torch.tensor(
                [self._breed_vocab.get(metadata.get("donor_breed", "Unknown"), 0)],
                dtype=torch.long,
            ).to(self.device),
            "fresh_or_frozen": torch.tensor(
                [self._ff_vocab.get(metadata.get("fresh_or_frozen", "Fresh"), 0)],
                dtype=torch.long,
            ).to(self.device),
            "technician_name": torch.tensor(
                [self._tech_vocab.get(metadata.get("technician_name", "Unknown"), 0)],
                dtype=torch.long,
            ).to(self.device),
        }

        return numeric, categorical

    def grade(
        self,
        image_bytes: bytes,
        metadata: dict | None = None,
        generate_heatmap: bool = True,
    ) -> dict:
        """Grade an embryo image.

        Parameters
        ----------
        image_bytes : raw JPEG/PNG bytes
        metadata : optional dict with embryo_stage, embryo_grade, donor_breed, etc.
        generate_heatmap : whether to produce Grad-CAM overlay

        Returns
        -------
        dict with keys:
            grade_label : str ("High", "Medium", "Low")
            grade_class : int (0, 1, 2)
            grade_probabilities : dict[str, float]
            viability_score : float
            heatmap_bytes : bytes | None (JPEG of Grad-CAM overlay)
        """
        self._load_model()

        from .models import generate_heatmap_overlay
        from .preprocessing import load_image_from_bytes

        # Preprocess image
        image_tensor = load_image_from_bytes(image_bytes).to(self.device)
        numeric, categorical = self._prepare_metadata(metadata)

        # Forward pass
        with torch.no_grad():
            grade_logits, viability = self.model(image_tensor, numeric, categorical)

        probs = torch.softmax(grade_logits, dim=1).squeeze().cpu().numpy()
        grade_class = int(probs.argmax())
        viability_score = float(viability.cpu().item())

        result = {
            "grade_label": GRADE_LABELS[grade_class],
            "grade_class": grade_class,
            "grade_probabilities": {
                GRADE_LABELS[i]: round(float(probs[i]), 4) for i in range(NUM_GRADES)
            },
            "viability_score": round(viability_score, 4),
            "heatmap_bytes": None,
        }

        # Generate Grad-CAM heatmap
        if generate_heatmap:
            try:
                image_tensor_grad = load_image_from_bytes(image_bytes).to(self.device)
                numeric_grad, categorical_grad = self._prepare_metadata(metadata)

                heatmap = self.grad_cam.generate(
                    image_tensor_grad, numeric_grad, categorical_grad,
                    target_class=grade_class,
                )
                overlay_bytes = generate_heatmap_overlay(image_bytes, heatmap)
                result["heatmap_bytes"] = overlay_bytes
            except Exception as e:
                logger.warning(f"Grad-CAM failed: {e}")

        return result

    def get_model_info(self) -> dict:
        """Return model metadata for API /model-info endpoint."""
        import json

        info = {
            "model_type": "EfficientNet-B0 + Metadata Fusion",
            "n_grades": NUM_GRADES,
            "grade_labels": GRADE_LABELS,
            "backbone": "efficientnet_b0",
            "trained": False,
        }

        history_path = self.model_dir / "grading_history.json"
        if history_path.exists():
            with open(history_path) as f:
                history = json.load(f)
            info["trained"] = True
            info["best_val_acc"] = history.get("final_val_acc")
            info["n_train"] = history.get("n_train")
            info["n_val"] = history.get("n_val")
            info["timestamp"] = history.get("timestamp")

        return info
