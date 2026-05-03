"""Pydantic schemas for embryo grading API."""

from pydantic import BaseModel, Field


class GradingMetadata(BaseModel):
    """Optional metadata to improve grading accuracy."""
    embryo_stage: float | None = Field(None, ge=1, le=9, description="Embryo stage (4-8 typical)")
    embryo_grade: float | None = Field(None, ge=1, le=4, description="Manual embryo grade")
    donor_breed: str | None = Field(None, description="Donor breed")
    fresh_or_frozen: str | None = Field(None, description="Fresh or Frozen")
    technician_name: str | None = Field(None, description="ET technician name")


class GradeProbabilities(BaseModel):
    """Probability for each grade class."""
    Low: float = Field(..., ge=0, le=1)
    Medium: float = Field(..., ge=0, le=1)
    High: float = Field(..., ge=0, le=1)


class GradingResult(BaseModel):
    """Response from the embryo grading endpoint."""
    grade_label: str = Field(..., description="Predicted grade: High, Medium, or Low viability")
    grade_class: int = Field(..., ge=0, le=2, description="Grade class index (0=Low, 1=Medium, 2=High)")
    grade_probabilities: GradeProbabilities
    viability_score: float = Field(..., ge=0, le=1, description="Viability probability (0-1)")
    heatmap_available: bool = Field(False, description="Whether Grad-CAM heatmap was generated")


class GradingResultWithHeatmap(BaseModel):
    """Response from embryo-with-heatmap endpoint."""

    grade_label: str = Field(..., description="Predicted grade: High, Medium, or Low viability")
    grade_class: int = Field(..., ge=0, le=2, description="Grade class index (0=Low, 1=Medium, 2=High)")
    grade_probabilities: GradeProbabilities
    viability_score: float = Field(..., ge=0, le=1, description="Viability probability (0-1)")
    heatmap_base64: str | None = Field(None, description="Base64-encoded Grad-CAM heatmap JPEG")


class ImageUploadResponse(BaseModel):
    """Response from image upload endpoint."""
    image_id: int
    file_path: str
    width_px: int | None = None
    height_px: int | None = None


class GradingModelInfo(BaseModel):
    """Model information response."""
    model_type: str
    n_grades: int
    grade_labels: dict[int, str]
    backbone: str
    trained: bool
    best_val_acc: float | None = None
    n_train: int | None = None
    n_val: int | None = None
    timestamp: str | None = None
