# Ovulite – Project State

## Current Position
- **Phase:** 4 – Lab QC & Anomaly Detection (COMPLETE)
- **Plan:** 3 of 3 (all complete)
- **Status:** Phase 4 complete, ready for Phase 5
- **Last updated:** 2025-02-28

Progress: ████████████████████████████████████████████████████████████ 100% (Phase 0: 4/4, Phase 1: 3/3, Phase 2: 3/3, Phase 3: 3/3, Phase 4: 3/3)

## Accumulated Decisions
- FastAPI (Python 3.11+) for backend
- React with TypeScript for frontend
- PostgreSQL 15+ for database
- Docker Compose for orchestration
- SQLAlchemy 2.0 + Alembic for ORM/migrations
- JWT + bcrypt for auth
- shadcn/ui for UI components
- TabPFN as primary ML model for pregnancy prediction
- OAuth2PasswordRequestForm for login (standard form-encoded)
- Token stored in localStorage (simpler for dev, revisit for production)
- Seed endpoint creates admin only on empty DB
- stdlib JSON logging with custom formatter (no structlog/loguru)
- UUID4 request_id middleware for request tracing
- PaginatedResponse[T] generic for all list endpoints
- get-or-create pattern for CSV ingestion dedup
- '.' treated as NULL during CSV parsing
- CL side normalized to title-case (Left/Right)
- Semen type "Pre-Sorted for Female" → "Sexed"
- PC result: "P"→"Pregnant", "O"→"Open", "R"→"Recheck"
- Client + server CL validation (0–50mm)
- Temporal holdout Dec 2025+ for final test set
- GroupKFold by donor for cross-validation
- TabPFN with CalibratedLR fallback
- Bootstrap CI (n=200) for uncertainty estimation
- Isotonic calibration post-hoc on all models
- SHAP Explainer for feature contributions
- Singleton predictor pattern for API serving
- Model artifacts in ml/artifacts/{version}/
- Predictions persisted to DB for audit trail
- 3-class pseudo-labels from pregnancy outcomes (no ground-truth embryo grades)
- SimCLR self-supervised pretraining before supervised fine-tuning
- EfficientNet-B0 backbone (1280-dim) with frozen early layers
- Metadata fusion via MLP branch (32-dim output)
- Combined grade (3-class) + viability (sigmoid) dual-head output
- Grad-CAM on last conv block for visual explanations
- Singleton EmbryoGrader pattern for API serving
- Isolation Forest contamination=0.15 (higher than default for small dataset)
- EWMA λ=0.2 (moderate smoothing), CUSUM k=0.5σ / h=4σ (industrial standard)
- 5 synthetic anomaly types for testing: low_preg_rate, cl_drift, grade_anomaly, volume_spike, mixed
- Lazy QC pipeline execution with JSON artifact caching
- Text-based bar chart visualization for QC control charts (upgrade to Recharts later)

## Pending Todos
- None (Phase 4 complete)

## Blockers / Concerns
- No git CI/CD yet — local Docker dev only
- Model training not yet run (requires PyTorch install + GPU recommended)
- BCScore 77.5% missing — handled with bc_missing flag in feature engineering
- TabPFN may need fallback if package not installable in deployment env
- QC pipeline needs actual data to produce meaningful alerts (run POST /qc/run after CSV import)

## Session Continuity
- **Last session:** 2025-02-28
- **Stopped at:** Completed Phase 4 (Lab QC & Anomaly Detection)
- **Resume file:** None
