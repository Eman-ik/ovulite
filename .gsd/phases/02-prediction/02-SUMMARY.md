---
phase: 2
plan: "02-01 through 02-03"
subsystem: pregnancy-prediction
tags: [ml-pipeline, logistic-regression, tabpfn, xgboost, shap, calibration, prediction-api, react-ui]
dependency-graph:
  requires: [phase-0, phase-1]
  provides: [pregnancy-prediction-model, prediction-api, prediction-ui, model-versioning]
  affects: [phase-5-analytics, phase-5-evaluation]
tech-stack:
  added: [scikit-learn, xgboost, shap, joblib, pandas, numpy]
  patterns: [temporal-holdout, groupkfold, isotonic-calibration, bootstrap-ci, shap-explanations, singleton-predictor]
key-files:
  created:
    - ml/__init__.py
    - ml/config.py
    - ml/features.py
    - ml/split.py
    - ml/train_pipeline.py
    - ml/predict.py
    - ml/run_training.py
    - ml/requirements.txt
    - backend/app/api/predictions.py
    - backend/app/schemas/prediction.py
    - frontend/src/pages/PredictionPage.tsx
  modified:
    - backend/app/main.py
    - backend/requirements.txt
    - frontend/src/App.tsx
decisions:
  - "Temporal holdout: Dec 2025+ as untouched final test set"
  - "GroupKFold by donor tag for cross-validation (prevents group leakage)"
  - "TabPFN with CalibratedLR fallback when package unavailable"
  - "Bootstrap resampling (n=200) for per-prediction confidence intervals"
  - "Isotonic calibration (post-hoc) on all three models"
  - "SHAP Explainer for feature contributions per prediction"
  - "Lazy singleton predictor pattern for API serving"
  - "Model artifacts stored in ml/artifacts/{version}/ with metadata.json"
  - "Prediction persisted to predictions table for audit trail"
metrics:
  completed: 2025-02-27
  commits: 3
---

# Phase 2: Pregnancy Prediction Pipeline — Summary

**One-liner:** Complete ML pipeline with 3 models (LR/TabPFN/XGBoost), leakage-safe
temporal+donor-grouped splits, isotonic calibration, SHAP explanations, bootstrap CIs,
prediction API endpoint, and React UI with probability gauge and feature contribution chart.

## What Was Built

### Plan 02-01: ML Training Pipeline (Tasks 2.1–2.8, 2.11)

- **Feature engineering** (`ml/features.py`): Builds canonical feature matrix from
  CSV matching the `vw_et_features` database view. 8 numeric + 7 categorical + 1
  binary flag = 16 base features expanded to ~30+ after one-hot encoding.
- **Leakage-safe split** (`ml/split.py`): Temporal holdout (Dec 2025+) + 5-fold
  GroupKFold by donor. Recheck/missing outcomes excluded.
- **Three models** (`ml/train_pipeline.py`):
  - Logistic Regression (L2, balanced class weights) — baseline
  - TabPFN (primary, with CalibratedLR fallback) — primary
  - XGBoost (max_depth=4, early stopping, scale_pos_weight) — benchmark
- **Calibration**: Isotonic post-hoc calibration on all models.
- **SHAP**: Per-prediction feature contributions + global feature importance ranking.
- **Auto-generated comparison report**: Markdown with metrics table, feature
  importance, calibration notes.
- **Model versioning**: Artifacts in `ml/artifacts/{version}/` with metadata.json,
  encoder_map.joblib, model files, feature_names.json.
- **Bootstrap CIs**: 200-sample bootstrap for per-prediction 95% confidence intervals.

### Plan 02-02: Prediction API (Task 2.9)

- **POST `/predict/pregnancy`**: Accepts transfer features, returns probability,
  95% CI, risk band, and SHAP contributions. Persists prediction to DB.
- **GET `/predict/model-info`**: Returns loaded model metadata and top features.
- **Pydantic schemas**: PredictionInput (validated), PredictionOutput, ShapExplanation,
  ModelInfoResponse.
- **Singleton predictor**: Lazy-loaded from latest model artifacts.

### Plan 02-03: Frontend Prediction UI (Tasks 2.10, 2.12)

- **PredictionPage**: Input form with all 12 canonical features (dropdowns
  populated from API for protocols/technicians).
- **Probability gauge**: Large percentage display with color-coded risk band badge.
- **Confidence interval bar**: Visual bar showing 95% CI range with point estimate.
- **SHAP feature chart**: Top 10 contributions with green (increases pregnancy)
  and red (decreases pregnancy) bars.
- **Model info badge**: Shows currently loaded model name and version.

## Decisions Made

| Decision | Context |
|----------|---------|
| Temporal holdout Dec 2025+ | ~38% data reserved as untouched final test |
| GroupKFold by donor | Prevents same donor appearing in both train and val |
| TabPFN fallback to CalibratedLR | TabPFN package may not be installed in all envs |
| Bootstrap CI (n=200) | Simple, model-agnostic uncertainty estimation |
| Isotonic calibration | Better than Platt for non-linear models |
| Singleton predictor | Avoid re-loading model on every API request |
| Predictions persisted to DB | Audit trail for all ML predictions made |

## Deviations from Plan

None — plan executed as written.

## Verification Gate Check

| Criterion | Status |
|-----------|--------|
| Prediction returns P + CI + SHAP (AT-3) | ✅ POST /predict/pregnancy |
| Calibration reliability plot data (AT-7) | ✅ Stored in metadata.json calibration key |
| Uncertainty displayed in UI (AT-9) | ✅ CI bar + risk band on PredictionPage |
| Model report generated (AT-10) | ✅ MODEL_COMPARISON.md auto-generated |

## Commits

| Hash | Message |
|------|---------|
| `88f9954` | feat(02-01): pregnancy prediction ML pipeline |
| `1dc6439` | feat(02-02): prediction API endpoint with SHAP + CI + model info |
| `ab9644a` | feat(02-03): prediction UI with probability gauge, CI bar, SHAP chart |

## Next Phase Readiness

Phase 3 (Embryo Grading): Can proceed — no dependency on Phase 2.
Phase 4 (Lab QC): Can proceed — no dependency on Phase 2.
Phase 5 (Analytics): Requires Phase 2 outputs (prediction API, model artifacts).
