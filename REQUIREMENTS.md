# Ovulite – Requirements Specification

## 1. Data Audit Summary

### 1.1 Primary Dataset: ET Summary - ET Data.csv

| Property              | Value                                              |
|-----------------------|----------------------------------------------------|
| Total data rows       | 488                                                |
| Total columns         | 39                                                 |
| Date range            | May 1, 2025 – Feb 4, 2026 (19 unique ET dates)    |
| Target variable       | `1st PC Result` (Pregnant / Open / Recheck)         |
| Class balance         | Open=334 (70.8%), Pregnant=136 (28.8%), Recheck=2  |

#### Column Inventory

| Index | Column                   | Type        | Missing % | Notes                                |
|-------|--------------------------|-------------|-----------|--------------------------------------|
| 0     | # ET                     | Integer     | 0%        | Sequential ET number                 |
| 1     | Lab                      | Categorical | 0%        | Lab identifier (all DZF)             |
| 2     | Satellite                | Categorical | 0%        | Satellite identifier (all DZF)       |
| 3     | Customer ID              | Categorical | 0%        | Client identifier                    |
| 4     | ET Date                  | Date        | 0%        | Transfer date                        |
| 5     | ET Location              | Text        | 0%        | Recipient farm                       |
| 6     | Recipient ID (1st)       | ID          | 0%        | Recipient tag                        |
| 7     | Recipient ID (2nd)       | ID          | ~varies   | Duplicate column                     |
| 8     | Cow/Heifer               | Categorical | 0%        | All "Cow" in current data            |
| 9     | Heat                     | Categorical | ~varies   | Heat observation                     |
| 10    | CL Side                  | Categorical | 4.9%      | Corpus luteum laterality             |
| 11    | CL measure (mm)          | Numeric     | 2.3%      | CL diameter — key biomarker          |
| 12    | Protocol                 | Categorical | 0%        | Synchronization protocol (5 types)   |
| 13    | Fresh or Frozen          | Categorical | 0%        | Embryo preservation method           |
| 14    | # Cane if Frozen         | Text        | ~high     | Cane number for frozen embryos       |
| 15    | Freezing date            | Date        | ~high     | Date of freezing                     |
| 16    | ET Tech                  | Categorical | 0%        | Transfer technician (5 people)       |
| 17    | ET assistant             | Categorical | ~varies   | Assistant name                       |
| 18    | BCScore                  | Numeric     | 77.5%     | Body condition score — high missing! |
| 19    | Embryo Stage 4-8         | Integer     | 0%        | Embryo stage code                    |
| 20    | Embryo Grade             | Integer     | 0%        | Embryo quality grade (mostly 1)      |
| 21    | Heat (2nd col)           | Numeric     | ~varies   | Duplicate heat column                |
| 22    | Heat day                 | Numeric     | ~varies   | Days since heat                      |
| 23    | 1st PC date              | Date        | ~low      | First pregnancy check date           |
| 24    | 1st PC Result            | Categorical | 3.3%      | **TARGET VARIABLE**                  |
| 25    | 2nd PC date              | Date        | ~high     | Second pregnancy check date          |
| 26    | 2nd PC Result            | Categorical | ~high     | Second PC result                     |
| 27    | Fetal Sexing             | Categorical | ~high     | Fetal sex if determined              |
| 28    | OPU Date                 | Date        | 15.4%     | Oocyte pickup date                   |
| 29    | Donor                    | ID          | 0%        | Donor cow identifier                 |
| 30    | Donor Breed              | Categorical | 0.4%      | Donor breed (13 categories)          |
| 31    | Donor BW EPD             | Numeric     | ~varies   | Donor birth weight EPD               |
| 32    | SIRE Name                | Text        | 1%        | Sire bull name                       |
| 33    | SIRE BW EPD              | Numeric     | ~varies   | Sire birth weight EPD                |
| 34    | Semen type               | Categorical | ~varies   | Conventional / Sexed                 |
| 35    | SIRE Breed               | Categorical | ~varies   | Sire breed                           |
| 36    | CLIENT                   | Categorical | ~varies   | Client name                          |
| 37    | DIP (1st)                | Numeric     | ~varies   | Days in pregnancy                    |
| 38    | DIP (2nd)                | Numeric     | ~varies   | Duplicate DIP column                 |

