# Ovulite – AI-Driven Reproductive Intelligence System for Bovine IVF

## Vision

An uncertainty-aware, explainable AI decision-support platform for cattle IVF and embryo transfer that predicts pregnancy probability, grades embryos objectively, monitors lab quality, and analyzes protocol effectiveness — all under ultra-small-data constraints.

**Ovulite does NOT replace clinical expertise. It structures data, reveals patterns, and makes uncertainty visible. The human remains the final decision authority.**

## Status

| Attribute        | Value                                |
|------------------|--------------------------------------|
| Current Phase    | Phase 0 – Foundation & Scaffold      |
| Version          | 0.0.0 (pre-alpha)                    |
| Last Updated     | 2026-02-26                           |
| Repository       | Ovulite new                          |
| Team             | Eman Malik, Inshal Zafar             |
| Supervisor       | Dr. Nusrat Shaheen                   |
| Sponsor          | DayZee Farms (Pvt.) Ltd.             |

## Core Modules (per Presentation PDF — source of truth)

| # | Module                                    | Type              |
|---|-------------------------------------------|-------------------|
| 1 | Secure Login & Access Control             | Auth / RBAC       |
| 2 | Data Intake & Validation                  | ETL / Governance   |
| 3 | AI Embryo Grading (Image + Metadata Fusion) | CNN + MLP        |
| 4 | Pregnancy Success Prediction              | ML (TabPFN primary)|
| 5 | Lab Quality Control & Anomaly Detection   | Unsupervised ML   |
| 6 | Protocol Effectiveness Analytics          | Statistical / ML   |
| 7 | Reproductive Performance Analytics Dashboard | Visualization  |

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   React (TypeScript)                 │
│               Frontend / Dashboard / UI              │
└───────────────────────┬─────────────────────────────┘
                        │ REST API
┌───────────────────────▼─────────────────────────────┐
│                  FastAPI (Python)                     │
│          Backend / Auth / Validation / API            │
├──────────┬──────────┬──────────┬─────────────────────┤
│ Pregnancy│ Embryo   │ Lab QC   │ Protocol Analytics  │
│ Engine   │ Grading  │ Module   │ Module              │
│ (TabPFN) │ (CNN+MLP)│ (IsoFor) │ (Regression+SHAP)  │
└──────────┴──────────┴──────────┴─────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│              PostgreSQL Database                     │
│     donors | sires | embryos | recipients |          │
│     et_transfers | technicians | protocol_logs |    │
│     embryo_images | predictions | anomalies         │
└─────────────────────────────────────────────────────┘
```

**Deployment:** Docker Compose (frontend + backend + database)

## Data Reality

| Dataset            | Records | Notes                                      |
|--------------------|---------|--------------------------------------------|
| ET Data (main)     | 488     | 39 columns, primary ML source              |
| Pregnancy Records  | ~280    | Across 4 client-specific CSV files          |
| Embryo Images      | 482     | Blastocyst JPGs, no grade subfolder labels  |
| Unique Donors      | 52      | High variance in per-donor sample count     |
| Unique ET Dates    | 19      | May 2025 – Feb 2026                         |
| ET Technicians     | 5       | Ruben dominates (407/488 = 83%)             |

**Class Distribution (Pregnancy Outcome):**
- Open: 334 (70.8%)
- Pregnant: 136 (28.8%)
- Recheck: 2 (0.4%)
- Missing: 16 (3.3%)

**This is an ultra-small-N, imbalanced dataset. All ML strategies must account for this.**

## Gold Standard Requirements

1. **Overfitting avoidance** — Small-data-optimal algorithms; strict validation
2. **Honest uncertainty** — Calibrated probabilities; confidence intervals; "data insufficient" alerts
3. **Biological interpretability** — SHAP; feature contributions; clinically meaningful explanations
4. **Clinical usability** — Actionable outputs; decision-support not automation
5. **Explicit limitations** — Document what the system cannot do

## Authoritative Source Hierarchy

1. `docs/OVULITE PRESENTATION (1).pdf` — **FINAL SOURCE OF TRUTH** for modules & architecture
2. `docs/Dataset Analysis for IVF Success (1).pdf` — Small-data architecture strategy (TabPFN)
3. `docs/Ovulite Decision Support with Metadata‐Only Inputs (1).pdf` — Structured-data ML strategy
4. `docs/OVULITE_SCOPE_DOCUMENT.pdf` — OUTDATED; do NOT follow unless explicitly needed

If conflict exists between documents → ALWAYS FOLLOW THE PRESENTATION PDF.
