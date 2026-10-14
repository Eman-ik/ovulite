
# Ovulite AI Platform — Modules 2–5: Architecture & Implementation Plan

Summary
- Extend Module 1 (ingestion/validation) into a production-ready multi-module AI platform:
  - Module 2: Pregnancy Prediction (probabilistic)
  - Module 3: Pregnancy Risk Stratification + Explainability
  - Module 4: Biomarker Integration (dynamic update)
  - Module 5: AI Clinical Decision Support (recommendations & reports)
- Deliverables:
  - Model training pipeline, evaluation suite, model registry
  - Inference service (API) with calibrated probability output
  - Explainability endpoint (SHAP/LIME, feature importances)
  - Decision support engine that consumes probability + business rules and returns action + reasons
  - n8n integration points for orchestrating inference, reports, notifications, and downstream modules

Core principles
- Output probabilities (not binary labels)
- Explain predictions with feature contributions
- Keep models, schema, and raw files versioned for reproducibility
- Allow dynamic re‑scoring when biomarkers arrive (late-available features)
- Provide audit trail linking raw -> processed -> features -> model version -> prediction -> report

Recommended tech stack (example)
- Data storage: S3 (raw, staging, processed), Postgres or Snowflake for feature/label storage
- Feature store: Feast (optional) or materialized feature tables in Postgres
- ML stack: Python, scikit-learn, XGBoost, LightGBM, CatBoost, PyTorch (for NN), imbalanced-learn
- Explainability: SHAP (TreeExplainer for tree ensembles), LIME (optional)
- Model registry / tracking: MLflow
- Serving: FastAPI + Docker (or KFServing/Triton if Kubernetes)
- Orchestration: Airflow or Prefect for scheduled training jobs; n8n for event-driven inference and notifications
- Monitoring: Prometheus/Grafana, Sentry for errors
- CI/CD: GitHub Actions or GitLab CI
- Secrets / credentials: Vault or cloud secrets manager
- Optional: Kubernetes for scale, or simple Docker Compose for small deployments

Data & features
- Keep ingestion metadata from Module 1 (file_name, checksum, raw_path, schema_version)
- Feature groups (examples):
  - Recipient: breed, age, parity, BCS, milk_yield, days_postpartum, health_history_flags
  - Synchronization: protocol, hormones, day_of_cycle
  - Embryo: stage, grade, fresh/frozen, IVF/AI, donor_id
  - Procedure: technician_id, farm_id, season, ambient_temp, heat_stress_index
  - Corpus Luteum: cl_diameter_mm, cl_score
  - Lab biomarkers (future): IFNt_level, PAG_level, progesterone_ng_ml, day_measured
- Target: pregnancy outcome at defined follow-up (e.g., confirmed pregnancy at day 30/45)
- Data schema & contracts:
  - Keep schema.yaml versioned and reference schema_version in ingestion_report
  - Define primary key: recipient_id + embryo_id + transfer_date
  - Label handling: define follow-up windows and how late labels are appended

Module 2 — Pregnancy Prediction (Primary AI)
- Goal: return calibrated pregnancy probability (0–1) and model_version
- Model strategy:
  - Preprocessing: impute (domain-aware), encode categorical (target/ordinal/one-hot), scale numeric (robust scaler)
  - Feature engineering: derived features (days_postpartum_bins, embryo_age_interactions, CL_area=π*(d/2)^2, heat_stress_flag)
  - Feature selection: tree-based importance + recursive feature elimination (as needed)
  - Handle class imbalance: SMOTE or class-weighting (model dependent)
  - Evaluate many estimators (your 20-model roster) using consistent CV + nested hyperparameter tuning
  - Ensemble: stacking (meta-learner), or weighted voting; prefer stacking with calibrated base learners
  - Probability calibration: isotonic or Platt scaling (sklearn.calibration)
  - Model registry: save model, version, preprocessing pipeline, feature list to MLflow
- Training pipeline (high level)
  - load cleaned_training_table()
  - split train/val/test by time or clustering to reduce leakage
  - pipeline = ColumnTransformer + Imputer + Encoders + Estimator
  - cross_validate models, compute metrics, save artifacts to MLflow
- Metrics to compute per model:
  - ROC-AUC, PR-AUC, Accuracy, Precision, Recall, F1, MCC, Brier score
  - Calibration curve (reliability), confusion matrix, predicted probabilities distribution
- Recommended default models to include:
  - LightGBM, XGBoost, CatBoost, RandomForest, HistGradientBoosting, LogisticRegression (with L1/L2), MLP, Stacking
- Production inference:
  - Serve preprocessing pipeline + model. Input is validated feature set; return:
    { "probability": 0.91, "model_version": "mX.Y", "score_time": "ISO", "features_used": ["age","cl_diameter", ...] }

