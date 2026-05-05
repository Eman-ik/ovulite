# Autonomous Agent Implementation Checklist

## Pre-Implementation Review
- [ ] Review [AUTONOMOUS_AGENT_IMPLEMENTATION_SUMMARY.md](AUTONOMOUS_AGENT_IMPLEMENTATION_SUMMARY.md)
- [ ] Read [backend/AUTONOMOUS_AGENT_README.md](backend/AUTONOMOUS_AGENT_README.md)
- [ ] Verify OpenAI API access and quota
- [ ] Ensure PostgreSQL 13+ with admin access

---

## Phase 1: Environment Setup

### Database Preparation
- [ ] Connect to PostgreSQL:
  ```bash
  psql -U ovulite -d ovulite -h localhost
  ```
- [ ] Enable vector extension:
  ```sql
  CREATE EXTENSION IF NOT EXISTS vector;
  SELECT * FROM pg_extension WHERE extname='vector';
  ```
- [ ] Verify existing tables:
  ```sql
  \dt et_transfers predictions embryos recipients technicians protocols
  ```

### Python Environment
- [ ] Navigate to backend:
  ```bash
  cd backend
  ```
- [ ] Create/activate virtual environment:
  ```bash
  python -m venv venv
  source venv/Scripts/activate  # Windows
  ```
- [ ] Install dependencies:
  ```bash
  pip install -r autonomous_agent_requirements.txt
  ```
- [ ] Verify installations:
  ```bash
  python -c "import langchain; import shap; import apscheduler; print('✅ All packages installed')"
  ```

### Environment Variables
- [ ] Set OpenAI API key:
  ```bash
  export OPENAI_API_KEY="sk-your-key-here"
  ```
- [ ] Verify DATABASE_URL in your `.env`:
  ```
  DATABASE_URL="postgresql://ovulite:ovulite_dev_password@localhost:5432/ovulite"
  ```

---

## Phase 2: API Integration

### Register Routes in FastAPI
- [ ] Open `backend/app/main.py`
- [ ] Add import:
  ```python
  from app.api import autonomous_agent
  ```
- [ ] Add router:
  ```python
  app.include_router(autonomous_agent.router)
  ```
- [ ] Verify endpoints:
  ```bash
  curl http://localhost:8000/docs  # Check Swagger UI
  ```

### Test Phase 1 Endpoints
- [ ] Test natural language query:
  ```bash
  curl -X POST http://localhost:8000/api/autonomous-agent/query \
    -H "Content-Type: application/json" \
    -d '{"query": "How many ET records are there?"}'
  ```
- [ ] Test upcoming ET records:
  ```bash
  curl http://localhost:8000/api/autonomous-agent/upcoming-et-records
  ```

### Test Phase 2 Endpoints
- [ ] Test diagnostics:
  ```bash
  curl -X POST http://localhost:8000/api/autonomous-agent/diagnose/prediction \
    -H "Content-Type: application/json" \
    -d '{"transfer_id": 1, "model_name": "xgboost", "prediction_score": 0.75}'
  ```

### Test Phase 3 Endpoints
- [ ] Check watchdog status:
  ```bash
  curl http://localhost:8000/api/autonomous-agent/watchdog/status
  ```
- [ ] Manually run health check:
  ```bash
  curl -X POST http://localhost:8000/api/autonomous-agent/watchdog/run-check
  ```

### Test Phase 4 Endpoints
- [ ] Discover research (slow, takes ~5s):
  ```bash
  curl -X POST http://localhost:8000/api/autonomous-agent/research/discover
  ```

---

## Phase 3: Frontend Integration

### Deploy Intelligence Feed Component
- [ ] Verify component exists:
  ```bash
  ls frontend/src/components/IntelligenceFeed.tsx
  ```
- [ ] Add to dashboard page (e.g., `src/pages/Dashboard.tsx`):
  ```tsx
  import { IntelligenceFeed } from "@/components/IntelligenceFeed";
  
  export default function Dashboard() {
    return (
      <div>
        {/* Other dashboard content */}
        <IntelligenceFeed autoRefresh={true} refreshInterval={60000} />
      </div>
    );
  }
  ```
- [ ] Verify component imports work:
  ```bash
  cd frontend && npm run build -- --no-minify
  ```
- [ ] Check for TypeScript errors:
  ```bash
  npx tsc --noEmit
  ```

### Test Frontend Component
- [ ] Load dashboard in browser at http://localhost:5174
- [ ] Verify Intelligence Feed loads
- [ ] Check browser console for errors
- [ ] Click refresh button and verify API calls

---

## Phase 4: Watchdog Configuration

### Initialize in Production
- [ ] Open `backend/app/main.py` (after app creation)
- [ ] Add startup event:
  ```python
  @app.on_event("startup")
  async def startup_watchdog():
      from app.autonomous_agent import ProactiveWatchdog
      
      watchdog = ProactiveWatchdog(
          database_url=DATABASE_URL,
          check_interval_minutes=60,
          confidence_threshold=0.85,
          et_warning_hours=24
      )
      
      # Optional: register notification callback
      async def on_alert(notification):
          print(f"🔔 {notification.title}: {notification.message}")
          # Add Slack/email/SMS here
      
      watchdog.register_notification_callback(on_alert)
      watchdog.start_monitoring()
      app.state.watchdog = watchdog
  ```
- [ ] Add shutdown event:
  ```python
  @app.on_event("shutdown")
  async def shutdown_watchdog():
      if hasattr(app.state, 'watchdog'):
          app.state.watchdog.stop_monitoring()
  ```

### Test Watchdog Cycle
- [ ] Start the backend:
  ```bash
  cd backend && uvicorn app.main:app --reload --port 8000
  ```
