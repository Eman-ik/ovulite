# Autonomous Agent - Simplified Mode (No LLM/pgvector Required)

## Summary

The 4-phase autonomous agent system is configured to work **without** OpenAI API key or pgvector extension. All core features are operational except for LLM-powered enhancements.

---

## What's Working ✅

### Phase 1: Semantic Knowledge Layer
- ✅ **SQL Queries**: Direct SQL execution against PostgreSQL (no LLM translation)
- ✅ **Upcoming ET Records**: List all transfers (next 7 days)
- ✅ **Low Confidence Predictions**: Filter predictions below confidence threshold
- ✅ **Keyword Search**: Document search using keyword matching (not pgvector)

**API Endpoints**:
- `POST /api/autonomous-agent/query` - Execute SQL query
- `GET /api/autonomous-agent/upcoming-et-records` - List upcoming transfers
- `GET /api/autonomous-agent/vector-search` - Keyword-based search (no pgvector needed)

---

### Phase 2: Diagnostics Layer
- ✅ **SHAP Explainability**: Explain model predictions using Shapley values
- ✅ **Feature Importance**: Identify top 5 features influencing prediction
- ✅ **Confidence Assessment**: Measure prediction confidence

**API Endpoints**:
- `POST /api/autonomous-agent/diagnose/prediction` - Explain any prediction
- `GET /api/autonomous-agent/diagnostics/low-confidence` - Get low-confidence alerts

**Example**:
```bash
curl -X POST "http://localhost:8000/api/autonomous-agent/diagnose/prediction" \
  -H "Content-Type: application/json" \
  -d '{
    "transfer_id": 123,
    "model_name": "xgboost_success_model",
    "prediction_score": 0.78,
    "input_features": {
      "embryo_grade": 3.5,
      "recipient_age": 5,
      "transfer_timing": 8
    }
  }'
```

---

### Phase 3: Watchdog Layer
- ✅ **Proactive Monitoring**: Hourly health checks of ET system
- ✅ **Automatic Alerts**: Triggers for:
  - Upcoming transfers (< 24 hours)
  - Low confidence predictions (< 85%)
  - Missing data in predictions
- ✅ **Background Scheduling**: APScheduler runs every hour

**API Endpoints**:
- `GET /api/autonomous-agent/watchdog/status` - Check watchdog health
- `POST /api/autonomous-agent/watchdog/start` - Start monitoring
- `POST /api/autonomous-agent/watchdog/run-check` - Manual health check

**Example**:
```bash
# Check watchdog status
curl "http://localhost:8000/api/autonomous-agent/watchdog/status"

# Start monitoring
curl -X POST "http://localhost:8000/api/autonomous-agent/watchdog/start"

# Manual check
curl -X POST "http://localhost:8000/api/autonomous-agent/watchdog/run-check"
```

---

### Phase 4: Research Intelligence Layer
- ✅ **Curated Knowledge Base**: 5 pre-loaded research insights
- ✅ **No Internet Required**: All knowledge is local
- ✅ **Embryo Selection Tips**: Actionable insights for improving selection accuracy
- ✅ **Model Optimization Hints**: Suggests for improving CNN and XGBoost models

**API Endpoints**:
- `POST /api/autonomous-agent/research/discover` - Get research insights
- `GET /api/autonomous-agent/methods-profile` - View Ovulite AI methods profile

**Example**:
```bash
curl -X POST "http://localhost:8000/api/autonomous-agent/research/discover" \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": ["embryo", "morphology"],
    "max_results": 5
  }'
```

---

## What's Simplified 🔧

| Feature | Original | Simplified Mode |
|---------|----------|-----------------|
| **SQL Queries** | LLM-translated natural language → SQL | Direct SQL queries (no translation) |
| **Vector Search** | pgvector + OpenAI embeddings | Keyword-based matching (in-memory) |
| **Research Discovery** | Live arXiv API + LLM analysis | Curated local knowledge base |
| **Paper Analysis** | GPT-4o analyzes relevance | Heuristic keyword matching |
| **External Dependencies** | 2 critical (pgvector, OpenAI) | 0 critical (all local) |

