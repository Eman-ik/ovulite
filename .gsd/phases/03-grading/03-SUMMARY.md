---
phase: 3
plan: 1
subsystem: ml-grading
tags: [pytorch, efficientnet, simclr, grad-cam, embryo-grading, image-classification]
dependency-graph:
  requires: [phase-0, phase-1]
  provides: [embryo-grading-api, grading-ui, grad-cam-heatmaps]
  affects: [phase-5-analytics]
tech-stack:
  added: [torch, torchvision, Pillow, opencv-python]
  patterns: [SimCLR-contrastive-pretraining, EfficientNet-backbone, metadata-fusion, Grad-CAM, pseudo-labeling]
key-files:
  created:
    - ml/grading/__init__.py
    - ml/grading/config.py
    - ml/grading/preprocessing.py
    - ml/grading/linkage.py
    - ml/grading/models.py
    - ml/grading/train.py
    - ml/grading/predict.py
    - ml/grading/run_training.py
    - backend/app/api/grading.py
    - backend/app/schemas/grading.py
    - frontend/src/pages/GradingPage.tsx
  modified:
    - backend/app/main.py
    - backend/requirements.txt
    - ml/requirements.txt
    - frontend/src/App.tsx
decisions:
  - 3-class pseudo-labels from pregnancy outcomes (no ground-truth embryo grades)
  - SimCLR self-supervised pretraining before supervised fine-tuning
  - EfficientNet-B0 backbone (1280-dim) with frozen early layers
  - Metadata fusion via MLP branch (32-dim output)
  - Combined grade (3-class) + viability (sigmoid) dual-head output
  - Grad-CAM on last conv block for visual explanations
  - Singleton EmbryoGrader pattern for API serving
metrics:
  duration: ~25min
  completed: 2025-02-27
---

# Phase 3: Embryo Grading Model Summary

**One-liner:** EfficientNet-B0 + metadata fusion with SimCLR pretraining, 3-class pseudo-labels from pregnancy outcomes, Grad-CAM heatmaps, drag-drop grading UI

## What Was Built

### ML Grading Pipeline (ml/grading/)
- **config.py** — All hyperparameters: IMAGE_SIZE=224, SimCLR (100 epochs, temp 0.5), supervised (50 epochs), EfficientNet-B0 backbone
- **preprocessing.py** — Train/eval/SimCLR augmentation transforms, EmbryoImageDataset for contrastive pairs, GradingDataset for supervised training with metadata tensors
- **linkage.py** — Maps blq{N}.jpg → ET record N, builds 3-class pseudo-labels: High viability (Pregnant), Medium (Open+Grade1), Low (Open+Grade≥2)
- **models.py** — SimCLRModel (backbone + projection head), EmbryoGradingModel (CNN + MetadataBranch + fusion MLP + grade/viability heads), GradCAM class, heatmap overlay generation
- **train.py** — Two-stage pipeline: (1) SimCLR contrastive pretraining on all 482 images, (2) supervised fine-tuning with class-weighted CE + BCE loss, early stopping, cosine/plateau schedulers
- **predict.py** — EmbryoGrader singleton: lazy model loading, grade inference, Grad-CAM heatmap generation
- **run_training.py** — CLI: `python -m ml.grading.run_training [--simclr | --supervised]`

### Backend API (backend/app/api/grading.py)
- `POST /grade/embryo` — Upload image + optional metadata → GradingResult (grade, viability, probabilities)
- `POST /grade/embryo-with-heatmap` — Same but returns base64-encoded Grad-CAM overlay
- `GET /grade/model-info` — Model metadata (type, accuracy, training info)
- `POST /grade/upload` — Store embryo image to disk + embryo_images table

### Frontend UI (frontend/src/pages/GradingPage.tsx)
- Drag-and-drop image upload with live preview
- Optional metadata form (stage, grade, breed, fresh/frozen, technician)
- Grade result card: viability label badge, score gauge bar
- Class probability bars (High/Medium/Low with color coding)
- Grad-CAM heatmap overlay toggle on uploaded image
- Route: `/embryo-grading` (already wired in AppLayout sidebar)

## Key Design Decisions

1. **Pseudo-labels instead of true grades:** 482/488 embryos are Grade 1, making true grade prediction useless. Used pregnancy outcome as proxy: Pregnant→High, Open+G1→Medium, Open+G≥2→Low
2. **SimCLR first:** Self-supervised contrastive pretraining learns visual features from all 482 images before supervised fine-tuning with the noisy pseudo-labels
3. **EfficientNet-B0:** Compact backbone (5.3M params) suitable for small dataset. Frozen early layers, fine-tune blocks 7-8 only
4. **Dual heads:** Grade classification (3-class CE) + viability regression (BCE). Grade is primary objective (loss weight 1.0 vs 0.5)
5. **Graceful degradation:** HAS_TORCH flag throughout; API returns 503 if PyTorch unavailable

## Deviations from Plan

None — plan executed as written.

## Commits

| # | Hash | Message |
|---|------|---------|
| 1 | d5c713c | feat(03-01): embryo grading ML pipeline |
| 2 | 9321826 | feat(03-02): grading API endpoints |
| 3 | 1582383 | feat(03-03): embryo grading UI |

## Next Phase Readiness

Phase 4 (Lab QC & Anomaly Detection) can proceed independently. No blockers.

Model training has not been run yet (requires PyTorch installation + GPU recommended). The API and UI are fully wired and will work once `ml/artifacts/grading/grading_model.pt` exists.