- [ ] Monitor logs for watchdog startup
- [ ] Wait 60+ seconds for first check
- [ ] Verify notifications logged

---

## Phase 5: Data Validation

### Test SQL Query Engine
- [ ] Test with real data query:
  ```python
  from app.autonomous_agent import SQLQueryEngine
  
  engine = SQLQueryEngine(database_url=DATABASE_URL)
  response = await engine.query(SQLQueryRequest(
      query="Show ET records for this week"
  ))
  print(response)
  ```

### Test Vector Store
- [ ] Add a test chunk:
  ```python
  from app.autonomous_agent import VectorStoreManager, DocumentChunk
  
  vector_store = VectorStoreManager(database_url=DATABASE_URL)
  chunk = DocumentChunk(
      content="This embryo showed excellent quality metrics",
      source="test"
  )
  doc_id = await vector_store.add_chunk(chunk)
  print(f"Added: {doc_id}")
  ```
- [ ] Search for it:
  ```python
  results = await vector_store.search("embryo quality", k=1)
  print(results)
  ```

### Test SHAP Diagnostics
- [ ] Create mock prediction:
  ```python
  from app.autonomous_agent import SHAPDiagnosticsEngine
  import numpy as np
  
  diagnostics = SHAPDiagnosticsEngine()
  features = np.array([[5, 15.2, 7.8, 0.45]])
  feature_names = ["Age", "CL Measure", "BC Score", "Heat Observed"]
  
  report = diagnostics.explain_xgboost_prediction(
      features, 
      feature_names,
      0.87
  )
  print(report.explanation)
  ```

---

## Phase 6: Performance & Monitoring

### Monitor Performance
- [ ] Check API response times:
  ```bash
  time curl http://localhost:8000/api/autonomous-agent/upcoming-et-records
  ```
- [ ] Monitor database connections:
  ```sql
  SELECT count(*) FROM pg_stat_activity;
  ```
- [ ] Check CPU/memory usage during watchdog cycles
- [ ] Monitor logs for errors:
  ```bash
  tail -f logs/autonomous_agent.log
  ```

### Optimize if Needed
- [ ] If SQL queries slow: add database indexes on et_date, confidence_lower
- [ ] If SHAP slow: reduce background data size
- [ ] If vector search slow: increase pgvector index parameters

---

## Phase 7: Notification Integration (Optional)

### Setup Slack Notifications
- [ ] Get Slack webhook URL
- [ ] Add to notification callback:
  ```python
  import requests
  
  async def send_slack_notification(notification):
      payload = {
          "text": f"{notification.title}",
          "blocks": [{
              "type": "section",
              "text": {"type": "mrkdwn", "text": f"*{notification.title}*\n{notification.message}"}
          }]
      }
      await requests.post(SLACK_WEBHOOK_URL, json=payload)
  
  watchdog.register_notification_callback(send_slack_notification)
  ```

### Setup Email Notifications
- [ ] Use FastAPI's background tasks or Celery
- [ ] Send SMTP email on alerts

---

## Phase 8: Production Deployment

### Docker Deployment
- [ ] Build image:
  ```bash
  docker build -f backend/Dockerfile -t ovulite-backend:autonomous .
  ```
- [ ] Update docker-compose.yml with required environment variables:
  ```yaml
  environment:
    - OPENAI_API_KEY=${OPENAI_API_KEY}
    - DATABASE_URL=postgresql://ovulite:password@db:5432/ovulite
  ```

### Database Persistence
- [ ] Ensure pgvector extension persists across restarts
- [ ] Backup vector embeddings regularly

### Monitoring & Logging
- [ ] Setup application monitoring (Sentry, DataDog)
- [ ] Enable watchdog error alerting
- [ ] Create dashboard for PP metrics

---

## Phase 9: Verification & Sign-off

### Final System Tests
- [ ] [ ] All 4 phases respond to API calls
- [ ] [ ] Intelligence Feed displays insights
- [ ] [ ] Watchdog runs automatically on schedule
- [ ] [ ] SHAP explanations are accurate
- [ ] [ ] arXiv search returns relevant papers
- [ ] [ ] Database queries have < 500ms latency
- [ ] [ ] No memory leaks after 24h operation

### Documentation Review
- [ ] [ ] All endpoint documentation complete
- [ ] [ ] Error codes documented
- [ ] [ ] Configuration options documented
- [ ] [ ] Troubleshooting guide complete

### User Acceptance
- [ ] [ ] Stakeholders approved Intelligence Feed UI
- [ ] [ ] Stakeholders understand watchdog alerts
- [ ] [ ] Data scientists reviewed SHAP outputs
- [ ] [ ] Feedback incorporated

---

## 🎉 Completion Checklist

- [ ] All implementation steps completed
- [ ] All 16 API endpoints tested
- [ ] Frontend component deployed
- [ ] Watchdog running in background
- [ ] Documentation is current
- [ ] Team is trained on new features
- [ ] System is production-ready

**Sign-off Date:** _______________  
**Approved By:** _______________

---

## Troubleshooting Quick Links

| Issue | Solution |
|-------|----------|
| "pgvector not found" | Run `CREATE EXTENSION vector;` in PostgreSQL |
| OpenAI API 401 | Check `OPENAI_API_KEY` environment variable |
| SQLQueryEngine error | Verify DATABASE_URL and database connectivity |
| SHAP errors | Ensure numpy/scikit-learn versions match |
| Watchdog not starting | Check APScheduler installation and logs |
| IntelligenceFeed blank | Verify FastAPI endpoints are accessible |
| Vector search empty | Ensure documents have been added to store |
| arXiv search slow | Check internet connection and feedparser |

---

**Last Updated:** May 5, 2026
