"""Embryo grading API endpoints (ROADMAP tasks 3.9-3.10).

Provides:
- POST /grade/embryo — upload image + optional metadata → grade + heatmap
- GET  /grade/model-info — model metadata
- POST /grade/upload — upload and store an embryo image
- GET  /grade/heatmap/{image_id} — retrieve cached Grad-CAM heatmap
"""

import base64
import hashlib
import io
import logging
import sys
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from app.schemas.grading import (
    GradingModelInfo,
    GradingResult,
    ImageUploadResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Add project root to sys.path so ml package is importable
_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# Lazy singleton
_grader = None


def _get_grader():
    global _grader
    if _grader is None:
        try:
            from ml.grading.predict import EmbryoGrader
            _grader = EmbryoGrader.get_instance()
        except ImportError as e:
            logger.error(f"Failed to import grading module: {e}")
            raise HTTPException(
                status_code=503,
                detail="Grading model not available. Install PyTorch dependencies.",
            )
    return _grader


# Heatmap cache (in-memory, keyed by image hash)
_heatmap_cache: dict[str, bytes] = {}


@router.post("/embryo", response_model=GradingResult)
async def grade_embryo(
    image: UploadFile = File(..., description="Embryo image (JPEG/PNG)"),
    embryo_stage: float | None = Form(None),
    embryo_grade: float | None = Form(None),
    donor_breed: str | None = Form(None),
    fresh_or_frozen: str | None = Form(None),
    technician_name: str | None = Form(None),
):
    """Grade an embryo image and return viability prediction with Grad-CAM heatmap.

    Upload a JPEG/PNG embryo image. Optionally provide metadata for improved accuracy.
    """
    # Validate file type
    if image.content_type and image.content_type not in ("image/jpeg", "image/png"):
        raise HTTPException(400, "Only JPEG and PNG images are supported")

    image_bytes = await image.read()
    if len(image_bytes) == 0:
        raise HTTPException(400, "Empty image file")
    if len(image_bytes) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(400, "Image too large (max 10MB)")

    # Build metadata dict
    metadata = {}
    if embryo_stage is not None:
        metadata["embryo_stage"] = embryo_stage
    if embryo_grade is not None:
        metadata["embryo_grade"] = embryo_grade
    if donor_breed is not None:
        metadata["donor_breed"] = donor_breed
    if fresh_or_frozen is not None:
        metadata["fresh_or_frozen"] = fresh_or_frozen
    if technician_name is not None:
        metadata["technician_name"] = technician_name

    try:
        grader = _get_grader()
        result = grader.grade(image_bytes, metadata=metadata or None, generate_heatmap=True)
    except ImportError as e:
        raise HTTPException(503, f"Grading model dependencies not available: {e}")
    except Exception as e:
        logger.exception("Grading failed")
        raise HTTPException(500, f"Grading failed: {str(e)}")

    # Cache heatmap if generated
    heatmap_available = result.get("heatmap_bytes") is not None
    if heatmap_available:
        img_hash = hashlib.sha256(image_bytes).hexdigest()[:16]
        _heatmap_cache[img_hash] = result["heatmap_bytes"]

    return GradingResult(
        grade_label=result["grade_label"],
        grade_class=result["grade_class"],
        grade_probabilities=result["grade_probabilities"],
        viability_score=result["viability_score"],
        heatmap_available=heatmap_available,
    )


@router.post("/embryo-with-heatmap")
async def grade_embryo_with_heatmap(
    image: UploadFile = File(..., description="Embryo image (JPEG/PNG)"),
    embryo_stage: float | None = Form(None),
    embryo_grade: float | None = Form(None),
    donor_breed: str | None = Form(None),
    fresh_or_frozen: str | None = Form(None),
    technician_name: str | None = Form(None),
):
    """Grade an embryo and return result with base64-encoded heatmap."""
    if image.content_type and image.content_type not in ("image/jpeg", "image/png"):
        raise HTTPException(400, "Only JPEG and PNG images are supported")

    image_bytes = await image.read()
    if len(image_bytes) == 0:
        raise HTTPException(400, "Empty image file")

    metadata = {}
    if embryo_stage is not None:
        metadata["embryo_stage"] = embryo_stage
    if embryo_grade is not None:
        metadata["embryo_grade"] = embryo_grade
    if donor_breed is not None:
        metadata["donor_breed"] = donor_breed
    if fresh_or_frozen is not None:
        metadata["fresh_or_frozen"] = fresh_or_frozen
    if technician_name is not None:
        metadata["technician_name"] = technician_name

    try:
        grader = _get_grader()
        result = grader.grade(image_bytes, metadata=metadata or None, generate_heatmap=True)
    except Exception as e:
        logger.exception("Grading failed")
        raise HTTPException(500, f"Grading failed: {str(e)}")

    response = {
        "grade_label": result["grade_label"],
        "grade_class": result["grade_class"],
        "grade_probabilities": result["grade_probabilities"],
        "viability_score": result["viability_score"],
        "heatmap_base64": None,
    }

    if result.get("heatmap_bytes"):
        response["heatmap_base64"] = base64.b64encode(result["heatmap_bytes"]).decode("ascii")

    return response


@router.get("/model-info", response_model=GradingModelInfo)
async def grading_model_info():
    """Return information about the current grading model."""
    try:
        grader = _get_grader()
        info = grader.get_model_info()
    except Exception as e:
        logger.exception("Failed to get model info")
        raise HTTPException(500, str(e))

    return GradingModelInfo(**info)


@router.post("/upload", response_model=ImageUploadResponse)
async def upload_embryo_image(
    image: UploadFile = File(..., description="Embryo image (JPEG/PNG)"),
    embryo_id: int | None = Form(None, description="Optional embryo ID to link to"),
    notes: str | None = Form(None),
):
    """Upload and store an embryo image for later grading.

    Saves the image to disk and creates a database record.
    """
    if image.content_type and image.content_type not in ("image/jpeg", "image/png"):
        raise HTTPException(400, "Only JPEG and PNG images are supported")

    image_bytes = await image.read()
    if len(image_bytes) == 0:
        raise HTTPException(400, "Empty image file")

    # Compute hash for dedup
    file_hash = hashlib.sha256(image_bytes).hexdigest()

    # Get dimensions
    width, height = None, None
    try:
        from PIL import Image as PILImage
        img = PILImage.open(io.BytesIO(image_bytes))
        width, height = img.size
    except Exception:
        pass

    # Save file
    upload_dir = _project_root / "uploads" / "embryo_images"
    upload_dir.mkdir(parents=True, exist_ok=True)

    ext = ".jpg" if image.content_type == "image/jpeg" else ".png"
    filename = f"{file_hash[:16]}{ext}"
    filepath = upload_dir / filename

    with open(filepath, "wb") as f:
        f.write(image_bytes)

    # Store in DB (use sync session for simplicity)
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        from app.database import SQLALCHEMY_DATABASE_URL
        from app.models.embryo_image import EmbryoImage

        engine = create_engine(SQLALCHEMY_DATABASE_URL.replace("+asyncpg", "").replace("postgresql://", "postgresql://"))
        with Session(engine) as session:
            record = EmbryoImage(
                embryo_id=embryo_id,
                file_path=str(filepath.relative_to(_project_root)),
                file_hash=file_hash,
                width_px=width,
                height_px=height,
                notes=notes,
            )
            session.add(record)
            session.commit()
            session.refresh(record)

            return ImageUploadResponse(
                image_id=record.image_id,
                file_path=record.file_path,
                width_px=width,
                height_px=height,
            )
    except Exception as e:
        logger.warning(f"DB insert failed, returning file-only response: {e}")
        # Return without DB record if DB is unavailable
        return ImageUploadResponse(
            image_id=0,
            file_path=str(filepath.relative_to(_project_root)),
            width_px=width,
            height_px=height,
        )
