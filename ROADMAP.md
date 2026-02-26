# Ovulite – Development Roadmap

> **Source of Truth:** `docs/OVULITE PRESENTATION (1).pdf`
> **Data constraint:** 488 ET records, 482 unlabeled embryo images, ultra-small N

---

## Phase 0 — Foundation & Scaffold

**Goal:** Repository structure, Docker infrastructure, database schema, auth system, structured logging

**Plans:** 4 plans in 3 waves

Plans:
- [ ] 00-01-PLAN.md — Monorepo scaffold + Docker infrastructure + environment config
- [ ] 00-02-PLAN.md — Database layer: SQLAlchemy models + Alembic migrations (12 tables + view)
- [ ] 00-03-PLAN.md — Frontend skeleton: React + Vite + Tailwind + routing + API client
- [ ] 00-04-PLAN.md — Auth system (JWT + bcrypt + RBAC) + structured logging

**Wave structure:**
| Wave | Plans | Parallel |
|------|-------|----------|
| 1 | 00-01 (scaffold + docker) | solo |
| 2 | 00-02 (backend + DB), 00-03 (frontend) | parallel |
| 3 | 00-04 (auth + logging) | solo |

**Verification gate:** `docker compose up` starts all services; login flow works; DB has 12 tables; structured JSON logs.

---

## Phase 1 — Data Intake & Validation

**Goal:** Ingest historical CSV data, validate, and expose CRUD API for ET records

| Task | Description | Deliverable |
|------|-------------|-------------|
| 1.1 | CSV ingestion script for ET Data.csv | Parses all 488 rows into normalized tables |
| 1.2 | CSV ingestion for client pregnancy reports | Cross-references with main ET data |
| 1.3 | Data cleaning pipeline | Handles duplicates, dirty donor IDs, date parsing |
| 1.4 | Validation rules engine | Rejects: missing CL, out-of-range values, invalid protocols |
| 1.5 | REST API: CRUD for donors, sires, recipients, embryos | Pydantic models + endpoints |
| 1.6 | REST API: CRUD for et_transfers | Full create/read/update with validation |
| 1.7 | REST API: Bulk import endpoint | Upload CSV → validate → ingest |
| 1.8 | Frontend: Data entry forms | ET record form with validation feedback |
| 1.9 | Frontend: Data table views | Paginated, sortable tables for all entities |
| 1.10 | Data dictionary documentation | Column definitions, valid ranges, business rules |

**Verification gate:** All 488 ET records imported; UI can enter new record; invalid CL rejected (AT-1, AT-2).

---

## Phase 2 — Pregnancy Prediction Pipeline

**Goal:** Train, evaluate, and serve pregnancy prediction model with uncertainty

| Task | Description | Deliverable |
|------|-------------|-------------|
| 2.1 | Feature engineering script | Canonical feature matrix from `vw_et_features` |
| 2.2 | Leakage-safe split implementation | Temporal holdout + GroupKFold by donor |
| 2.3 | Baseline: Logistic Regression | Trained model + metrics report |
| 2.4 | Primary: TabPFN integration | TabPFN model + metrics report |
| 2.5 | Benchmark: XGBoost | XGBoost model + metrics report |
| 2.6 | Calibration (Isotonic/Platt) | Post-hoc calibration on validation set |
| 2.7 | SHAP explanations | Per-prediction feature contributions |
| 2.8 | Model comparison report | Side-by-side metrics table (Markdown) |
| 2.9 | Prediction API endpoint | `POST /predict/pregnancy` → P + CI + SHAP |
| 2.10 | Frontend: Prediction UI | Input form → probability + explanation display |
| 2.11 | Model versioning & artifact storage | Saved models with metadata JSON |
| 2.12 | Uncertainty display in UI | Confidence intervals, risk bands, calibration plot |

**Metrics on holdout:**
- ROC-AUC, PR-AUC, Calibration curve, Confusion matrix, Brier score

**Verification gate:** Prediction returns probability + CI + SHAP for new input (AT-3, AT-7, AT-9).

---

## Phase 3 — Embryo Grading Model

**Goal:** AI embryo grading via image + metadata fusion with visual explanations

