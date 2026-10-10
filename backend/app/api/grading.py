"""Embryo grading / similarity API endpoints.

Provides:
- POST /grade/embryo — upload image → Grade 1/2/3 prediction (real trained classifier)
- POST /grade/embryo-with-heatmap — same, plus a Grad-CAM visual explanation
- POST /grade/similar-cases — upload image → nearest visually-similar known cases
- GET  /grade/model-info — similarity model metadata
- POST /grade/upload — upload and store an embryo image

Note on history: /grade/embryo and /grade/embryo-with-heatmap were removed in
an earlier version of this router because the classifier had never been
trained on real labels — the local ET dataset's `Embryo Grade` column is
482/488 rows = Grade 1, no exploitable signal. /grade/similar-cases was
added as an honest replacement (SimCLR nearest-neighbor search, no labels
required). That gap is now closed: the same 482 images were verified
(MD5, byte-identical) to be a published, openly licensed dataset — Rocha
et al. 2017, Scientific Data — which carries real, varied expert grade
labels for those exact images. See
docs/dataset/external/rocha2017_bovine_blastocyst/DATASET_CARD.md and
ml/grading/real_labels.py / train_real_grading.py. /grade/embryo and
/grade/embryo-with-heatmap are restored here, now backed by a real trained
classifier — see GradePredictionResponse.caveats for what it does and does
not support (trained on an external dataset, not Ovulite's own farm data).
/grade/similar-cases remains available as a complementary tool.
"""

import hashlib
import io
import logging
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    LAB_WRITE_ROLES,
    PREDICTION_RUN_ROLES,
    get_current_user,
    require_role,
)
from app.database import get_db
from app.models.embryo import Embryo
from app.models.embryo_ai_assessment import EmbryoAIAssessment
from app.models.user import User
from app.schemas.grading import (
    EmbryoAIAssessmentResponse,
    EmbryoGradeComparison,
    GradePredictionResponse,
    GradePredictionWithHeatmapResponse,
    GradingModelInfo,
    ImageUploadResponse,
    SimilarCase,
    SimilarCaseMetadata,
    SimilarCasesResponse,
)

from ml.grading.morphometrics import BlastocystNotFound

logger = logging.getLogger(__name__)
router = APIRouter()

# Add project root to sys.path so ml package is importable
_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

_MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10MB


def _validate_and_normalize_image(image_bytes: bytes) -> tuple[bytes, int, int]:
    """Validate image bytes and normalize output while stripping metadata.

    Returns normalized image bytes, width, and height.
    """
    if len(image_bytes) == 0:
        raise HTTPException(400, "Empty image file")
    if len(image_bytes) > _MAX_IMAGE_BYTES:
        raise HTTPException(400, "Image too large (max 10MB)")

    try:
        from PIL import Image as PILImage

        # Ensure decoder is initialized and can read uploaded formats.
        PILImage.init()

        with PILImage.open(io.BytesIO(image_bytes)) as img:
            rgb = img.convert("RGB")
            width, height = rgb.size

        # Re-encode to strip EXIF and other metadata.
        sanitized = io.BytesIO()
        rgb.save(sanitized, format="JPEG", quality=95)
        sanitized_bytes = sanitized.getvalue()
        return sanitized_bytes, width, height
    except ImportError:
        logger.exception("Pillow is not installed; cannot process uploaded image")
        raise HTTPException(500, "Image processing backend is unavailable")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, "Invalid image file")


def _get_similarity_index():
    """Lazy-load the singleton similarity index. Raises on failure (no fake fallback)."""
    from ml.grading.similarity import get_similarity_index

    return get_similarity_index()


def _get_tabular_classifier():
    """Lazy-load the morphometric grader now served by POST /grade/embryo.

    It beats the CNN on the same held-out split (0.597 vs 0.542 accuracy, 0.385
    vs 0.192 Grade-2 recall) and is ~30x faster on CPU. The CNN is still used by
    /grade/embryo-with-heatmap, which needs Grad-CAM.
    """
    from ml.grading.tabular_predict import get_tabular_classifier

    return get_tabular_classifier()


def _get_grade_classifier():
    """Lazy-load the singleton grade classifier. Raises on failure (no fake fallback)."""
    from ml.grading.grade_classifier import get_grade_classifier

    return get_grade_classifier()


