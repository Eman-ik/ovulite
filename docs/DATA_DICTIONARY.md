# Ovulite — Data Dictionary

## Overview

This document defines every column in the Ovulite database, its source in the
raw CSV, valid ranges, and business rules that apply during ingestion and
validation.

Source file: `docs/dataset/ET Summary - ET Data.csv` (488 rows, 39 columns).

---

## Table: `donors`

| Column | Type | Source CSV Column | Valid Range / Rules | Notes |
|--------|------|-------------------|---------------------|-------|
| `donor_id` | SERIAL PK | — | Auto-increment | |
| `tag_id` | VARCHAR UNIQUE NOT NULL | `Donor ID / Tag #` | Non-empty string | Used as natural key for dedup |
| `breed` | VARCHAR NULL | `Donor Breed` | Free text | Dirty data: some rows contain dates or IDs; stored as-is |
| `owner_name` | VARCHAR NULL | `Customer ID` | Free text | Inferred from first appearance in CSV |
| `created_at` | TIMESTAMPTZ | — | Auto | |

**Business Rules**

- Unique on `tag_id` (case-sensitive).
- If a donor tag appears with different breeds in separate rows, the **first
  non-null** breed wins (get-or-create semantics in ingestion).

---

## Table: `sires`

| Column | Type | Source CSV Column | Valid Range / Rules | Notes |
|--------|------|-------------------|---------------------|-------|
| `sire_id` | SERIAL PK | — | Auto-increment | |
| `name` | VARCHAR UNIQUE NOT NULL | `Bull Name / Code` | Non-empty string | Natural key |
| `breed` | VARCHAR NULL | `Semen Breed` | Free text | |
| `stud_code` | VARCHAR NULL | — | — | Not in CSV; reserved for manual entry |
| `semen_type` | VARCHAR NULL | `Semen Type` | `Conventional`, `Sexed`, `Sexed Female` | "Pre-Sorted for Female" → "Sexed" during ingestion |
| `created_at` | TIMESTAMPTZ | — | Auto | |

**Business Rules**

- Unique on `name`.
- `semen_type` normalized: "Pre-Sorted for Female" mapped to "Sexed".

---

## Table: `recipients`

| Column | Type | Source CSV Column | Valid Range / Rules | Notes |
|--------|------|-------------------|---------------------|-------|
| `recipient_id` | SERIAL PK | — | Auto-increment | |
| `tag_id` | VARCHAR UNIQUE NOT NULL | `Recipient ID` | Non-empty string | Natural key |
| `breed` | VARCHAR NULL | `Recipient Breed` | Free text | |
| `farm_location` | VARCHAR NULL | `Farm Location` | Free text | |
| `created_at` | TIMESTAMPTZ | — | Auto | |

**Business Rules**

- Unique on `tag_id`.
- Some tag IDs are numeric-only (e.g. "123"); stored as strings to preserve
  leading zeros or mixed formats.

---

## Table: `technicians`

| Column | Type | Source CSV Column | Valid Range / Rules | Notes |
|--------|------|-------------------|---------------------|-------|
| `technician_id` | SERIAL PK | — | Auto-increment | |
| `name` | VARCHAR UNIQUE NOT NULL | `ET Technician` | Non-empty string | |
| `license_number` | VARCHAR NULL | — | — | Not in CSV |
| `created_at` | TIMESTAMPTZ | — | Auto | |

**Business Rules**

- Unique on `name`.
- 5 technicians found in dataset: Dr. Affan Qureshi, Dr. M. Wahaj, Dr. Javaid
  Hayat, Dr. Raza Ali, Dr. Hamad.

---

## Table: `protocols`

| Column | Type | Source CSV Column | Valid Range / Rules | Notes |
|--------|------|-------------------|---------------------|-------|
| `protocol_id` | SERIAL PK | — | Auto-increment | |
| `name` | VARCHAR UNIQUE NOT NULL | `Protocol Used` | Non-empty string | |
| `description` | TEXT NULL | — | — | Not in CSV |
| `created_at` | TIMESTAMPTZ | — | Auto | |

**Business Rules**

- 5 protocols in dataset: `CIDR`, `CIDR (Day 6)`, `CIDR Short`, `Natural heat`,
  `Natural Heat` (case variation).
- Stored as-is during ingestion (case preserved).

---

## Table: `embryos`

| Column | Type | Source CSV Column | Valid Range / Rules | Notes |
|--------|------|-------------------|---------------------|-------|
| `embryo_id` | SERIAL PK | — | Auto-increment | |
| `donor_id` | FK → donors | via `Donor ID / Tag #` | Must exist | |
| `sire_id` | FK → sires | via `Bull Name / Code` | Must exist | |
| `stage` | SMALLINT NULL | `Embryo Stage` | 1–9 | IETS numeric stage; typical 4–8 |
| `grade` | SMALLINT NULL | `Embryo Grade` | 1–4 | IETS quality grade; 1 = excellent, 4 = dead/degenerate |
| `fresh_or_frozen` | VARCHAR NULL | `Fresh/Frozen` | `Fresh` or `Frozen` | |
| `opu_date` | DATE NULL | `OPU-date` | Valid date | M/D/YYYY in CSV → ISO 8601 |
| `cane_number` | VARCHAR NULL | `Cane #` | Free text | Only present for frozen embryos |
| `created_at` | TIMESTAMPTZ | — | Auto | |