Module 3 — Pregnancy Risk Stratification & Explainability
- Risk mapping
  - Define bands, e.g.:
    - Probability >= 0.85 → Risk = LOW
    - 0.70 <= prob < 0.85 → Risk = MODERATE
    - prob < 0.70 → Risk = HIGH
  - Make bands configurable and logged per prediction
- Explainability
  - Use SHAP TreeExplainer for tree ensembles; return top-K features with SHAP values
  - Provide global feature importance and local explanations per prediction:
    - local: ordered list [("cl_diameter", +0.12), ("heat_stress", -0.10), ...]
    - global: feature importance bar chart, mean abs SHAP
  - Provide textual reasoning templates (rule-like) assembled from top SHAP features and domain rules, e.g.:
    - "Small CL (cl_diameter 12mm) reduces probability by 0.14; embryo grade 3 reduces by 0.08; heat stress reduces by 0.06."
- Combine explanations + business rules to produce "Reason" list for Module 5
- Implementation:
  - Implement /explain endpoint that returns shap_values, base_value, feature_names and a short human-readable reason summary

Module 4 — Biomarker Integration (dynamic updates)
- Key idea: prediction can be re-scored when later biomarkers (IFNτ, PAG, Progesterone) arrive
- Pattern:
  - At transfer time → initial prediction p0 (Model v)
  - After biomarker measurement → re-run inference with biomarker features → p1 (same or new model)
  - Alternatively: build a second-stage model / delta-model that predicts adjustment to p0 using biomarker inputs + p0
- Implementation options:
  1) Unified model that accepts biomarkers (but missing values allowed) → initial predictions use missing biomarkers; later re-score when biomarkers provided
  2) Two-stage approach: baseline model (no biomarkers) + biomarker updater model that takes baseline probability + biomarkers → outputs updated probability
- Practical approach:
  - Use option 2 for clarity: train a small model f_update(p0, IFNt, Prog, PAG, day_of_biomarker) → delta_p (or new calibrated prob)
  - Advantage: simpler to deploy, isolates biomarker effect, easier to explain
- Example flow:
  - Transfer: store p0 with model_version_0
  - Biomarker arrives (e.g., day 17): n8n trigger → fetch original features & p0 → call /biomarker_update endpoint → get p1 + explanation → update record, regenerate report & notify
- Safety: when biomarker contradicts p0 strongly, flag for clinical review

Module 5 — AI Clinical Decision Support
- Translate probability + explainability → action + reasons + expected success
- Decision rules (examples):
  - If prob >= 0.85 and risk == LOW → "Proceed with transfer" (Expected success 80–90%)
  - If 0.70 <= prob < 0.85 and risk == MODERATE → "Proceed, but monitor; consider higher-value embryo or re-evaluate recipient"
  - If prob < 0.70 or CL small or high heat stress → "Do NOT transfer — reasons: [list]" and suggested alternatives
- Decision output:
  {
    "probability": 0.71,
    "risk": "HIGH",
    "recommendation": "Do NOT transfer",
    "confidence": "moderate",
    "reasons": ["Small CL (12mm)", "Embryo grade 3", "Heat stress on day"],
    "actions": ["Select different recipient", "Consider fresh embryo", "Re-evaluate CL in X days"]
  }
- Build a templated report generator:
  - PDF or HTML summary including provenance, features, model_version, SHAP reasons, recommended action, and links to source files + validation reports
- Operationalize: decision support system must log clinician overrides for continuous learning

ML Pipeline implementation (concise pseudocode)
- Training job pseudocode:
```
# train.py (conceptual)
from sklearn.model_selection import StratifiedKFold, GridSearchCV
from sklearn.calibration import CalibratedClassifierCV
import mlflow

data = load_cleaned_data()
X, y = extract_features_and_label(data)
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

models = {
  'lgb': LightGBM(...),
  'xgb': XGB(...),
  'rf': RandomForest(...),
  'lr': LogisticRegression(...),
  'mlp': MLP(...),
  # add others...
}

for name, model in models.items():
  # pipeline includes preprocessing
  pipeline = Pipeline([('pre', preprocessor), ('clf', model)])
  clf = GridSearchCV(pipeline, param_grid[name], cv=cv, scoring='roc_auc')
  clf.fit(X, y)
  best = clf.best_estimator_
  # calibrate
  calib = CalibratedClassifierCV(best, cv='prefit', method='isotonic')
  calib.fit(X_val, y_val)
  # evaluate on holdout, compute metrics
  metrics = evaluate(calib, X_test, y_test)
  mlflow.log_params(...)
  mlflow.log_metrics(metrics)
  mlflow.sklearn.log_model(calib, "model")
```
- Save preprocessing artifacts and feature list in MLflow

Serving & API (FastAPI example)
- Endpoints:
  - POST /predict → validated features → returns probability, model_version
  - POST /explain → same input → returns SHAP local explanation + top reasons
  - POST /biomarker_update → p0 + biomarkers → returns updated probability + delta + explanation
  - GET /models → list model versions, metrics
