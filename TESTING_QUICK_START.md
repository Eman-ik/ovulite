# Ovulite Testing Quick Reference

## 📋 What You Have

✅ **ALL 5 PHASES COMPLETE**

- Phase 0: Foundation & Scaffold (Auth, Docker, DB)
- Phase 1: Data Intake & Validation (488 ET records)
- Phase 2: Pregnancy Prediction (TabPFN + SHAP)
- Phase 3: Embryo Grading (EfficientNet + Grad-CAM)
- Phase 4: Lab QC (Isolation Forest + Control Charts)
- Phase 5: Analytics Dashboard (KPIs + Protocol Analysis)

## 🚀 Quick Start Testing

### 1. Start Services

\\\powershell
# Backend
cd "d:\Ovulite new\backend"
& "d:\Ovulite new\.venv\Scripts\Activate.ps1"
$env:DATABASE_URL = "postgresql://ovulite:ovulite_dev_password@localhost:5432/ovulite"
$env:SECRET_KEY = "change-me-in-production-use-openssl-rand-hex-32"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (new terminal)
cd "d:\Ovulite new\frontend"
npm run dev
\\\

### 2. Get Token

\\\powershell
$response = Invoke-RestMethod -Method POST `
  -Uri http://localhost:8000/auth/login `
  -ContentType "application/x-www-form-urlencoded" `
  -Body "username=admin&password=ovulite2026"
$token = $response.access_token
$headers = @{ Authorization = "Bearer $token" }
\\\

### 3. Import Data

\\\powershell
# Option 1: Upload CSV via API
curl.exe -X POST http://localhost:8000/import/csv `
  -H "Authorization: Bearer $token" `
  -F "file=@docs/dataset/ET Summary - ET Data.csv"

# Option 2: Run import script directly
cd "d:\Ovulite new\backend"
python scripts/ingest_et_data.py
\\\

### 4. Test Key Endpoints

\\\powershell
# Check data import
(Invoke-RestMethod -Uri "http://localhost:8000/transfers/?limit=1" -Headers $headers).total

# Get pregnancy prediction
$body = @{cl_size_mm=25; embryo_stage="Morula"; protocol_name="CIDR"} | ConvertTo-Json
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/predict/pregnancy" `
  -Headers ($headers + @{"Content-Type"="application/json"}) -Body $body

# Run QC pipeline
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/qc/run" -Headers $headers

# Get analytics KPIs
Invoke-RestMethod -Uri "http://localhost:8000/analytics/kpis" -Headers $headers
\\\

### 5. Test Frontend

Visit: http://localhost:5173

Login: **admin** / **ovulite2026**

Navigate all pages:
- ✅ Dashboard
- ✅ Data Entry
- ✅ Predictions
- ✅ Embryo Grading
- ✅ Lab QC
- ✅ Analytics

## 📊 10 Acceptance Tests

| AT | Description | Status |
|----|-------------|--------|
| 1 | 488 ET records imported | ✅ Ready |
| 2 | Invalid CL rejected | ✅ Ready |
| 3 | Prediction with CI + SHAP | ✅ Ready |
| 4 | Grade with Grad-CAM | ✅ Ready |
| 5 | Anomaly detection | ✅ Ready |
| 6 | Dashboard KPIs | ✅ Ready |
| 7 | Uncertainty displayed | ✅ Ready |
| 8 | RBAC enforced | ✅ Ready |
| 9 | SHAP explanations | ✅ Ready |
| 10 | API documented | ✅ Ready |

## 📚 Documentation Files

1. **SYSTEM_VERIFICATION_GUIDE.md** (27KB) — Complete testing procedures
2. **VERIFY.md** — Original verification guide
3. **SETUP.md** — Initial setup instructions
4. **REQUIREMENTS.md** — Full requirements specification
5. **ROADMAP.md** — Phase-by-phase development plan
6. **docs/LIMITATIONS.md** — System limitations
7. **docs/MODEL_REPORT.md** — ML model documentation
8. **docs/USER_GUIDE.md** — End-user guide

## 🔧 Common Commands

\\\powershell
# Check database tables
psql -U ovulite -d ovulite -h localhost -c "\dt"

# Verify admin user
psql -U ovulite -d ovulite -h localhost -c "SELECT * FROM users WHERE username='admin';"

# Check API health
Invoke-RestMethod -Uri http://localhost:8000/health

# View Swagger docs
Start-Process http://localhost:8000/docs

# Check ports in use
Get-NetTCPConnection -LocalPort 8000,5173 -ErrorAction SilentlyContinue
\\\

## 🐛 Fixed Issues

✅ **Login CORS Issue Resolved**
- Backend now accepts ports 5173-5176
- Frontend can run on any available port

## 🎯 Next Steps

1. Review **SYSTEM_VERIFICATION_GUIDE.md** for complete testing procedure
2. Execute all 10 acceptance tests systematically
3. Test each module's functionality end-to-end
4. Verify ML models are loaded (may need training)
5. Document any issues found

---
**Generated:** 2026-03-06 10:37:18
