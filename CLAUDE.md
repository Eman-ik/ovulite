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

## Design system — blue-grey palette ("Sebum to Antibiotics")

Adopted 2026-10-15 for the whole website, replacing Minimal Green. Reference swatches:
`#596070` Sebum, `#757F99` Cartilage, `#94A9BE` Substantia Grisea, `#B2CDDF` Lymphatic,
`#C9D9E6` Neutrophils, `#EAF1F1` Antibiotics.

- **Theme tokens** are in `frontend/src/index.css` under `:root` (light) and `[data-theme="dark"]`.
  Components use the tokens, so changing a token changes every screen that uses it.
- **Text** is `#2E3645` on the light grounds, or `#EAF1F1` on dark fills. `#3F4758` for secondary
  text. Never Cartilage `#757F99` as text. Never light text on Lymphatic or Neutrophils.
- **Status colours keep their meaning** and are not part of the palette: danger `#9d3730`, warning
  `#7a5a12`, info `#35748a`. Do not recolour them to match the theme.
- **Dashboard chart gallery:** `components/dashboard/ChartGallery.tsx` has ten programme-wide charts of
  nine types: donut, radial, combo bar-and-line, stacked area, waterfall, radar, bubble scatter, treemap,
  stacked bars, and columns. They use real transfer records only. The lab-side funnel (oocytes, embryos,
  live births) comes from the demo seeder, so the gallery leaves it out. The dashboard's own Reproductive
  Funnel still shows those seeded figures. The gallery shows only for roles with `canViewAnalytics`. It
  ignores the dashboard filters, and its captions say so. Bars, segments, bubbles and columns from fewer
  than 20 transfers are drawn faded. Legend, tooltip and treemap text is set in ink.
- **Chart palette:** all chart series colours come from `frontend/src/lib/chartPalette.ts`
  (`CHART_SERIES`, from the pastel Fruit Salad and swatch references). Don't hard-code chart
  colours; import from there. Axes, gridlines and status colours are not part of it. The
  landing page's own charts keep the photo-sampled colours it was given. The pastels are
  light, so strokes sit near 1.5:1 on white. Charts rely on hue plus labels.
- **App background:** after sign-in, `AppLayout` shows the spheres image (`/auth/login-bg.png`)
  behind the whole app under a 30% light wash. Cards (`.dash-card`) are 74% white glass with blur,
  and the sidebar and mobile top bar are glass, so the image shows through. Re-run the contrast check
  if you change the wash or card opacity.
- **Retired:** the Minimal Green values (`#051F20`, `#235347`, `#8EB69B`, `#DAF1DE`, `#f2f7f3` and
  the green rgba family). Do not reintroduce them.
- **Scoping:** `.dash-blue` (dashboard) is now redundant with the global tokens but harmless.
- **Landing page** keeps its black-text rule and its own scroll character and background story.
- **Companion character** is a separate system (below), coloured in lilac and blue.
- **Login and signup** share the same light frosted-glass design over the spheres background
  (`/auth/login-bg.png`). Signup still shows the Google button, which login no longer does.
- Verified: login, signup, dashboard, cases, laboratory and landing had zero AA failures on the
  gradient-aware check. Run the same check after any colour change.

## Companion character: removed

The lilac companion that walked and reacted to actions on app and auth pages was removed on
2026-10-15 at the owner's request. It is no longer rendered anywhere. The landing page keeps its own
scroll-driven character (`OvuliteLandingPage.tsx`, `RollingCharacter` and `HitBubble`), which is a
separate piece of code. Login and signup use `components/auth/AuthBackdrop.tsx`: the sphere picture
drifts slowly, with rising glints, and stops under reduced motion.

## House style

Do not ship UI that implies more certainty than the data supports. Several fixes in this repo
exist solely because a screen did: a hardcoded ROC-AUC 0.78, an export button that fired
confetti and produced no file, a "Prediction Confidence 95%" tile that was really form
completeness, a "retained 286.5%" from comparing independent cohorts. If a number cannot be
computed honestly, say so on the screen instead.
