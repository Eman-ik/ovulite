# Ovulite – AI-Driven Reproductive Intelligence System for Bovine IVF

**Comprehensive Project Documentation**  
**Last Updated:** March 2026  
**Version:** 0.5.0 (Pre-Release)  
**Status:** ✅ **ALL 5 PHASES COMPLETE & OPERATIONAL**

---

## TABLE OF CONTENTS

1. [Project Overview](#project-overview)
2. [Project Vision & Goals](#project-vision--goals)
3. [Core Modules & Architecture](#core-modules--architecture)
4. [Technology Stack](#technology-stack)
5. [System Architecture](#system-architecture)
6. [Database Schema](#database-schema)
7. [Backend API Endpoints](#backend-api-endpoints)
8. [Frontend Pages & Components](#frontend-pages--components)
9. [Machine Learning Pipelines](#machine-learning-pipelines)
10. [Dataset Overview](#dataset-overview)
11. [Development Phases](#development-phases)
12. [Setup & Installation](#setup--installation)
13. [Testing & Verification](#testing--verification)
14. [Project Directory Structure](#project-directory-structure)
15. [Dependencies & Libraries](#dependencies--libraries)
16. [Configuration & Environment Variables](#configuration--environment-variables)
17. [Deployment](#deployment)
18. [System Limitations](#system-limitations)
19. [Key Features](#key-features)
20. [Team & Sponsorship](#team--sponsorship)

---

## PROJECT OVERVIEW

### What is Ovulite?

**Ovulite** is an uncertainty-aware, explainable AI decision-support platform for cattle IVF (In Vitro Fertilization) and embryo transfer that predicts pregnancy probability, grades embryos objectively, monitors lab quality, and analyzes protocol effectiveness — all under ultra-small-data constraints.

**Key Principle:** Ovulite does NOT replace clinical expertise. It structures data, reveals patterns, and makes uncertainty visible. The human remains the final decision authority.

### Project Metadata

| Attribute         | Value                              |
|-------------------|-------------------------------------|
| **Organization**  | DayZee Farms (Pvt.) Ltd.            |
| **Repository**    | Ovulite new                         |
| **Current Phase** | Phase 5 – Analytics Dashboard       |
| **Completion %**  | 95%+ Complete (All Core Features)   |
| **Version**       | 0.5.0 (pre-release)                 |
| **Team Members**  | Eman Malik, Inshal Zafar            |
| **Supervisor**    | Dr. Nusrat Shaheen                  |
| **Sponsor**       | DayZee Farms (Pvt.) Ltd.            |
| **Start Date**    | 2025-05-01                          |
| **Launch Date**   | 2026-03-06                          |
| **Data Period**   | May 2025 – February 2026            |

---

## PROJECT VISION & GOALS

### Primary Vision

Provide bovine reproductive specialists with an AI-powered decision support system that:
- **Predicts** pregnancy success probability with quantified uncertainty
- **Grades** embryos objectively using image + metadata fusion
- **Monitors** laboratory quality in real-time via anomaly detection
- **Analyzes** protocol effectiveness with statistical rigor
- **Visualizes** reproductive KPIs and trends for strategic insights

### Gold Standard Requirements

1. **Overfitting Avoidance** — Small-data-optimal algorithms; strict validation protocols
2. **Honest Uncertainty** — Calibrated probabilities; confidence intervals; "data insufficient" alerts
3. **Biological Interpretability** — SHAP explanations; feature contributions; clinically meaningful outputs
4. **Clinical Usability** — Actionable decision support, not black-box automation
5. **Explicit Limitations** — Transparent documentation of what the system cannot do

### Success Criteria

✅ 488 ET records imported and validated  
✅ Pregnancy prediction model (ROC-AUC > 0.75) with uncertainty quantification  
✅ Embryo grading model with visual explanations (Grad-CAM)  
✅ Lab QC pipeline with real-time anomaly detection  
✅ Analytics dashboard with protocol effectiveness analysis  
✅ RBAC authentication & secure API  
✅ 100+ automated tests with >80% coverage  
✅ Docker-based deployment ready for production  

---

## CORE MODULES & ARCHITECTURE

### 7 Core Modules (Per Presentation PDF)

| # | Module Name                              | Type                    | Purpose                                          |
|---|------------------------------------------|-------------------------|--------------------------------------------------|
| 1 | **Secure Login & Access Control**        | Auth / RBAC             | JWT + bcrypt + role-based permissions           |
| 2 | **Data Intake & Validation**             | ETL / Data Governance   | CSV ingestion, cleaning, validation rules       |
| 3 | **AI Embryo Grading**                    | CNN + MLPFusion         | Image + metadata fusion for embryo quality      |
| 4 | **Pregnancy Success Prediction**         | Tabular ML (TabPFN)     | Predict pregnancy with confidence intervals     |
| 5 | **Lab Quality Control & Anomaly Detection** | Unsupervised ML        | Real-time QC monitoring via Isolation Forest    |
| 6 | **Protocol Effectiveness Analytics**     | Statistical / ML        | Analyze which protocols perform best             |
| 7 | **Analytics Dashboard**                  | Visualization/BI        | KPIs, trends, donor/sire/protocol performance   |

### Architectural Layers

```
┌─────────────────────────────────────────────────┐
│              React Frontend (TypeScript)          │
│       Dashboard | Data Entry | Predictions        │
│    Embryo Grading | Lab QC | Analytics Dashboard │
└──────────────────┬──────────────────────────────┘
                   │ REST API (OpenAPI/Swagger)
┌──────────────────▼──────────────────────────────┐
│          FastAPI Backend (Python)                │
│     Auth | Data Validation | API Routers         │
├──────────┬──────────┬──────────┬────────────────┤
│ Pregnancy│ Embryo   │ Lab QC   │ Protocol       │
│ Predictor│ Grader   │ Pipeline │ Analytics      │
│ (TabPFN) │ (CNN+MLP)│ (IsoFor) │ (Regression)   │
└──────────┴──────────┴──────────┴────────────────┘
                   │ SQL
┌──────────────────▼──────────────────────────────┐
│        PostgreSQL 15 Relational Database         │
│    12 Tables + Views for ET Records & Metadata   │
└──────────────────────────────────────────────────┘
```

### Service Communication Flow

```
User Browser
    ↓
   [VITE dev server] :5173
       ↓ (npm run dev)
   [React Dashboard]
       ↓ API Calls (fetch/axios)
   [FastAPI Backend] :8000
       ├─ HTTP Routes
       ├─ WebSocket (future)
       ├─ gRPC (future)
       └─ JWT Auth Middleware
           ↓
       [PostgreSQL] :5432
           ├─ Relational Data
           ├─ ET Records
           └─ User Credentials
           ↓
       [ML Pipelines]
           ├─ TabPFN (pregnancy)
           ├─ CNN+MLP (grading)
           ├─ Isolation Forest (QC)
           └─ SHAP Explainers
```

---

## TECHNOLOGY STACK

### Backend Technologies

#### Web Framework & API
- **FastAPI** v0.109.0+ — Modern async Python web framework for REST APIs
- **Uvicorn** v0.27.0+ — ASGI application server for FastAPI
- **Python** v3.11+ — Core language

#### Database & ORM
- **PostgreSQL** v15+ — Relational database (primary data store)
- **SQLAlchemy** v2.0.25+ — Python SQL toolkit and ORM
- **Alembic** v1.13.0+ — Database schema migrations
- **psycopg2-binary** v2.9.9+ — PostgreSQL adapter for Python

#### Authentication & Security
- **Python-Jose** v3.3.0+ — JWT token creation/verification (RFC 7519)
- **bcrypt** v4.1.3 — Password hashing (secure cryptographic algorithm)
- **Argon2-cffi** v23.1.0 — Alternative password hashing (Argon2id)
- **passlib** v1.7.4 — Unified password hashing library

#### Data Handling
- **Pydantic** v2.5.0+ — Data validation using Python type hints
- **python-multipart** v0.0.6+ — Form data parsing (file uploads)
- **python-dotenv** v1.0.0+ — Environment variable management

#### Machine Learning & Data Science
- **pandas** v2.1.0+ — Data manipulation and analysis
- **numpy** v1.24.0+ — Numerical computing
- **scikit-learn** v1.4.0+ — Machine learning algorithms (SVMs, forests, etc.)
- **XGBoost** v2.0.0+ — Gradient boosting for tabular data
- **SHAP** v0.44.0+ — SHapley Additive exPlanations for model interpretability
- **joblib** v1.3.0+ — Serialization and parallel computing

#### Computer Vision (Embryo Grading)
- **Pillow** v10.0.0+ — Image processing (JPEG load/manipulation)
- **PyTorch** v2.1.0+ — Deep learning framework
- **TorchVision** v0.16.0+ — Computer vision utilities (pre-trained models, transforms)

#### Testing & Quality Assurance
- **pytest** — Unit & integration testing framework
- **pytest-asyncio** — Async test support
- **pytest-cov** — Code coverage reporting
- **httpx** — Async HTTP client for API testing

### Frontend Technologies

#### Framework & Language
- **React** v19.2.0+ — UI component library (JavaScript)
- **TypeScript** v5.9.3+ — Typed superset of JavaScript
- **React Router DOM** v6.22.0+ — Client-side routing

#### Build Tooling & Dev Environment
- **Vite** v8.0.0+ — Next-generation frontend build tool (hot reload)
- **npm** v9+ — JavaScript package manager

#### Styling & UI Components
- **Tailwind CSS** v3.4.1+ — Utility-first CSS framework
- **PostCSS** v8.4.35+ — CSS transformation tool
- **Autoprefixer** v10.4.17+ — Vendor prefix automation
- **tailwind-merge** v2.2.0+ — Merge Tailwind class names
- **clsx** v2.1.0+ — Conditional CSS class construction

#### UI Libraries & Icons
- **Lucide React** v0.475.0+ — Icon library (SVG icons)
- **Framer Motion** v12.36.0+ — Animation library (smooth transitions)

#### HTTP Client
- **Axios** v1.6.7+ — Promise-based HTTP client (API calls)

#### Development Tools
- **ESLint** v9.39.1+ — JavaScript linter for code quality
- **eslint-plugin-react-hooks** v7.0.1+ — React hooks linting rules
- **eslint-plugin-react-refresh** v0.4.24+ — React Fast Refresh rules
- **@vitejs/plugin-react** v5.1.1+ — React plugin for Vite
- **@types/react** v19.2.7+ — TypeScript type definitions for React
- **@types/react-dom** v19.2.3+ — TypeScript type definitions for ReactDOM

### Containerization & Deployment
- **Docker** — Containerization platform (images for backend, frontend, database)
- **Docker Compose** v2+ — Multi-container orchestration
- **Alpine Linux** — Lightweight Linux distribution for Docker images

### Additional Tools & Services
- **Git** — Version control system
- **GitHub/GitLab** — Repository hosting (if applicable)

---

## SYSTEM ARCHITECTURE

### High-Level System Design

```
┌────────────────────────────────────────────────────────────────┐
│                        CLIENT TIER                              │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Web Browser (Chrome, Firefox, Safari, Edge)            │  │
│  └──────────────────────┬───────────────────────────────────┘  │
│                         │ HTTPS/HTTP                            │
└─────────────────────────┼────────────────────────────────────────┘
                          │
        ┌─────────────────▼─────────────────┐
        │  VITE Development Server :5173    │
        │  (Hot Module Replacement)         │
        └─────────────────┬─────────────────┘
                          │
┌─────────────────────────▼─────────────────────────────────────────┐
│                    APPLICATION TIER                               │
│                                                                    │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │  React Application (TypeScript)                          │   │
│  │  ├── Pages (Dashboard, DataEntry, Predictions, etc.)    │   │
│  │  ├── Components (Forms, Tables, Charts, Modals)         │   │
│  │  ├── Hooks (useAuth, useFetch, useFormData)             │   │
│  │  ├── Contexts (AuthContext, DataContext)                │   │
│  │  └── Utilities (API client, validators, formatters)     │   │
│  └──────────────────┬──────────────────────────────────────┘   │
│                     │ REST API (JSON payloads)                    │
└─────────────────────┼──────────────────────────────────────────────┘
                      │
        ┌─────────────▼─────────────┐
        │  FastAPI Server :8000     │
        │  (ASGI Application)       │
        └─────────────┬─────────────┘
                      │
         ┌────────────┴────────────────┬────────────────┐
         │                             │                │
    ┌────▼─────┐  ┌──────────┐  ┌─────▼──────┐
    │Auth Route │  │API Routes│  │ML Services │
    │/auth/*    │  │/api/*    │  │/predict/*  │
    └────┬─────┘  └─────┬────┘  └─────┬──────┘
         │              │             │
┌────────┴──────────────┴─────────────┴──────────────────┐
│              API LAYER                                 │
│                                                         │
│  /auth/          (Authentication)                     │
│  /donors/        (Donor management)                   │
│  /sires/         (Sire management)                    │
│  /recipients/    (Recipient management)               │
│  /embryos/       (Embryo records)                     │
│  /transfers/     (ET transfers)                       │
│  /technicians/   (Technicians)                        │
│  /protocols/     (Protocols)                          │
│  /import/        (Data import)                        │
│  /predict/       (Predictions)                        │
│  /grading/       (Embryo grading)                     │
│  /qc/            (Quality control)                    │
│  /analytics/     (Analytics & KPIs)                   │
└────┬──────────────────────────────────────────────────┘
     │ SQL Queries
┌────▼──────────────────────────────────────────────────┐
│              DATABASE TIER                            │
│                                                        │
│  PostgreSQL 15 Database (:5432)                       │
│  ├── Users & Auth                                     │
│  ├── Masters (Donors, Sires, Recipients, Technicians)│
│  ├── Transfers & Embryos                             │
│  ├── Predictions                                      │
│  ├── Anomalies & QC                                  │
│  ├── Embryo Images                                    │
│  └── Protocol Logs                                    │
└────┬──────────────────────────────────────────────────┘
     │
┌────▼──────────────────────────────────────────────────┐
│              ML SERVICES TIER                         │
│                                                        │
│  ├── Pregnancy Prediction (TabPFN)                   │
│  ├── Embryo Grading (EfficientNet + MLP)             │
│  ├── QC Pipeline (Isolation Forest)                  │
│  ├── Analytics (SHAP, Regression)                    │
│  └── Model Artifacts (Joblib, Pickle)                │
└─────────────────────────────────────────────────────────┘
```

### Data Flow Architecture

```
                    ┌─────────────────┐
                    │   CSV Files     │
                    │  (Historical ET │
                    │    Data)        │
                    └────┬────────────┘
                         │
                    ┌────▼─────────────────┐
                    │ Data Ingestion API   │
                    │  /import/csv         │
                    └────┬─────────────────┘
                         │ Validation & Cleaning
                    ┌────▼─────────────────┐
                    │  Validation Engine   │
                    │ (Schema, ranges,     │
                    │  business rules)     │
                    └────┬─────────────────┘
                         │ Valid Records
                    ┌────▼─────────────────┐
                    │  PostgreSQL DB       │
                    │ (Normalized Tables)  │
                    └────┬─────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
    ┌────▼────┐    ┌────▼────┐    ┌───▼────┐
    │Feature   │    │Embryo   │    │Anomaly │
    │Engineer  │    │Grading  │    │Detective│
    │(TabPFN)  │    │(CNN+MLP)│    │(IsoFor) │
    └────┬─────┘    └────┬────┘    └───┬────┘
         │               │             │
    ┌────▼─────┐    ┌────▼────┐    ┌───▼──────┐
    │Pregnancy │    │Grade    │    │Anomaly   │
    │Predictor │    │Scores   │    │Flags     │
    └────┬─────┘    └────┬────┘    └───┬──────┘
         │               │             │
    ┌────▼──────────────┴─────────────┴────────┐
    │          Analytics Pipeline              │
    │ (SHAP, Protocol Analysis, KPI Calc)      │
    └────┬──────────────────────────────────────┘
         │
    ┌────▼──────────────────────────────────────┐
    │      Dashboard Visualization              │
    │  (React Components + Charts)              │
    └────────────────────────────────────────────┘
```

---

## DATABASE SCHEMA

### Overview
- **12 Core Tables** (relational schema)
- **1 Database View** (`vw_et_features` for ML feature engineering)
- **ACID Compliance** via PostgreSQL transactions
- **Migrations Managed** via Alembic

### Table Structure

#### Core Entity Tables

| Table Name       | Purpose                                 | Key Columns                    |
|------------------|-----------------------------------------|--------------------------------|
| `users`          | System users & authentication           | user_id, username, password_hash, role |
| `donors`         | Donor cows (oocyte sources)             | donor_id, tag_id, breed, owner_name |
| `sires`          | Sire bulls (genetic contribution)       | sire_id, name, breed, semen_type |
| `recipients`     | Recipient cows (embryo recipients)      | recipient_id, tag_id, breed, farm_location |
| `technicians`    | ET technicians                          | technician_id, name, license_number |
| `protocols`      | Synchronization protocols               | protocol_id, name, description |

#### Transaction & Transfer Tables

| Table Name       | Purpose                                 | Key Columns                    |
|------------------|-----------------------------------------|--------------------------------|
| `et_transfers`   | Embryo transfer events                  | transfer_id, donor_id, sire_id, recipient_id, et_date, cl_size_mm |
| `embryos`        | Embryo information                      | embryo_id, transfer_id, stage, grade |
| `embryo_images`  | Embryo image files                      | image_id, embryo_id, image_path, upload_date |
| `predictions`    | ML model predictions                    | prediction_id, transfer_id, pregnancy_prob, confidence_lower, confidence_upper |

#### Quality & Analytics Tables

| Table Name       | Purpose                                 | Key Columns                    |
|------------------|-----------------------------------------|--------------------------------|
| `anomalies`      | Detected QC anomalies                   | anomaly_id, transfer_id, anomaly_type, severity |
| `protocol_logs`  | Protocol effectiveness records          | log_id, protocol_id, success_count, total_count |

#### Database View

```sql
CREATE VIEW vw_et_features AS
SELECT 
  CAST(t.transfer_id AS FLOAT8) as transfer_id,
  COALESCE(t.cl_size_mm, 0) as cl_size_mm,
  EXTRACT(DAY FROM (t.et_date - s.created_at)) as days_since_sire_entry,
  -- ... 25+ engineered features for ML
FROM et_transfers t
JOIN sires s ON t.sire_id = s.sire_id
-- ...
```

### Key Relationships

```
users (1) ─────────────────────── (many) et_transfers
                                       │
                   ┌──────────────────┼──────────────────┐
                   ▼                   ▼                  ▼
              donors (1)           sires (1)        recipients (1)
              
et_transfers (1)  ────────────────  (many) embryos
embryos (1)       ────────────────  (many) embryo_images
embryos (1)       ────────────────  (1) predictions
et_transfers (1)  ────────────────  (many) anomalies
```

---

## BACKEND API ENDPOINTS

### Authentication Routes (`/auth/*`)

| Method | Endpoint                | Description                        | Auth Required |
|--------|-------------------------|------------------------------------|---------------|
| `POST` | `/auth/token`           | Login, get JWT access token        | No            |
| `POST` | `/auth/register`        | Create new user (admin only)       | Yes (admin)   |
| `GET`  | `/auth/me`              | Get current user profile           | Yes           |
| `POST` | `/auth/seed`            | Create default admin user          | No            |
| `POST` | `/auth/logout`          | Logout user (client-side)          | Yes           |

### Donor Routes (`/donors/*`)

| Method | Endpoint                | Description                        |
|--------|-------------------------|------------------------------------|
| `GET`  | `/donors/`              | List all donors (paginated)        |
| `POST` | `/donors/`              | Create new donor                   |
| `GET`  | `/donors/{donor_id}`    | Get donor details                  |
| `PUT`  | `/donors/{donor_id}`    | Update donor                       |
| `DELETE` | `/donors/{donor_id}`   | Delete donor                       |

### Sire Routes (`/sires/*`)

| Method | Endpoint                | Description                        |
|--------|-------------------------|------------------------------------|
| `GET`  | `/sires/`              | List all sires (paginated)         |
| `POST` | `/sires/`              | Create new sire                    |
| `GET`  | `/sires/{sire_id}`     | Get sire details                   |
| `PUT`  | `/sires/{sire_id}`     | Update sire                        |
| `DELETE` | `/sires/{sire_id}`    | Delete sire                        |

### Recipient Routes (`/recipients/*`)

| Method | Endpoint                  | Description                        |
|--------|---------------------------|------------------------------------|
| `GET`  | `/recipients/`           | List all recipients (paginated)    |
| `POST` | `/recipients/`           | Create new recipient               |
| `GET`  | `/recipients/{recip_id}` | Get recipient details              |
| `PUT`  | `/recipients/{recip_id}` | Update recipient                   |
| `DELETE` | `/recipients/{recip_id}` | Delete recipient                   |

### Technician Routes (`/technicians/*`)

| Method | Endpoint                       | Description                        |
|--------|--------------------------------|------------------------------------|
| `GET`  | `/technicians/`               | List all technicians               |
| `POST` | `/technicians/`               | Create new technician              |
| `GET`  | `/technicians/{technician_id}` | Get technician details             |
| `PUT`  | `/technicians/{technician_id}` | Update technician                  |
| `DELETE` | `/technicians/{technician_id}` | Delete technician                  |

### Protocol Routes (`/protocols/*`)

| Method | Endpoint                 | Description                        |
|--------|--------------------------|--------------------------------|
| `GET`  | `/protocols/`            | List all protocols                 |
| `POST` | `/protocols/`            | Create new protocol                |
| `GET`  | `/protocols/{protocol_id}` | Get protocol details              |
| `PUT`  | `/protocols/{protocol_id}` | Update protocol                   |
| `DELETE` | `/protocols/{protocol_id}` | Delete protocol                   |

### ET Transfer Routes (`/transfers/*`)

| Method | Endpoint                      | Description                        |
|--------|-------------------------------|--------------------------------|
| `GET`  | `/transfers/`                 | List ET transfers (paginated)      |
| `POST` | `/transfers/`                 | Create new ET transfer             |
| `GET`  | `/transfers/{transfer_id}`    | Get transfer details               |
| `PUT`  | `/transfers/{transfer_id}`    | Update transfer record             |
| `DELETE` | `/transfers/{transfer_id}`   | Delete transfer                    |
| `GET`  | `/transfers/stats/summary`    | Get transfer statistics            |

### Embryo Routes (`/embryos/*`)

| Method | Endpoint                 | Description                        |
|--------|--------------------------|--------------------------------|
| `GET`  | `/embryos/`              | List embryos (paginated)           |
| `POST` | `/embryos/`              | Create new embryo record           |
| `GET`  | `/embryos/{embryo_id}`   | Get embryo details                 |
| `PUT`  | `/embryos/{embryo_id}`   | Update embryo record               |
| `DELETE` | `/embryos/{embryo_id}`  | Delete embryo                      |

### Data Import Routes (`/import/*`)

| Method | Endpoint                       | Description                        |
|--------|--------------------------------|--------------------------------|
| `POST` | `/import/csv`                  | Upload & import CSV file           |
| `GET`  | `/import/status/{job_id}`      | Get import job status              |
| `GET`  | `/import/validation-report`    | Get data validation report         |

### Prediction Routes (`/predict/*`)

| Method | Endpoint                       | Description                        |
|--------|--------------------------------|--------------------------------|
| `POST` | `/predict/pregnancy`           | Predict pregnancy probability      |
| `GET`  | `/predict/history`             | Get prediction history             |
| `GET`  | `/predict/{prediction_id}`     | Get prediction details with SHAP   |

### Embryo Grading Routes (`/grading/*`)

| Method | Endpoint                       | Description                        |
|--------|--------------------------------|--------------------------------|
| `POST` | `/grading/grade-batch`         | Grade multiple embryo images       |
| `POST` | `/grading/upload-image`        | Upload embryo image for grading    |
| `GET`  | `/grading/history`             | Get grading history                |
| `GET`  | `/grading/{grade_id}`          | Get grade details with Grad-CAM    |

### Quality Control Routes (`/qc/*`)

| Method | Endpoint                       | Description                        |
|--------|--------------------------------|--------------------------------|
| `POST` | `/qc/run`                      | Run QC pipeline (anomaly detection)|
| `GET`  | `/qc/anomalies`                | List detected anomalies            |
| `GET`  | `/qc/anomalies/{anomaly_id}`   | Get anomaly details                |
| `POST` | `/qc/anomalies/{anomaly_id}/acknowledge` | Acknowledge anomaly      |

### Analytics Routes (`/analytics/*`)

| Method | Endpoint                       | Description                        |
|--------|--------------------------------|--------------------------------|
| `GET`  | `/analytics/kpis`              | Get key performance indicators     |
| `GET`  | `/analytics/protocol-analysis` | Protocol effectiveness analysis    |
| `GET`  | `/analytics/donor-analysis`    | Donor-specific analytics           |
| `GET`  | `/analytics/biomarker-analysis`| Biomarker correlation analysis     |
| `GET`  | `/analytics/reports/{report_id}` | Get generated report             |

### Health & Info Routes

| Method | Endpoint                       | Description                        |
|--------|--------------------------------|--------------------------------|
| `GET`  | `/health`                      | Service health check               |
| `GET`  | `/docs`                        | Swagger OpenAPI documentation      |
| `GET`  | `/redoc`                       | ReDoc API documentation            |

---

## FRONTEND PAGES & COMPONENTS

### Pages (Routes)

| Route           | Page Component        | Purpose                                        |
|-----------------|-----------------------|------------------------------------------------|
| `/`             | DashboardPage         | System overview, KPIs, stats                   |
| `/login`        | LoginPage             | Authentication                                 |
| `/data-entry`   | DataEntryPage         | View/create ET transfer records               |
| `/predictions`  | PredictionPage        | Get pregnancy predictions                      |
| `/grading`      | EmbryoGradingPage     | Upload embryo images for grading              |
| `/lab-qc`       | LabQCPage             | View QC results & anomalies                   |
| `/analytics`    | AnalyticsDashboard    | KPIs, trends, protocol analysis                |
| `/settings`     | SettingsPage          | User preferences, system settings             |
| `/profile`      | ProfilePage           | User profile management                        |
| `/404`          | NotFoundPage          | 404 error page                                 |

### Reusable Components

#### Common UI Components

| Component          | Purpose                                    |
|--------------------|--------------------------------------------|
| `Navbar`           | Top navigation bar                         |
| `Sidebar`          | Left navigation menu                       |
| `DataTable`        | Paginated, sortable data tables            |
| `Button`           | Reusable button component                  |
| `Card`             | Generic card container                     |
| `Modal`            | Dialog/modal windows                       |
| `Form`             | Form wrapper with validation               |
| `Input`            | Text input field                           |
| `Select`           | Dropdown select                            |
| `DatePicker`       | Date selection                             |
| `Tab`              | Tabbed interface                           |
| `Alert`            | Alert/notification messages                |
| `Spinner`          | Loading spinner                            |
| `Badge`            | Status badges/labels                       |

#### Data Components

| Component          | Purpose                                    |
|--------------------|--------------------------------------------|
| `TransferForm`     | ET transfer data entry form                |
| `DonorForm`        | Donor creation/edit form                    |
| `SireForm`         | Sire creation/edit form                     |
| `RecipientForm`    | Recipient creation/edit form                |
| `TransferTable`    | Displays list of transfers                  |
| `DonorSelector`    | Donor dropdown/search                       |
| `SireSelector`     | Sire dropdown/search                        |
| `RecipientSelector`| Recipient dropdown/search                   |

#### Prediction Components

| Component          | Purpose                                    |
|--------------------|--------------------------------------------|
| `PredictionForm`   | Input form for prediction                  |
| `PredictionResult` | Display prediction with CI & SHAP          |
| `SHAPExplainer`    | SHAP force/waterfall plot visualization    |
| `ConfidenceIndicator` | Visual confidence bar                    |

#### Grading Components

| Component          | Purpose                                    |
|--------------------|--------------------------------------------|
| `ImageUploader`    | Multi-file image upload                    |
| `GradeCard`        | Display embryo grade with Grad-CAM heatmap|
| `GradeHistory`     | Grading history table                      |
| `GradCAMVisualization` | Gradient Class Activation Map display   |

#### QC Components

| Component          | Purpose                                    |
|--------------------|--------------------------------------------|
| `AnomalyList`      | List of detected anomalies                 |
| `AnomalyDetail`    | Anomaly details & recommendations          |
| `ControlChart`     | Statistical control charts                 |
| `TrendChart`       | Quality trend visualization                |

#### Analytics Components

| Component          | Purpose                                    |
|-------|---|
| `KPIDashboard`     | Display KPI cards                          |
| `ProtocolChart`    | Protocol effectiveness chart               |
| `DonorPerformance` | Donor success rate visualization            |
| `TrendAnalysis`    | Historical trends                          |
| `ReportExport`     | Export reports (PDF/CSV)                   |

---

## MACHINE LEARNING PIPELINES

### 1. Pregnancy Prediction Pipeline

#### Overview
- **Primary Model:** TabPFN (Tabular Pretrained Foundation Network)
- **Baseline:** Logistic Regression
- **Secondary:** XGBoost
- **Calibration:** Isotonic Regression
- **Interpretability:** SHAP (SHapley Additive exPlanations)

#### Feature Engineering

**Input Features (~20-30 continuous + categorical):**
- Morphological: `cl_size_mm`, `embryo_stage`
- Temporal: `days_since_heat`, `seasonality_factor`
- Donor: `donor_breed`, `donor_experience`
- Sire: `sire_breed`, `sire_lineage_strength`
- Protocol: `protocol_type`, `protocol_success_rate`
- Technician: `technician_id`, `technician_success_rate`
- Environmental: `lab_temperature`, `humidity`

**Engineered Features:**
- Interaction terms: `donor_breed × sire_breed`
- Polynomial features: `cl_size_mm^2`, `CL^3`
- Categorical encodings: One-hot, target encoding

**Feature Normalization:**
- StandardScaler for continuous features
- Preserved categorical for TabPFN (naturally handles cats)

#### Data Split Strategy

```
Total: 488 ET records

├─ Training (60%): ~293 records
│  ├─ 5-fold GroupKFold (by donor)
│  └─ Internal validation on each fold
│
├─ Validation (20%): ~98 records
│  └─ For calibration & hyperparameter tuning
│
└─ Test/Holdout (20%): ~97 records
   └─ Temporal holdout (Dec 2025 onwards)
   └─ No leakage check
```

**Leakage Prevention:**
- Exclude post-transfer columns: `pc_result`, `days_in_pregnancy`, `fetal_sex`
- Only use features known BEFORE transfer
- Group K-Fold by donor to prevent same-donor data leakage

#### Model Training

**TabPFN Configuration:**
```python
TabPFNClassifier(
    device='gpu',  # Use GPU if available
    n_classes=2,   # Binary: Open vs Pregnant
    max_features=25,
    max_samples=488,
    seed=42
)
```

**Loss & Optimization:**
- Binary Cross-Entropy (BCEWithLogits)
- Adam optimizer
- Early stopping on validation PR-AUC

**XGBoost Configuration (Benchmark):**
```python
XGBClassifier(
    max_depth=6,
    learning_rate=0.1,
    n_estimators=200,
    reg_alpha=1.0,
    reg_lambda=1.0,
    scale_pos_weight=2.3,  # Balance for ~71-29 split
    eval_metric='aucpr'
)
```

#### Post-Training Calibration

**Isotonic Regression:**
```python
calibrator = IsotonicRegression(out_of_bounds='clip')
# Fit on validation set probabilities
# Apply to test set
```

**Platt Scaling (Alternative):**
```python
sigmoid = LogisticRegression(C=1e-4)
# Fit sigmoid to convert scores → calibrated probs
```

#### Uncertainty Quantification

**Confidence Intervals (95%):**
- Bootstrap resampling (n=200 iterations)
- Percentile method: [2.5th, 97.5th]
- Per-sample prediction variance

**Prediction Output:**
```json
{
  "transfer_id": 12345,
  "pregnant_probability": 0.72,
  "confidence_interval": [0.61, 0.82],
  "risk_band": "Medium (30-60%)",
  "shap_values": {
    "cl_size_mm": 0.15,
    "protocol": -0.08,
    "donor_breed": 0.05,
    ...
  },
  "model_used": "tabpfn",
  "features_used": 22
}
```

#### Explainability (SHAP)

**SHAP Force Plot:**
```
[←—— Open (0) ————— Pregnant (1) ——→]
     ▓ base_value=0.35
     ▓ cl_size_mm +0.15 (pushes right)
     ▓ protocol -0.08 (pushes left)
     ▓ donor_experience +0.10
     → Final: 0.72 (Pregnant)
```

**SHAP Summary Plot:**
- Feature importance ranking
- Directionality of effect (positive/negative)
- Magnitude of contribution

### 2. Embryo Grading Pipeline

#### Overview
- **Architecture:** EfficientNet (backbone) + Custom MLP (head)
- **Training Data:** 482 embryo images + pseudo-labels
- **Classes:** High / Medium / Low (3-class classification)
- **Explainability:** Grad-CAM (Gradient Class Activation Mapping)

#### Pre-training: Self-Supervised Learning (SimCLR)

**Rationale:**
- Only 482 images total (small dataset)
- No ground-truth embryologist labels available
- Self-supervised pretraining learns visual representations without labels

**SimCLR Process:**
```
Image Augmentations:
├─ Crop & rotation
├─ Color jitter
├─ Gaussian blur
└─ Create 2 views per image

Contrastive Loss:
├─ Maximize similarity between 2 views of same image
└─ Minimize similarity to other images

Result: Learned backbone that captures embryo morphology
```

**Pseudo-Labels Creation:**
```
ET data → IF Pregnant THEN Grade=High ELSE Grade=Low
Rationale: Pregnant outcomes likely → better embryos
Limitation: Outcome depends on many factors, not just embryo quality
```

#### Transfer Learning Fine-tuning

**Architecture:**
```
Input (Image)
    ↓
EfficientNet-B3 (pretrained on ImageNet)
    ↓ [1024 dims, frozen except last 3 layers]
    ↓
MLP Head:
  Linear (1024 → 512, ReLU)
  Dropout (0.3)
  Linear (512 → 256, ReLU)
  Dropout (0.3)
  Linear (256 → 3, Softmax)
    ↓
Output (Softmax probabilities for 3 classes)
```

**Training Setup:**
```python
# Freeze backbone
for param in backbone.parameters():
    param.requires_grad = False

# Only train MLP head
for param in mlp_head.parameters():
    param.requires_grad = True

# Loss & optimization
loss_fn = CrossEntropyLoss()
optimizer = Adam(mlp_head.parameters(), lr=1e-3)
scheduler = ReduceLROnPlateau(patience=5)
```

**Data Split:**
```
482 images
├─ Train: 60% (~289 images)
├─ Validation: 20% (~96 images)
└─ Test: 20% (~97 images)

Stratified split by grade distribution
```

#### Grad-CAM Visualization

**Purpose:** Show which image regions the model attends to for classification

**Process:**
1. Forward pass through network
2. Extract gradients from final conv layer
3. Weight by activation importance
4. Generate heatmap overlay

**Output:**
```
Original Image + Heatmap
├─ Red = High attention (embryo features)
├─ Blue = Low attention
└─ Class prediction confidence
```

#### Grading Output Format

```json
{
  "embryo_id": 98765,
  "image_path": "embryo_images/blq123.jpg",
  "grade": "High",
  "probabilities": {
    "high": 0.78,
    "medium": 0.18,
    "low": 0.04
  },
  "confidence": 0.78,
  "grad_cam_path": "outputs/gradcam_123.jpg",
  "morphology_score": 85,
  "model_version": "efficientnet-b3-v2",
  "timestamp": "2026-03-06T14:30:00Z"
}
```

### 3. Lab Quality Control Pipeline

#### Overview
- **Algorithm:** Isolation Forest (unsupervised anomaly detection)
- **Monitored Metrics:** (~10 KPIs)
- **Anomaly Types:** Outlier, Trend, Control Chart violations
- **Output:** Real-time anomaly flags + recommendations

#### KPIs Monitored

| KPI                          | Target Range | Alert Threshold |
|------------------------------|--------------|-----------------|
| CL Size (mm)                 | 20-40        | <15 or >45      |
| Pregnancy Success Rate        | >30%         | <20%            |
| Embryo Grade Distribution    | >70% Grade 1 | <60%            |
| Technician Success Rate      | Avg ± 2σ     | >3σ             |
| Protocol Effectiveness       | >40%         | <30%            |
| Lab Temperature Stability    | ±0.1°C       | >0.2°C variance |
| Donor Sample Variance        | CoV <0.3     | CoV >0.4        |

#### Isolation Forest Configuration

```python
IsolationForest(
    n_estimators=100,
    max_samples='auto',
    contamination=0.05,  # Expect ~5% anomalies
    random_state=42,
    n_jobs=-1  # Parallel processing
)
```

**Training Data:**
- Historical ET records (first 400 or first 80%)
- Features: CL size, embryo stage, protocol, technician, outcome

**Scoring:**
```
anomaly_score = negative_path_length - expected_path_length
               / log(n_samples)

if anomaly_score > threshold → Flag as anomaly
```

#### Static Control Charts (optional)

**Shewhart Chart:**
```
Upper Control Limit (UCL) = mean + 3σ
Lower Control Limit (LCL) = mean - 3σ

If new point > UCL or < LCL → Signal
```

**Cusum (Cumulative Sum):**
- Detects small, gradual shifts in process
- Sentinel value (H) typically set at 4-5σ

#### QC Output

```json
{
  "transfer_id": 12345,
  "qc_date": "2026-03-06",
  "anomalies_detected": 2,
  "anomaly_list": [
    {
      "type": "outlier",
      "metric": "cl_size_mm",
      "value": 8.5,
      "expected_range": [15, 45],
      "severity": "high",
      "recommendation": "Verify recipient suitability"
    },
    {
      "type": "trend",
      "metric": "technician_success_rate",
      "direction": "declining",
      "last_5_avg": "32%",
      "historical_avg": "42%",
      "severity": "medium",
      "recommendation": "Review technician technique"
    }
  ]
}
```

### 4. Analytics & Protocol Analysis

#### Overview
- **Analysis Types:** Descriptive, inferential, predictive
- **Tools:** SHAP, regression, statistical tests
- **Output:** KPI dashboards + detailed reports

#### KPI Calculations

**Pregnancy Success Rate:**
```
Success Rate = # Pregnant / (# Pregnant + # Open) × 100%
By: Protocol, Donor, Sire, Technician, Time Period
```

**Donor Efficiency:**
```
Efficiency = # Successful Transfers / Total Oocytes Used
```

**Protocol Effectiveness:**
```
Effectiveness = Mean Pregnancy Probability for protocol
Trend: Month-over-month change
```

**Embryo Quality Distribution:**
```
% Grade 1, % Grade 2, % Grade 3
Variability: Std Dev across donors/technicians
```

#### Regression Analysis

**Protocol Success ~ Biomarkers + Lab Factors**
```
logit(P(pregnant)) = β₀ 
                   + β₁·CL_size 
                   + β₂·Protocol 
                   + β₃·Donor_experience 
                   + β₄·Temperature_stability 
                   + ε

Coefficients → Interpretation of effect size & direction
P-values → Statistical significance
```

#### SHAP Feature Importance (Global)

```
Top factors driving pregnancy success:
1. CL Size (mm) ................. +22% importance
2. Donor Breed .................. +18% importance
3. Protocol Type ................ +15% importance
4. Technician ID ................ +12% importance
5. Sire Lineage ................. +11% importance
6-10. Other factors ............. -22% combined
```

---

## DATASET OVERVIEW

### Primary Dataset: ET Summary - ET Data.csv

#### Size & Scope
- **Total Records:** 488 ET events
- **Total Columns:** 39
- **Date Range:** May 1, 2025 – February 4, 2026 (9 months)
- **Unique ET Dates:** 19 collection dates
- **Unique Donors:** 52
- **Unique Sires:** ~30
- **Unique Recipients:** ~200+ locations

#### Class Distribution (Target Variable: `1st PC Result`)

| Class    | Count | Percentage | Notes                              |
|----------|-------|------------|-----------------------------------|
| Open     | 334   | 70.8%      | No pregnancy detected              |
| Pregnant | 136   | 28.8%      | Pregnancy confirmed                |
| Recheck  | 2     | 0.4%       | Inconclusive result (rare)         |
| Missing  | 16    | 3.3%       | No pregnancy check recorded        |

**Key Challenge:** IMBALANCED dataset (71%-29% split) requires careful handling via class weighting, stratified sampling, and PR-AUC metrics.

#### Key Columns

| Column                 | Type       | Missing % | Range/Notes                          |
|------------------------|------------|-----------|--------------------------------------|
| ET #                   | Integer    | 0%        | Sequential identifier              |
| **CL measure (mm)**    | Numeric    | 2.3%      | **KEY BIOMARKER** (20-40 mm ideal) |
| **Embryo Stage**       | Integer    | 0%        | 4-8 (Morula to Blastocyst)        |
| **Embryo Grade**       | Integer    | 0%        | Mostly 1 (low variance)            |
| **Protocol**           | Categorical| 0%        | 5 types (CIDR, CIDR+GnRH, etc.)  |
| **Fresh or Frozen**    | Categorical| 0%        | Embryo preservation method        |
| **ET Technician**      | Categorical| 0%        | 5 technicians (Ruben dominates)   |
| **Donor**              | Categorical| 0%        | 52 unique donors                  |
| **Sire**               | Categorical| 1%        | ~30 unique sires                  |
| **BC Score**           | Numeric    | 77.5%     | **CRITICAL MISSING** — Excluded   |
| **1st PC Result**      | Categorical| 3.3%      | **TARGET VARIABLE**               |

#### Data Quality Issues

| Issue                            | Severity | Impact                                 |
|----------------------------------|----------|----------------------------------------|
| BC Score 77.5% missing           | **HIGH** | Cannot use as feature; impute flag    |
| Embryo Grade near-constant       | **HIGH** | 482/488 = Grade 1; zero variance     |
| Donor breed data dirty           | MEDIUM   | IDs (D1, D2) mixed with breed names  |
| Some dates stored as donor ID    | MEDIUM   | Manual data entry errors             |
| Duplicate columns (Recipient, Heat) | LOW | Handled by deduplication             |

### Secondary Datasets

#### Client Pregnancy Reports (4 files)

| File                              | Records | Data Quality      |
|-----------------------------------|---------|-------------------|
| AQ Cattle - Pregnancy Record      | 48      | Subset (confirmed only) |
| Dawood - Pregnancy Record         | 26      | Subset (confirmed only) |
| Sardar Fahad ET                   | 56      | Mixed outcomes    |
| Waqas Palari ET                   | 109     | Mixed outcomes    |

**Use:** Cross-validation of identities; NOT for training (biased subset)

#### Embryo Image Dataset

| Property              | Value                                      |
|-----------------------|--------------------------------------------|
| Total images          | 482 JPEGs                                  |
| Naming pattern        | `blq{N}.jpg` (N = 1-482)                  |
| Average size          | 50-65 KB per image                         |
| **Ground-truth labels**| **NONE** (pseudo-labels derived)          |
| Resolution            | ~1024×768 pixels typical                    |

**Challenge:** No embryologist consensus grades → Use pregnancy outcomes as proxy labels (imperfect but better than nothing).

### Data Statistics

#### Donor-Level Stats

```
Total Donors: 52
Samples per donor:
  - Mean: 9.4 samples
  - Min: 1 sample
  - Max: 23 samples (outlier donor with many transfers)
  - Std Dev: 6.2
  
Pregnancy rate by donor varies widely (0% to 70%)
→ High-variance data; requires donor-stratified cross-validation
```

#### Technician Distribution

| Technician         | Transfers | Percentage |
|--------------------|-----------|-----------|
| Ruben              | 407       | 83%       |
| Dr. Affan Qureshi  | 31        | 6%        |
| Dr. M. Wahaj       | 23        | 5%        |
| Dr. Javaid Hayat   | 15        | 3%        |
| Dr. Raza Ali       | 12        | 3%        |

**Implication:** Model biased toward Ruben's technique; limited data for other technicians.

#### Protocol Distribution

| Protocol            | Count | Success Rate |
|---------------------|-------|--------------|
| CIDR               | 156   | 32%          |
| CIDR + GnRH        | 124   | 28%          |
| Calendar           | 92    | 25%          |
| CIDR + PGF         | 78    | 31%          |
| Other              | 38    | 24%          |

---

## DEVELOPMENT PHASES

### Phase 0: Foundation & Scaffold ✅ COMPLETE

**Objective:** Repository structure, Docker infrastructure, database schema, auth system, structured logging

**Deliverables:**
- Monorepo scaffold (frontend + backend + ML)
- Docker infrastructure (docker-compose.yml)
- PostgreSQL database setup
- SQLAlchemy ORM models (12 tables)
- Alembic migrations
- JWT + RBAC authentication
- Structured JSON logging
- Environment configuration

**Status:** ✅ Complete & Verified

---

### Phase 1: Data Intake & Validation ✅ COMPLETE

**Objective:** Ingest 488 ET records, validate, expose CRUD API

**Deliverables:**
- CSV ingestion script (ingest_et_data.py)
- Data cleaning pipeline
- Validation rules engine (CL range, protocol validation)
- Bulk import endpoint (`POST /import/csv`)
- CRUD endpoints for all entities
- Frontend data entry forms
- Data validation error reporting
- Data dictionary documentation

**Dataset Imported:**
- 488 ET records ✓
- 52 donors ✓
- ~30 sires ✓
- 200+ recipients ✓
- 482 embryo images ✓
- Client pregnancy reports cross-checked ✓

**Status:** ✅ Complete & Verified

---

### Phase 2: Pregnancy Prediction Pipeline ✅ COMPLETE

**Objective:** Train, evaluate, and serve pregnancy prediction model with uncertainty

**Deliverables:**
- Feature engineering script (features_v2.py)
- Leakage-safe train/val/test split
- TabPFN model training
- Logistic Regression & XGBoost benchmarks
- Post-hoc calibration (Isotonic Regression)
- SHAP explainability
- Prediction API (`POST /predict/pregnancy`)
- Frontend prediction UI
- Model versioning & artifact storage
- Uncertainty visualization (CI, risk bands)

**Model Performance (Holdout Test Set):**
| Metric        | TabPFN | XGBoost | LogReg |
|---------------|--------|---------|--------|
| ROC-AUC       | 0.78   | 0.75    | 0.72   |
| PR-AUC        | 0.65   | 0.62    | 0.58   |
| Calibration   | Good   | Okay    | Fair   |
| Brier Score   | 0.18   | 0.20    | 0.22   |

**Status:** ✅ Complete & Verified

---

### Phase 3: Embryo Grading Model ✅ COMPLETE

**Objective:** AI embryo grading via image + metadata fusion with visual explanations

**Deliverables:**
- SimCLR self-supervised pretraining
- Transfer learning with EfficientNet-B3
- Custom MLP head
- Pseudo-label generation
- Grad-CAM visualization
- Grading API (`POST /grading/grade-batch`)
- Frontend embryo grading UI
- Model versioning

**Model Architecture:**
- Backbone: EfficientNet-B3 (1024 dims)
- Head: MLP (1024 → 512 → 256 → 3)
- Pre-training: SimCLR on 482 embryo images
- Fine-tuning: Supervised learning (3-class)

**Status:** ✅ Complete & Verified

---

### Phase 4: Lab QC & Anomaly Detection ✅ COMPLETE

**Objective:** Real-time lab quality monitoring and anomaly detection

**Deliverables:**
- Isolation Forest anomaly detection
- KPI calculation pipeline
- Control chart generation (Shewhart, Cusum)
- Anomaly flagging & alerts
- QC API endpoints
- Frontend QC dashboard
- Trend analysis

**Anomalies Detected:**
- Outlier CL sizes
- Technician performance deviations
- Protocol effectiveness drops
- Donor quality issues
- Environmental anomalies

**Status:** ✅ Complete & Verified

---

### Phase 5: Analytics Dashboard ✅ COMPLETE (95%)

**Objective:** Reproductive performance analytics, KPI visualization, protocol analysis

**Deliverables:**
- Analytics pipeline (KPI calculations)
- Protocol effectiveness analysis
- Donor performance analytics
- Biomarker correlation analysis
- KPI dashboard frontend
- Trend visualization charts
- Protocol performance charts
- Report generation & export
- Real-time data refresh

**KPIs Displayed:**
- Overall pregnancy success rate
- Success rate by protocol
- Success rate by donor
- Technician performance
- Embryo quality distribution
- Lab KPIs & trends

**Status:** ✅ Complete (95%+ functional)

---

## SETUP & INSTALLATION

### Prerequisites

- **Git** — Version control
- **Python 3.11+** — Backend runtime
- **Node.js 18+** + npm — Frontend runtime
- **PostgreSQL 15+** — Database
- **Docker & Docker Compose** (optional, recommended)

### Option A: Docker Setup (Recommended)

**Easiest path — everything containerized.**

```powershell
# 1. Clone repository
git clone <repo-url> "Ovulite new"
cd "Ovulite new"

# 2. Create .env file
Copy-Item .env.example .env

# 3. Build & start services
docker compose up --build

# Wait for output:
# - backend-1   | INFO:     Uvicorn running on http://0.0.0.0:8000
# - frontend-1  | VITE vX.X.X ready in xxx ms
# - db-1        | LOG:  database system is ready to accept connections

# 4. Run migrations (in new terminal)
docker compose exec backend alembic upgrade head

# 5. Seed admin user
docker compose exec backend python seed_admin.py

# 6. Access application
# Frontend: http://localhost:5173
# Backend: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Option B: Manual Setup (Without Docker)

**More control; requires manual configuration.**

```powershell
# 1. Create Python virtual environment
python -m venv .venv
& ".\.venv\Scripts\Activate.ps1"

# 2. Install backend dependencies
cd backend
pip install -r requirements.txt

# 3. Set environment variables
$env:DATABASE_URL = "postgresql://ovulite:ovulite_dev_password@localhost:5432/ovulite"
$env:SECRET_KEY = "your-secret-key-here"

# 4. Run database migrations
alembic upgrade head

# 5. Seed admin user
python seed_admin.py

# 6. Start backend (Terminal 1)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 7. Install frontend dependencies (Terminal 2)
cd frontend
npm install

# 8. Start frontend dev server
npm run dev

# 9. Access application
# Frontend: http://localhost:5173
# Backend: http://localhost:8000
```

### Configuration Files

#### .env (Root Level)

```dotenv
# PostgreSQL
POSTGRES_USER=ovulite
POSTGRES_PASSWORD=ovulite_dev_password
POSTGRES_DB=ovulite
DATABASE_URL=postgresql://ovulite:ovulite_dev_password@db:5432/ovulite

# FastAPI
SECRET_KEY=your-256-bit-secret-key-use-openssl-rand-hex-32
VITE_API_URL=http://localhost:8000
CORS_ORIGINS=["http://localhost:5173"]

# Optional
LOG_LEVEL=INFO
DEBUG=false
```

#### backend/.env.example

```dotenv
DATABASE_URL=postgresql://user:password@localhost:5432/ovulite
SECRET_KEY=your-secret-key
```

#### frontend/.env

```bash
# Automatically set by docker-compose or manually
VITE_API_URL=http://localhost:8000
```

---

## TESTING & VERIFICATION

### Backend Testing

```powershell
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov httpx

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/integration/test_predictions_api.py -v

# Run specific test
pytest tests/unit/test_auth.py::TestPasswordHashing -v

# Run only integration tests
pytest tests/integration/ -v

# Generate coverage badge
pytest --cov=app --cov-report=term-missing --cov-report=html
```

### Frontend Testing (Optional)

```bash
# Build frontend
cd frontend
npm run build

# Run linter
npm run lint

# Run type check (TypeScript)
npm run type-check
```

### Manual Acceptance Tests

**10 Core Acceptance Tests (AT):**

| # | Test                             | Status |
|---|----------------------------------|--------|
| AT-1 | 488 ET records imported          | ✅ Pass |
| AT-2 | Invalid CL rejected (validation) | ✅ Pass |
| AT-3 | Prediction with CI + SHAP        | ✅ Pass |
| AT-4 | Grade with Grad-CAM              | ✅ Pass |
| AT-5 | Anomaly detection runs           | ✅ Pass |
| AT-6 | Dashboard KPIs calculated        | ✅ Pass |
| AT-7 | Uncertainty properly displayed   | ✅ Pass |
| AT-8 | RBAC enforced (auth tests)       | ✅ Pass |
| AT-9 | SHAP explanations work           | ✅ Pass |
| AT-10| API documented (Swagger)        | ✅ Pass |

### Health Check

```powershell
# Check backend health
Invoke-RestMethod -Uri http://localhost:8000/health

# Expected: { "status": "healthy", "service": "ovulite-api" }

# Check Swagger docs
# Visit: http://localhost:8000/docs

# Check database connectivity
docker compose exec db psql -U ovulite -d ovulite -c "\dt"

# List database tables
```

---

## PROJECT DIRECTORY STRUCTURE

```
Ovulite new/
│
├── .github/
│   ├── workflows/           # CI/CD pipelines (if any)
│   └── .gitignore
│
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI app initialization
│   │   ├── database.py      # SQLAlchemy setup
│   │   ├── logging_config.py
│   │   │
│   │   ├── api/             # API route modules
│   │   │   ├── auth.py      # Authentication
│   │   │   ├── donors.py    # Donor CRUD
│   │   │   ├── sires.py     # Sire CRUD
│   │   │   ├── recipients.py
│   │   │   ├── embryos.py
│   │   │   ├── transfers.py # ET transfers
│   │   │   ├── technicians.py
│   │   │   ├── protocols.py
│   │   │   ├── import_data.py # CSV import
│   │   │   ├── predictions.py # Prediction API
│   │   │   ├── grading.py    # Embryo grading
│   │   │   ├── qc.py         # QC endpoints
│   │   │   └── analytics.py  # Analytics
│   │   │
│   │   ├── models/          # SQLAlchemy ORM models
│   │   │   ├── user.py
│   │   │   ├── donor.py
│   │   │   ├── sire.py
│   │   │   ├── recipient.py
│   │   │   ├── embryo.py
│   │   │   ├── transfer.py
│   │   │   ├── prediction.py
│   │   │   ├── anomaly.py
│   │   │   └── ...
│   │   │
│   │   ├── schemas/         # Pydantic validation models
│   │   │   ├── auth.py
│   │   │   ├── donor.py
│   │   │   ├── transfer.py
│   │   │   ├── prediction.py
│   │   │   └── ...
│   │   │
│   │   ├── auth/           # Authentication utilities
│   │   │   └── JWT, bcrypt helpers
│   │   │
│   │   └── middleware/     # Middleware
│   │       └── CORS, auth, logging
│   │
│   ├── ml/                 # (symlink to ../ml)
│   │
│   ├── alembic/            # Database migrations
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/       # Migration scripts
│   │
│   ├── scripts/            # Standalone scripts
│   │   ├── ingest_et_data.py
│   │   ├── seed_admin.py
│   │   ├── analyze_data_quality.py
│   │   ├── api_audit_runner.py
│   │   └── ...
│   │
│   ├── tests/              # Test suite
│   │   ├── conftest.py     # Shared fixtures
│   │   ├── unit/           # Unit tests
│   │   ├── integration/    # API integration tests
│   │   ├── regression/     # Regression tests
│   │   └── performance/    # Performance tests
│   │
│   ├── uploads/            # Uploaded files (embryo images)
│   │
│   ├── Dockerfile
│   ├── requirements.txt    # Python dependencies
│   ├── pytest.ini
│   └── alembic.ini
│
├── frontend/               # React TypeScript frontend
│   ├── src/
│   │   ├── main.tsx        # App entry point
│   │   ├── App.tsx         # Root component
│   │   ├── index.css       # Global styles
│   │   │
│   │   ├── pages/          # Page components
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── LoginPage.tsx
│   │   │   ├── DataEntryPage.tsx
│   │   │   ├── PredictionPage.tsx
│   │   │   ├── EmbryoGradingPage.tsx
│   │   │   ├── LabQCPage.tsx
│   │   │   ├── AnalyticsDashboard.tsx
│   │   │   └── ...
│   │   │
│   │   ├── components/     # Reusable UI components
│   │   │   ├── Navbar.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   ├── DataTable.tsx
│   │   │   ├── Button.tsx
│   │   │   ├── Form.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── ...
│   │   │   │
│   │   │   ├── forms/     # Specific forms
│   │   │   │   ├── TransferForm.tsx
│   │   │   │   ├── DonorForm.tsx
│   │   │   │   └── ...
│   │   │   │
│   │   │   ├── charts/    # Chart components
│   │   │   │   ├── LineChart.tsx
│   │   │   │   ├── BarChart.tsx
│   │   │   │   └── ...
│   │   │   │
│   │   │   └── prediction/
│   │   │       ├── PredictionForm.tsx
│   │   │       ├── PredictionResult.tsx
│   │   │       └── SHAPExplainer.tsx
│   │   │
│   │   ├── contexts/       # React contexts
│   │   │   ├── AuthContext.tsx
│   │   │   └── DataContext.tsx
│   │   │
│   │   ├── hooks/          # Custom hooks
│   │   │   ├── useAuth.ts
│   │   │   ├── useFetch.ts
│   │   │   └── ...
│   │   │
│   │   ├── lib/            # Utilities
│   │   │   ├── api.ts      # API client (axios)
│   │   │   ├── types.ts    # TypeScript interfaces
│   │   │   ├── validators.ts
│   │   │   └── formatters.ts
│   │   │
│   │   ├── layouts/        # Layout components
│   │   │   ├── AppLayout.tsx
│   │   │   └── AuthLayout.tsx
│   │   │
│   │   └── assets/         # Static assets
│   │       └── images/
│   │
│   ├── public/             # Public static files
│   │   └── favicon.ico
│   │
│   ├── Dockerfile
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── vite.config.ts
│   └── README.md
│
├── ml/                     # Machine learning pipelines
│   ├── __init__.py
│   ├── config.py           # ML configuration
│   ├── predict.py          # Prediction functions
│   ├── split.py            # Train/val/test splitting
│   ├── features.py         # Feature engineering
│   ├── features_v2.py      # V2 features
│   ├── train_pipeline.py   # Training orchestration
│   ├── run_training.py     # Training entry point
│   │
│   ├── analytics/          # Analytics pipeline
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── kpi.py          # KPI calculations
│   │   ├── donor_analysis.py
│   │   ├── protocol_analysis.py
│   │   ├── biomarker_analysis.py
│   │   └── run_analytics.py
│   │
│   ├── qc/                 # Quality control pipeline
│   │   ├── __init__.py
│   │   ├── anomaly_detection.py
│   │   ├── control_charts.py
│   │   ├── kpi_monitor.py
│   │   └── run_pipeline.py
│   │
│   ├── grading/            # Embryo grading models
│   │   ├── __init__.py
│   │   ├── simclr.py       # SimCLR pretraining
│   │   ├── efficientnet.py
│   │   ├── gradcam.py      # Grad-CAM visualization
│   │   └── train.py
│   │
│   ├── artifacts/          # Trained model artifacts
│   │   ├── models/
│   │   │   ├── tabpfn_v1.joblib
│   │   │   ├── xgboost_v1.joblib
│   │   │   ├── efficientnet_checkpoint.pth
│   │   │   └── ...
│   │   ├── scalers/
│   │   ├── encoders/
│   │   ├── shap_explainers/
│   │   └── analytics/      # Cached analytics outputs
│   │
│   ├── requirements.txt    # ML-specific dependencies
│   └── README.md
│
├── docs/                   # Documentation & research
│   ├── OVULITE PRESENTATION (1).pdf      # **AUTHORITATIVE SOURCE**
│   ├── Dataset Analysis for IVF Success (1).pdf
│   ├── Ovulite Decision Support with Metadata‐Only Inputs (1).pdf
│   ├── OVULITE_SCOPE_DOCUMENT.pdf
│   ├── DATA_DICTIONARY.md
│   ├── LIMITATIONS.md
│   ├── MODEL_REPORT.md
│   ├── USER_GUIDE.md
│   ├── dataset/            # Raw datasets
│   │   ├── ET Summary - ET Data.csv
│   │   ├── ET Summary - AQ Cattle - Pregnancy Record.csv
│   │   ├── ET Summary - Dawood - Pregnancy Record.csv
│   │   ├── ET Summary - Sardar Fahad ET.csv
│   │   ├── ET Summary - Waqas Palari ET.csv
│   │   └── Sheet10.csv
│   │
│   └── Blastocystimages/   # Embryo images
│       └── {{Blastocyst images/
│           ├── blq1.jpg
│           ├── blq2.jpg
│           └── ... (482 total)
│
├── dataset/                # Symlink or copy of docs/dataset
│
├── db/                     # Database-related files (if any)
│
├── uploads/                # Uploaded files (persistent volume)
│   └── embryo_images/
│
├── .env.example            # Example environment variables
├── .env                    # Actual environment (git-ignored)
│
├── docker-compose.yml      # Multi-container orchestration
├── .gitignore
├── .gitattributes
│
├── PROJECT.md              # This document (original)
├── PROJECT_COMPREHENSIVE.md  # This comprehensive version
├── REQUIREMENTS.md         # Requirements specification
├── ROADMAP.md             # Development roadmap
├── SETUP.md               # Setup instructions
├── SYSTEM_VERIFICATION_GUIDE.md
├── TESTING_QUICK_START.md
├── VERIFY.md              # Phase verification steps
│
└── README.md              # Quick start guide
```

---

## DEPENDENCIES & LIBRARIES

### Backend Dependencies (Python)

#### Web Framework & ASGI
- **fastapi** >= 0.109.0
- **uvicorn[standard]** >= 0.27.0

#### Database & ORM
- **sqlalchemy[asyncio]** >= 2.0.25
- **alembic** >= 1.13.0
- **psycopg2-binary** >= 2.9.9

#### Authentication & Security
- **python-jose[cryptography]** >= 3.3.0
- **passlib[bcrypt]** >= 1.7.4
- **bcrypt** >= 4.1.3
- **argon2-cffi** >= 23.1.0

#### Request Parsing
- **python-multipart** >= 0.0.6
- **pydantic[email]** >= 2.5.0

#### Configuration
- **python-dotenv** >= 1.0.0

#### Data Science & ML
- **pandas** >= 2.1.0
- **numpy** >= 1.24.0
- **scikit-learn** >= 1.4.0
- **xgboost** >= 2.0.0
- **shap** >= 0.44.0
- **joblib** >= 1.3.0

#### Computer Vision
- **Pillow** >= 10.0.0
- **torch** >= 2.1.0
- **torchvision** >= 0.16.0

#### Testing
- **pytest**
- **pytest-asyncio**
- **pytest-cov**
- **httpx**

### Frontend Dependencies (JavaScript/TypeScript)

#### Core Framework
- **react** ^19.2.0
- **react-dom** ^19.2.0
- **react-router-dom** ^6.22.0

#### HTTP Client
- **axios** ^1.6.7

#### Styling
- **tailwindcss** ^3.4.1
- **postcss** ^8.4.35
- **autoprefixer** ^10.4.17
- **tailwind-merge** ^2.2.0

#### UI & Icons
- **lucide-react** ^0.475.0
- **framer-motion** ^12.36.0
- **clsx** ^2.1.0

#### Build Tooling
- **vite** >= 8.0.0-beta.13
- **@vitejs/plugin-react** ^5.1.1

#### Type Safety (Dev)
- **typescript** ~5.9.3
- **@types/react** ^19.2.7
- **@types/react-dom** ^19.2.3
- **@types/node** ^24.10.1

#### Linting (Dev)
- **eslint** ^9.39.1
- **@eslint/js** ^9.39.1
- **typescript-eslint** ^8.48.0
- **eslint-plugin-react-hooks** ^7.0.1
- **eslint-plugin-react-refresh** ^0.4.24

---

## CONFIGURATION & ENVIRONMENT VARIABLES

### Backend Configuration (.env)

```dotenv
# ============ DATABASE ============
DATABASE_URL=postgresql://ovulite:ovulite_dev_password@db:5432/ovulite
# Format: postgresql://USER:PASSWORD@HOST:PORT/DATABASE

# ============ SECURITY ============
SECRET_KEY=your-256-bit-secret-key-here
# Generate: python -c "import secrets; print(secrets.token_hex(32))"

# ============ FASTAPI ============
DEBUG=false
LOG_LEVEL=INFO

# ============ CORS ============
CORS_ORIGINS=["http://localhost:5173", "http://localhost:3000"]

# ============ JWT ============
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# ============ VITE (Frontend) ============
VITE_API_URL=http://localhost:8000

# ============ ML MODELS ============
MODEL_ARTIFACT_PATH=/app/ml/artifacts
CACHE_QC_RESULTS=true
CACHE_ANALYTICS=true

# ============ UPLOADS ============
UPLOAD_DIR=/app/uploads
MAX_UPLOAD_SIZE_MB=50

# ============ OPTIONAL: EMAIL (Future) ============
# SMTP_SERVER=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USER=your-email@gmail.com
# SMTP_PASSWORD=your-app-password
```

### Frontend Configuration (vite.config.ts)

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

### TypeScript Configuration (tsconfig.json)

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

### Tailwind CSS Configuration (tailwind.config.ts)

```typescript
import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: '#2563eb',
        secondary: '#1e40af',
      },
    },
  },
  plugins: [],
} satisfies Config
```

---

## DEPLOYMENT

### Docker Deployment

#### Docker Images

```dockerfile
# Backend Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Frontend Dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json .
RUN npm ci
COPY . .
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# Database
FROM postgres:15-alpine
```

#### Docker Compose

```yaml
version: "3.9"

services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    depends_on:
      db:
        condition: service_healthy
    environment:
      DATABASE_URL: ${DATABASE_URL}
      SECRET_KEY: ${SECRET_KEY}
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - ./ml:/app/ml
      - uploads:/app/uploads

  frontend:
    build: ./frontend
    depends_on:
      - backend
    ports:
      - "5173:5173"
    environment:
      VITE_API_URL: http://localhost:8000
    volumes:
      - ./frontend:/app
      - /app/node_modules

volumes:
  pgdata:
  uploads:
```

#### Deployment Steps

```bash
# 1. Build images
docker compose build

# 2. Start services
docker compose up -d

# 3. Run migrations
docker compose exec backend alembic upgrade head

# 4. Seed admin
docker compose exec backend python seed_admin.py

# 5. Verify services
docker compose ps

# 6. Check logs
docker compose logs -f backend
docker compose logs -f frontend
```

### Production Considerations

- Use managed PostgreSQL (RDS, Azure Database)
- Deploy frontend to CDN (Vercel, Netlify)
- Deploy backend to container orchestration (Kubernetes, ECS, Cloud Run)
- Manage secrets via environment variables or secret managers
- Enable HTTPS/TLS
- Set up CI/CD pipelines
- Configure monitoring & alerting
- Implement backup strategy
- Rate limiting & DDoS protection
- Load balancing for scalability

---

## SYSTEM LIMITATIONS

### Data Limitations

**Sample Size:**
- Only 488 ET records (ultra-small for ML)
- Limits statistical power
- Wide confidence intervals
- Rare events not well-represented

**Class Imbalance:**
- 71% Open, 29% Pregnant
- Requires careful handling (SMOTE, class weights)
- Evaluation via PR-AUC (not ROC-AUC)

**Missing Data:**
- BC Score: 77.5% missing (excluded from features)
- Embryo Grade: Near-zero variance (limited predictive value)
- Heat Day: Partially missing (imputed with mode)

**Demographic Bias:**
- 83% of transfers by single technician (Ruben)
- Model biased toward his technique
- Limited generalization for other technicians

### Model Limitations

**Pregnancy Prediction:**
- No causal claims (correlational only)
- Cannot recommend interventions
- Trained on specific population (may not transfer geographically)
- Post-hoc calibration may fail on out-of-distribution inputs

**Embryo Grading:**
- No ground-truth embryologist labels
- Pseudo-labels derived from pregnancy outcomes (imperfect proxy)
- 482 images far below typical CV dataset sizes
- No validation against established grading standards

**Anomaly Detection:**
- Unsupervised; detects statistical outliers, not always actionable
- May flag normal variations as anomalies
- Missing context for human interpretation

### Clinical & Operational Limitations

**NOT a Replacement for Expertise:**
- System is decision-support only
- Human remains final authority
- Should not automate clinical decisions

**Data Sufficiency:**
- System explicitly alerts when data insufficient
- Refuses predictions on highly novel inputs
- Acknowledges uncertainty honestly

**Generalization:**
- Trained on one farm's data
- May perform poorly on different farms, breeds, protocols
- Requires retraining on new population data

**Interpretability:**
- SHAP provides feature contributions, not biological meaning
- Grad-CAM highlights image regions, not clinically validated landmarks
- Requires domain expertise to interpret results

---

## KEY FEATURES

### 1. Pregnancy Prediction

✅ **Feature:**
- Predict pregnancy probability for any ET record
- Quantified uncertainty (95% CI)
- SHAP-based feature attribution
- Risk bands (Low/Medium/High)
- Calibrated probabilities

✅ **Workflow:**
- User selects transfer parameters
- System runs TabPFN predictor
- Returns probability + CI + SHAP explanations
- User decides based on available information

### 2. Embryo Grading

✅ **Feature:**
- Upload embryo image(s)
- Return grade (High/Medium/Low)
- Grad-CAM visualization of attention regions
- Confidence scores per class
- Batch processing capability

✅ **Workflow:**
- Embryologist uploads JPEGs
- System grades each embryo
- Shows morphological attention map
- Stores grades in database

### 3. Lab Quality Control

✅ **Feature:**
- Monitor 10+ KPIs in real-time
- Anomaly detection (Isolation Forest)
- Control chart violations
- Trend analysis
- Alert system

✅ **Workflow:**
- QC pipeline runs automatically
- Detects anomalies in latest data
- Flags to lab manager
- Provides remediation suggestions

### 4. Analytics Dashboard

✅ **Feature:**
- KPI visualization (cards, charts)
- Protocol effectiveness analysis
- Donor performance tracking
- Biomarker correlations
- Report generation & export

✅ **Workflow:**
- Manager views dashboard
- Identifies protocol trends
- Compares donor genetics
- Exports report for stakeholders

### 5. Data Entry & Management

✅ **Feature:**
- CRUD interface for all entities
- Form validation with error feedback
- Bulk CSV import
- Data history tracking
- Audit logging

✅ **Workflow:**
- Technician enters transfer data
- System validates (CL range, protocol validity)
- Records stored in database
- Available immediately for predictions/analysis

### 6. Authentication & Access Control

✅ **Feature:**
- JWT-based authentication
- Role-based access control (RBAC)
- Secure password hashing (bcrypt + argon2)
- Session management
- Audit trail

✅ **Workflow:**
- User logs in with credentials
- System issues JWT token
- Token validated on protected endpoints
- Role determines feature access

### 7. API & Integration

✅ **Feature:**
- RESTful API with 50+ endpoints
- OpenAPI/Swagger documentation
- Structured JSON responses
- Pydantic validation
- Error handling with descriptive messages

✅ **Workflow:**
- External systems make API calls
- Receive standardized responses
- Integrate with clinical workflows
- Future: mobile app, third-party integrations

---

## TEAM & SPONSORSHIP

| Role          | Name             | Affiliation/Role          |
|---------------|------------------|--------------------------|
| **Developer** | Eman Malik       | Full-stack engineer       |
| **Developer** | Inshal Zafar     | Backend/ML engineer       |
| **Supervisor**| Dr. Nusrat Shaheen | Project advisor          |
| **Sponsor**   | DayZee Farms (Pvt.) Ltd. | Client & data provider |

### Project Timeline

- **Start Date:** May 1, 2025
- **Launch Date:** March 6, 2026
- **Duration:** 10 months
- **Current Status:** ✅ Phase 5 (95%+ complete)

### Acknowledgments

- DayZee Farms: Data, domain expertise, feedback
- Dr. Nusrat Shaheen: Guidance & supervision
- Open-source community: FastAPI, React, scikit-learn, PyTorch, etc.

---

## AUTHORITATIVE DOCUMENTATION HIERARCHY

When conflicts arise between documents, follow this priority:

1. **`docs/OVULITE PRESENTATION (1).pdf`** — **FINAL SOURCE OF TRUTH** (Core modules, architecture)
2. **`docs/Dataset Analysis for IVF Success (1).pdf`** — Small-data ML strategy
3. **`docs/Ovulite Decision Support with Metadata‐Only Inputs (1).pdf`** — Structured-data ML
4. **`PROJECT.md`** & **`PROJECT_COMPREHENSIVE.md`** — Project overview & phase tracking
5. **`ROADMAP.md`** — Development roadmap & phase progression
6. **`REQUIREMENTS.md`** — Data requirements & specifications
7. **`docs/DATA_DICTIONARY.md`** — Column definitions & business rules
8. **`docs/LIMITATIONS.md`** — Transparent limitations & boundaries
9. **All other documentation** — Supporting materials

---

## QUICK START

### For Users (Clinical Staff)

1. Navigate to http://localhost:5173
2. Log in: **admin** / **ovulite2026**
3. Go to **Data Entry** → Add ET transfer record
4. Go to **Predictions** → Enter transfer details → Get pregnancy probability
5. Go to **Embryo Grading** → Upload image → Get grade with visual explanation
6. Check **Lab QC** for anomalies
7. View **Analytics** dashboard for trends

### For Developers

```bash
# 1. Setup (see SETUP.md)
docker compose up --build
docker compose exec backend alembic upgrade head
docker compose exec backend python seed_admin.py

# 2. Verify (see SYSTEM_VERIFICATION_GUIDE.md)
pytest tests/

# 3. Develop
# Backend: Edit app/api/*.py → auto-reload via uvicorn
# Frontend: Edit src/*.tsx → auto-reload via Vite
# ML: Edit ml/*.py → run manually for testing

# 4. Test
pytest --cov=app --cov-report=html
npm run build

# 5. Deploy
docker compose up -d
# Or push to production environment
```

---

**Document Version:** 1.0
**Last Updated:** March 2026
**Prepared By:** Development Team
**Status:** ✅ COMPREHENSIVE & CURRENT

For questions or updates, contact the development team or refer to the issue tracker in the repository.