#### Data Quality Issues

1. **Duplicate columns:** Recipient ID (cols 6-7), Heat (cols 9,21), DIP (cols 37-38) — need deduplication
2. **BCScore 77.5% missing** — Cannot be used as primary feature; imputation or exclusion needed
3. **Embryo Grade near-constant** — 482/488 = Grade 1; zero predictive variance from this alone
4. **Cow/Heifer no variance** — All records are "Cow"; no predictive value
5. **Lab/Satellite constant** — All DZF; no variance
6. **Donor breed data quality** — Some IDs mistakenly in breed column (D1, D2, D3, 600)
7. **Dirty date formats** — Some donors have dates as IDs (5/14/2025, 9/4/2025, 6/12/2025)

### 1.2 Client Pregnancy Reports (4 files)

| File                              | Rows | Columns | Notes                                     |
|-----------------------------------|------|---------|-------------------------------------------|
| AQ Cattle - Pregnancy Record      | 48   | 8       | Confirmed pregnancies only (biased)       |
| Dawood - Pregnancy Record         | 26   | 7       | Confirmed pregnancies only                |
| Sardar Fahad ET                   | 56   | 9       | Mixed status (Pregnant/Recheck)           |
| Waqas Palari ET                   | 109  | 9       | Mixed Pregnant Y/N                        |

**These are client-facing reports, NOT raw data. They contain only confirmed pregnancies or summaries. Use for cross-validation of identities but NOT as primary training data.**

### 1.3 Sheet10.csv (Donor-Sire Mapping)

| Columns    | Rows | Content                                |
|------------|------|----------------------------------------|
| Donor, Sire| 51   | Donor-to-sire pairings with recipient IDs |

### 1.4 Embryo Image Dataset

| Property          | Value                                      |
|-------------------|--------------------------------------------|
| Total images      | 482                                        |
| Format            | JPEG (.jpg)                                |
| Naming pattern    | `blq{N}.jpg` (N = 1-482)                  |
| Subdirectories    | None (flat folder)                         |
| Labels            | **NONE** — no grade/class subfolder structure |
| Avg size          | ~50-65 KB per image                        |

**Critical: Images have NO ground-truth labels. Labels must be mapped from ET Data `Embryo Grade` column, but that column is nearly constant (Grade 1). Self-supervised pretraining (SimCLR-style) is required before supervised fine-tuning.**

---

## 2. Database Schema Design

### 2.1 Core Tables