@router.post("/embryo", response_model=GradePredictionResponse)
async def grade_embryo(
    image: UploadFile = File(..., description="Embryo image (any file format)"),
    _current_user: User = Depends(require_role(*PREDICTION_RUN_ROLES)),
):
    """Predict embryo grade (1/2/3) for an uploaded image.

    Backed by a real trained classifier (ml/grading/train_real_grading.py)
    using the verified Rocha et al. 2017 grade labels — see
    GradePredictionResponse.caveats for scope and limitations.
    """
    raw_image_bytes = await image.read()
    # Validate (size, decodability) but measure the original pixels. The
    # sanitised re-encode is for storage; putting it before the measurement
    # flipped the grade on 3 of 39 test images.
    _validate_and_normalize_image(raw_image_bytes)

    try:
        classifier = _get_tabular_classifier()
        result = classifier.predict(raw_image_bytes)
    except BlastocystNotFound as e:
        # A specific, actionable failure: the framing is wrong, not the model.
        raise HTTPException(
            422,
            f"No blastocyst could be located in this image ({e}). It should show a "
            "single, roughly centred embryo filling a good part of the frame.",
        )
    except FileNotFoundError as e:
        raise HTTPException(503, f"Embryo grade classifier not available: {e}")
    except ImportError as e:
        raise HTTPException(503, f"Grade classifier dependencies not available: {e}")
    except Exception as e:
        logger.exception("Grade prediction failed")
        raise HTTPException(500, f"Grade prediction failed: {str(e)}")

    return GradePredictionResponse(
        predicted_grade=result["predicted_grade"],
        predicted_label=result["predicted_label"],
        confidence=result["confidence"],
        probabilities=result["probabilities"],
        model_type="morphometric_tabular_grade_classifier",
        model_version=classifier.version,
        # Grad-CAM belongs to the CNN. This model explains itself through named
        # morphometrics instead, so promising a heatmap here would be a lie.
        heatmap_available=False,
    )


@router.post("/embryo-with-heatmap", response_model=GradePredictionWithHeatmapResponse)
async def grade_embryo_with_heatmap(
    image: UploadFile = File(..., description="Embryo image (any file format)"),
    _current_user: User = Depends(require_role(*PREDICTION_RUN_ROLES)),
):
    """Predict embryo grade and return a Grad-CAM overlay explaining the prediction."""
    import base64

    raw_image_bytes = await image.read()
    image_bytes, _, _ = _validate_and_normalize_image(raw_image_bytes)

    try:
        classifier = _get_grade_classifier()
        result, overlay_bytes = classifier.predict_with_heatmap(image_bytes)
    except FileNotFoundError as e:
        raise HTTPException(503, f"Embryo grade classifier not available: {e}")
    except ImportError as e:
        raise HTTPException(503, f"Grade classifier dependencies not available: {e}")
    except Exception as e:
        logger.exception("Grade prediction with heatmap failed")
        raise HTTPException(500, f"Grade prediction failed: {str(e)}")

    return GradePredictionWithHeatmapResponse(
        predicted_grade=result["predicted_grade"],
        predicted_label=result["predicted_label"],
        confidence=result["confidence"],
        probabilities=result["probabilities"],
        model_version=classifier.version,
        heatmap_available=True,
        heatmap_image_base64=base64.b64encode(overlay_bytes).decode("ascii"),
    )


@router.post("/similar-cases", response_model=SimilarCasesResponse)
async def grade_similar_cases(
    image: UploadFile = File(..., description="Embryo image (any file format)"),
    k: int = Form(5, ge=1, le=20, description="Number of similar cases to return"),
    _current_user: User = Depends(require_role(*PREDICTION_RUN_ROLES)),
):
    """Find the k most visually similar known embryo cases for an uploaded image.

    This is a nearest-neighbor visual reference tool built on unsupervised
    SimCLR embeddings — it does NOT assign a grade or a calibrated confidence
    score. Use it to see which historical cases (and their recorded outcomes,
    where available) looked most similar to the new image.
    """
    raw_image_bytes = await image.read()
    image_bytes, _, _ = _validate_and_normalize_image(raw_image_bytes)

    try:
        index = _get_similarity_index()
        matches = index.find_similar(image_bytes, k=k)
    except FileNotFoundError as e:
        raise HTTPException(503, f"Embryo similarity model not available: {e}")
    except ImportError as e:
        raise HTTPException(503, f"Similarity model dependencies not available: {e}")
    except Exception as e:
        logger.exception("Similarity search failed")
        raise HTTPException(500, f"Similarity search failed: {str(e)}")

    return SimilarCasesResponse(
        matches=[
            SimilarCase(
                rank=m["rank"],
                filename=m["filename"],
                similarity=m["similarity"],
                metadata=SimilarCaseMetadata(**m["metadata"]),
            )
            for m in matches
        ],
        n_index_cases=len(index.filenames),
        model_type="simclr_efficientnet_b0",
    )


@router.get("/model-info", response_model=GradingModelInfo)
async def grading_model_info(_current_user: User = Depends(get_current_user)):
    """Describe the model that POST /grade/embryo actually serves.

    This reported the SimCLR similarity index, which backs /grade/similar-cases
    rather than grading. Naming the wrong model here is how one model's metrics
    end up attributed to another.
    """
    try:
        classifier = _get_tabular_classifier()
    except (FileNotFoundError, ImportError) as exc:
        return GradingModelInfo(
            model_type=f"morphometric tabular grader (unavailable: {exc})",
            backbone="none",
            trained=False,
            n_index_cases=None,
            timestamp=None,
        )
    except Exception as e:
        logger.exception("Failed to get grading model info")
        raise HTTPException(500, str(e))

    summary = classifier.accuracy_summary()
    cv = summary.get("cv_accuracy")
    return GradingModelInfo(
        model_type=(
            f"morphometric tabular grader ({classifier.selected_model}); "
            f"cross-validated accuracy {cv:.3f} against a human-agreement "
            "ceiling of 0.587" if cv is not None
            else f"morphometric tabular grader ({classifier.selected_model})"
        ),
        backbone="ml/grading/morphometrics.py — Hough + watershed + GLCM, 36 features",
        trained=True,
        n_index_cases=summary.get("n_test"),
        timestamp=classifier.version,
    )