- FastAPI snippet (conceptual):
```
from fastapi import FastAPI
app = FastAPI()

@app.post("/predict")
def predict(payload: PredictPayload):
    features = validate_and_preprocess(payload)
    prob = model.predict_proba([features])[0,1]
    return {"probability": float(prob), "model_version": model_version, "timestamp": now}

@app.post("/explain")
def explain(payload: PredictPayload):
    features = validate_and_preprocess(payload)
    shap_values = shap_explainer.shap_values(features)
    top = summarize_shap(shap_values, feature_names)
    return {"probability": prob, "shap": top}
```
- Deploy behind authentication, TLS, and rate limiting

Explainability (SHAP)
- For tree models use shap.TreeExplainer (fast)
- Return:
  - base_value, shap_values (per feature), top_k_contributors (feature, shap_value, direction)
- Present explanations as:
  - numeric contributions and plain-language summary (e.g., "CL diameter +0.12 increases probability")

Calibration & Ensembles
- Calibrate each base learner on held-out set or use cross-validated calibration
- For stacking: meta-learner trained on base model out-of-fold predictions; calibrate meta-learner
- Save calibration curves, Brier score to MLflow

n8n integration for Modules 2–5
- Overview: n8n remains the event-driven orchestration layer.
- High-level flow:
  - Module 1 finish → n8n triggers Module 2 inference job (HTTP Request to model API) → receives probability & model_version → call /explain to obtain SHAP summary → call decision support function (Python node) → write prediction + explanation to processed/predictions/ and DB → generate validation & decision report (Python node) → send notifications (Slack/Email) → optionally trigger Module 4 biomarker watch (S3/GDrive) for re-score events
- Node-by-node suggestions (concrete)
  1) Trigger: (already) ingestion success or Manual Trigger
  2) Function / Python: Build feature payload using validated CSV row(s) + provenance columns
  3) HTTP Request: POST /predict to model server for batch or single predictions
  4) HTTP Request: POST /explain (optional; may be expensive) or call explain on selected cases
  5) Python Node: DecisionSupport - map probability → risk band → recommendation + textual reasoning (combine SHAP top features and rule overrides)
  6) Write Binary / S3 node: Save predictions to processed/predictions/{date}/predictions.csv (include model_version and feature snapshot)
  7) Write CSV: Append rejected_rows (from Module 1) if downstream decision depends on it
  8) Python Node: Render report HTML / PDF (call LaTeX or WeasyPrint)
  9) HTTP / Slack / Email Node: Send final notification with link(s)
 10) Trigger: If biomarkers arrive later, File Watch → fetch biomarkers → call /biomarker_update endpoint and repeat decision flow (update record + re-notify)
- Where to use Python nodes:
  - Feature engineering for inference (apply same transforms as training or call feature store)
  - Decision support logic (rules + assemble reasons)
  - Report generation (HTML/PDF)
- Data model written by n8n:
  - predictions table CSV columns: primary_key, model_version, probability, risk_band, recommendation, reasons_json, features_json, shap_json, timestamp
  - reports stored under reports/predictions/{id}.html and linked in ingestion metadata

Quarantine & retriggering
- If Module 2 receives an input with insufficient primary keys or corrupted relationships, the Module 1 quarantine rules apply: skip inference and mark file/quips for manual review
- For rows with warning-level issues: inference proceeds, but annotate features with 'flagged_fields' so Module 5 can include caution in recommendations

CI/CD, retraining, and governance
- Scheduled retraining: weekly or monthly based on new labeled data; implement data drift checks to trigger retraining sooner
- Retrain when:
  - performance drop by pre-defined threshold (ROC-AUC or PR-AUC)
  - calibration drift (Brier score increases) or label distribution shift
- Keep model registry in MLflow; promote model versions to staging/production after evaluation & manual approval
- Logging & audit trail: each prediction must store model_version, preprocessing_version, and ingestion provenance
- Human-in-the-loop: store clinician overrides; use them as additional labeled data for model updates

Monitoring & metrics to collect
- Prediction service metrics:
  - request latency, error rate, throughput
  - distribution of probabilities, % in each risk band
  - number of biomarker-updates and delta probabilities
- Model performance monitoring:
  - rolling ROC-AUC, PR-AUC, Brier score on ground-truth labels (as they become available)
  - calibration (reliability diagram)
  - feature distribution drift per feature (KL divergence or PSI)
- Business KPIs:
  - pregnancy success rate over time per farm / cohort
  - clinician acceptance rate of recommendations
  - false negative/false positive clinical harms (case review)

Privacy & security
- PII: de-identify recipient/patient identifiers in analytics; store mapping in encrypted vault
- Data encryption at rest and in transit (S3 SSE, TLS)
- Access controls: RBAC for model registry, inference endpoints, and n8n
- Audit logs: store who triggered what and when

Biom