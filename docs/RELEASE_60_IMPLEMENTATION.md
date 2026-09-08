# OVULITE scoped 60% release

Implemented scope: modules 2, 3 and 5. Modules 0, 4, 6 and 7 are excluded at the user's request. The supplied SRS does not define Module 0, so authentication was left unchanged. Pre-existing and concurrent edits elsewhere in the workspace were preserved. This release does not certify prediction accuracy, grading performance, analytics, or laboratory QC.

## Delivered workflows

### M2 — Case traceability

Case Detail includes Timeline & History, with recorded OPU, IVF, freezing, transfer, pregnancy checks, loss and calving events. Donor and recipient histories show earlier dated transfers (up to 100 with a total count). Canonical snapshots, actor/time audit entries and source-row provenance are available for new entries. Case search includes ET number, embryo identifier and sire. Existing records with unknown provenance remain explicitly unclassified; historical values are not invented.

### M3 — Canonical collection and governance

The schema contains 58 fields covering recipient, donor, sire/semen, embryo, production, protocol, transfer, environment and follow-up. The machine-readable schema and downloadable CSV template derive from the same validation model as manual entry and CSV ingestion. See [the generated dictionary](CANONICAL_ET_DICTIONARY.md) for required fields, units, categories and checks.

CSV intake supports strict UTF-8 inspection, explicit column mapping, required-field checks, row errors, missingness, unmapped columns, duplicate detection, preview and transactional commit. Duplicate ET numbers and external embryo identifiers are checked within each organization. Mapping corrections retain earlier validation revisions. The original source, checksum, declared source classification, reference, uploader, report and row-level provenance are retained. Original source bytes can be downloaded. Synthetic batches stay staged and cannot enter clinical tables through this workflow.

Manual entry uses the same canonical validation and stores the full snapshot. Transfer edits validate links and record audits. Legacy positional CSV entry points return HTTP 410 directing clients to mapped intake; image archive upload remains available. No intake data is copied into prediction or analytics datasets.

### M5 — Licensed literature and RAG

Literature Intelligence supports organization-scoped document curation, idempotent loading of 60 licensed bovine reproduction papers, retrieval and cited model synthesis. The bundled manifest retains authors, title, year, source URL, DOI/PMCID, license, content checksum, scope and truncation metadata. Corresponding source XML preserves licensing evidence. Text includes abstracts and article bodies; reference lists are removed. Selection requires an explicit CC BY or CC0 license and bovine IVF/ET relevance. This screening is not a formal study-quality appraisal.

Passages preserve sentence context. Lexical retrieval and a persisted vector index select evidence from multiple sources. The offline index is a normalized hashing vector, not a pretrained semantic model; the optional Ollama configuration uses nomic-embed-text. Generation supports Ollama and llama.cpp, uses a structured response schema and validates citation numbers. Unsupported questions can abstain. Disabled, failed or invalid generation explicitly falls back to retrieved passages. Citation validation checks source references, not scientific entailment: users can inspect every cited passage. No reproductive case data is sent to the literature model.

## Start the local CPU literature service on Windows

The project-local runtime is available under ignored `.runtime/literature`; weights are not committed. To reproduce the download from official llama.cpp and Qwen sources:

```powershell
.\.venv\Scripts\python.exe backend/scripts/bootstrap_literature_runtime.py
.\backend\scripts\start_literature_runtime.ps1
```

In the backend process environment, enable this service:

```powershell
$env:LITERATURE_RAG_ENABLED='true'
$env:LITERATURE_GENERATION_PROVIDER='llama_cpp'
$env:LITERATURE_MODEL_URL='http://127.0.0.1:8012'
$env:LITERATURE_GENERATION_MODEL='qwen2.5:1.5b'
$env:LITERATURE_EMBEDDING_MODEL='hash-512-v1'
```

Then start/restart the backend using the normal project command. In Literature Intelligence, select **Load 60-paper licensed starter corpus** for the signed-in organization. The corpus is not inserted automatically into a user's database.

The bootstrap verifies download hashes and records the selected versions in `.runtime/literature/runtime.json`. This workstation downloaded llama.cpp b10867 and Qwen2.5-1.5B-Instruct Q4_K_M at model revision `91cad51170dc346986eccefdc2dd33a9da36ead9` (Apache 2.0). Model SHA-256: `6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e`. The server binds to loopback; startup disables its web UI and restricts browser origins. CPU response times depend on hardware.

Alternatively, `docker-compose.literature.yml` supplies the Ollama model service alongside the normal Compose stack. See `backend/.env.literature.example`. Docker Desktop could not start on this workstation; the native CPU path is provided independently.

## Database and deployment

Migrations 008–011 add literature documents/chunks, intake batches/provenance/revisions, case metadata/audits and unique external embryo identifiers, following existing migration 007. Apply the normal Alembic upgrade procedure to the intended deployment database. No live user database migration, historical rewrite, or production deployment was performed. Application startup continues the project's existing table-registration behavior.

The new endpoints are `/intake/*`, `/case-timeline/{transfer_id}/timeline`, and `/literature/*`. Existing role and organization context controls access. New source records are immutable through these application routes; this is not tamper-proof database storage.

## Verification

Automated integration coverage includes schema validation, lineage, organization isolation, roles, duplicates, transactional/replay behavior, source revisions/downloads, migration upgrade/downgrade, corpus license/checksum/idempotence, persisted indexing, both model adapters, invalid citations and model outage fallback. Tests use isolated databases. The production frontend build passes. Browser smoke checks exercised loading the corpus, evidence retrieval, manual creation and case timeline in a separate temporary database.

`backend/scripts/smoke_literature_rag.py` exercises the actual downloaded CPU model against the bundled corpus and writes `outputs/literature-rag-smoke.json`. This is software integration evidence, not a scientific performance benchmark. The model can abstain when it cannot support an answer.

## Scope boundaries

Real-data prediction training, grading validation, model cards for prediction, dashboard analytics and QC remain outside this change because their modules were explicitly excluded. Researcher outreach was not sent. Previously stored historical records are not retroactively asserted to have verified sources. Full release acceptance across excluded modules requires their separate assessment.
