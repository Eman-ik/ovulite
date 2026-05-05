# Ovulite Autonomous Agent - Final Setup Guide

**Status**: ✅ Backend API routes registered, Frontend component integrated

---

## Step 1: Enable pgvector in PostgreSQL

Connect to your PostgreSQL database and enable the pgvector extension:

### Option A: Using psql (Command Line)
```bash
# Connect to your database
psql -U ovulite -d ovulite -h localhost

# Run the command at the psql prompt:
CREATE EXTENSION IF NOT EXISTS vector;

# Verify it's installed:
SELECT * FROM pg_extension WHERE extname='vector';

# Exit psql
\q
```

### Option B: Using pgAdmin (GUI)
1. Open pgAdmin and connect to your server
2. Navigate to: your_server → Databases → ovulite → Extensions
3. Right-click on "Extensions" → Create → Extension
4. Select "vector" from the dropdown
5. Click "Save"

### Option C: Using DBeaver
1. Connect to your database
2. Right-click the database → SQL → SQL Editor
3. Copy and paste:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
4. Execute (Ctrl+Enter)

### Verify Installation
```bash
psql -U ovulite -d ovulite -c "SELECT * FROM pg_extension WHERE extname='vector';"
```

You should see output showing the vector extension is installed.

---

## Step 2: Set OpenAI API Key Environment Variable

The Autonomous Agent uses OpenAI GPT-4o for natural language processing. You need to set your API key.

### Option A: Windows PowerShell (Recommended)
```powershell
# Set for current session only
$env:OPENAI_API_KEY = "sk-your-actual-key-here"

# Verify it's set
$env:OPENAI_API_KEY
```

### Option B: Permanent Windows (via System Properties)
1. Press `Win + X` → "System"
2. Click "Advanced system settings" → "Environment Variables"
3. Click "New" under "User variables"
4. Variable name: `OPENAI_API_KEY`
5. Variable value: `sk-your-actual-key-here`
6. Click "OK" and restart your terminal

### Option C: .env File (Development)
Create/edit `.env` in the root of your project:
```bash
OPENAI_API_KEY=sk-your-actual-key-here
DATABASE_URL=postgresql://ovulite:ovulite_dev_password@localhost:5432/ovulite
```

### Option D: Docker (if using Docker)
Add to your `docker-compose.yml`:
```yaml
services:
  backend:
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DATABASE_URL=postgresql://ovulite:password@db:5432/ovulite
```

Then run:
```bash
export OPENAI_API_KEY="sk-your-actual-key-here"
docker-compose up
```

### Get Your OpenAI API Key
1. Go to https://platform.openai.com/api-keys
2. Create a new API key (keep it secret!)
3. Copy it and use in the steps above

---

## Step 3: Verify Everything is Connected

### Test Backend API Routes
```bash
# Check that autonomous agent routes are registered
curl http://localhost:8000/docs

# In the browser, you should see "/api/autonomous-agent/" endpoints listed
```

### Test from Python
```python
# Open a Python terminal in your venv
python

# Test imports
from app.autonomous_agent import SQLQueryEngine, SHAPDiagnosticsEngine, ProactiveWatchdog, ResearchScout
print("✅ All autonomous agent modules imported successfully")

# Test database connection
from app.database import SessionLocal
db = SessionLocal()
print("✅ Database connection successful")

# Exit
exit()
```

### Test Frontend Component
```bash
# Start the frontend (if not running)
cd frontend
npm run dev

# Open browser at http://localhost:5174
# You should see the Intelligence Feed component at the top of the dashboard
```

---

## Step 4: Start the Application

### Start Backend with Watchdog
```bash
cd backend

# Ensure environment variable is set
$env:OPENAI_API_KEY = "sk-your-key"

# Start uvicorn with watchdog enabled
uvicorn app.main:app --reload --port 8000
```

Check logs for:
```
INFO:     Ovulite API started
INFO:     Proactive Watchdog initialized
```

### Start Frontend (if not running)
```bash
cd frontend
npm run dev
```

---

## 📋 Deployment Checklist

- [ ] pgvector extension enabled in PostgreSQL
- [ ] `OPENAI_API_KEY` environment variable set
- [ ] Backend started with `uvicorn`
- [ ] Frontend running at `http://localhost:5174`
- [ ] Can see Intelligence Feed on dashboard
- [ ] API endpoints accessible at `/docs`
- [ ] No errors in backend logs

---

## 🧪 Quick Verification Tests

### Test 1: Health Check
```bash
curl http://localhost:8000/health
```
Should return `{"status": "ok"}`

### Test 2: SQL Query Engine
```bash
curl -X POST http://localhost:8000/api/autonomous-agent/query \
  -H "Content-Type: application/json" \
  -d '{"query": "How many ET records are scheduled?"}'
```

### Test 3: Watchdog Status
```bash
curl http://localhost:8000/api/autonomous-agent/watchdog/status
```

Should return watchdog configuration

### Test 4: Research Discovery (takes ~3-5 seconds)
```bash
curl -X POST http://localhost:8000/api/autonomous-agent/research/discover
```

Should return research insights from arXiv

---

## 🔧 Troubleshooting

### "pgvector not found" Error
```sql
-- Verify extension exists
SELECT * FROM pg_available_extensions WHERE name='vector';

-- If not available, check PostgreSQL version (need 13+)
SELECT version();
```

### "OPENAI_API_KEY not set" Error
```bash
# Verify environment variable is set
echo $env:OPENAI_API_KEY  # Windows PowerShell
echo $OPENAI_API_KEY      # Linux/Mac

# If empty, set it:
$env:OPENAI_API_KEY = "sk-your-key"
```

### Backend refuses to start
- Check PostgreSQL is running: `pg_isready`
- Verify DATABASE_URL is correct
- Check port 8000 is available: `netstat -an | findstr :8000`

### Intelligence Feed not showing
- Check browser console for API errors (F12)
- Verify backend is running at http://localhost:8000
- Verify OpenAI API key is valid (not expired/revoked)

### Watchdog not running
- Check for errors in backend logs
- Verify APScheduler is installed: `pip list | grep apscheduler`
- Check database connectivity

---

## 📊 What Happens After Setup

1. **Dashboard loads** → Intelligence Feed auto-fetches insights
2. **Every 60 minutes** → Watchdog runs health checks
3. **Real-time** → All API endpoints ready to receive queries
4. **24 hours** → Research Scout finds new papers on arXiv
5. **Per prediction** → SHAP diagnostics explain model outputs

---

## 🎯 Next Steps

1. **Explore API endpoints** at `http://localhost:8000/docs`
2. **Test Intelligence Feed** by creating ET records
3. **Try natural language queries** via the SQL Query Engine
4. **Monitor live watchdog** alerts on dashboard
5. **Discover research** papers via Research Scout

---

## 📚 Documentation

- **Full Implementation:** [AUTONOMOUS_AGENT_IMPLEMENTATION_SUMMARY.md](../AUTONOMOUS_AGENT_IMPLEMENTATION_SUMMARY.md)
- **Technical Details:** [backend/AUTONOMOUS_AGENT_README.md](../backend/AUTONOMOUS_AGENT_README.md)
- **Setup Checklist:** [AUTONOMOUS_AGENT_IMPLEMENTATION_CHECKLIST.md](../AUTONOMOUS_AGENT_IMPLEMENTATION_CHECKLIST.md)

---

**Everything is now ready! 🚀**

Your Ovulite Autonomous Agent is fully set up and production-ready.
