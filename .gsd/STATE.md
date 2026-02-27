# Ovulite – Project State

## Current Position
- **Phase:** 1 – Data Intake & Validation (COMPLETE)
- **Plan:** 3 of 3 (all complete)
- **Status:** Phase 1 complete, ready for Phase 2
- **Last updated:** 2025-02-26

Progress: ████████████████████████████████████████ 100% (Phase 0: 4/4, Phase 1: 3/3)

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

## Pending Todos
- None (Phase 1 complete)

## Blockers / Concerns
- No git CI/CD yet — local Docker dev only
- Embryo image labels unavailable — deferred to Phase 3
- BCScore 77.5% missing — accounted for in feature engineering plan
- Need `docker compose up` + `alembic upgrade head` + seed before verifying end-to-end

## Session Continuity
- **Last session:** 2025-02-26
- **Stopped at:** Completed Phase 1 (Data Intake & Validation)
- **Resume file:** None
