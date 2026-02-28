# Phase 4: Lab QC & Anomaly Detection — Summary

## One-liner
Isolation Forest anomaly detection + EWMA/CUSUM control charts with React dashboard and FastAPI endpoints

## Objective
Unsupervised monitoring of lab process health: detect anomalous technician batches, track metric drift over time, generate severity-tagged alerts, and surface all QC data in a real-time dashboard.

## Tasks Completed

| # | Task | Commit | Key Files |
|---|------|--------|-----------|
| 1 | QC feature engineering + Isolation Forest + EWMA/CUSUM + synthetic injection + alerts | `86df599` | ml/qc/*.py (8 files) |
| 2 | Backend QC API endpoints + Pydantic schemas | `eb433a9` | backend/app/api/qc.py, backend/app/schemas/qc.py, backend/app/main.py |
| 3 | Frontend QC dashboard with control charts, alerts, technician stats | `9a0ba62` | frontend/src/pages/QCDashboardPage.tsx, frontend/src/App.tsx |

## What Was Built

### ML QC Module (`ml/qc/`)
- **config.py** — Isolation Forest parameters (contamination=0.15, n_estimators=200), EWMA (λ=0.2, L=3), CUSUM (k=0.5, h=4), alert severities, feature grouping, min sample sizes
- **features.py** — `load_et_data()` auto-discovers CSV, `compute_technician_stats()` (pregnancy rate, CL stats, grade/BC scores), `compute_protocol_stats()`, `compute_monthly_metrics()`, `compute_batch_features()` (z-scores relative to global), `build_qc_feature_matrix()` (technician×month batches with min sample filtering)
- **anomaly_detector.py** — `train_isolation_forest()` trains on feature matrix, produces anomaly scores + severity labels, saves model via joblib
- **control_charts.py** — `compute_ewma()` (exponentially weighted moving average with target/UCL/LCL), `compute_cusum()` (cumulative sum with directional shift detection), `build_control_charts()` for pregnancy_rate, avg_cl_measure, avg_embryo_grade
- **synthetic.py** — `inject_synthetic_anomalies()` with 5 anomaly types (low_preg_rate, cl_drift, grade_anomaly, volume_spike, mixed), `verify_detection()` checks detection rate against ground truth
- **alerts.py** — `Alert` class (type/entity/severity/metric/value/baseline/description), `generate_iforest_alerts()` from anomaly results, `generate_chart_alerts()` from control chart violations, `combine_and_prioritize()` sorts critical→warning→info
- **run_pipeline.py** — CLI entry point tying all modules; saves JSON artifacts to `ml/artifacts/qc/` (summary, charts, alerts)

### Backend QC API (`backend/app/api/qc.py`)
- `GET /qc/anomalies` — filtered anomaly alerts with severity query param, auto-runs pipeline if no artifacts
- `GET /qc/charts` — EWMA + CUSUM control chart data per metric, filterable by metric name
- `GET /qc/technicians` — per-technician QC stats with global pregnancy rate comparison
- `GET /qc/summary` — pipeline overview (total records, batches, anomaly rate, alert counts)
- `POST /qc/run` — trigger QC pipeline execution with optional synthetic anomaly injection

### Frontend QC Dashboard (`frontend/src/pages/QCDashboardPage.tsx`)
- Summary cards (total records, anomalies detected, active alerts with severity badges, technician count)
- Interactive control charts with metric selector (EWMA bar chart with UCL/LCL/out-of-control markers, CUSUM dual-direction bars with shift detection)
- QC Alerts table (severity badge, source type, entity, period, description, metric value)
- Technician Performance table (transfer count, pregnancy rate, vs-mean with trend arrows, CL stats, embryo grade, BC score)
- Pipeline run/refresh controls

## Decisions Made
- Lazy pipeline execution: API auto-runs QC pipeline if no artifacts exist, caches JSON to disk
- 5 synthetic anomaly types for comprehensive detection testing
- EWMA λ=0.2 (moderate smoothing), CUSUM k=0.5σ/h=4σ (standard industrial parameters)
- Isolation Forest contamination=0.15 (higher than default 0.10 due to small dataset variance)
- Text-based bar chart visualization (no charting library dependency) — suitable for MVP, can upgrade to Recharts later
- Route `/lab-qc` matches pre-existing AppLayout navigation item

## Deviations from Plan
None — plan executed as designed.

## Verification
- **AT-5 (synthetic anomaly detected):** `ml/qc/synthetic.py` provides `inject_synthetic_anomalies()` + `verify_detection()`. The `POST /qc/run?with_synthetic=true` endpoint exercises this validation.
- Control charts produce EWMA/CUSUM data with out-of-control flags
- Alert system generates severity-tagged notifications from both Isolation Forest and chart violations

## Tech Stack Additions
- **Libraries:** scikit-learn (Isolation Forest), numpy/pandas (EWMA/CUSUM), joblib (model serialization)
- **Patterns:** Lazy ML pipeline execution with JSON artifact caching; composite alert prioritization

## Files Created
- `ml/qc/__init__.py`
- `ml/qc/config.py`
- `ml/qc/features.py`
- `ml/qc/anomaly_detector.py`
- `ml/qc/control_charts.py`
- `ml/qc/synthetic.py`
- `ml/qc/alerts.py`
- `ml/qc/run_pipeline.py`
- `backend/app/api/qc.py`
- `backend/app/schemas/qc.py`
- `frontend/src/pages/QCDashboardPage.tsx`

## Files Modified
- `backend/app/main.py` — added QC router
- `frontend/src/App.tsx` — added `/lab-qc` route

## Next Phase Readiness
Phase 5 (Analytics Dashboard & Final Evaluation) can proceed. All Phase 5 prerequisites are met:
- Phase 2 outputs: Pregnancy prediction model + SHAP explanations
- Phase 3 outputs: Embryo grading model + Grad-CAM
- Phase 4 outputs: QC anomaly detection + control charts + technician stats
