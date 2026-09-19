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

## Embryo grading — this one actually works

`ml/artifacts/grader_checkpoint_v1.pth` (1.4 KB) is a **superseded placeholder**; its own config says so.
The live artifact is `ml/artifacts/grading/real_labels_v1/grade_classifier.pt` (17 MB), EfficientNet-B0 with
SimCLR-pretrained init, trained on real labels.

Labels come from the Rocha et al. (2017) bovine blastocyst set, already in the repo:
`docs/dataset/external/rocha2017_bovine_blastocyst/labels_clean.csv` + `docs/dataset/Blastocystimages.zip`.
482 images, all matched to labels, 3 independent embryologist IETS gradings plus a modal grade, and 36
precomputed morphometric features.

- Modal grade distribution: **112 / 173 / 194** across grades 1/2/3 — real variance, unlike `embryos.grade`
  in the app database, which is still 489/489 Grade 1 and remains unusable as a label.
- Test accuracy **54.2%**, macro-F1 0.475, n=72. Majority-class baseline is 40.3%, so it has learned
  something real.
- **The ceiling is human disagreement.** Pairwise rater kappa is 0.411-0.727 (raw agreement 61.2-82.0%),
  and all three graders agree on only 58.7% of images. A model cannot reliably beat the consensus that
  defines its own label — quote that ceiling whenever quoting the accuracy.
- Known weakness: Grade 2 recall is 0.192. The middle class collapses into Grade 3, which is the usual
  failure mode when an ordinal target is trained with plain cross-entropy.

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
- Live predictions span 0.112–0.238 (sd 0.018) against a 38.6% base rate, so every case lands
  in the "Low" risk band and the Brier score is worse than always predicting the base rate.
  The prediction page states this above the estimate rather than hiding it.

## House style

Do not ship UI that implies more certainty than the data supports. Several fixes in this repo
exist solely because a screen did: a hardcoded ROC-AUC 0.78, an export button that fired
confetti and produced no file, a "Prediction Confidence 95%" tile that was really form
completeness, a "retained 286.5%" from comparing independent cohorts. If a number cannot be
computed honestly, say so on the screen instead.