**Business Rules**

- `stage` validated 1–9 by Pydantic schema. Reject if outside range.
- `grade` validated 1–4. Reject if outside range.
- `fresh_or_frozen` only accepts `Fresh` or `Frozen` (case-sensitive).
- `opu_date` parsed from M/D/YYYY format; `"."` treated as NULL.

---

## Table: `et_transfers`

| Column | Type | Source CSV Column | Valid Range / Rules | Notes |
|--------|------|-------------------|---------------------|-------|
| `transfer_id` | SERIAL PK | — | Auto-increment | |
| `et_number` | INTEGER NULL | `ET #` | Positive integer | Unique across dataset (1–488) |
| `et_date` | DATE NOT NULL | `ET Date` | Valid date | M/D/YYYY in CSV → ISO 8601 |
| `customer_id` | VARCHAR NULL | `Customer ID` | Free text | 3 customers in dataset |
| `farm_location` | VARCHAR NULL | `Farm Location` | Free text | |
| `recipient_id` | FK → recipients | via `Recipient ID` | Must exist | |
| `bc_score` | NUMERIC(3,1) NULL | `BC Score` | 1.0–5.0 (typical) | 77.5% missing in dataset (378/488 NULL) |
| `cl_side` | VARCHAR NULL | `CL-Side` | `Left` or `Right` | Normalized: lowercase → title-case during ingestion |
| `cl_measure_mm` | NUMERIC(5,1) NULL | `CL Measure (mm)` | 0–50 mm | `"."` → NULL; validated by Pydantic (0–50 range) |
| `embryo_id` | FK → embryos | — | Must exist | Created during ingestion from donor+sire+embryo columns |
| `protocol_id` | FK → protocols | via `Protocol Used` | Must exist | |
| `heat_observed` | BOOLEAN NULL | `Heat Observed` | true/false | |
| `heat_day` | SMALLINT NULL | `Heat Day` | Integer | Day number when heat detected |
| `semen_type` | VARCHAR NULL | `Semen Type` | `Conventional`, `Sexed`, `Sexed Female` | Denormalized; also on sires |
| `technician_id` | FK → technicians | via `ET Technician` | Must exist | |
| `assistant_name` | VARCHAR NULL | `ET Technician Assistant` | Free text | |
| `pc1_date` | DATE NULL | `1st PC date` | Valid date | First pregnancy check |
| `pc1_result` | VARCHAR NULL | `1st PC Result` | `Pregnant`, `Open`, `Recheck` | Normalized: `"P"` → `"Pregnant"`, `"O"` → `"Open"` |
| `created_at` | TIMESTAMPTZ | — | Auto | |
| `updated_at` | TIMESTAMPTZ | — | Auto | |

**Business Rules**

- `et_date` is **required** (NOT NULL). Reject records without it.
- `cl_measure_mm` validated 0–50 by Pydantic. API returns 422 if outside range.
- `cl_side` only accepts `Left` or `Right` (title-case). Ingestion normalizes
  `"left"` → `"Left"`.
- `pc1_result` normalized from abbreviations: `"P"` → `"Pregnant"`, `"O"` →
  `"Open"`, `"R"` → `"Recheck"`.
- CSV value `"."` is treated as NULL for all nullable fields.

---

## Validation Summary

| Rule | Field | Constraint | Enforcement |
|------|-------|-----------|-------------|
| AT-1 | `cl_measure_mm` | Must be 0–50 mm | Pydantic validator + frontend min/max |
| AT-2 | `embryo.stage` | Must be 1–9 | Pydantic validator |
| AT-3 | `embryo.grade` | Must be 1–4 | Pydantic validator |
| AT-4 | `et_date` | Required, valid date | NOT NULL constraint + Pydantic |
| AT-5 | `cl_side` | `Left` or `Right` only | Pydantic validator |
| AT-6 | `pc1_result` | `Pregnant`, `Open`, `Recheck` or NULL | Pydantic validator |
| AT-7 | `fresh_or_frozen` | `Fresh` or `Frozen` only | Pydantic validator |

---

## CSV Data Quality Notes

- **488 valid rows** (one trailing blank row excluded).
- **Date format:** M/D/YYYY (American) — `1/15/2024`.
- **Missing value marker:** `"."` (single dot) used instead of empty string.
- **BC Score:** 77.5% missing (378 of 488 rows) — accounted for in ML feature engineering.
- **CL measure:** 11 values are `"."` → treated as NULL.
- **Donor breed column:** Contains some dirty entries (dates, other IDs in breed field).
- **Customer IDs:** 3 distinct: DZF, Maidan Cattle (Karachi), Model Cattle (Karachi).
- **Protocols:** 5 types (CIDR, CIDR Day 6, CIDR Short, Natural heat/Heat).
- **Semen types:** Conventional, Pre-Sorted for Female (→ Sexed), Sexed Female.