---

## How to Use (Quick Start)

### 1. Start Backend Server

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Expected output:
```
INFO:     Ovulite API server started
INFO:     Application startup complete
Uvicorn running on http://127.0.0.1:8000
```

### 2. Check API Docs

Open browser: **http://localhost:8000/docs**

You'll see all 16 endpoints documented with interactive Try-It-Out panels.

### 3. Test Each Phase

**Test Phase 1** (SQL):
```bash
curl -X POST "http://localhost:8000/api/autonomous-agent/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT COUNT(*) FROM et_transfers"}'
```

**Test Phase 2** (SHAP):
```bash
curl -X POST "http://localhost:8000/api/autonomous-agent/diagnose/prediction" \
  -H "Content-Type: application/json" \
  -d '{
    "transfer_id": 1,
    "model_name": "xgboost_success_model",
    "prediction_score": 0.82,
    "input_features": {"embryo_grade": 3, "recipient_age": 4, "transfer_day": 8}
  }'
```

**Test Phase 3** (Watchdog):
```bash
curl "http://localhost:8000/api/autonomous-agent/watchdog/status"
```

**Test Phase 4** (Research):
```bash
curl -X POST "http://localhost:8000/api/autonomous-agent/research/discover" \
  -H "Content-Type: application/json" \
  -d '{"max_results": 3}'
```

### 4. Monitor Dashboard

The **Admin Dashboard** (`http://localhost:5174/admin`) shows **Intelligence Feed** with real-time insights from all 4 phases.

---

## Limitations Without LLM Features 📉

### What You Lose:
1. **Natural Language Queries**: Must write SQL directly (Phase 1)
2. **Vector Similarity Search**: Uses simple keyword matching instead of semantic search
3. **Live Research**: Can't fetch latest arXiv papers (Phase 4)
4. **Semantic Paper Analysis**: Can't use GPT-4o to analyze paper relevance

### Workarounds:
- For NL queries → Learn basic SQL or use provided examples
- For semantic search → Expand knowledge base with more keywords
- For live research → Manually fetch papers and add to knowledge base
- For paper analysis → Use provided curated insights or manual review

---

## Future Enhancement Path 🚀

To re-enable LLM features when ready:

1. **Get OpenAI API Key**:
   - Visit https://platform.openai.com/api-keys
   - Create API key (skip if corporate access blocked)

2. **Install pgvector**:
   - Option A: Download binary from https://github.com/pgvector/pgvector/releases
   - Option B: Run PostgreSQL via Docker with pgvector pre-installed

3. **Update autonomous_agent_requirements.txt**:
   ```txt
   langchain-openai>=0.1.0  # Re-enable
   pgvector>=0.2.5  # Re-enable
   ```

4. **Revert Phase Files**:
   - Phase 1: Switch back to LLM-based SQL translation
   - Phase 4: Switch back to live arXiv discovery

---

## Architecture

```
Ovulite Autonomous Agent (Simplified)
│
├── Phase 1: Semantic Knowledge
│   ├── SQL Query Engine (direct SQL, no LLM)
│   ├── Keyword Search (no pgvector)
│   └── ET Record Lookup
│
├── Phase 2: Diagnostics
│   ├── SHAP Explainability ✅
│   ├── Feature Importance ✅
│   └── Confidence Scoring ✅
│
├── Phase 3: Watchdog
│   ├── Health Checks ✅
│   ├── Alert Triggers ✅
│   └── APScheduler ✅
│
└── Phase 4: Research Intelligence
    ├── Curated Knowledge Base ✅
    ├── Local Insights ✅
    └── No Internet Required ✅
```

---

## Summary

All **4 phases are operational** working without external API keys or system extensions:
- **Phase 1**: SQL queries (direct, not LLM-translated)
- **Phase 2**: SHAP diagnostics (full capability)
- **Phase 3**: Watchdog monitoring (full capability)
- **Phase 4**: Curated research (local knowledge base)

**Ready to deploy!** Start backend server and open API docs at `http://localhost:8000/docs`.
