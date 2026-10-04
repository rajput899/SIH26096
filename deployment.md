# SIH26096 — Local Development and Deployment

## Implemented boundary

compose.yml configures five services: Next.js frontend, FastAPI backend, PostgreSQL, Qdrant and Ollama. See status.md for actual verification and blockers. Phase 1 adds archive schema, staff authentication, original storage and ARCHIVE UI. Phase 2 adds a PostgreSQL worker, local OCR/PDF extraction and curator text review. Phase 3 adds the visitor kiosk and source-grounded local research path; see the Phase 3 section below for model/runtime acceptance. Translation and voice input remain deferred. No model downloads occur automatically.

## Prerequisites and configuration

Use Docker Desktop with a running Linux engine (or Docker Engine on Linux) and Docker Compose. Confirm `docker info` succeeds in the terminal performing setup. Python 3.13 runs the setup/smoke scripts and optional host backend; Node.js 22.14+ runs optional host frontend/testing. Initial downloads need network access; no paid external API is used.

From the repository root:

```powershell
python scripts/init_env.py
docker compose config --quiet
docker compose up -d --build --wait --wait-timeout 240
docker compose ps
python scripts/check_foundation.py
```

The initializer creates ignored `.env` from `.env.example` with a cryptographically random database password. It never prints the secret or overwrites an existing file. Empty passwords fail validation. Do not commit `.env` or share fully interpolated Compose output; use `config --quiet`.

Configuration covers database connection fields, Qdrant URL, Ollama provider/base URL/optional model names, bounded health timeout, server-only backend URL and frontend/backend host ports. Passwords remain separate from URLs. Port changes require matching smoke-test/Playwright URL overrides.

Changing POSTGRES_PASSWORD after database initialization does not rotate the existing database credential. Keep the original configuration, or deliberately rotate through PostgreSQL and then update configuration. Do not delete volumes to resolve routine configuration mistakes.

## Local topology and health contract

- Frontend: http://localhost:3000. Browser calls same-origin `/api/health`; Next.js calls FastAPI through server-only BACKEND_INTERNAL_URL. No browser database secrets or permissive CORS.
- Backend: http://localhost:8000. `/health/live` returns 200 for process liveness. `/health/ready` returns 200 only when all required dependency probes pass, otherwise 503 with sanitized errors. API documentation is at `/docs`.
- PostgreSQL probe authenticates and executes `SELECT 1`. Qdrant probe calls `/readyz` and `/collections`. Ollama probe calls `/api/tags`.
- Only frontend/backend ports are published, bound to loopback. PostgreSQL/Qdrant/Ollama remain inside the Compose network. Named volumes persist their data.
- PostgreSQL and Ollama have container health checks. Qdrant is checked by backend readiness without assuming curl exists in its image. Backend readiness therefore gates full Compose health.

The LLM protocol exposes only a configuration/connectivity probe. `LLM_PROVIDER=ollama` is the only enabled provider; unsupported providers and external Ollama URLs are rejected. Compose sets `OLLAMA_NO_CLOUD=1`. Model names default to empty: a reachable server without models is valid in Phase 0. Explicitly configured missing models fail readiness. This is not inference or embedding-dimension validation.

Inspect installed models using `docker compose exec ollama ollama list`. Do not pull models in this phase. Host Ollama is a later deployment option requiring corresponding Compose dependency changes; the current target is the full Compose topology.

## Tests after startup

```powershell
docker compose exec backend python -m pytest -p no:cacheprovider -m "not integration" -q
docker compose exec -e RUN_INTEGRATION=1 backend python -m pytest -p no:cacheprovider -m integration -q
docker compose exec backend python -m ruff check --no-cache app tests
docker compose exec backend python -m ruff format --check app tests
docker compose exec frontend npm run lint
docker compose exec frontend npm run typecheck
docker compose run --rm --no-deps frontend npm run build
```

The separate build container avoids modifying the running development server's `.next` directory. Both images are development images including test dependencies.

Browser checks run from a host terminal:

```powershell
cd frontend
npm ci
npx playwright install chromium
npm run test:e2e
```

Playwright covers the real page/backend report, a strict all-dependencies-ready assertion, and an explicitly simulated API failure followed by recovery to the real response. The strict readiness test must pass before foundation completion. Synthetic unit tests are not evidence of live database or model-server connectivity. Set PLAYWRIGHT_BASE_URL when changing the frontend port.

## Optional host development

Compose is the default. For frontend hot reload on the host, stop the Compose frontend first, then from `frontend` copy `.env.example` to `.env.local` only if no customized file exists, run `npm ci`, and run `npm run dev`. Its example uses `BACKEND_INTERNAL_URL=http://127.0.0.1:8000`.