```sql
-- ============================================================
-- TABLE: donors
-- ============================================================
CREATE TABLE donors (
    donor_id        SERIAL PRIMARY KEY,
    tag_id          VARCHAR(50) NOT NULL UNIQUE,
    breed           VARCHAR(100),
    birth_weight_epd DECIMAL(6,2),
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE: sires
-- ============================================================
CREATE TABLE sires (
    sire_id         SERIAL PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,
    breed           VARCHAR(100),
    birth_weight_epd DECIMAL(6,2),
    semen_type      VARCHAR(50) CHECK (semen_type IN ('Conventional', 'Sexed', 'Unknown')),
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE: recipients
-- ============================================================
CREATE TABLE recipients (
    recipient_id    SERIAL PRIMARY KEY,
    tag_id          VARCHAR(50) NOT NULL,
    farm_location   VARCHAR(200),
    cow_or_heifer   VARCHAR(20) CHECK (cow_or_heifer IN ('Cow', 'Heifer')),
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE: technicians
-- ============================================================
CREATE TABLE technicians (
    technician_id   SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL UNIQUE,
    role            VARCHAR(50) DEFAULT 'ET Technician',
    active          BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE: protocols
-- ============================================================
CREATE TABLE protocols (
    protocol_id     SERIAL PRIMARY KEY,
    name            VARCHAR(200) NOT NULL UNIQUE,
    description     TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE: embryos
-- ============================================================
CREATE TABLE embryos (
    embryo_id       SERIAL PRIMARY KEY,
    donor_id        INTEGER REFERENCES donors(donor_id),
    sire_id         INTEGER REFERENCES sires(sire_id),
    opu_date        DATE,
    stage           INTEGER CHECK (stage BETWEEN 1 AND 9),
    grade           INTEGER CHECK (grade BETWEEN 1 AND 4),
    fresh_or_frozen VARCHAR(20) CHECK (fresh_or_frozen IN ('Fresh', 'Frozen')),
    cane_number     VARCHAR(50),
    freezing_date   DATE,
    ai_grade        INTEGER,               -- AI-predicted grade
    ai_viability    DECIMAL(5,4),           -- AI-predicted viability probability
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE: et_transfers  (ONE ROW PER TRANSFER ATTEMPT)
-- ============================================================
CREATE TABLE et_transfers (
    transfer_id     SERIAL PRIMARY KEY,
    et_number       INTEGER,                -- sequential ET number
    lab             VARCHAR(50),
    satellite       VARCHAR(50),
    customer_id     VARCHAR(50),
    et_date         DATE NOT NULL,
    farm_location   VARCHAR(200),

    -- Recipient
    recipient_id    INTEGER REFERENCES recipients(recipient_id),
    bc_score        DECIMAL(4,2),           -- body condition score

    -- CL (Corpus Luteum) data
    cl_side         VARCHAR(10),            -- Left / Right
    cl_measure_mm   DECIMAL(5,1),           -- CL diameter

    -- Synchronization
    protocol_id     INTEGER REFERENCES protocols(protocol_id),
    heat_observed   BOOLEAN,
    heat_day        INTEGER,

    -- Embryo
    embryo_id       INTEGER REFERENCES embryos(embryo_id),

    -- Staff
    technician_id   INTEGER REFERENCES technicians(technician_id),
    assistant_name  VARCHAR(100),

    -- Outcome (POST-TRANSFER — leakage risk!)
    pc1_date        DATE,
    pc1_result      VARCHAR(20) CHECK (pc1_result IN ('Pregnant', 'Open', 'Recheck', NULL)),
    pc2_date        DATE,
    pc2_result      VARCHAR(20),
    fetal_sexing    VARCHAR(20),
    days_in_pregnancy INTEGER,

    -- Metadata
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE: embryo_images  (path registry only)
-- ============================================================
CREATE TABLE embryo_images (
    image_id        SERIAL PRIMARY KEY,
    embryo_id       INTEGER REFERENCES embryos(embryo_id),
    file_path       VARCHAR(500) NOT NULL,
    file_hash       VARCHAR(64),            -- SHA-256 for dedup
    width_px        INTEGER,
    height_px       INTEGER,
    uploaded_at     TIMESTAMPTZ DEFAULT NOW(),
    notes           TEXT
);

-- ============================================================
-- TABLE: protocol_logs  (per-transfer protocol details)
-- ============================================================
CREATE TABLE protocol_logs (
    log_id          SERIAL PRIMARY KEY,
    transfer_id     INTEGER REFERENCES et_transfers(transfer_id),
    protocol_id     INTEGER REFERENCES protocols(protocol_id),
    step_name       VARCHAR(100),
    step_date       DATE,
    drug_name       VARCHAR(100),
    dosage          VARCHAR(50),
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE: predictions  (model output audit trail)
-- ============================================================
CREATE TABLE predictions (
    prediction_id   SERIAL PRIMARY KEY,
    transfer_id     INTEGER REFERENCES et_transfers(transfer_id),
    model_name      VARCHAR(100) NOT NULL,
    model_version   VARCHAR(50),
    probability     DECIMAL(5,4) NOT NULL,
    confidence_lower DECIMAL(5,4),
    confidence_upper DECIMAL(5,4),
    risk_band       VARCHAR(20),            -- Low / Medium / High
    shap_json       JSONB,                  -- Feature contributions
    predicted_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE: anomalies  (QC module output)
-- ============================================================
CREATE TABLE anomalies (
    anomaly_id      SERIAL PRIMARY KEY,
    anomaly_type    VARCHAR(50) NOT NULL,    -- technician_deviation, media_anomaly, rate_drift
    entity_type     VARCHAR(50),            -- technician, media, batch
    entity_id       VARCHAR(100),
    severity        VARCHAR(20),            -- info, warning, critical
    description     TEXT,
    metric_value    DECIMAL(8,4),
    baseline_value  DECIMAL(8,4),
    detected_at     TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE: users  (authentication)
-- ============================================================
CREATE TABLE users (
    user_id         SERIAL PRIMARY KEY,
    username        VARCHAR(100) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    role            VARCHAR(50) CHECK (role IN ('admin', 'veterinarian', 'embryologist', 'viewer')),
    full_name       VARCHAR(200),
    email           VARCHAR(200),
    active          BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    last_login      TIMESTAMPTZ
);
```

