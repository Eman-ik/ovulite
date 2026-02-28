# Ovulite — Final Model Report

> **Version:** 1.0  
> **Date:** 2025-02-28  
> **Authors:** AI-Generated (Copilot)

---

## 1. Executive Summary

Ovulite is an AI-driven reproductive intelligence system for bovine embryo transfer (ET) programs. It provides:

1. **Pregnancy Prediction** — binary classification (Pregnant vs Open) from pre-transfer features
2. **Embryo Grading** — 3-class quality assessment from blastocyst images + metadata
3. **Lab QC Monitoring** — unsupervised anomaly detection on technician/protocol/batch metrics
4. **Analytics Dashboard** — KPIs, protocol effectiveness, donor performance, biomarker analysis

Built on 488 ET records and 482 blastocyst images from Pakistani cattle IVF programs.

---

## 2. Data Summary

| Metric | Value |
|--------|-------|
| Total ET Records | 488 |
| With Pregnancy Outcome | ~472 |
| Pregnancy Rate | ~28.8% |
| Class Balance | 71% Open / 29% Pregnant |
| Blastocyst Images | 482 |
| Unique Donors | ~50+ |
| Unique Technicians | ~10 |
| Protocols | ~5 |
| Date Range | ~12+ months |

### Key Data Challenges
- Ultra-small N for ML (488 records)
- 77.5% missing BC scores
- No ground-truth embryo grade labels
- Near-zero variance in embryo grade column

---

## 3. Pregnancy Prediction Model

### Architecture
- **Primary**: TabPFN (Prior-Fitted Network for tabular data) with CalibratedLR fallback
- **Fallback**: XGBoost (max_depth=4, strong regularization) and Logistic Regression
- **Calibration**: Isotonic calibration post-hoc on all models
- **Validation**: GroupKFold (5 folds, grouped by donor)
- **Holdout**: Temporal split (Dec 2025+)

### Features
- **Numeric (8)**: cl_measure_mm, embryo_stage, embryo_grade, heat_day, donor_bw_epd, sire_bw_epd, days_opu_to_et, bc_score
- **Categorical (7)**: cl_side, protocol_name, fresh_or_frozen, technician_name, donor_breed, semen_type, customer_id
- **Binary (1)**: bc_missing flag

### Leakage Prevention
Excluded: pc1_result, pc1_date, pc2_result, pc2_date, fetal_sexing, days_in_pregnancy, et_number, lab, satellite

### Expected Performance
- **PR-AUC**: Primary metric (preferred due to class imbalance)
- **ROC-AUC, Brier Score, F1**: Secondary metrics
- **Bootstrap CI**: 200 iterations for uncertainty quantification
- **SHAP**: TreeExplainer for feature contribution analysis

### Inference
- Singleton `PregnancyPredictor` pattern
- Predictions persisted to database for audit trail
- Risk bands: Low (0–30%), Medium (30–60%), High (60–100%)

---

## 4. Embryo Grading Model

### Architecture
- **Backbone**: EfficientNet-B0 (1280-dim feature vector)
- **Pretraining**: SimCLR self-supervised on 482 unlabeled images
- **Head**: Dual-output — 3-class grade (softmax) + viability score (sigmoid)
- **Metadata fusion**: MLP branch (32-dim) concatenated with image features
- **Explainability**: Grad-CAM on last convolutional block

### Labels
- Pseudo-labels from pregnancy outcomes:
  - **High**: Pregnant (P) on first PC check
  - **Medium**: Recheck (R)
  - **Low**: Open (O)
- NOT embryologist consensus — these are outcome-derived proxies

### Training Strategy
1. SimCLR pretraining (contrastive learning on augmented pairs)
2. Transfer to supervised model with frozen early layers
3. Fine-tuning with combined cross-entropy + BCE loss
4. Grad-CAM visualization for interpretability

---

## 5. QC Anomaly Detection

### Approach
- **Isolation Forest**: contamination=0.15, n_estimators=200
- **Feature Matrix**: Technician × month batches with z-score normalization
- **Metrics**: pregnancy_rate, avg_cl_measure, avg_embryo_grade, transfer_count, std_cl_measure
- **Control Charts**: EWMA (λ=0.2, L=3) and CUSUM (k=0.5σ, h=4σ)
- **Alert System**: 3 severities (critical, warning, info) from both IF and chart violations

### Synthetic Validation
- 5 anomaly types: low_preg_rate, cl_drift, grade_anomaly, volume_spike, mixed
- `verify_detection()` checks detection rate against ground truth injected anomalies

---

## 6. Analytics

### Protocol Effectiveness
- Pregnancy rates per protocol with Wilson 95% CIs
- Logistic regression with protocol as feature (adjusted for CL measure, heat day)
- Permutation importance for protocol variable contribution

### Donor Performance
- Per-donor pregnancy rates, trends, breed-level statistics
- Active months tracking, comparison to global mean

### Biomarker Sweet Spots
- CL measure binned analysis (8 bins from 0–50mm)
- BC score and heat day quantile-bin analysis
- Optimal range identification with Wilson CIs

### KPIs
- Total transfers, pregnancy rate, embryo utilization
- IVF funnel (embryos → CL verified → transferred → outcome → pregnant)
- Monthly trends, fresh vs frozen comparison

---

## 7. System Architecture

```
Frontend (React 19 + TypeScript + Vite)
    ├── Dashboard (DashboardPage)
    ├── Data Entry (DataEntryPage, TransferFormPage)
    ├── Predictions (PredictionPage)
    ├── Embryo Grading (GradingPage)
    ├── Lab QC (QCDashboardPage)
    └── Analytics (AnalyticsPage)

Backend (FastAPI + SQLAlchemy 2.0 + PostgreSQL)
    ├── Auth (JWT + bcrypt + RBAC)
    ├── CRUD APIs (donors, sires, recipients, embryos, transfers, technicians, protocols)
    ├── Import API (CSV ingestion)
    ├── Prediction API (TabPFN inference)
    ├── Grading API (EfficientNet inference)
    ├── QC API (Isolation Forest + control charts)
    └── Analytics API (KPIs + protocol + donor + biomarker)

ML Pipeline
    ├── ml/config.py (features, model params)
    ├── ml/train_pipeline.py (training orchestration)
    ├── ml/predict.py (inference singleton)
    ├── ml/grading/ (embryo grading pipeline)
    ├── ml/qc/ (anomaly detection pipeline)
    └── ml/analytics/ (analytics computations)
```

---

## 8. Known Limitations

See [LIMITATIONS.md](LIMITATIONS.md) for comprehensive documentation of:
- Data limitations (sample size, missing data, class imbalance)
- Model limitations (calibration, generalization, causal claims)
- System boundaries (when not to trust predictions)
- Ethical considerations

---

## 9. Recommendations for Production

1. **Re-train models** as new data accumulates (~quarterly or every 100 records)
2. **Monitor calibration** via Brier score on rolling evaluation windows
3. **Track prediction drift** using the QC monitoring infrastructure
4. **Collect embryologist grades** for future supervised grading model
5. **A/B test protocols** if system suggests protocol differences
6. **Audit trail**: All predictions are persisted — use for retrospective analysis
7. **GPU deployment**: Embryo grading inference benefits from GPU; pregnancy prediction is CPU-sufficient