For the host API, stop the Compose backend to free its port, then from the repository root:

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
backend/.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --env-file .env --host 127.0.0.1 --port 8000
```

Default service hostnames resolve only inside Compose. A host API can prove liveness but reports degraded dependencies unless explicitly given reachable local services. Prefer the Compose API for real dependency verification. Do not claim the host liveness check establishes the complete stack.

Resolved packages are pinned in frontend/package-lock.json and backend/requirements.txt. The Python lock is generated from requirements-dev.in (including requirements.in). Regenerate deliberately with `uv pip compile backend/requirements-dev.in --python-version 3.13 --output-file backend/requirements.txt`, then retest. uv is an optional development resolver, not an application service.

## Restart, shutdown and environment troubleshooting

```powershell
docker compose logs --tail 80 backend frontend
docker compose restart
docker compose down
```

Do not append `--volumes` during routine teardown. Source edits require rebuilding the relevant image (`docker compose up -d --build`); host development offers hot reload.

A missing Docker engine pipe means the engine is not available. A permission-denied error on dockerDesktopLinuxEngine requires a terminal with authorized Docker access. This agent environment may not support granting named-pipe access. Windows `spawn EPERM` can block Next.js/Playwright subprocesses even when static checks work. Run the above workflow from an authorized local terminal and retain the results; neither blocker counts as a passed runtime test.

## Later deployment and preservation

Worker jobs, comprehensive staff management, coherent PostgreSQL-plus-files backups and tested restore belong to later phases. Volumes alone are not backups. Before external hosting, add TLS, controlled origins, appropriate secrets and institutional access policy. Hosting provider/hardware remain undecided; Kubernetes, microservices and paid LLM APIs are not required.

Implementation references: [Next.js installation](https://nextjs.org/docs/app/getting-started/installation), [Tailwind with Next.js](https://tailwindcss.com/docs/installation/framework-guides/nextjs), [FastAPI containers](https://fastapi.tiangolo.com/deployment/docker/), [Compose startup order](https://docs.docker.com/compose/how-tos/startup-order/), [Ollama model-list API](https://docs.ollama.com/api/tags), [Ollama local-only configuration](https://docs.ollama.com/faq).

## Phase 1 operation

Existing dependencies are unchanged. Rebuild only changed application images:

```powershell
docker compose up -d --build --wait --wait-timeout 240 backend frontend
docker compose exec backend python -m app.staff YOUR_LOGIN --role admin
```

Provisioning prompts twice for a password (minimum 12 characters), stores PBKDF2-SHA256 with a random salt, and refuses duplicate logins. No default account or seeded password exists. Use `--role curator` for review/publish access without upload permission. Staff passwords are entered at `/archive`; authorization is kept only in page memory and cleared on sign-out/reload. HTTP Basic is supported only over the existing loopback-only local deployment; TLS is required before external exposure. Password recovery, account-management UI and brute-force protection remain future institutional management work.

Open http://localhost:3000/archive, sign in, supply verified source and record URLs, rights, language and metadata, confirm permission and upload a PDF/PNG/JPEG/UTF-8 text file (10 MiB maximum). Downloads use attachment disposition. Format checks validate signatures/UTF-8, not complete file structure or malware. Uploaded records appear immediately in the staff list. Review the original, then confirm metadata/provenance/rights review; publish in a separate action. Public listing/download requires BOTH published status and public access. Withdraw removes public visibility immediately.

API prefix `/archive` (frontend same-origin proxy `/api/archive`):

- `GET /documents`: public published metadata, newest 200.
- `GET /staff/me`, `GET /staff/documents`: authenticated role and staff metadata list.
- `POST /staff/documents?metadata=<URL-encoded JSON>`: admin upload; request body is raw file bytes with the correct Content-Type. Metadata fields are defined in `app/archive.py` `Metadata`. This avoids adding a multipart dependency. Metadata is not secret; never put credentials in the URL.
- `POST /staff/documents/{UUID}/transition`: JSON action verify, publish, or withdraw; verify requires `metadata_reviewed: true`.
- `GET /documents/{UUID}/original` and `GET /staff/documents/{UUID}/original`: access-checked, checksum-checked original attachments.

The backend automatically applies versioned SQL migrations before serving. `archive_data` preserves originals across container recreation. Do not remove volumes. The archive volume is not a backup.

Run actual PostgreSQL/file workflow tests without adding archival holdings:

```powershell
docker compose exec -e RUN_INTEGRATION=1 backend python -m pytest -p no:cacheprovider -q
```

Archive integration tests create random isolated PostgreSQL schemas and temporary storage, use explicitly synthetic content, then remove the test schemas. They never seed public holdings. Production archival material must be supplied with checked permissions. Archive listing is capped at 200; pagination, metadata editing/tags and historical-date entry are deferred.

## Phase 2 operation and verification

Build the changed application images and new worker from the same backend codebase (existing volumes are retained):

```powershell
docker compose up -d --build --wait --wait-timeout 240 backend frontend worker
```

Backend startup applies migration 002 transactionally. The worker mounts originals read-only and writes text only to PostgreSQL. The image includes pinned RapidOCR/ONNX Runtime/pypdfium2 dependencies and the OCR models shipped inside the RapidOCR wheel. Build-time initialization checks the model runtime. Processing uses explicit local model files and does not fetch source URLs or models. Native OpenCV requires libgl1/libglib2.0-0 in the Debian image.

In ARCHIVE, sign in as curator/admin, open a record's Document processing and text review section, select automatic embedded-text/OCR or forced OCR, and queue extraction. Refresh processing status until succeeded/failed. Compare each physical page with the downloaded original, edit text, supply a review note and save a new reviewed revision. Review history is selectable and read-only. Confirm original comparison, then verify current text. Metadata verification/publication remain separate existing actions. Saving later corrections withdraws the record from public visibility and requires reverification/republication.

Staff API additions under `/archive/staff/documents/{id}` (same-origin proxy supported):

- POST `/processing` with `{ "mode": "auto" }` or `{ "mode": "ocr" }`; idempotent for the existing mode/job.
- GET `/processing`; POST `/processing/retry` for failed jobs below three attempts.
- GET `/text` or `/text?revision=N` for ordered pages and retained history.
- POST `/text/revisions` with `base_revision`, `pages: [{sequence, text}, ...]` (every existing page exactly once) and `note`. Stale edits return 409; invalid page lists return 422.
- POST `/text/verify` with `revision` and `original_compared: true`; only current reviewed text is eligible.

Limits: 50 PDF pages, 20 million rendered/image pixels, 100,000 characters per page, 180-second job timeout by default. Scanned PDFs render at 2x PDF points (144 dpi); quality is not guaranteed for small text. OCR confidence is a review aid, never proof of correctness. Failed or timed-out jobs store no partial text revision. Crash leases recover after 90 seconds. A database outage leaves committed jobs durable for the worker to resume.

Full isolated processing verification from a normal authorized Windows terminal:

```powershell
powershell -File scripts/check_phase2.ps1
```

The script builds changed services, runs six processing tests against real PostgreSQL, static checks, a production frontend build, then a Playwright processing/review flow. It creates a random isolated database schema and temporary file storage, uses an explicitly synthetic two-page scanned PDF and shuts down its test processes. It requires existing host frontend dependencies and installed Chrome (override `-BrowserExecutable` if needed); it does not install a browser or seed production archival records. `work/phase2-e2e.pdf` is a synthetic test artifact. Use localhost for the isolated Next.js development origin.

For backend processing tests alone:

```powershell
docker compose exec -e RUN_INTEGRATION=1 backend python -m pytest -p no:cacheprovider tests/test_processing.py -q
```

See status.md for what was actually executed. An unrun script is not acceptance evidence. Docker named-pipe permission failures must be resolved in the task/terminal permissions; no alternative database or mocked persistence is substituted.
# Phase 3 kiosk and research assistant — 2026-09-28

Phases 0–2 remain installed. Do not recreate volumes, reset the database or reinstall dependencies. Migration 003 adds search derivatives and answer evidence. The existing worker performs extraction first, then indexing.

## Run and verify from Windows PowerShell

Prerequisites: existing Docker Desktop Linux engine, existing `.env`, foundation services, local Node/Playwright setup and Chrome. Ports 3001 and isolated backend port 8011 must be free. Changed application images are built with existing dependency layers; no volumes are reset.

```powershell
Set-Location 'C:\Users\Hackathon\Documents\Codex\2026-09-24\we-are-starting-sih26096-completely-from'
.\scripts\check_phase3.ps1
```

The script runs PostgreSQL regression/research tests, Ruff, ESLint, typecheck, production build, and staff/processing/kiosk browser tests against a temporary database schema, temporary original-file storage and a separate Qdrant collection. It starts a disposable frontend on 3001 and cleans up fixture services, schema, credentials and collection. Synthetic fixtures never enter production. Screenshots/traces remain under `frontend/test-results`.

Primary kiosk: http://localhost:3000. Staff: `/staff`. Service diagnostics: `/system`.

Expected baseline final output:

```text
PASS: Phase 3 baseline runtime suite. Real model acceptance NOT RUN; repeat with -RunAI after configuring installed models.
Manual acceptance still required: listen to local speech, screen-reader navigation, touch hardware and legitimate archival source questions.
```

A passing baseline is NOT full Phase 3 acceptance. `-RunAI` requires a real cited model answer and successful semantic indexing. Mocked responses cannot satisfy that test.

## Model configuration

Both model settings currently remain empty. Inspect installed models:

```powershell
docker compose exec ollama ollama list
```

Choose an installed local instruction/chat model that follows Ollama's JSON-schema format. Set `OLLAMA_GENERATION_MODEL` in the existing `.env` to its exact name/tag. Do not assume installation because Ollama is healthy. Application code never downloads models.

Suggested multilingual embedding option: BAAI BGE-M3, MIT licensed ([model card](https://huggingface.co/BAAI/bge-m3), [Ollama package](https://ollama.com/library/bge-m3)). It has NOT been tested on this machine. If you choose it and it is not installed, this explicit command downloads the weights and needs internet, disk space and RAM:

```powershell
docker compose exec ollama ollama pull bge-m3
```

Edit only relevant nonsecret settings in `.env`, retaining existing database credentials:

```dotenv
# Replace this placeholder with the exact installed generation model.
OLLAMA_GENERATION_MODEL=your-installed-model
OLLAMA_EMBEDDING_MODEL=bge-m3
RESEARCH_COLLECTION=verified_archive_v1
GENERATION_TIMEOUT_SECONDS=45
```

Generation timeout permits 5–60 seconds. Worker embedding calls allow 30 seconds per batch; query embedding calls allow 12 seconds. Cold loading or slow hardware may return unavailable; retry after warming the model. Model quality, latency and language support still need actual testing.

```powershell
.\scripts\check_phase3.ps1 -RunAI
# Optional browser location:
.\scripts\check_phase3.ps1 -RunAI -BrowserExecutable 'C:/path/to/chrome.exe'
```

Expected automated final success with models:

```text
PASS: Phase 3 automated runtime suite, including real Ollama/Qdrant acceptance
```

The script applies settings by recreating changed application containers. To supply real holdings: Staff → permitted original upload → extraction → reviewed revision → text verification → metadata verification → explicit publication. Indexing follows asynchronously. Only CURRENT verified, public, published text is eligible.

## Degraded operation and remaining acceptance

- Missing generation model: clear unavailable response with retrieved verified excerpts. No reliable retrieved content: insufficient-evidence response without generation.
- Missing embeddings or Qdrant: PostgreSQL text search with an explicit semantic-search warning. Catalogue/original/verified reading stays available independently.
- Backend/worker startup does not wait for Ollama health; dependency readiness still reports degradation. `compose --wait` can fail for unhealthy AI services while ordinary archive routes remain usable.
- Different embedding dimensions require a new `RESEARCH_COLLECTION` name on backend and worker. No destructive automatic recreation. Model digest changes trigger reindexing; ready records inspect identity every five minutes, failures retry every minute.
- Visitor questions/context stay in page memory; clear conversation, End session and inactivity clear them. Generated summaries/evidence are stored in PostgreSQL for provenance and invalidated when sources change. No public answer-history endpoint exists.
- Browser fullscreen uses an explicit visitor action; Escape/Exit Kiosk Mode exits. It does not lock Windows. Staff stays accessible. Inactivity warns after five minutes and resets after six; Continue my visit extends it.
- Text size, contrast, reduced motion and partial English/Hindi main navigation are implemented. Other English controls retain English semantics. This is not content translation.
- Read-aloud requires installed local voices. Missing support is reported. Audio guide, pages, excerpts and answers share Pause/Resume/Stop. Automated API simulation does not establish audible output. Voice input is not implemented.

Before completion, record actual suite output and manually verify keyboard traversal, screen-reader landmarks/announcements, audible speech controls, portrait/landscape with enlarged text, touch hardware, fullscreen and session clearing. Also test one permitted real published source against its citations/original, an unsupported question and unavailable model/vector services. UI existence alone is not acceptance.


## Heritage deployment extension — 2026-09-29
See [HERITAGE_VERIFICATION.md](HERITAGE_VERIFICATION.md) for the exact owner-run regression/browser commands, optional Gemini and SMTP setup, and manual acceptance. Keep all existing volumes. Backend image adds ffmpeg/ffprobe and the pinned official google-genai SDK; no frontend secret environment variables are added. Migration 004 runs through the existing migration mechanism. Docker runtime acceptance of this extension is pending; do not confuse the existing running image with newly edited source.

## Migration 005 and second-session runtime checks
Migration 005 is additive and runs automatically at backend startup through the existing migration ledger. It connects newly verified recording cue snapshots to immutable research text with start/end seconds. It never changes originals or publishes records. Existing pre-005 recording transcripts need a new reviewed revision and explicit verification before becoming searchable; no production recordings existed during this session. Preserve all existing environment settings and volumes. No new package dependencies or secret settings were introduced by the second session.
Docker was accessible with approved elevated execution in this session. Use HERITAGE_VERIFICATION.md and status.md for current results; earlier named-pipe blockers describe the previous sandbox attempt. Local Windows Next build still reports spawn EPERM, while the Docker production build passes.