@router.post("/upload", response_model=ImageUploadResponse)
async def upload_embryo_image(
    image: UploadFile = File(..., description="Embryo image (any file format)"),
    embryo_id: int | None = Form(None, description="Optional embryo ID to link to"),
    notes: str | None = Form(None),
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(*LAB_WRITE_ROLES)),
):
    """Upload and store an embryo image for later review.

    Saves the image to disk and creates a database record.
    """
    raw_image_bytes = await image.read()
    image_bytes, width, height = _validate_and_normalize_image(raw_image_bytes)

    # Compute hash for dedup
    file_hash = hashlib.sha256(image_bytes).hexdigest()

    # Save file
    upload_dir = _project_root / "uploads" / "embryo_images"
    upload_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{file_hash[:16]}.jpg"
    filepath = upload_dir / filename

    with open(filepath, "wb") as f:
        f.write(image_bytes)

    relative_path = filepath.relative_to(_project_root).as_posix()

    # Store in DB using API dependency session (supports test overrides).
    try:
        from app.models.embryo_image import EmbryoImage

        record = EmbryoImage(
            embryo_id=embryo_id,
            file_path=relative_path,
            file_hash=file_hash,
            width_px=width,
            height_px=height,
            notes=notes,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

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
            file_path=relative_path,
            width_px=width,
            height_px=height,
        )


@router.post("/embryo/{embryo_id}", response_model=EmbryoAIAssessmentResponse)
async def grade_and_record(
    embryo_id: int,
    image: UploadFile = File(..., description="Embryo image"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*LAB_WRITE_ROLES)),
):
    """Grade an image and record the result against an embryo.

    Writes a row in ``embryo_ai_assessments`` and never touches
    ``embryos.grade``, which is the embryologist's own assessment. The SRS
    requires the two to stay independent: a model that edited the human record
    would make every later comparison between them meaningless.

    Assessments accumulate rather than replace, so re-grading after a model
    change leaves both results readable.
    """
    embryo = (
        db.query(Embryo)
        .filter(
            Embryo.embryo_id == embryo_id,
            Embryo.organization_id == current_user.organization_id,
        )
        .first()
    )
    if embryo is None:
        raise HTTPException(404, "Embryo not found")

    raw_image_bytes = await image.read()
    _validate_and_normalize_image(raw_image_bytes)

    try:
        classifier = _get_tabular_classifier()
        result = classifier.predict(raw_image_bytes)
    except BlastocystNotFound as e:
        raise HTTPException(
            422,
            f"No blastocyst could be located in this image ({e}). It should show a "
            "single, roughly centred embryo filling a good part of the frame.",
        )
    except (FileNotFoundError, ImportError) as e:
        raise HTTPException(503, f"Embryo grade classifier not available: {e}")
    except Exception as e:
        logger.exception("Grade prediction failed")
        raise HTTPException(500, f"Grade prediction failed: {e}")

    assessment = EmbryoAIAssessment(
        organization_id=current_user.organization_id,
        embryo_id=embryo_id,
        model_name="morphometric_tabular_grade_classifier",
        model_version=classifier.version,
        predicted_grade=result["predicted_grade"],
        confidence=result["confidence"],
        probabilities=result["probabilities"],
        features=result["features"],
        image_sha256=hashlib.sha256(raw_image_bytes).hexdigest(),
        assessed_by_user_id=current_user.user_id,
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment


@router.get("/embryo/{embryo_id}/assessments", response_model=EmbryoGradeComparison)
async def embryo_grade_comparison(
    embryo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """The embryologist's grade and every AI assessment, side by side.

    Deliberately not reconciled into one number. ``agrees`` is reported so a
    reviewer can find disagreements, not so the system can resolve them.
    """
    embryo = (
        db.query(Embryo)
        .filter(
            Embryo.embryo_id == embryo_id,
            Embryo.organization_id == current_user.organization_id,
        )
        .first()
    )
    if embryo is None:
        raise HTTPException(404, "Embryo not found")

    assessments = (
        db.query(EmbryoAIAssessment)
        .filter(
            EmbryoAIAssessment.embryo_id == embryo_id,
            EmbryoAIAssessment.organization_id == current_user.organization_id,
        )
        .order_by(EmbryoAIAssessment.assessed_at.desc())
        .all()
    )
    latest = assessments[0].predicted_grade if assessments else None
    return EmbryoGradeComparison(
        embryo_id=embryo_id,
        manual_grade=embryo.grade,
        ai_assessments=assessments,
        latest_ai_grade=latest,
        agrees=None if (latest is None or embryo.grade is None) else latest == embryo.grade,
    )