### 2.2 Canonical ET View (for ML feature matrix)

```sql
CREATE VIEW vw_et_features AS
SELECT
    t.transfer_id,
    t.et_date,
    t.farm_location,

    -- Recipient features
    r.tag_id            AS recipient_tag,
    r.cow_or_heifer,
    t.bc_score,
    t.cl_side,
    t.cl_measure_mm,
    t.heat_observed,
    t.heat_day,

    -- Protocol
    p.name              AS protocol_name,

    -- Embryo features
    e.stage             AS embryo_stage,
    e.grade             AS embryo_grade,
    e.fresh_or_frozen,
    e.opu_date,
    (t.et_date - e.opu_date) AS days_opu_to_et,

    -- Donor features
    d.tag_id            AS donor_tag,
    d.breed             AS donor_breed,
    d.birth_weight_epd  AS donor_bw_epd,

    -- Sire features
    s.name              AS sire_name,
    s.breed             AS sire_breed,
    s.birth_weight_epd  AS sire_bw_epd,
    s.semen_type,

    -- Staff
    tech.name           AS technician_name,
    t.assistant_name,

    -- Target (exclude from features during training!)
    t.pc1_result        AS pregnancy_outcome

FROM et_transfers t
LEFT JOIN recipients r   ON t.recipient_id  = r.recipient_id
LEFT JOIN embryos e      ON t.embryo_id     = e.embryo_id
LEFT JOIN donors d       ON e.donor_id      = d.donor_id
LEFT JOIN sires s        ON e.sire_id       = s.sire_id
LEFT JOIN protocols p    ON t.protocol_id   = p.protocol_id
LEFT JOIN technicians tech ON t.technician_id = tech.technician_id;
```

---

## 3. Leakage-Safe Data Split Plan

### 3.1 Leakage Risks Identified

| Risk                          | Category        | Mitigation                                    |
|-------------------------------|-----------------|-----------------------------------------------|
| Same donor in train AND test  | Group leakage   | Donor-based GroupKFold split                  |
| Future outcome in features    | Temporal leakage| Exclude pc1_result, pc2_result, DIP from X    |
| 2nd PC confirming 1st PC      | Target leakage  | Only use 1st PC Result as target              |
| Fetal sexing implies pregnant  | Target leakage  | Exclude fetal_sexing from features            |
| DIP implies pregnant           | Target leakage  | Exclude DIP from features                     |
| Recipient repeats across time | Group leakage   | Track; secondary split strategy               |

### 3.2 Split Strategy: Temporal + Donor-Grouped Hybrid

**Primary strategy: Time-based forward-chaining split**

```
Timeline:  May 2025 ──────────────────────────────────── Feb 2026
           │        TRAIN (≤ Nov 14)        │  TEST (≥ Nov 30)  │
           │         ~358 records           │   ~130 records     │
           │                                │                    │
           │   5-Fold GroupKFold CV          │   UNTOUCHED        │
           │   (grouped by donor)           │   HOLDOUT          │
```

