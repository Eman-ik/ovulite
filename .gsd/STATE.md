# Ovulite – Project State

## Current Position
- **Phase:** 0 – Foundation & Scaffold (COMPLETE)
- **Plan:** 4 of 4 (all complete)
- **Status:** Phase 0 complete, ready for Phase 1
- **Last updated:** 2026-02-26

Progress: ████████████████████ 100% (4/4 plans in Phase 0)

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

## Pending Todos
- None (Phase 0 complete)

## Blockers / Concerns
- No git CI/CD yet — local Docker dev only for Phase 0
- Embryo image labels unavailable — deferred to Phase 3
- BCScore 77.5% missing — accounted for in feature engineering plan

## Session Continuity
- **Last session:** 2026-02-26
- **Stopped at:** Completed 00-04-PLAN.md (Phase 0 fully done)
- **Resume file:** None
