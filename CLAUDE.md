# Ovulite — working notes

Bovine IVF / embryo-transfer platform. FastAPI + SQLAlchemy 2.0 + PostgreSQL backend,
React 19 + TypeScript + Vite + Tailwind frontend, Python ML.

## Running it

The backend reads `DATABASE_URL` from its environment. If it is unset — or set to the
docker-compose hostname `@db:5432` — `app/database.py` silently falls back to a local
**SQLite file that contains none of the real data**. A backend that starts fine but shows
an empty app is almost always this.

```bash
# Backend — the DATABASE_URL is not optional
cd backend && DATABASE_URL="postgresql://ovulite:ovulite_dev_password@127.0.0.1:5432/ovulite" \
  ./venv/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- Frontend dev server: **port 5174** (`npm run dev` in `frontend/`). SETUP.md says 5173; it is wrong.
- Postgres runs on the host, not in Docker. Docker Desktop does not start in this environment.
- `pg_dump` lives at `C:/Program Files/PostgreSQL/18/bin/pg_dump.exe`.
- Logins: `admin` / `lab_tech` / `et_tech` / `test_vet` / `researcher` / `test_viewer`, password `ovulite2026`.
  `/auth/login` takes **form-encoded** fields, not JSON.

**Do not kill or restart a server the user is running** without asking first. Ask, or add an
entry to `.claude/launch.json` and use the preview tooling.

## Verification rules

- **`tsc --noEmit` does not validate JSX structure.** It has passed on an unbalanced
  `motion.div` that rendered a blank page. Always finish with `npx vite build`.
- Before trusting a measurement script you just wrote, check it against a case you already
  know the answer to. A contrast auditor here reported 51 failures that were all artefacts of
  not compositing alpha, and later reported false positives on any text sitting on a gradient.
- Console output can mangle UTF-8. Verify an encoding bug against the raw response bytes
  before "fixing" it.
- Paginated CRUD routers cap `page_size` at **100**; asking for more returns 422. Use
  `fetchAllPages()` in `frontend/src/lib/api.ts`.

## Schema and API gotchas

- Several `*Update` schemas (`OPUSessionUpdate`, `IVFBatchUpdate`, `EmbryoUpdate`, …) are
  standalone `BaseModel`s, not subclasses of their `*Base`. A field missing from them is
  **silently dropped on PUT** — the API returns 200 and saves nothing. Add new fields to the
  Update model too.
- `ETTransferBase` validators run over **responses** as well as requests, so a single bad row
  makes the whole list endpoint 500.
- Multi-tenancy is `OrganizationScopedMixin` with **no automatic query filtering**. Every
  endpoint must filter `organization_id` itself, including after joins.
- The audit listener carries its actor on `Session.info`, not a ContextVar (FastAPI runs sync
  dependencies in a worker thread), and writes in `after_flush`, not `before_flush` (no primary
  key exists yet in `before_flush`). See `backend/app/services/audit.py`.
- Model training reads `docs/dataset/ovulite_cleaned_et_data.csv`, **not the database**. Seeded
  demo rows therefore cannot reach the model.

## Design system — "Minimal Green"

`#051F20` `#0B2B26` `#163832` `#235347` `#8EB69B` `#DAF1DE`

- **App = light surfaces** on green tokens (`frontend/src/index.css`): background `#f2f7f3`,
  card `#ffffff`, primary `#235347`, accent `#8EB69B`, muted text `#5c7268`.
- **Landing page and auth pages = dark**, `#051F20` ground with `#DAF1DE` text.
- **Dark is the default theme.** `ThemeContext` and both auth pages treat an absent stored
  value as dark; only an explicit `"light"` opts out.
- `#235347` and `#163832` are **surface colours only** — at 1.96:1 on the dark ground they are
  invisible as text. Anything rendered as `color:` uses `#DAF1DE`, `#8EB69B`, `#c6dccd` or `#5c7268`.
- Semantic colours, already tuned to pass AA: warning `#7a5a12`, danger `#9d3730`,
  info/blue `#1f5468` and `#35748a`.
- Fonts: `Plus Jakarta Sans` (display), `Inter` (body), `Instrument Serif` (accent italic).
- No bubble/`GlassBubbles` animation on the auth pages — it was removed deliberately.

## Embryo grading — the one model that works

`POST /grade/embryo` serves a **morphometric tabular model**, not the CNN.
`ml/artifacts/grading/tabular_extracted_v1/` — random forest over 36 features that
`ml/grading/morphometrics.py` computes from the raw image (Hough-located disc,
watershed ICM, masked GLCM texture, grey-level statistics).

Measured on the same held-out 72 images, identical split and seed:

| model | accuracy | macro F1 | Grade 2 recall |
|---|---|---|---|
| tabular, our extractor (**served**) | 0.597 | 0.564 | 0.385 |
| tabular, Rocha's published features | 0.625 | 0.611 | 0.423 |
| EfficientNet-B0 + CORAL + fusion | 0.556 | 0.501 | 0.269 |
| EfficientNet-B0 (previously served) | 0.542 | 0.475 | 0.192 |
| majority class | 0.403 | — | — |

**Quote 0.587 ± 0.041**, the cross-validated figure. The 72-image test number carries
a ±0.11 interval either way.

- **The ceiling is human disagreement.** Three graders agree unanimously on only 58.7%
  of these images (pairwise kappa 0.411-0.727). Anything near 0.75 is the label's noise
  floor, not headroom. Quote the kappa whenever quoting accuracy.
