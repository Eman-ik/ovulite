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

- **Type checking:** the root `frontend/tsconfig.json` only holds `references`, so `npx tsc --noEmit` checks
  nothing and always exits 0. Use `npx tsc -p tsconfig.app.json --noEmit`. Until this was caught, every earlier
  "tsc clean" in this repo had checked no files. `vite build` does not type-check either, so run both.

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
- **Dashboard chart gallery:** `components/dashboard/ChartGallery.tsx` shows ten programme charts. Each has its
  own controls (View, Measure, Period, Min transfers) and a "What it shows" takeaway computed from the rows it
  draws. Data comes from `GET /dashboard/charts` (`backend/app/api/dashboard.py`), computed from transfer records
  under the dashboard filters; with no date range it covers the whole programme. The `/analytics/*` endpoints read
  static artifact files, not the database, so the gallery must not use them. Clicking a bar, slice, bubble or
  period sets the matching dashboard filter (breed, fresh/frozen, protocol, donor, or the period's dates); the active
  filters show as chips above the charts. Faded bars, segments, bubbles and columns have fewer than 20 transfers with
  a result. Live births are not in the funnel's steepest-drop claim: no calving outcome is recorded for this
  programme, so a zero there is missing data. The lab-side funnel still shows seeded figures. The homepage has no
  Data Quality panel; `/dashboard/data-quality` remains in the API.
- **Takeaways:** the gallery, the two trend charts and the funnel each state a finding. The text is computed, and it
  must say when a difference is not clear. The donor takeaway also reports how many "clear" donors chance alone would
  give (about 5% of the donors tested).
- **Dashboard interaction:** the filter bar drives every panel and chart on the homepage. *Drill level* (Auto / Day /
  Week / Month above the trends) passes `granularity` to `/dashboard/trends`; Day is refused over a year (422).
  *Slicing*: clicking a row or bar in the Performance panel sets the matching filter, and clicking it again clears it.
  Pivoting and zoom/pan are not built.
- **KPI card colours:** `KPI_COLORS` in `components/dashboard/KpiCard.tsx` uses the Sea / Heaven / Shine /
  Blush / Wave reference palette. Each card has a soft tint, the icon tile takes the solid colour, and the
  sparkline uses a darker shade derived from the palette so it stays visible on white.
- **Colour is a verdict, not a ranking.** A group is coloured `positive` or `negative` only when its whole
  95% Wilson interval sits above or below the programme rate (`verdict(k, n, programme)` in
  `frontend/src/lib/chartPalette.ts`). Otherwise it takes `volume`, the "no clear difference" colour, however far
  its point estimate sits from the programme rate. Colouring a point estimate that is 1-2 points off, with
  overlapping intervals, was the old behaviour and it read noise as findings. `roleProps(role)` gives fill and
  outline, `textOn(fill)` the label colour. Counts that are not rates keep fixed roles (pregnant, open, pending,
  transfers). Never colour a series by its position in a list. **Every dashboard chart has a legend**: a Recharts
  `Legend`, or the shared `RoleKey` component when the swatches are cells or shapes. Any new chart needs one.
  The programme rate is pregnant ÷ transfers with an outcome under the current filters (53.2% at last count).
- **Chart palette:** all chart series colours come from `frontend/src/lib/chartPalette.ts`
  (`CHART_SERIES`, from the pastel reference palettes). Teal and lime were removed from the series on
  2026-10-15 to make the dashboard less green; the set is now wave, watermelon, mango, grape, blush,
  old rose, lemon and hazelnut. Don't hard-code chart
  colours; import from there. Axes, gridlines and status colours are not part of it. The
  landing page's own charts keep the photo-sampled colours it was given. The pastels are
  light, so strokes sit near 1.5:1 on white. Charts rely on hue plus labels.
- **Site background:** `components/backdrop/SilkBackdrop.tsx` is the one shared background. It shows the silk
  picture (`/backdrop/silk.jpg`) with a light wash, and twelve glassy bubbles of different sizes drifting over
  it. It is a fixed layer at z -10, so its parent needs the `isolate` class. It is used on login, signup, the
  app shell and the landing page. Cards keep their glass (74% white, blurred), so text stays readable.
- **Retired:** the Minimal Green values (`#051F20`, `#235347`, `#8EB69B`, `#DAF1DE`, `#f2f7f3` and
  the green rgba family). Do not reintroduce them.
- **Scoping:** `.dash-blue` (dashboard) is now redundant with the global tokens but harmless.
- **Landing page** keeps its black-text rule and its own scroll character and background story.
- **Companion character** is a separate system (below), coloured in lilac and blue.
- **Login and signup** share the same light frosted-glass design over the site background. Signup still shows the Google button, which login no longer does.
- Verified: login, signup, dashboard, cases, laboratory and landing had zero AA failures on the
  gradient-aware check. Run the same check after any colour change.

## Companion character: removed

The lilac companion that walked and reacted to actions on app and auth pages was removed on
2026-10-15 at the owner's request. It is no longer rendered anywhere. The landing page keeps its own
scroll-driven character (`OvuliteLandingPage.tsx`, `RollingCharacter` and `HitBubble`), which is a
separate piece of code. Login and signup use the shared `components/backdrop/SilkBackdrop.tsx`
(see the site background note above).

## House style

Do not ship UI that implies more certainty than the data supports. Several fixes in this repo
exist solely because a screen did: a hardcoded ROC-AUC 0.78, an export button that fired
confetti and produced no file, a "Prediction Confidence 95%" tile that was really form
completeness, a "retained 286.5%" from comparing independent cohorts. If a number cannot be
computed honestly, say so on the screen instead.
