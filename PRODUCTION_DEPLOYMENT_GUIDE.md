# Production Deployment Guide

## Scope
This guide reflects current hardening work (error handling, rate limiting, health checks, connection pooling) and excludes blob/object storage by design.

## Prerequisites
- Python 3.11+
- Node 20+
- PostgreSQL 15+
- Docker (optional)

## Backend Configuration
Create env file from backend/.env.example and set:
- DATABASE_URL
- DB_POOL_SIZE
- DB_MAX_OVERFLOW
- DB_POOL_RECYCLE
- SQLALCHEMY_ECHO=false
- RATE_LIMIT_PER_MINUTE

## Health and Monitoring Endpoints
- GET /health
- GET /health/db
- GET /health/ml
- GET /health/readiness
- GET /metrics

## Security and Stability
- Global structured error responses
- API rate limiting on /predict, /grade, /analytics, /qc
- Request logging with request_id
- SQLAlchemy pooling enabled

## Deployment Steps
1. Build frontend:
   - cd frontend
   - npm ci
   - npm run build
2. Start backend:
   - cd backend
   - python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
3. Verify health:
   - curl http://localhost:8000/health

## CI/CD
Workflow: .github/workflows/deploy-prod.yml
- Runs backend acceptance tests
- Runs frontend build