- Labels: Rocha et al. (2017), already in the repo. Modal grade 112/173/194 across
  grades 1/2/3 — real variance, unlike `embryos.grade` in the app database, which is
  still 489/489 Grade 1 and remains unusable as a label.
- **Never put the sanitiser before the measurement.** `_validate_and_normalize_image`
  re-encodes to JPEG q95 to strip EXIF; measuring that copy instead of the original
  flipped the grade on 3 of 39 images and shifted confidence by up to 0.47. Validate for
  storage, measure the original pixels.
- `heatmap_available` is **false** on this endpoint. Grad-CAM belongs to the CNN, which
  still backs `/grade/embryo-with-heatmap`.
- Ordinal loss (CORAL) was tried and did not help: arms at
  `ml/artifacts/grading/ablation_*`, summary in `ablation_summary.json`. All CNN arms
  fall within noise of each other.
- **Untested outside Rocha's framing.** All 479 images are centred, uniformly lit and
  1280x1024. A real lab photo has never been through this. Total failure returns 422;
  silent degradation on awkward framing is unmeasured.

## Demo data

`backend/scripts/seed_demo_data.py` fills the gaps that make screens render empty (OPU oocyte
counts, IVF lab numbers, IVM batches, embryo observations, recipient evaluations, protocol
steps, synchronisation enrolments, PC2 checks, calving records, QC anomalies).

- Every row it writes is tagged `[demo-seed v1]` in `notes`; `--purge` removes exactly those.
- It never overwrites a recorded value and never touches the outcome spine (`et_date`,
  `pc1_result`, embryo/donor/sire identity), so headline rates cannot move.
- `calving_records` is the one table where it invents an outcome — no calving was ever
  recorded for this programme, so **every live-birth figure in the app is synthetic**.
- `backend/scripts/generate_predictions.py` produces real predictions by calling the live
  `POST /predict/pregnancy`, then copies `pc1_result` into `actual_outcome`.
- Take a `pg_dump` into `backups/` before any destructive data work.

## What the model actually does

The pipeline works end to end. The discrimination does not.

- Deployed artifact `ml/artifacts/v1.0.0`, LogisticRegression, 35 features, holdout ROC-AUC
  **0.510**; XGBoost 0.484; TabPFN is not installed and silently falls back to CalibratedLR.
- Holdout confusion matrix is `tp=0` for all three models — they predict the majority class
  for every case, so precision and recall for pregnancy are zero.
- Grouped CV by donor: 0.552 / 0.572 against a shuffled-label null of 0.501 ± 0.040 /
  0.503 ± 0.049, permutation **p = 0.143 / 0.190**. Events per feature 8.5.
- **Retraining does not fix this** — `ml/permutation_test.py` and `ml/diagnose_split.py` already
  establish it under pooled CV, within-regime CV and rolling origin. Do not propose a new split
  as a remedy; more labelled outcomes are the only thing that would change the answer.
- Live predictions span 0.112–0.238 (sd 0.018) against a **28.6%** base rate (136 pregnant of
  476 scored rows in `ovulite_cleaned_et_data.csv`; the raw ET CSV agrees at 136/470 = 28.9%).
  An earlier note here said 38.6% — wrong by ten points, and it never reached the code. Every
  case still lands in the "Low" band and the Brier score is still worse than always predicting
  the base rate; the band threshold is 0.35 and the predictions top out at 0.238.
  The prediction page states this above the estimate rather than hiding it.

## Lab QC (M7)

`python -m ml.qc.acceptance_demo` walks the whole chain in one run — no data, normal data,
injected faults, detection, alert contents — and prints a verdict. Run it before claiming
anything about QC.

- **The reporting contract holds. The detection does not.** Inject 5 faults across 4
  technician-month batches and Isolation Forest finds **1**. Sweeping contamination from
  0.10 to 0.42 (flagging 5 of 12 batches) finds the same one and adds four false positives,
  so it is not a flag-budget problem — 12 batches over 4 technicians is no cohort to judge
  against. Do not "fix" this by retuning contamination.
- **Control charts cannot run on this data.** Only 3–4 months clear `MIN_MONTHLY_RECORDS`,
  against `MIN_CHART_PERIODS = 8`. Below that an EWMA chart tests points against a baseline
  estimated from those same points and flags its own noise; it was calling a
  1.3-percentage-point move an out-of-control pregnancy rate. The chart now reports
  `status: "insufficient_history"` and the dashboard says so instead of drawing an empty axis.
- The first EWMA point is never alerted on: `ewma[0]` is seeded with `values[0]`, so point 0
  is tested against a statistic it defines.
- `pandas.DataFrame.get(name, default)` returns the **scalar** default when the column is
  missing, not a Series. This bit twice: it killed `load_et_data` on any CSV missing a column,
  and `verify_detection` did `df[df.get("is_synthetic", False) == True]` → `df[False]` →
  KeyError, so the synthetic-verification path had never once executed.
- QC reads the transfer-level ET CSV. Cleavage and blastocyst rates are **not** in its feature
  space — they live on `ivf_batches` and every one of those numbers is demo-seeded.
- Alerts carry `metric`, `metric_value`, `baseline_value`, `period` and `severity`, and state
  no cause. Protocol, technician and month move together in this dataset; it cannot attribute.

## House style

Do not ship UI that implies more certainty than the data supports. Several fixes in this repo
exist solely because a screen did: a hardcoded ROC-AUC 0.78, an export button that fired
confetti and produced no file, a "Prediction Confidence 95%" tile that was really form
completeness, a "retained 286.5%" from comparing independent cohorts. If a number cannot be
computed honestly, say so on the screen instead.