**Step-by-step:**

1. **Temporal holdout:** Records from Dec 2025 onward (~185 records, 38%) reserved as final holdout — NEVER touched during development.

2. **Training set:** Records up through Nov 14, 2025 (~303 records, 62%).

3. **Cross-validation within training:** 5-fold GroupKFold where groups = donor_tag. This ensures no donor appears in both train and validation folds.

4. **Recheck handling:** 2 "Recheck" records excluded entirely (ambiguous outcome).

5. **Missing outcome handling:** 16 records with missing `1st PC Result` excluded from supervised learning.

### 3.3 Feature Exclusion List (leakage prevention)

These columns MUST NEVER appear in the feature matrix:

| Column              | Reason                                       |
|---------------------|----------------------------------------------|
| 1st PC Result       | **TARGET VARIABLE**                          |
| 1st PC date         | Post-transfer temporal leakage               |
| 2nd PC date         | Post-transfer temporal leakage               |
| 2nd PC Result       | Post-transfer outcome                        |
| Fetal Sexing        | Only available if pregnant                   |
| DIP                 | Only nonzero if pregnant                     |
| # ET                | Sequential ID, not a feature                 |
| Lab / Satellite     | Zero variance (all DZF)                      |

### 3.4 Final Feature Set for Pregnancy Prediction

| Feature             | Type        | Preprocessing                        |
|---------------------|-------------|--------------------------------------|
| CL measure (mm)     | Numeric     | Impute median; scale                 |
| CL Side             | Categorical | One-hot encode (L/R/missing)         |
| Protocol            | Categorical | One-hot encode (5 categories)        |
| Fresh or Frozen     | Categorical | Binary encode                        |
| Embryo Stage        | Ordinal     | Integer 4-8                          |
| Embryo Grade        | Ordinal     | Integer (low variance warning)       |
| ET Tech             | Categorical | One-hot or target encode             |
| Donor Breed         | Categorical | Group rare breeds; one-hot           |
| Donor BW EPD        | Numeric     | Impute median; scale                 |
| Sire BW EPD         | Numeric     | Impute median; scale                 |
| Semen Type          | Categorical | Binary encode                        |
| Heat Day            | Numeric     | Impute; scale                        |
| Customer ID         | Categorical | One-hot or target encode             |
| Days OPU→ET         | Numeric     | Derived: ET Date - OPU Date          |
| BCScore             | Numeric     | 77.5% missing — include with flag    |
| BC_missing flag      | Binary      | 1 if BCScore missing                 |

---

## 4. Model Requirements

### 4.1 Pregnancy Prediction Engine

| Requirement                    | Specification                                |
|--------------------------------|----------------------------------------------|
| Primary model                  | TabPFN                                       |
| Baseline model                 | Logistic Regression (L2, class_weight=balanced)|
| Secondary benchmark            | XGBoost (max_depth≤4, early stopping)        |
| Validation                     | 5-fold GroupKFold (grouped by donor)         |
| Final evaluation               | Temporal holdout (Dec 2025+)                 |
| Calibration                    | Isotonic or Platt scaling (post-hoc)         |
| Interpretability               | SHAP values for every prediction             |
| Output format                  | P(pregnant), confidence interval, risk band  |

**Metrics required (all on holdout):**
- ROC-AUC
- PR-AUC (critical given imbalance)
- Calibration curve (reliability diagram)
- Confusion matrix
- Brier score

### 4.2 Embryo Grading Module

| Requirement                    | Specification                                |
|--------------------------------|----------------------------------------------|
| Backbone                       | EfficientNet-B0 or ResNet18 (pretrained)     |
| Image preprocessing            | Normalize, resize 224×224, augment           |
| Augmentation                   | Rotate, flip, contrast jitter                |
| Transfer learning              | Freeze early layers; fine-tune final blocks  |
| Metadata fusion                | Embryo day + stage + donor + media + tech    |
| Fusion architecture            | CNN embedding ⊕ metadata → MLP → output    |
| Outputs                        | Grade (1/2/3), viability probability, Grad-CAM|
| Fallback (no labels)           | SimCLR-style self-supervised pretraining     |

