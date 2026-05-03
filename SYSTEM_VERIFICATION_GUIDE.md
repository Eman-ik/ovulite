# Ovulite — Complete System Verification & Testing Guide

> **Purpose:** Complete end-to-end verification guide for all 5 phases of the Ovulite AI-Driven Reproductive Intelligence System. This document provides systematic testing procedures to validate every feature, API endpoint, and UI component.

**Project Status:** ✅ ALL PHASES COMPLETE (Phase 0-5)  
**Last Updated:** 2026-03-06  
**Version:** 1.0.0

---

## Table of Contents

1. [Prerequisites & Setup](#prerequisites--setup)
2. [Phase 0: Foundation & Scaffold](#phase-0-foundation--scaffold)
3. [Phase 1: Data Intake & Validation](#phase-1-data-intake--validation)
4. [Phase 2: Pregnancy Prediction Pipeline](#phase-2-pregnancy-prediction-pipeline)
5. [Phase 3: Embryo Grading Model](#phase-3-embryo-grading-model)
6. [Phase 4: Lab QC & Anomaly Detection](#phase-4-lab-qc--anomaly-detection)
7. [Phase 5: Analytics Dashboard](#phase-5-analytics-dashboard)
8. [Acceptance Tests Summary](#acceptance-tests-summary)
9. [Full System Smoke Test](#full-system-smoke-test)
10. [Testing Workflow Checklist](#testing-workflow-checklist)

---

## Prerequisites & Setup

### 1.1 — Environment Requirements

**Backend:**
- Python 3.11+
- PostgreSQL 15+
- Virtual environment activated

**Frontend:**
- Node.js 18+
- npm 9+

**Docker (Alternative):**
- Docker Desktop running
- docker-compose v2+

### 1.2 — Initial Setup Steps

#### Option A: Docker Setup

\\\powershell
# 1. Start services
cd "d:\Ovulite new"
docker-compose up -d

# 2. Wait for health check
Start-Sleep -Seconds 10

# 3. Verify database
docker-compose exec db psql -U ovulite -d ovulite -c "\dt"
\\\

#### Option B: Manual Setup

\\\powershell
# 1. Start PostgreSQL (ensure it's running on localhost:5432)

# 2. Backend setup
cd "d:\Ovulite new\backend"
& "d:\Ovulite new\.venv\Scripts\Activate.ps1"
$env:DATABASE_URL = "postgresql://ovulite:ovulite_dev_password@localhost:5432/ovulite"
$env:SECRET_KEY = "change-me-in-production-use-openssl-rand-hex-32"
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 3. Frontend setup (in new terminal)
cd "d:\Ovulite new\frontend"
npm run dev
\\\

### 1.3 — Database Setup

\\\powershell
# Run migrations
cd backend
alembic upgrade head

# Seed admin user
python seed_admin.py

# Expected output:
# Admin created! user_id=1, username=admin
\\\

### 1.4 — Get Authentication Token

**All API tests require a JWT token. Run this first:**

\\\powershell
$response = Invoke-RestMethod -Method POST -Uri http://localhost:8000/auth/login `
  -ContentType "application/x-www-form-urlencoded" `
  -Body "username=admin&password=ovulite2026"

$token = $response.access_token
$headers = @{ Authorization = "Bearer $token" }

Write-Host "Token obtained successfully!"
\\\

---

## Phase 0: Foundation & Scaffold

**Goal:** Docker infrastructure, database schema (13 tables), auth system (JWT + RBAC), structured JSON logging

### Test 0.1 — Health Check

\\\powershell
Invoke-RestMethod -Uri http://localhost:8000/health
\\\

**✅ Expected:**
\\\json
{ "status": "healthy", "service": "ovulite-api" }
\\\

### Test 0.2 — Database Tables

\\\powershell
$env:PGPASSWORD = "ovulite_dev_password"
psql -U ovulite -d ovulite -h localhost -c "\dt"
\\\

**✅ Expected: 13 tables**
- alembic_version
- anomalies
- donors
- embryo_images
- embryos
- et_transfers
- predictions
- protocol_logs
- protocols
- recipients
- sires
- technicians
- users

### Test 0.3 — Swagger API Documentation

**Open in browser:** http://localhost:8000/docs

**✅ Expected:** Interactive Swagger UI with 13 endpoint groups:
- auth, analytics, donors, embryos, grading, import, predictions, protocols, qc, recipients, sires, technicians, transfers

### Test 0.4 — Admin User Exists

\\\powershell
$env:PGPASSWORD = "ovulite_dev_password"
psql -U ovulite -d ovulite -h localhost -c "SELECT username, role, active FROM users WHERE username='admin';"
\\\

**✅ Expected:**
\\\
 username | role  | active
----------+-------+--------
 admin    | admin | t
\\\

### Test 0.5 — Login Flow (JWT Token)

\\\powershell
$response = Invoke-RestMethod -Method POST `
  -Uri http://localhost:8000/auth/login `
  -ContentType "application/x-www-form-urlencoded" `
  -Body "username=admin&password=ovulite2026"

$response
\\\

**✅ Expected:**
\\\json
{ 
  "access_token": "<jwt-token-string>",
  "token_type": "bearer" 
}
\\\

### Test 0.6 — Protected Endpoint

\\\powershell
Invoke-RestMethod -Uri http://localhost:8000/auth/me -Headers $headers
\\\

**✅ Expected:** Returns admin user profile
\\\json
{
  "user_id": 1,
  "username": "admin",
  "role": "admin",
  "full_name": "System Administrator",
  "active": true
}
\\\

### Test 0.7 — RBAC: Unauthorized Access Blocked

\\\powershell
try {
    Invoke-RestMethod -Uri http://localhost:8000/auth/me
} catch {
    $_.Exception.Response.StatusCode.value__
}
\\\

**✅ Expected:** Status **401** (Unauthorized)

### Test 0.8 — CORS Configuration

\\\powershell
$response = Invoke-WebRequest -Uri http://localhost:8000/auth/login `
  -Method POST -Body "username=admin&password=ovulite2026" `
  -ContentType "application/x-www-form-urlencoded" `
  -Headers @{"Origin"="http://localhost:5173"}

$response.Headers.GetEnumerator() | Where-Object { $_.Key -match 'access-control' }
\\\

**✅ Expected:** CORS headers present:
- access-control-allow-origin: http://localhost:5173
- access-control-allow-credentials: true

### Test 0.9 — Structured JSON Logging

**Check backend terminal output:**

**✅ Expected:** Log lines in JSON format
\\\json
{
  "timestamp": "2026-03-06T10:00:00.000Z",
  "level": "INFO",
  "message": "GET /health → 200 (1.23ms)",
  "request_id": "a1b2c3d4-..."
}
\\\

### Test 0.10 — Frontend Loads

**Open:** http://localhost:5173

**✅ Expected:** 
- Redirects to /login
- Login form visible with username/password fields
- Ovulite branding and "AI-Driven Reproductive Intelligence System" tagline

### Test 0.11 — Frontend Login

1. Enter dmin / ovulite2026
2. Click **Sign in**

**✅ Expected:**
- Redirects to Dashboard (/)
- Sidebar navigation visible with:
  - Dashboard
  - Data Entry
  - Predictions
  - Embryo Grading
  - Lab QC
  - Analytics

---

## Phase 1: Data Intake & Validation

**Goal:** Ingest 488 ET records from CSV, expose CRUD API, frontend data entry with validation

### Test 1.1 — CSV Import (AT-1: Data ingestion)

\\\powershell
# Upload CSV file
$csvPath = "d:\Ovulite new\docs\dataset\ET Summary - ET Data.csv"
$boundary = [System.Guid]::NewGuid().ToString()
$LF = "
"

$bodyLines = @(
    "--$boundary",
    "Content-Disposition: form-data; name="file"; filename="ET Summary - ET Data.csv"",
    "Content-Type: text/csv",
    "",
    [System.IO.File]::ReadAllText($csvPath),
    "--$boundary--"
) -join $LF

Invoke-RestMethod -Method POST `
  -Uri "http://localhost:8000/import/csv" `
  -Headers (@{Authorization="Bearer $token"} + @{"Content-Type"="multipart/form-data; boundary=$boundary"}) `
  -Body $bodyLines
\\\

**✅ Expected:** Import summary with counts
\\\json
{
  "donors_created": 52,
  "sires_created": 45,
  "recipients_created": 334,
  "transfers_created": 488,
  "message": "Import completed successfully"
}
\\\

### Test 1.2 — Verify Record Counts

\\\powershell
# Check donors
($donorsResp = Invoke-RestMethod -Uri "http://localhost:8000/donors/?limit=1" -Headers $headers)
Write-Host "Total Donors: $($donorsResp.total)"

# Check transfers
($transfersResp = Invoke-RestMethod -Uri "http://localhost:8000/transfers/?limit=1" -Headers $headers)
Write-Host "Total Transfers: $($transfersResp.total)"
\\\

**✅ Expected:** 
- Donors: ~52
- Transfers: ~488

### Test 1.3 — Donor CRUD

\\\powershell
# List donors
Invoke-RestMethod -Uri "http://localhost:8000/donors/?limit=5" `
  -Headers $headers | ConvertTo-Json -Depth 5

# Get specific donor
Invoke-RestMethod -Uri "http://localhost:8000/donors/1" `
  -Headers $headers
\\\

**✅ Expected:** Paginated response with items, 	otal, page, size

### Test 1.4 — Transfer CRUD

\\\powershell
# List transfers with filters
Invoke-RestMethod -Uri "http://localhost:8000/transfers/?limit=10&pc1_result=Pregnant" `
  -Headers $headers | ConvertTo-Json -Depth 5
\\\

**✅ Expected:** Transfers list with donor, recipient, embryo, sire relationships

### Test 1.5 — All Entity Endpoints

\\\powershell
# Test all CRUD endpoints
@("sires", "recipients", "embryos", "technicians", "protocols") | ForEach-Object {
    Write-Host "Testing $_ endpoint..."
    Invoke-RestMethod -Uri "http://localhost:8000/$_/?limit=3" -Headers $headers | ConvertTo-Json -Depth 2
}
\\\

**✅ Expected:** All endpoints return paginated data

### Test 1.6 — CL Validation (AT-2: Invalid CL rejected)

\\\powershell
$invalidBody = @{
    recipient_id = 1
    donor_id = 1
    sire_id = 1
    transfer_date = "2025-01-01"
    cl_size_mm = 999
} | ConvertTo-Json

try {
    Invoke-RestMethod -Method POST `
      -Uri "http://localhost:8000/transfers/" `
      -Headers ($headers + @{ "Content-Type" = "application/json" }) `
      -Body $invalidBody
} catch {
    Write-Host "✅ Validation error as expected: $($_.Exception.Message)"
    $_.Exception.Response.StatusCode.value__
}
\\\

**✅ Expected:** Status **422** (Validation Error) — CL value 999 rejected

### Test 1.7 — Frontend: Data Entry Page

**Navigate to:** http://localhost:5173/data-entry

**✅ Expected:**
- Paginated table showing imported ET records
- Columns: date, donor, recipient, sire, protocol, CL, result
- Sortable, filterable, paginated
- Color-coded pregnancy result badges (green=Pregnant, gray=Open, yellow=Recheck)

### Test 1.8 — Frontend: New Transfer Form

**Navigate to:** http://localhost:5173/data-entry/new

**✅ Expected:**
- Complete form with 4 sections:
  1. Transfer Info (date, location, protocol)
  2. Recipient & CL (recipient, CL size, CL side)
  3. Embryo Info (donor, sire, stage, grade)
  4. Pregnancy Check (date, result)
- Dropdowns populated from API
- Client-side validation (CL 0-50mm)
- Submit creates new record

### Test 1.9 — Frontend: Edit Transfer

1. Click any record in Data Entry table
2. Modify CL size
3. Save

**✅ Expected:** Record updated successfully

---

## Phase 2: Pregnancy Prediction Pipeline

**Goal:** Train & serve pregnancy prediction model with probability, confidence interval, SHAP explanations

### Test 2.1 — Model Info Endpoint

\\\powershell
Invoke-RestMethod -Uri "http://localhost:8000/predict/model-info" `
  -Headers $headers | ConvertTo-Json -Depth 5
\\\

**✅ Expected:** Model metadata
\\\json
{
  "model_type": "TabPFN",
  "version": "1.0.0",
  "features": [...],
  "metrics": {
    "roc_auc": 0.XX,
    "pr_auc": 0.XX,
    "brier_score": 0.XX
  }
}
\\\

### Test 2.2 — Pregnancy Prediction (AT-3)

\\\powershell
$predBody = @{
    donor_id = 1
    sire_id = 1
    recipient_id = 1
    cl_size_mm = 25
    embryo_stage = "Morula"
    cl_side = "Left"
    protocol_name = "CIDR"
    semen_type = "Conventional"
    technician_name = "Dr. Ahmad"
} | ConvertTo-Json

Invoke-RestMethod -Method POST `
  -Uri "http://localhost:8000/predict/pregnancy" `
  -Headers ($headers + @{ "Content-Type" = "application/json" }) `
  -Body $predBody | ConvertTo-Json -Depth 5
\\\

**✅ Expected response contains:**
\\\json
{
  "probability": 0.42,
  "risk_band": "Medium",
  "confidence_interval": {
    "lower": 0.35,
    "upper": 0.65
  },
  "shap_values": {
    "cl_size_mm": 0.12,
    "protocol_name": 0.08,
    "embryo_stage": -0.05
  },
  "model_version": "1.0.0"
}
\\\

### Test 2.3 — SHAP Feature Contributions (AT-9)

From Test 2.2 response, verify shap_values:

**✅ Expected:** Dictionary with signed contribution values showing feature impact

### Test 2.4 — Confidence Interval (AT-7: Uncertainty)

From Test 2.2 response, verify confidence_interval:

**✅ Expected:** 
- lower < probability < upper
- Reasonable width reflecting model uncertainty

### Test 2.5 — Frontend: Prediction Page

**Navigate to:** http://localhost:5173/predictions

**✅ Expected:**
- Input form with all prediction features
- Submit button
- Results section with:
  - Large probability percentage gauge
  - Color-coded risk band badge
  - Confidence interval bar visualization
  - SHAP feature importance chart (top 10 features)
  - Model info badge

### Test 2.6 — ML Pipeline Files

\\\powershell
Test-Path "d:\Ovulite new\ml\features.py"
Test-Path "d:\Ovulite new\ml\train_pipeline.py"
Test-Path "d:\Ovulite new\ml\predict.py"
\\\

**✅ Expected:** All return True

---

## Phase 3: Embryo Grading Model

**Goal:** AI embryo grading via image + metadata fusion with Grad-CAM visual explanations

### Test 3.1 — Grading Model Info

\\\powershell
Invoke-RestMethod -Uri "http://localhost:8000/grade/model-info" `
  -Headers $headers | ConvertTo-Json -Depth 5
\\\

**✅ Expected:** 
\\\json
{
  "model_type": "EfficientNet-B0 + Metadata Fusion",
  "architecture": "SimCLR pretrained",
  "input_size": 224,
  "output_classes": ["High", "Medium", "Low"]
}
\\\

### Test 3.2 — Image Upload

\\\powershell
# Test with any embryo image
$imagePath = "d:\Ovulite new\docs\Blastocystimages\Blastocyst images\blq1.jpg"

# Create multipart form data
curl.exe -X POST http://localhost:8000/grade/upload `
  -H "Authorization: Bearer $token" `
  -F "file=@$imagePath"
\\\

**✅ Expected:** 
\\\json
{
  "image_id": 1,
  "file_path": "uploads/embryos/XXX.jpg"
}
\\\

### Test 3.3 — Embryo Grading (AT-4)

\\\powershell
curl.exe -X POST http://localhost:8000/grade/embryo `
  -H "Authorization: Bearer $token" `
  -F "file=@$imagePath"
\\\

**✅ Expected:**
\\\json
{
  "grade": 1,
  "viability_score": 0.78,
  "confidence": 0.82,
  "class_probabilities": {
    "High": 0.65,
    "Medium": 0.25,
    "Low": 0.10
  }
}
\\\

### Test 3.4 — Grad-CAM Heatmap (AT-4)

\\\powershell
curl.exe -X POST http://localhost:8000/grade/embryo-with-heatmap `
  -H "Authorization: Bearer $token" `
  -F "file=@$imagePath"
\\\

**✅ Expected:** Response includes heatmap field with base64-encoded image

### Test 3.5 — Frontend: Embryo Grading Page

**Navigate to:** http://localhost:5173/embryo-grading

**✅ Expected:**
- Drag-and-drop image upload area
- After upload:
  - Original embryo image displayed
  - Grade result (1/2/3) with viability label
  - Viability score gauge
  - Class probability breakdown bars
  - Grad-CAM heatmap overlay toggle
  - Heatmap highlights important image regions

---

## Phase 4: Lab QC & Anomaly Detection

**Goal:** Unsupervised monitoring of lab process health — anomaly detection, control charts, alerts

### Test 4.1 — Run QC Pipeline

\\\powershell
Invoke-RestMethod -Method POST `
  -Uri "http://localhost:8000/qc/run?with_synthetic=true" `
  -Headers $headers | ConvertTo-Json -Depth 5
\\\

**✅ Expected:** Pipeline execution summary

### Test 4.2 — QC Summary

\\\powershell
Invoke-RestMethod -Uri "http://localhost:8000/qc/summary" `
  -Headers $headers | ConvertTo-Json -Depth 5
\\\

**✅ Expected:**
\\\json
{
  "total_anomalies": 15,
  "anomaly_types": {
    "low_preg_rate": 3,
    "cl_drift": 2,
    "volume_spike": 1
  },
  "severity_distribution": {
    "critical": 2,
    "warning": 8,
    "info": 5
  },
  "last_run": "2026-03-06T10:00:00Z"
}
\\\

### Test 4.3 — Anomaly List (AT-5)

\\\powershell
Invoke-RestMethod -Uri "http://localhost:8000/qc/anomalies" `
  -Headers $headers | ConvertTo-Json -Depth 5
\\\

**✅ Expected:** List of anomalies with:
- id, anomaly_type, severity
- description, entity_type, entity_id
- detected_at timestamp

### Test 4.4 — Control Charts

\\\powershell
Invoke-RestMethod -Uri "http://localhost:8000/qc/charts" `
  -Headers $headers | ConvertTo-Json -Depth 5
\\\

**✅ Expected:** Control chart data
\\\json
{
  "pregnancy_rate": {
    "ewma": [...],
    "cusum": [...]
  },
  "cl_measure": {
    "ewma": [...],
    "cusum": [...]
  }
}
\\\

### Test 4.5 — Technician QC Stats

\\\powershell
Invoke-RestMethod -Uri "http://localhost:8000/qc/technicians" `
  -Headers $headers | ConvertTo-Json -Depth 5
\\\

**✅ Expected:** Per-technician metrics
\\\json
[
  {
    "technician_name": "Dr. Ahmad",
    "transfer_count": 407,
    "pregnancy_rate": 0.29,
    "vs_mean": 0.01,
    "avg_cl_measure": 24.5
  }
]
\\\

### Test 4.6 — Frontend: Lab QC Dashboard

**Navigate to:** http://localhost:5173/lab-qc

**✅ Expected:**
- **Summary cards:** total records, anomalies, active alerts, technician count
- **Control charts:** EWMA and CUSUM visualizations with UCL/LCL
- **Anomaly table:** severity badges, type, entity, description
- **Technician performance table:** transfer count, pregnancy rate, vs-mean arrows
- **"Run QC Pipeline" button** functional

---

## Phase 5: Analytics Dashboard

**Goal:** Unified reproductive dashboard, protocol analytics, biomarker analysis, full system evaluation

### Test 5.1 — Run Analytics Pipeline

\\\powershell
Invoke-RestMethod -Method POST `
  -Uri "http://localhost:8000/analytics/run" `
  -Headers $headers
\\\

**✅ Expected:** Pipeline processes data and caches results

### Test 5.2 — KPI Dashboard (AT-6)

\\\powershell
Invoke-RestMethod -Uri "http://localhost:8000/analytics/kpis" `
  -Headers $headers | ConvertTo-Json -Depth 5
\\\

**✅ Expected:**
\\\json
{
  "total_transfers": 488,
  "pregnancy_rate": {
    "value": 0.288,
    "ci_lower": 0.25,
    "ci_upper": 0.33
  },
  "embryo_utilization": 0.95,
  "total_donors": 52,
  "total_embryos": 488
}
\\\

### Test 5.3 — Trends Analysis

\\\powershell
Invoke-RestMethod -Uri "http://localhost:8000/analytics/trends" `
  -Headers $headers | ConvertTo-Json -Depth 5
\\\

**✅ Expected:** Time-series pregnancy rate trends by month

### Test 5.4 — IVF Funnel

\\\powershell
Invoke-RestMethod -Uri "http://localhost:8000/analytics/funnel" `
  -Headers $headers | ConvertTo-Json -Depth 5
\\\

**✅ Expected:** Funnel stages
\\\json
{
  "stages": [
    { "name": "Donors", "count": 52, "conversion": 1.0 },
    { "name": "OPU Procedures", "count": 410, "conversion": 0.84 },
    { "name": "Embryos Created", "count": 488, "conversion": 1.0 },
    { "name": "Embryos Transferred", "count": 488, "conversion": 1.0 },
    { "name": "Pregnancies", "count": 136, "conversion": 0.29 }
  ]
}
\\\

### Test 5.5 — Protocol Analysis

\\\powershell
# Protocol effectiveness
Invoke-RestMethod -Uri "http://localhost:8000/analytics/protocols" `
  -Headers $headers | ConvertTo-Json -Depth 5

# Protocol regression
Invoke-RestMethod -Uri "http://localhost:8000/analytics/protocols/regression" `
  -Headers $headers | ConvertTo-Json -Depth 5

# Feature importance
Invoke-RestMethod -Uri "http://localhost:8000/analytics/protocols/importance" `
  -Headers $headers | ConvertTo-Json -Depth 5
\\\

**✅ Expected:** 
- Per-protocol pregnancy rates with Wilson CIs
- Logistic regression coefficients
- Permutation importance scores

### Test 5.6 — Donor Analytics

\\\powershell
# Donor performance
Invoke-RestMethod -Uri "http://localhost:8000/analytics/donors" `
  -Headers $headers | ConvertTo-Json -Depth 5

# Donor trends
Invoke-RestMethod -Uri "http://localhost:8000/analytics/donors/trends" `
  -Headers $headers | ConvertTo-Json -Depth 5
\\\

**✅ Expected:** Per-donor success rates and trends

### Test 5.7 — Breed Analytics

\\\powershell
Invoke-RestMethod -Uri "http://localhost:8000/analytics/breeds" `
  -Headers $headers | ConvertTo-Json -Depth 5
\\\

**✅ Expected:** Pregnancy rates by breed

### Test 5.8 — Biomarker Sweet-Spots (AT-6)

\\\powershell
Invoke-RestMethod -Uri "http://localhost:8000/analytics/biomarkers" `
  -Headers $headers | ConvertTo-Json -Depth 5
\\\

**✅ Expected:** CL size analysis
\\\json
{
  "cl_measure": {
    "bins": [
      { "range": "< 10mm", "pregnancy_rate": 0.15, "n": 12 },
      { "range": "20-22mm", "pregnancy_rate": 0.42, "n": 87, "optimal": true },
      { "range": "> 30mm", "pregnancy_rate": 0.22, "n": 23 }
    ],
    "optimal_range": "20-22mm"
  }
}
\\\

### Test 5.9 — Frontend: Analytics Page

**Navigate to:** http://localhost:5173/analytics

**✅ Expected:**

**Overview Tab:**
- KPI cards (total transfers, pregnancy rate, embryo utilization)
- Fresh vs Frozen comparison chart
- IVF funnel visualization
- Monthly pregnancy rate trends

**Protocols Tab:**
- Horizontal bar chart with 95% CI overlays
- Protocol detail table with pregnancy rates
- Regression results section
- Feature importance chart

**Donors Tab:**
- Top 15 donor performance bars
- Full donor table with vs-mean indicators
- Donor trends over time

**Biomarkers Tab:**
- CL size sweet-spot analysis with optimal range highlighted
- BC score analysis
- Heat day analysis

### Test 5.10 — Documentation Files

\\\powershell
Test-Path "d:\Ovulite new\docs\LIMITATIONS.md"
Test-Path "d:\Ovulite new\docs\MODEL_REPORT.md"
Test-Path "d:\Ovulite new\docs\USER_GUIDE.md"
\\\

**✅ Expected:** All return True

---

## Acceptance Tests Summary

**These are the 10 formal acceptance tests from ROADMAP:**

| AT | Test Description | Phase | Verification Command | Expected Result |
|----|------------------|-------|----------------------|-----------------|
| **AT-1** | All 488 ET records imported | 1 | \GET /transfers/?limit=1\ → check \	otal\ | \	otal ≈ 488\ |
| **AT-2** | Invalid CL rejected | 1 | POST transfer with \cl_size_mm: 999\ | \422 Validation Error\ |
| **AT-3** | Prediction returns P + CI + SHAP | 2 | POST \/predict/pregnancy\ | Response has \probability\, \confidence_interval\, \shap_values\ |
| **AT-4** | Upload image → grade + heatmap | 3 | POST \/grade/embryo-with-heatmap\ | Response has \grade\, \heatmap\ (base64) |
| **AT-5** | Synthetic anomaly detected | 4 | POST \/qc/run?with_synthetic=true\ → GET \/qc/anomalies\ | Injected anomalies flagged |
| **AT-6** | Dashboard renders all KPIs | 5 | Visit \/analytics\ | KPI cards, charts, funnel render correctly |
| **AT-7** | Uncertainty displayed | 2 | Check prediction response | \confidence_interval\ present with lower/upper bounds |
| **AT-8** | RBAC enforced | 0 | Call protected endpoint without token | \401 Unauthorized\ |
| **AT-9** | SHAP explanations present | 2 | Check prediction response | \shap_values\ dictionary with feature contributions |
| **AT-10** | All endpoints documented | 0 | Visit \/docs\ | Swagger shows all 13 router groups |

---

## Full System Smoke Test

**Execute in 5 minutes:**

\\\powershell
# 1. Health check
Invoke-RestMethod -Uri http://localhost:8000/health

# 2. Swagger
Start-Process http://localhost:8000/docs

# 3. Login and get token
$response = Invoke-RestMethod -Method POST `
  -Uri http://localhost:8000/auth/login `
  -ContentType "application/x-www-form-urlencoded" `
  -Body "username=admin&password=ovulite2026"
$token = $response.access_token
$headers = @{ Authorization = "Bearer $token" }

# 4. Check data
($t = Invoke-RestMethod -Uri "http://localhost:8000/transfers/?limit=1" -Headers $headers)
Write-Host "Total transfers: $($t.total)"

# 5. Prediction
$predBody = @{ cl_size_mm=25; embryo_stage="Morula"; protocol_name="CIDR" } | ConvertTo-Json
($pred = Invoke-RestMethod -Method POST `
  -Uri "http://localhost:8000/predict/pregnancy" `
  -Headers ($headers + @{"Content-Type"="application/json"}) `
  -Body $predBody)
Write-Host "Pregnancy probability: $($pred.probability)"

# 6. QC
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/qc/run" -Headers $headers

# 7. Analytics
($kpi = Invoke-RestMethod -Uri "http://localhost:8000/analytics/kpis" -Headers $headers)
Write-Host "Pregnancy rate: $($kpi.pregnancy_rate.value)"

# 8. Frontend
Start-Process http://localhost:5173

Write-Host "
✅ Smoke test complete!"
\\\

---

## Testing Workflow Checklist

### Pre-Test Setup
- [ ] PostgreSQL running on localhost:5432
- [ ] Backend running on http://localhost:8000
- [ ] Frontend running on http://localhost:5173
- [ ] Database migrations applied (\lembic upgrade head\)
- [ ] Admin user seeded
- [ ] JWT token obtained and stored in \`eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInJvbGUiOiJhZG1pbiIsImV4cCI6MTc3Mjc3NTgzOX0.OkKQ2rWpc8Rn6jWbd7De0x4_t1LPhTPv8rXJFclV3OM\ variable

### Phase 0: Foundation
- [ ] Health endpoint responds
- [ ] 13 database tables exist
- [ ] Swagger documentation loads
- [ ] Login flow works
- [ ] Protected endpoints require auth
- [ ] CORS headers present
- [ ] Frontend loads and login works

### Phase 1: Data Intake
- [ ] CSV import succeeds (488 records)
- [ ] All CRUD endpoints return data
- [ ] CL validation rejects invalid values
- [ ] Frontend data entry page displays records
- [ ] Transfer form creates new records

### Phase 2: Pregnancy Prediction
- [ ] Model info endpoint returns metadata
- [ ] Prediction returns probability + CI + SHAP
- [ ] Frontend prediction page works
- [ ] Probability gauge displays correctly
- [ ] SHAP chart shows feature contributions

### Phase 3: Embryo Grading
- [ ] Model info endpoint returns architecture
- [ ] Image upload works
- [ ] Grading returns grade + viability
- [ ] Grad-CAM heatmap generated
- [ ] Frontend grading page displays results and heatmap

### Phase 4: Lab QC
- [ ] QC pipeline runs successfully
- [ ] Anomalies detected and stored
- [ ] Control charts generated (EWMA/CUSUM)
- [ ] Technician stats computed
- [ ] Frontend QC dashboard renders

### Phase 5: Analytics
- [ ] Analytics pipeline runs
- [ ] KPIs computed correctly
- [ ] Protocol analysis completed
- [ ] Donor analytics available
- [ ] Biomarker sweet-spots identified
- [ ] Frontend analytics dashboard renders all tabs

### Acceptance Tests
- [ ] AT-1: 488 records imported
- [ ] AT-2: Invalid CL rejected
- [ ] AT-3: Prediction with CI + SHAP
- [ ] AT-4: Grade with heatmap
- [ ] AT-5: Synthetic anomalies detected
- [ ] AT-6: Dashboard KPIs render
- [ ] AT-7: Uncertainty displayed
- [ ] AT-8: RBAC enforced
- [ ] AT-9: SHAP explanations present
- [ ] AT-10: All endpoints documented

### Documentation
- [ ] LIMITATIONS.md reviewed
- [ ] MODEL_REPORT.md reviewed
- [ ] USER_GUIDE.md reviewed

---

## Testing Notes

### Common Issues & Solutions

**Port Already in Use:**
\\\powershell
# Kill processes on ports 8000 and 5173
Get-NetTCPConnection -LocalPort 8000,5173 -ErrorAction SilentlyContinue | 
  ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
\\\

**CORS Errors:**
- Backend must allow origins: http://localhost:5173-5176
- Check \ackend/app/main.py\ CORS configuration

**Token Expired:**
- JWT tokens expire after 30 minutes
- Re-run the token acquisition command

**CSV Import Fails:**
- Ensure CSV path is correct
- Check database is writable
- Verify foreign key constraints

**ML Models Not Loaded:**
- Check \ml/artifacts/\ directory has model files
- Run training scripts if needed: \python -m ml.run_training\

### Performance Notes

- **First API call** to each ML endpoint may be slow (model loading)
- **Subsequent calls** use cached models
- **QC pipeline** takes ~10-30 seconds depending on data size
- **Analytics pipeline** takes ~5-15 seconds

---

**Document Version:** 1.0.0  
**Last Updated:** 2026-03-06  
**Status:** ✅ ALL PHASES COMPLETE
