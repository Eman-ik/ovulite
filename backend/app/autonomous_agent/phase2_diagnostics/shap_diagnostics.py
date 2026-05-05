"""Phase 2: Observability & Diagnostics Layer - Model Explainability with SHAP"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import shap
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ModelMetadata(BaseModel):
    """Metadata about a model for diagnostics."""
    model_name: str = Field(..., description="Name of the model")
    model_version: str = Field(..., description="Version of the model")
    model_type: str = Field(..., description="Type: 'cnn' or 'xgboost'")
    confidence_score: float = Field(..., description="Prediction confidence (0-1)")
    probability: float = Field(..., description="Predicted probability")


class DiagnosticFeature(BaseModel):
    """Individual feature contribution to prediction."""
    feature_name: str = Field(..., description="Name of the feature")
    shap_value: float = Field(..., description="SHAP value (contribution to output)")
    feature_value: Optional[float] = Field(default=None, description="Actual value of the feature")
    impact: str = Field(..., description="Impact: 'positive', 'negative', or 'neutral'")


class DiagnosticReport(BaseModel):
    """Comprehensive diagnostic report for a model prediction."""
    transfer_id: int = Field(..., description="ET transfer ID")
    model_name: str = Field(..., description="Model name")
    confidence_score: float = Field(..., description="Prediction confidence")
    confidence_assessment: str = Field(..., description="Assessment: 'high', 'medium', or 'low'")
    top_features: List[DiagnosticFeature] = Field(..., description="Top contributing features")
    explanation: str = Field(..., description="Natural language explanation of the prediction")
    recommendations: List[str] = Field(..., description="Recommendations for action")
    diagnostic_timestamp: str = Field(..., description="When this diagnostic was created")


class SHAPDiagnosticsEngine:
    """
    SHAP-based Diagnostics Engine for Model Explainability
    
    Extracts and explains:
    - CNN quality assessment predictions
    - XGBoost success rate predictions
    - Feature importance and their contributions
    """
    
    def __init__(
        self,
        cnn_model: Optional[Any] = None,
        xgb_model: Optional[Any] = None,
        background_data: Optional[np.ndarray] = None
    ):
        """
        Initialize SHAP Diagnostics Engine.
        
        Args:
            cnn_model: Trained CNN model
            xgb_model: Trained XGBoost model
            background_data: Background data for SHAP explainer
        """
        self.cnn_model = cnn_model
        self.xgb_model = xgb_model
        self.background_data = background_data
        
        # Initialize SHAP explainers
        self.cnn_explainer = None
        self.xgb_explainer = None
        
        if xgb_model and background_data is not None:
            try:
                self.xgb_explainer = shap.TreeExplainer(xgb_model)
                logger.info("TreeExplainer initialized for XGBoost")
            except Exception as e:
                logger.warning(f"Failed to initialize TreeExplainer: {str(e)}")
        
        logger.info("SHAP Diagnostics Engine initialized")
    
    def explain_xgboost_prediction(
        self,
        input_features: np.ndarray,
        feature_names: List[str],
        prediction_proba: float
    ) -> DiagnosticReport:
        """
        Explain an XGBoost prediction using SHAP values.
        
        Args:
            input_features: Feature vector for prediction
            feature_names: Names of features
            prediction_proba: Model probability output
            
        Returns:
            DiagnosticReport with SHAP-based explanation
        """
        try:
            if self.xgb_explainer is None:
                raise ValueError("XGBoost explainer not initialized")
            
            # Get SHAP values
            shap_values = self.xgb_explainer.shap_values(input_features.reshape(1, -1))
            base_value = self.xgb_explainer.expected_value
            
            # Extract top features by absolute SHAP value
            top_features = self._extract_top_features(
                shap_values[0],
                feature_names,
                input_features,
                k=5
            )
            
            # Assess confidence
            confidence_assessment = self._assess_confidence(prediction_proba)
            
            # Generate natural language explanation
            explanation = self._generate_explanation(
                prediction_proba,
                confidence_assessment,
                top_features
            )
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                confidence_assessment,
                top_features,
                prediction_proba
            )
            
            return DiagnosticReport(
                transfer_id=0,  # Will be set by caller
                model_name="XGBoost Success Predictor",
                confidence_score=prediction_proba,
                confidence_assessment=confidence_assessment,
                top_features=top_features,
                explanation=explanation,
                recommendations=recommendations,
                diagnostic_timestamp=str(np.datetime64('now'))
            )
            
        except Exception as e:
            logger.error(f"XGBoost explanation failed: {str(e)}")
            raise
    
    def explain_cnn_prediction(
        self,
        input_image: np.ndarray,
        prediction_score: float,
        grad_cam_available: bool = False
    ) -> DiagnosticReport:
        """
        Explain a CNN prediction using attention/gradient analysis.
        
        Args:
            input_image: Input image array
            prediction_score: CNN prediction score
            grad_cam_available: Whether Grad-CAM is available
            
        Returns:
            DiagnosticReport with CNN explanation
        """
        try:
            confidence_assessment = self._assess_confidence(prediction_score)
            
            # Extract insights about the image
            image_features = self._analyze_image_quality(input_image)
            
            explanation = self._generate_cnn_explanation(
                prediction_score,
                confidence_assessment,
                image_features
            )
            
            recommendations = self._generate_cnn_recommendations(
                confidence_assessment,
                image_features
            )
            
            return DiagnosticReport(
                transfer_id=0,  # Will be set by caller
                model_name="CNN Embryo Quality Assessor",
                confidence_score=prediction_score,
                confidence_assessment=confidence_assessment,
                top_features=[
                    DiagnosticFeature(
                        feature_name=name,
                        shap_value=0.0,
                        feature_value=value,
                        impact="positive" if value > 0.5 else "negative"
                    )
                    for name, value in image_features.items()
                ],
                explanation=explanation,
                recommendations=recommendations,
                diagnostic_timestamp=str(np.datetime64('now'))
            )
            
        except Exception as e:
            logger.error(f"CNN explanation failed: {str(e)}")
            raise
    
    def _extract_top_features(
        self,
        shap_values: np.ndarray,
        feature_names: List[str],
        input_features: np.ndarray,
        k: int = 5
    ) -> List[DiagnosticFeature]:
        """Extract top k features by SHAP value magnitude."""
        abs_shap = np.abs(shap_values)
        top_indices = np.argsort(abs_shap)[-k:][::-1]
        
        top_features = []
        for idx in top_indices:
            feature = DiagnosticFeature(
                feature_name=feature_names[idx],
                shap_value=float(shap_values[idx]),
                feature_value=float(input_features[idx]),
                impact="positive" if shap_values[idx] > 0 else "negative"
            )
            top_features.append(feature)
        
        return top_features
    
    def _assess_confidence(self, score: float) -> str:
        """Assess confidence level based on score."""
        if score >= 0.85:
            return "high"
        elif score >= 0.70:
            return "medium"
        else:
            return "low"
    
    def _analyze_image_quality(self, image: np.ndarray) -> Dict[str, float]:
        """Analyze image quality metrics."""
        return {
            "brightness_level": float(np.mean(image) / 255.0),
            "contrast_ratio": float(np.std(image) / 255.0),
            "noise_estimation": float(np.std(np.diff(image, axis=0)) / 255.0),
            "sharpness": 0.0  # Placeholder for edge detection
        }
    
    def _generate_explanation(
        self,
        prediction: float,
        confidence: str,
        top_features: List[DiagnosticFeature]
    ) -> str:
        """Generate natural language explanation of prediction."""
        top_feature_names = ", ".join([f.feature_name for f in top_features[:3]])
        
        return f"The model predicts a {prediction:.1%} success rate with {confidence} confidence. " \
               f"The strongest predictors are: {top_feature_names}. " \
               f"The positive contributors indicate favorable conditions."
    
    def _generate_recommendations(
        self,
        confidence: str,
        features: List[DiagnosticFeature],
        prediction: float
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        if confidence == "low":
            recommendations.append("⚠️ WARNING: Low confidence in prediction. Request additional data validation.")
            recommendations.append("Consider re-running with fresh samples or different equipment.")
        
        if prediction < 0.70:
            recommendations.append("❌ HIGH RISK: Success probability below 70%. Review recipient synchrony status.")
        elif prediction >= 0.85:
            recommendations.append("✅ FAVORABLE: High success probability. Proceed with transfer.")
        
        return recommendations
    
    def _generate_cnn_explanation(
        self,
        score: float,
        confidence: str,
        image_features: Dict[str, float]
    ) -> str:
        """Generate explanation for CNN prediction."""
        bright = "bright" if image_features["brightness_level"] > 0.5 else "dim"
        contrast = "high" if image_features["contrast_ratio"] > 0.3 else "low"
        
        return f"Embryo quality assessed at {score:.1%} ({confidence} confidence). " \
               f"Image analysis shows {bright} conditions with {contrast} contrast. " \
               f"Noise level is {'acceptable' if image_features['noise_estimation'] < 0.2 else 'elevated'}."
    
    def _generate_cnn_recommendations(
        self,
        confidence: str,
        image_features: Dict[str, float]
    ) -> List[str]:
        """Generate recommendations for CNN predictions."""
        recommendations = []
        
        if image_features["brightness_level"] < 0.3:
            recommendations.append("⚠️ Image too dim. Adjust lighting for better embryo visibility.")
        
        if image_features["brightness_level"] > 0.8:
            recommendations.append("⚠️ Image overexposed. Reduce light intensity.")
        
        if image_features["noise_estimation"] > 0.3:
            recommendations.append("⚠️ High noise detected. Check microscope alignment and lens cleanliness.")
        
        return recommendations