### 4.3 Lab QC Module

| Requirement                    | Specification                                |
|--------------------------------|----------------------------------------------|
| Method                         | Isolation Forest + EWMA/CUSUM control charts |
| NOT predictive                 | Monitoring and anomaly detection only        |
| Inputs                         | Media, tech, embryo day, pregnancy rate, date|
| Outputs                        | Technician deviation, media anomaly, drift   |

### 4.4 Protocol Analytics

| Requirement                    | Specification                                |
|--------------------------------|----------------------------------------------|
| Method                         | Multivariate logistic regression             |
| Adjustment                     | Propensity-score covariate adjustment        |
| Interpretability               | SHAP analysis for protocol impact            |
| Display                        | Pregnancy % by protocol                      |

---

## 5. System Requirements

### 5.1 Frontend

| Requirement          | Specification                               |
|----------------------|---------------------------------------------|
| Framework            | React with TypeScript                       |
| State management     | React Context or Zustand                    |
| Charts               | Recharts or Plotly.js                       |
| UI components        | shadcn/ui (already present)                 |
| Responsive           | Desktop-first, tablet-compatible            |

### 5.2 Backend

| Requirement          | Specification                               |
|----------------------|---------------------------------------------|
| Framework            | FastAPI (Python 3.11+)                      |
| Authentication       | JWT-based with bcrypt password hashing      |
| API validation       | Pydantic v2 models                          |
| Image handling       | File upload → disk storage → DB registry    |
| ML serving           | In-process model loading; versioned artifacts|
| Logging              | Structured logging (JSON format)            |

### 5.3 Database

| Requirement          | Specification                               |
|----------------------|---------------------------------------------|
| Engine               | PostgreSQL 15+                              |
| Migrations           | Alembic                                     |
| ORM                  | SQLAlchemy 2.0                              |

### 5.4 Deployment

| Requirement          | Specification                               |
|----------------------|---------------------------------------------|
| Orchestration        | Docker Compose                              |
| Services             | frontend + backend + db (3 containers)      |
| Volumes              | DB data, model artifacts, uploaded images   |
| Environment          | .env file for secrets                       |

### 5.5 Engineering Standards

| Requirement                | Specification                            |
|----------------------------|------------------------------------------|
| Role-based access          | Admin, Veterinarian, Embryologist, Viewer|
| API input validation       | Pydantic models on all endpoints         |
| Image registry             | DB table + filesystem storage            |
| Structured logging         | JSON logs with request tracing           |
| Model versioning           | Saved artifacts with metadata JSON       |
| Reproducible training      | Seed-fixed scripts with config files     |
| Data dictionary            | Documented in REQUIREMENTS.md (above)    |
| Model report               | Markdown report per trained model version|

---

## 6. Acceptance Tests

| ID   | Test                                          | Module      | Criteria                            |
|------|-----------------------------------------------|-------------|-------------------------------------|
| AT-1 | Enter ET record via UI                        | Data Intake | Record persists in DB               |
| AT-2 | Reject invalid CL or missing required fields  | Validation  | Error message shown; record blocked |
| AT-3 | Predict pregnancy with P + explanation         | Prediction  | Returns probability + SHAP + band   |
| AT-4 | Upload embryo image → grade + heatmap         | Grading     | Returns grade + Grad-CAM overlay    |
| AT-5 | Detect synthetic anomaly batch                | Lab QC      | Anomaly flagged within 1 session    |
| AT-6 | Render reproductive KPI dashboard             | Dashboard   | All charts load; filters work       |
| AT-7 | Show calibration reliability plot             | Evaluation  | Calibration curve renders           |
| AT-8 | Role-based login blocks unauthorized access   | Auth        | Non-admin cannot access admin pages |
| AT-9 | Uncertainty displayed for every prediction    | UX          | Confidence interval visible in UI   |
| AT-10| Model report generated after training         | Engineering | Markdown report with all metrics    |
