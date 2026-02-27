"""Prediction API — POST /predict/pregnancy → P + CI + SHAP (ROADMAP task 2.9).

Loads trained model artifacts and serves real-time pregnancy predictions
with uncertainty estimates and SHAP explanations.
"""

import logging
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.prediction import Prediction
from app.models.user import User
from app.schemas.prediction import (
    ModelInfoResponse,
    PredictionInput,
    PredictionOutput,
    ShapContribution,
    ShapExplanation,
)

# Add project root to path so ml package is importable
_project_root = str(Path(__file__).resolve().parent.parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_predictor():
    """Lazy-load the ML predictor (singleton)."""
    try:
        from ml.predict import get_predictor

        return get_predictor()
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="No trained model found. Run training pipeline first.",
        )
    except Exception as exc:
        logger.error("Failed to load predictor: %s", exc)
        raise HTTPException(status_code=503, detail=f"Model loading error: {exc}")


@router.post("/pregnancy", response_model=PredictionOutput)
def predict_pregnancy(
    input_data: PredictionInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Predict pregnancy probability for an ET transfer.

    Returns probability, 95% confidence interval, risk band, and SHAP
    feature contributions.
    """
    predictor = _get_predictor()

    # Build features dict from input
    features = input_data.model_dump(exclude={"transfer_id"}, exclude_none=False)

    try:
        result = predictor.predict(features)
    except Exception as exc:
        logger.error("Prediction failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Prediction error: {exc}")

    # Build SHAP explanation
    shap_raw = result.get("shap_values", {})
    contributions = [
        ShapContribution(feature=feat, value=val)
        for feat, val in shap_raw.get("contributions", [])
    ]
    shap_explanation = ShapExplanation(
        base_value=shap_raw.get("base_value", 0),
        contributions=contributions,
    )

    # Persist prediction to DB
    prediction_record = Prediction(
        transfer_id=input_data.transfer_id,
        model_name=result["model_name"],
        model_version=result["model_version"],
        probability=result["probability"],
        confidence_lower=result["confidence_lower"],
        confidence_upper=result["confidence_upper"],
        risk_band=result["risk_band"],
        shap_json={
            "base_value": shap_raw.get("base_value", 0),
            "contributions": shap_raw.get("contributions", []),
        },
    )
    db.add(prediction_record)
    db.commit()
    db.refresh(prediction_record)

    return PredictionOutput(
        probability=result["probability"],
        confidence_lower=result["confidence_lower"],
        confidence_upper=result["confidence_upper"],
        risk_band=result["risk_band"],
        model_name=result["model_name"],
        model_version=result["model_version"],
        shap_explanation=shap_explanation,
        prediction_id=prediction_record.prediction_id,
    )


@router.get("/model-info", response_model=ModelInfoResponse)
def get_model_info(current_user: User = Depends(get_current_user)):
    """Return information about the currently loaded prediction model."""
    predictor = _get_predictor()
    metadata = predictor.metadata

    return ModelInfoResponse(
        model_name=predictor.model_name,
        model_version=predictor.version,
        n_features=len(predictor.feature_names),
        best_model_key=metadata.get("best_model", "unknown"),
        training_split=metadata.get("split", {}),
        top_features=metadata.get("shap_top_features", []),
    )