| Task | Description | Deliverable |
|------|-------------|-------------|
| 3.1 | Image preprocessing pipeline | Normalize, resize 224×224, augmentation |
| 3.2 | Image-to-record linkage | Map blq{N}.jpg → embryo records |
| 3.3 | Self-supervised pretraining (SimCLR) | Contrastive learning on 482 images |
| 3.4 | CNN backbone setup (EfficientNet-B0) | Pretrained weights, frozen early layers |
| 3.5 | Metadata branch encoding | Embryo day + stage + donor + media + tech → embedding |
| 3.6 | Fusion model (CNN + MLP) | Combined architecture trained end-to-end |
| 3.7 | Grad-CAM implementation | Heatmap generation for visual explanations |
| 3.8 | Grade + viability output head | Grade (1/2/3) + viability probability |
| 3.9 | Grading API endpoint | `POST /grade/embryo` → grade + heatmap + score |
| 3.10 | Image upload API | File upload → storage → DB registry |
| 3.11 | Frontend: Upload & grading UI | Drag-drop image → grade + Grad-CAM overlay |

**Verification gate:** Upload image → returns grade + heatmap (AT-4).

---

## Phase 4 — Lab QC & Anomaly Detection

**Goal:** Unsupervised monitoring of lab process health

| Task | Description | Deliverable |
|------|-------------|-------------|
| 4.1 | Feature engineering for QC signals | Technician stats, media batch stats, temporal aggregation |
| 4.2 | Isolation Forest training | Anomaly scoring on technician/media/batch |
| 4.3 | EWMA / CUSUM control charts | Time-series drift detection |
| 4.4 | Synthetic anomaly injection for testing | Generate test batches with known anomalies |
| 4.5 | QC API endpoints | `GET /qc/anomalies`, `GET /qc/charts` |
| 4.6 | Frontend: QC dashboard | Control charts + anomaly alerts |
| 4.7 | Alert system | Severity-tagged anomaly notifications |

**Verification gate:** Synthetic anomaly batch detected and flagged (AT-5).

---

## Phase 5 — Analytics Dashboard & Final Evaluation

**Goal:** Unified reproductive dashboard + protocol analytics + system evaluation

| Task | Description | Deliverable |
|------|-------------|-------------|
| 5.1 | Protocol effectiveness analysis | Logistic regression + propensity score adjustment |
| 5.2 | SHAP analysis for protocol impact | Feature importance for protocol variable |
| 5.3 | Pregnancy % by protocol visualization | Bar/funnel charts |
| 5.4 | Reproductive KPI dashboard | Pregnancy rates, embryo utilization, IVF funnel |
| 5.5 | Donor performance analytics | Per-donor success rates + trends |
| 5.6 | Technician performance analytics | Per-tech stats (appropriately anonymized) |
| 5.7 | Biomarker sweet spot analysis | CL size vs pregnancy rate curves |
| 5.8 | Model monitoring dashboard | Calibration plot, drift detection over time |
| 5.9 | Full system acceptance testing | Run all AT-1 through AT-10 |
| 5.10 | Limitations documentation | What system cannot do; confidence boundaries |
| 5.11 | Final model report | Comprehensive Markdown with all metrics and plots |
| 5.12 | User documentation | System guide for veterinarians and embryologists |

**Verification gate:** All acceptance tests pass (AT-1 through AT-10). Dashboard renders all KPIs (AT-6).

---

## Phase Dependencies

```
Phase 0 ──► Phase 1 ──► Phase 2 ──┐
                   │               ├──► Phase 5
                   └──► Phase 3 ──┤
                   └──► Phase 4 ──┘
```

- Phase 2, 3, 4 can proceed in parallel after Phase 1 completes
- Phase 5 requires outputs from Phases 2, 3, and 4

---

## Risk Register

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| TabPFN fails on this dataset | High | Medium | XGBoost + Logistic Regression as fallbacks |
| Embryo images have no usable labels | High | High | SimCLR self-supervised pretraining |
| 488 records insufficient for XGBoost | Medium | Medium | Max depth ≤ 4; strong regularization |
| BCScore 77.5% missing | Medium | Certain | Missing flag indicator + imputation |
| Embryo grade has no variance | Medium | Certain | Rely on other features; document limitation |
| Donor data quality issues | Medium | Certain | Manual mapping table; fuzzy matching |
| Class imbalance (71% Open) | High | Certain | class_weight=balanced; PR-AUC metric |
| Overfitting to small N | Critical | High | Strict holdout; simplicity bias; monitoring |

---

## Current Phase: 0 — Foundation & Scaffold

**Next action:** Execute Phase 0 tasks (repository scaffold → Docker → DB schema → Auth)
