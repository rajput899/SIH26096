# SIH26096 — Project Status
## Runtime/source mismatch and kiosk repair — 2026-10-01 (latest)

**Actual visible UI verified at http://localhost:3000.** This entry supersedes earlier runtime availability statements. Docker backend/database are now running; they were not started or restarted by this task.

### Diagnosed before editing

The old local Next process was no longer serving port 3000. `Get-NetTCPConnection` identified Docker backend PID 28068. `docker compose ps` showed `sih26096-frontend-1` running `npm run dev`; `docker inspect` showed `/app` working directory and NO source mounts. Reading its `src/app/page.tsx` confirmed FOUR cards, while workspace `frontend/src/app/page.tsx` already had SIX. The container used an older source copy baked into its image. This was a serving-source mismatch, not a rollback of the workspace. Container package.json/package-lock.json/next.config.ts hashes matched workspace, so no dependency reinstall/image build was needed.

Chrome screenshots and DOM checks before repair found one main per route (`/`, `/archive`, `/experience`, `/speeches`, `/ai`), four homepage cards, no homepage/speeches duplicate rendering. Real speeches response showed zero published recordings. The sticky bottom accessibility bar covered page content. Source inspection found the six-minute inactivity reset installed for ALL visitors, and End session displayed outside kiosk mode. Header/hero visually had separated lines; raw textContent concatenated adjacent inline text across a line break. Added explicit whitespace for these text boundaries without redesigning typography.

### Changes and preservation

- `compose.yml`: frontend-only read-only `./frontend/src:/app/src:ro` mount so dev serves current workspace through subsequent Docker restarts. Recreated only frontend using `docker compose up -d --no-deps --no-build frontend`. Same port 3000; no alternate preview, image rebuild, dependency startup or database action.
- `frontend/src/components/Kiosk.tsx`: idle timer and End session restricted to browser fullscreen kiosk mode; scroll counts as kiosk activity. Reset message appears only on home and expires after ten seconds. Brand text boundary has explicit whitespace. Added route-appropriate speeches audio-guide wording. Existing audio controls and local-voice requirement preserved.
- `frontend/src/app/globals.css`: accessibility footer in normal flow, expanded settings occupy their own row, no nested settings scroll area, flexible labels/navigation; mobile header in normal flow and brand can wrap. Established colors/card shapes/typography retained.
- `frontend/src/app/page.tsx`: only explicit whitespace at hero line boundary; preserved all SIX existing boxed cards and current Media/manuscript routes. Media retains photo/video Archive routes; audio remains `/speeches`.
- `frontend/tests/runtime-repair.spec.ts`: live route/zero-recording checks, ordinary browsing vs kiosk timers, enlarged-text desktop/mobile accessibility checks.
- `frontend/tests/kiosk.spec.ts`: existing navigation regression now enters kiosk before ending its session, consistent with intended behavior.
- `status.md`, diagnostic scripts `inspect-runtime.cjs`, `work/inspect-runtime.cjs`, `work/inspect-runtime-final.cjs`, `work/check-runtime-viewport.cjs`, and outputs recorded below.

Workspace baselines and complete old container source preserved under `work/runtime-repair-baseline`; reviewable changes in `outputs/runtime-repair-source.diff`. No Git repository (`git status --short` failed); checkpoints/diffs used instead. Backend, postgres and worker IDs/start timestamps match exactly before/after (`outputs/runtime-services-before.log`, `outputs/runtime-services-after.log`). No originals, OCR, rights, publication, records, migrations or authorization code changed.

### Commands and results

Read-only diagnosis included `Get-Content` of homepage/layout/Kiosk/globals.css/CollectionNavigation/Archive/Speeches/status and checkpoint diffs; `rg --files frontend/src/app`; `Get-ChildItem work`; `Get-Content frontend/AGENTS.md` and installed Next layouts/pages guide. Initial guide lookup using `.mdx` failed; actual `.md` guide was found/read. Process inspection without elevation once returned Access denied; approved read-only elevated inspection succeeded. An early log read preceded log creation and reported missing typecheck/build files; later reads confirmed completion.

```powershell
Get-NetTCPConnection -LocalPort 3000 -State Listen | Select-Object LocalAddress,OwningProcess | ConvertTo-Json
Get-CimInstance Win32_Process -Filter 'ProcessId = 28068' | Select-Object ProcessId,Name,CommandLine | ConvertTo-Json
docker compose ps
docker inspect sih26096-frontend-1 --format '{{json .Config.WorkingDir}} {{json .Mounts}} {{json .Config.Cmd}}'
docker exec sih26096-frontend-1 cat src/app/page.tsx src/app/layout.tsx
docker exec sih26096-frontend-1 sha256sum src/components/Kiosk.tsx src/app/globals.css src/app/page.tsx
docker exec sih26096-frontend-1 sha256sum package.json package-lock.json next.config.ts
Get-FileHash frontend/package.json,frontend/package-lock.json,frontend/next.config.ts -Algorithm SHA256
node inspect-runtime.cjs
docker cp sih26096-frontend-1:/app/src work/runtime-repair-baseline/container-src
docker inspect sih26096-backend-1 sih26096-postgres-1 sih26096-worker-1 --format '{{.Name}} {{.Id}} {{.State.StartedAt}}' > outputs/runtime-services-before.log
docker compose up -d --no-deps --no-build frontend > outputs/runtime-frontend-refresh.log 2>&1
docker inspect sih26096-backend-1 sih26096-postgres-1 sih26096-worker-1 --format '{{.Name}} {{.Id}} {{.State.StartedAt}}' > outputs/runtime-services-after.log
Compare-Object (Get-Content outputs/runtime-services-before.log) (Get-Content outputs/runtime-services-after.log)
docker inspect sih26096-frontend-1 --format '{{json .Mounts}}'
npm.cmd --prefix frontend run lint > outputs/runtime-lint.log 2>&1
npm.cmd --prefix frontend run typecheck > outputs/runtime-typecheck.log 2>&1
npm.cmd --prefix frontend run build > outputs/runtime-build.log 2>&1
```

Lint/typecheck/production build PASSED. Production build ran locally; Docker still runs dev with mounted source. Compare-Object produced no differences; mount inspection shows RW:false. No backend feature success is inferred from container health.

```powershell
$env:PLAYWRIGHT_BASE_URL='http://localhost:3000'
$env:ARCHIVE_E2E_BROWSER='C:\Program Files\Google\Chrome\Application\chrome.exe'
npm.cmd --prefix frontend run test:e2e -- tests/runtime-repair.spec.ts tests/main-homepage.spec.ts tests/collections.spec.ts tests/content-states.spec.ts tests/reader-quiz.spec.ts --workers=1 --output=../outputs/runtime-browser > outputs/runtime-browser.log 2>&1
npm.cmd --prefix frontend run test:e2e -- tests/kiosk.spec.ts --grep 'visitor navigation|browser fullscreen|read-aloud controls' --workers=1 --output=../outputs/runtime-kiosk-browser > outputs/runtime-kiosk-browser.log 2>&1
npm.cmd --prefix frontend run test:e2e -- tests/runtime-repair.spec.ts --workers=1 --output=../outputs/runtime-browser-final > outputs/runtime-browser-final.log 2>&1
node work/inspect-runtime-final.cjs
node work/check-runtime-viewport.cjs > outputs/runtime-viewport.log
npm.cmd --prefix frontend run lint > outputs/runtime-lint-final.log 2>&1
```

First browser run: **13 passed / 1 failed** (test selector for Text size timed out; UI exposed correct combobox). Corrected test to `getByRole('combobox', {name:'Text size',exact:true})`. Final runtime suite **3 passed**; existing kiosk suite **3 passed**. Combined final coverage: **17 distinct passing regressions**, with initial failure retained. Tests verify six boxed cards at desktop/tablet/mobile, Media and manuscripts/back/home routes, independent main rendering, real empty recordings, ordinary draft survives seven simulated minutes, kiosk warning/continue/manual reset/timeout/exit, 140% text size, Hindi navigation, contrast/motion, footer does not cover main, fullscreen enter/exit. Existing source-reader/quiz/collection content cases remain mocked. Speech API controls/missing-voice handling were simulated, not a listening test.

Screenshots inspected from `outputs/runtime-browser-final` and `outputs/runtime-home-final.png` plus mobile controls. Full-page screenshots taken while scrolled can reposition sticky/fixed chrome in the capture; viewport evidence is recorded separately. Browser screenshots are actual localhost:3000, not another preview.

Unverified: live AI generation, audible local speech quality, recording playback/synchronization, physical touchscreen and backend private/withdrawn file authorization were not exercised in this UI repair. No content was published. Zero published recordings is an actual successful API empty state, not fabricated content or a hidden service error. Earlier letters registration/review gaps remain outside this repair.

## Reader, private letters reconciliation and quiz UI — 2026-10-01 (latest)

Checked the existing application at **http://localhost:3000**. Earlier entries below are historical; in particular their Docker/preview state is superseded by this entry. Preserved all six homepage cards and existing Media/photo/video routes and `/speeches`. No backend/database restart, publication, rights changes, original copying or OCR processing occurred.

Changes:
- `frontend/src/app/archive/[id]/page.tsx`: original image/scan left, reviewed transcription right on desktop; stacked on phones. Source details below transcription, then existing source-scoped AI. Added title, unknown date/confidence, text review and publication indicators. Empty approved text explicitly disables source AI. Video assistant uses the same scoped endpoint and reviewed source responses; existing protected playback/caption component retained.
- `frontend/src/app/globals.css`: reader column order and wrapping; quiz question/option alignment, responsive sizing, focus/disabled styles and text-labelled correct/incorrect feedback.
- `frontend/src/app/quiz/[id]/page.tsx`: wrapped option text, disabled answer fieldsets while submitting, per-answer feedback from returned reviewed answer. Server scoring, certificate and consent requests unchanged.
- `frontend/src/components/CollectionBrowser.tsx`: existing Manuscripts & Letters notice links to curator workspace with explicit identification/rights/text review steps.
- `frontend/tests/reader-quiz.spec.ts`: three fixture-based browser regressions for reader layout and scoped questions, video citations/unavailable state, and long quiz options/scoring response/opt-in state.
- `outputs/letters-reader-inventory.json` and `outputs/LETTERS_READER_REVIEW.md`: private filename/path/SHA-256 reconciliation for every letters-folder candidate, matching OCR derivative and review gaps. No OCR text copied into public files. Baselines saved under `work/reader-quiz-baseline`; diff saved to `outputs/reader-quiz-source.diff`.

Dataset result: **25 of 25 JPEG files accounted for; 25 matching existing OCR derivatives with text; zero newly registered or published records.** Complete original filenames are listed in `outputs/LETTERS_READER_REVIEW.md`; exact paths and hashes are in the JSON inventory. All are unidentified candidates, rights unverified, OCR unreviewed. Prior `outputs/collections-inventory.json` had no corresponding archive records; this is a prior snapshot, not current database proof. The collection has NOT been populated with these files: live registration and authenticated curator discovery remain blocked. Existing bulk corpus importer supports PDF/audio/video but not JPEG record creation; ordinary upload requires truthful provenance confirmation. Do not invent that confirmation, automatically publish, or repeat OCR to work around this limitation. The private report provides curator reconciliation steps and the UI links to the existing staff workspace.

Validation actually executed:
- `npm.cmd --prefix frontend run lint > outputs/reader-quiz-lint.log 2>&1` — passed.
- `npm.cmd --prefix frontend run typecheck > outputs/reader-quiz-typecheck.log 2>&1` — passed.
- `npm.cmd --prefix frontend run build > outputs/reader-quiz-build.log 2>&1` — passed, exit 0; production compilation only, did not replace/restart running services.
- `$env:PLAYWRIGHT_BASE_URL='http://localhost:3000'; npm.cmd --prefix frontend run test:e2e -- tests/main-homepage.spec.ts tests/collections.spec.ts tests/content-states.spec.ts tests/reader-quiz.spec.ts --workers=1 --output=../outputs/reader-quiz-browser-artifacts > outputs/reader-quiz-browser.log 2>&1` — 11 failed to launch: bundled Playwright Chromium executable absent. No application assertion ran in this attempt.
- `$env:PLAYWRIGHT_BASE_URL='http://localhost:3000'; $env:ARCHIVE_E2E_BROWSER='C:\Program Files\Google\Chrome\Application\chrome.exe'; npm.cmd --prefix frontend run test:e2e -- tests/main-homepage.spec.ts tests/collections.spec.ts tests/content-states.spec.ts tests/reader-quiz.spec.ts --workers=1 --output=../outputs/reader-quiz-browser-chrome > outputs/reader-quiz-browser-chrome.log 2>&1` — **11 passed (20.7 seconds)** in installed Chrome. Actual homepage and same-origin navigation; API content, AI answers/citations and quiz responses are mocked. Checked desktop/mobile reader and quiz wrapping, all six cards at 1366/768/390, Media→photos/videos, audio→speeches, collection errors/retry/empty states, source ID in AI POST, page/timestamp citation rendering, missing approved text, server-returned score display and unchecked/disabled voluntary sharing. Screenshots retained and visually inspected (desktop homepage/reader, mobile quiz).
- `npm.cmd --prefix frontend run lint > outputs/reader-quiz-lint-final.log 2>&1` and `npm.cmd --prefix frontend run typecheck > outputs/reader-quiz-typecheck-final.log 2>&1` — both passed after test additions.
- Read-only `docker compose ps` — daemon responds now; only worker shown, restarting. HTTP request to `http://localhost:3000` returned 200; `http://localhost:8000/health/live` connection refused. `git status --short` unavailable: directory has no Git repository. Existing checkpoint/diff files inspected instead.
- Dataset reconciliation and unified checkpoint diff were generated using inline Python via `python -X utf8 -`, reading the actual Dataset/Ambedkar_letters files, SHA-256, existing outputs/dataset-image-review derivatives and prior inventory. Files were not classified from names. See manifests for exact inputs/results.

Not verified / blocked: live current database membership, ingestion, staff-only/unpublished/withdrawn API authorization and protected original/thumbnail/playback URLs; live Gemini/local-model grounding; real OCR source accuracy/page identity pending curator review; real video/audio playback or synchronization; certificate generation/email delivery; touchscreen behavior. Mocked tests do not establish those properties. No content was made public. To finish population, an authorized operator must restore backend availability separately, reconcile current checksums, register unresolved images privately through a provenance-safe ingestion path, attach existing derivatives, and review identification/source rights/text before any separate publication action. Do not restart services automatically for this task.

Additional final checks: inline Python `urllib.request.urlopen` requested each of the 25 exact dataset paths and each checksum-matched OCR derivative path at localhost:3000 (URL-encoded, 20-second timeout). **50/50 returned HTTP 404**; results are in `outputs/reader-quiz-direct-path-check.json`. This verifies static-path non-exposure only, not backend authorization. `Get-NetTCPConnection -LocalPort 3000 -State Listen | Select-Object LocalAddress,LocalPort,OwningProcess` identified PID 1864. `Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'node.exe' -and $_.CommandLine -match 'next' } | Select-Object ProcessId,CommandLine | ConvertTo-Json` confirmed the server path is this project's `frontend/node_modules/next/dist/server/lib/start-server.js`, parent Next command `dev --hostname 0.0.0.0 --port 3000` (PID 12976). Final `(Invoke-WebRequest 'http://localhost:3000' -TimeoutSec 10).StatusCode` returned 200. No frontend restart was needed. One intermediate `Get-Content outputs/reader-quiz-source.diff -TotalCount 8` failed because the still-running path-check/diff script had not produced it yet; the subsequent read succeeded. All original failed-run logs and browser artifacts were retained.

Manual acceptance once services are restored: open localhost:3000, navigate all six cards; reconcile all 25 inventory rows in authenticated staff view; verify pending records and raw OCR are unavailable anonymously, including direct original/thumbnail/playback requests; approve only independently reviewed test records, compare scan/text/page citations, verify source-scoped AI and real timed captions; complete a quiz and optional certificate without email/leaderboard consent, then test explicit opt-in separately. Do not infer feature health from a reachable server.

## Main homepage correction — 2026-10-01

**Verified frontend URL: http://localhost:3000/** (HTTP 200 and actual Chrome tests). The existing four explore cards are preserved, with two matching fully clickable cards — Manuscripts & Letters and Media — in the same six-card grid. The Archive card is restored to its original single clickable surface. Media reuses existing Archive photo/video destinations; audio stays at `/speeches`. No new content was published. No other port was used for this continuation.

Docker's daemon is unavailable (named pipe not found); localhost:3000 initially refused connections. There was no running container source to identify. Compose/Dockerfile identify `frontend/src` as the configured application source; this continuation started **only** the existing local Next frontend from `frontend`, on port 3000, using that source. Backend/database services were not started, modified or restarted. Backend-dependent content/access verification remains BLOCKED, not passed.

Checks: source lint, typecheck and production build passed after resolving execution/generated-build issues; 8 targeted browser tests passed on localhost:3000. Actual homepage, responsive cards and relative navigation tested; recording/image content/error fixtures are mocked. Details and commands below supersede earlier runtime URLs/status claims.

## Targeted homepage / Archive correction — 2026-10-01

The separate homepage collection block is removed. The four established exploration cards remain; **only Manuscripts & Letters, Photographs and Videos** are linked inside The Archive card and the shared Archive navigation. `/speeches` remains the existing destination for approved audio/MP3 recordings; the old `collection=audio` entry redirects there. The requested preview is **http://127.0.0.1:3002/**. Original services at 3000/8000 were not restarted or modified.

Fresh targeted validation: frontend lint, typecheck and production build passed; 13 browser tests passed, followed by 5 passing collection/origin tests after final alignment adjustments; 1 isolated collection authorization test passed; all 403 restricted direct/proxy/static URLs were denied. Desktop/tablet/mobile screenshots inspected. No new content was published, classified or ingested. No live Gemini/email/ASR or physical touchscreen checks were run in this correction. Exact changed files, commands and limitations are in the final section below. Earlier collection-card layout descriptions are historical and superseded by this entry.

## Collection continuation — verified 2026-10-01

Implemented homepage collection cards, protected collection browsing and current Service Status wording. **No real dataset images or recordings were published.** The 25 letter-folder images remain unclassified candidates; none has verified identity/public-display rights. Photographs and Videos now distinguish dataset membership from other approved archive records, with honest empty states. Existing readers preserve originals and show only reviewed text.

**Current-source preview:** http://127.0.0.1:3002. Existing services at 3000/8000 and the active OCR wrapper were not rebuilt, restarted or reset. The requested production build was run in disposable containers. No Git repository exists in this project directory; `git status --short` and `git diff --stat` failed accordingly. Source checkpoints remain in `work/collections-baseline`; reviewable source diff is `outputs/collections-source.diff`.

**Fresh results:** backend 79 passed / 2 optional live checks skipped; strengthened collection integration test 1 passed; current-source isolated browser workflows 12 passed; final collection + service browser tests 6 passed; content/redesign browser tests 8 passed in the earlier mixed run. Backend/audit Ruff, frontend lint, typecheck and final production build passed. A separate live Gemini question returned an answer with validated citations. 403 frontend proxy/direct/static URL requests denied restricted access; all 92 dataset and 33 stored-original hashes matched. Intermediate failures and exact verification commands are recorded below. Historical status claims are not substitutes for these results.

Dataset inventory at 2026-09-30T20:03:09Z is saved in `outputs/collections-inventory.json` and `outputs/COLLECTIONS_AUDIT.md`. OCR is still progressing independently; these counts are a snapshot, not completion. Compilation hold remains unchanged.

## Current content continuation — OCR in progress, 2026-10-01

The existing application is preserved. Recording discovery now distinguishes service errors, empty collections and unmatched filters; staff checkpoint previews show machine confidence. Fresh validation: backend 78 passed/2 optional live checks skipped; 4 wrapper safety tests; 12 isolated workflow tests; 8 focused browser tests; Ruff, frontend lint/typecheck/build passed. Live Gemini citation and abstention checks passed separately. Private Volume 16 research returned no evidence or generation.

**Active job:** `sih26096-backend-run-f7d808f93379`, one bounded sequential OCR wrapper, log `outputs/content-ocr-batches.log`. Do not restart or duplicate it. Pending work in Volumes 8–15 is complete; Volume 16 and the remaining non-held PDFs are being processed. This is not a completed processing claim. The last exact report is `outputs/CONTENT_AUDIT.md` / `outputs/content-inventory.json`; it is a snapshot during processing.

**Explicit hold:** The 13,824-page compilation is **awaiting curator identity and scope verification**. No OCR/import/index/publication/modification. Curator must establish identity/edition from reliable documentation, assess its relationship to separate volumes, and define intended processing scope. Filename/overlap is not proof. Its 1,305 pending pages remain held.

**Public coverage:** 2 reviewed PIB supplementary excerpts; no additional dataset record is eligible for public release or RAG. Review and rights decisions, image classification/registration, historical transcripts and authorized BHASHINI/ASR configuration remain outstanding. All 92 dataset hashes still match. No photograph publication or account/access changes.

Historical entries below remain preserved; final continuation entries record exact commands and outcomes.

## Latest continuation outcome — 2026-10-01

Archive, topic-led Experience, shared source reader, reviewed recording captions/highlighting, quiz UX and leaderboard placement are implemented in the existing app and running at http://localhost:3000. Historical entries below remain an audit trail; this summary and the final continuation entries supersede older empty-catalogue and runtime-blocker reports.

**Accepted checks:** Docker lint/typecheck/production build and Ruff passed; backend baseline 77 passed/2 optional live checks skipped, plus 1 new isolated cross-volume test passed; existing workflow browser suite 12 passed; final new browser suite **6 passed in 13.6s** (outputs/redesign-oct01-browser.log). Live Gemini produced a source-checked answer and abstained on an unsupported question. Media timing was tested with synthetic audio/video; video API was mocked. No live BHASHINI, ASR or SMTP, physical touchscreen, audible narration or screen-reader acceptance claimed.

**Preservation:** 92/92 Dataset hashes and 33/33 stored original hashes matched; record publication/access states unchanged; 124 restricted endpoint checks denied access correctly. Protected photograph remains unpublished. No account reset, access bypass, secret change, migration change or volume deletion. No Git metadata exists; pre-edit source/tests saved under work/redesign-baseline.

**Coverage and blockers:** 29 new private OCR pages processed in bounded batches; Volume_07 now awaits review, with 25 empty pages flagged. Corpus: 24,567/27,693 PDF checkpoint pages extracted, 3,126 OCR pending, 156 OCR pages, 124 empty pages; compilation overlaps other holdings and is held. Only the two reviewed PIB excerpts are published/indexed; they remain supplementary modern accounts. Further public RAG expansion requires reviewed text and confirmed display rights. BHASHINI/automatic ASR remain blocked by missing authorized configuration. These content/service phases are not complete.

Detailed changes, commands, intermediate failures, corrected regressions and manual acceptance checklist are in the final sections of this file.

## Current outcome — 2026-09-28

**Phases 0, 1 and 2: COMPLETE and verified, as confirmed by the owner.** Foundation, original preservation, PostgreSQL metadata, staff access, OCR/extraction, revision history and curator review/publication are retained. Earlier Phase 2 sandbox/harness blockers no longer describe that phase's acceptance.

**Phase 3: IMPLEMENTED IN THE WORKING TREE; RUNTIME ACCEPTANCE PENDING. Not complete.** The owner will run Docker/runtime checks from normal Windows PowerShell. This agent cannot access Docker's Windows named pipe. Existing containers were not rebuilt or updated in this turn, so they still serve the previous application image. No phase beyond Phase 3 was started.

## Phase 3 implementation present

- Welcome/home with AI / ARCHIVE / EXPERIENCE cards, shared navigation, back/home, staff/service links, responsive portrait/landscape styles and explicit empty/error/loading states. Existing staff upload/OCR/review/publication UI is retained at `/staff`; dependency diagnostics moved to `/system`.
- Public archive title/description search and language/material filters; document metadata/provenance, preserved-original viewing/download, verified text and real page locators. Requested older revision links return an explicit conflict instead of silently showing a different revision. Plain text never receives a fabricated page number.
- Migration 003 adds passage FTS indexing, durable search-index state and generated-artifact/evidence tables. Original files and extraction/review snapshots are not rewritten. The existing worker prioritizes OCR jobs, then builds idempotent page-bounded passages and optionally Ollama embeddings/Qdrant vectors.
- Local Ollama `/api/chat` structured generation and `/api/embed` embeddings through existing HTTP dependencies. Model names are configurable and remain unset locally. No model was installed or downloaded; no paid provider or extra retrieval framework was introduced.
- PostgreSQL FTS and Qdrant candidate fusion with language/material filters, current publication/revision authorization and embedding-model digest isolation. Generation requires retrieved current verified/public/published evidence. No-source and missing/invalid-model responses are explicit; excerpts remain available when generation fails.
- Every generated paragraph must have a retrieved passage ID and an exact source quote. Server resolves titles/pages/links. A second permission check under item locks rejects changed sources before storing or returning answers. Revision/access changes invalidate dependent artifacts and queue index maintenance. Exact quotes prove attribution, not full semantic correctness of every model paraphrase; visitors are told to inspect originals.
- AI UI has suggested questions, limited follow-up context (last four visitor questions), source excerpt panels, original/page links, clear/retry controls and labelled AI summaries. Questions stay in page memory; generated answers/evidence are retained for provenance. Navigating away from the AI route clears that page's conversation state.
- Accessibility settings change text size, contrast and motion; semantic controls, focus styles, skip link and announcements are present. Main navigation has English/Hindi labels; other UI remains English. This is partial navigation localization, not content translation.
- Read-aloud is implemented using installed LOCAL browser/system voices only, with guide/page/excerpt/answer controls and Pause/Resume/Stop. Missing support is reported. No voice recognition or voice commands. Actual audible output and assistive-technology compatibility are NOT yet accepted.
- User-triggered browser fullscreen with exit/error handling; this is not Windows lockdown. End session clears page memory. Inactivity warns at five minutes and clears at six, with Continue my visit available.
- EXPERIENCE is an honest introduction with archive/AI navigation and unavailable timeline/gallery/story descriptions. No fabricated exhibit, date, story or historical content.

## Actual checks in this turn

| Check | Actual result |
|---|---|
| Existing live HTTP API | Backend `/health/live` returned OK. `/archive/documents` returned zero public records. These were previous-image endpoints, not proof of Phase 3 runtime. |
| Local backend tests excluding integration | **PASS: 21 passed, 11 deselected**, 9.77s on final run. Includes three actual local OCR/extraction regression tests, foundation unit checks and six research unit/provider-contract checks. HTTP model contract tests use explicit mocks. |
| Local temporary directories | Standard pytest temporary directory was denied by Windows sandbox; used the existing ignored `work/phase2_pytest_paths.py` fixture override for local-only tests. Docker tests use normal isolated temporary directories. |
| Ruff | **PASS**, app and tests. |
| Frontend ESLint | **PASS**, whole frontend. |
| Next route type generation and TypeScript | **PASS**. |
| Production Next build | Compiled successfully in 16.9s, then failed spawning TypeScript worker with **`spawn EPERM`**. Full production build is NOT passed. |
| New PowerShell harness syntax | **PASS**, PowerShell AST parser, `scripts/check_phase3.ps1`. Runtime not run. |
| PostgreSQL migration / hybrid retrieval / artifact invalidation integration | **NOT RUN here**: Docker named-pipe restriction. Tests are prepared, not claimed passed. |
| Real Ollama/Qdrant answer acceptance | **NOT RUN**: model settings empty; runtime access unavailable. |
| New browser visitor/staff regression/fullscreen/responsive tests | **NOT RUN**. Prepared Playwright suite includes explicit speech-API/error simulations, which do not establish audible speech or real model inference. |
| Manual accessibility / touch / real archival research | **NOT RUN**. Required before completion. |

Known benign test warning: installed Starlette deprecates httpx TestClient integration; no overlapping HTTP dependency was introduced to silence it.

## Test and data boundaries

The regression/research suite creates temporary PostgreSQL schemas, temporary original storage and unique Qdrant collections. It tests real upload, extraction, review, separate publication, text persistence, physical PDF locators, lexical search, stale-vector exclusion, missing generation model and withdrawal during generation. The default model orchestration tests deliberately mock generation to test access/citation contracts. `RUN_AI_ACCEPTANCE=1` adds a separate real-model/vector test requiring an actual cited answer; a mock cannot satisfy it.

No real archival document was acquired and no synthetic record was added to production. Fixtures are labelled synthetic software tests with explicit nonhistorical provenance. A permitted, published real source is still necessary to evaluate historical answer quality. Earlier OCR acceptance demonstrates the fixture/workflow, not handwriting or all Indian-script accuracy.

## Changed files in this Phase 3 turn

- Backend: `app/config.py`, `app/llm.py`, `app/main.py`, `app/worker.py`; new `app/research.py`, `app/research_index.py`, `app/migrations/003_research.sql`.
- Backend tests: new `tests/test_research.py`; `tests/conftest.py`, `tests/serve_archive_e2e.py` add isolated vector-collection scope/cleanup.
- Frontend: `src/app/layout.tsx`, `globals.css`, home `page.tsx`, visitor `archive/page.tsx`, archive API proxy timeout; new `src/components/Kiosk.tsx`, `ai/page.tsx`, `archive/[id]/page.tsx`, `experience/page.tsx`, `staff/page.tsx`, `system/page.tsx`.
- Browser tests: new `tests/kiosk.spec.ts`; existing archive/processing/foundation tests updated for staff/system routes and shared accessibility controls.
- Operations/docs: `compose.yml`, `.env.example`, new `scripts/check_phase3.ps1`, `architecture.md`, `database.md`, `implementation.md`, `deployment.md`, `agent.md`, this `status.md`.
- No dependency manifests/locks changed. No edit to migrations 001/002, original-file storage code, processing API, OCR engine, curator-review component or Phase 2 verification script. Real `.env` secrets/settings were not changed.

## Run instructions and exact next action

From the project root in normal Windows PowerShell:

```powershell
.\scripts\check_phase3.ps1
```

This builds the changed app images, runs backend integration/regression checks, lint/typecheck, production build and isolated real browser flows. It preserves production data and cleans up fixture services/storage/schema/collection. See deployment.md for prerequisites, expected output and alternate browser path.

Inspect `docker compose exec ollama ollama list`, select an installed generation model and a suitable multilingual embedding model, and configure their exact names in the existing `.env`. BGE-M3 is a documented MIT-licensed multilingual candidate, NOT yet validated locally. Keep models configurable; there is no automatic download. Then run:

```powershell
.\scripts\check_phase3.ps1 -RunAI
```

Do not declare Phase 3 complete from the default suite alone. Record actual results, fix failures, then verify a permitted real published document, audible narration, screen-reader semantics, keyboard/touch traversal, large text, landscape/portrait and fullscreen entry/exit. No advanced timeline, gallery, stories, graph, translation, voice input, bulk ingestion or OS kiosk setup is included.
## Follow-up: homepage deployment diagnosis

Actual HTTP checks against localhost:3000 confirmed `/` still serves the foundation page, while `/system`, `/staff` and `/api/archive/catalog` return 404. The working-tree root is `frontend/src/app/page.tsx` (there is no `frontend/app/page.tsx`); it already renders the Phase 3 kiosk through the shared Kiosk layout. Source includes the system, staff and public archive routes. Compose builds from `./frontend`, Dockerfile copies source to `/app`, and no source bind mount exists. Live responses are consistent with the older application image; Docker/process inspection is denied, so the serving container's exact launch directory could not be independently inspected.

No application routing or archive/processing code was changed for this follow-up. Added `scripts/refresh_kiosk.ps1`: explicitly targets this project directory, builds existing application images, runs frontend lint/typecheck/production build, deploys backend/frontend/worker together to preserve visitor API compatibility, then checks the ACTUAL root HTML, navigation routes, system/staff pages and public catalogue endpoint. It preserves data volumes and does not run the full Phase 3 suite. Script syntax passes; runtime remains unexecuted here because Docker's named pipe is inaccessible.

Follow-up local checks: ESLint PASS; route typegen + TypeScript PASS; production build compiled in 4.5s then failed with `spawn EPERM` at the TypeScript worker. **The live homepage is not claimed fixed.** Run `.\scripts\refresh_kiosk.ps1` from normal PowerShell and require its actual-route PASS messages; then reload localhost:3000 with Ctrl+F5. Full Phase 3 acceptance remains separate.

## 2026-09-29 — heritage master-request continuation (NOT runtime complete)
The running root was checked over HTTP and already returned the kiosk “Discover a legacy” screen; /ai, /archive, /experience, /staff and /system returned HTTP 200. Public catalogue returned zero records at inspection. These observations concern the existing running image, not acceptance of today's edits.
Owner clarified the named photograph is verified/public but unpublished, and “Allowed” is not confirmed public-display permission. It remains untouched and must stay unpublished. Code also lacked card thumbnails and an automatic photograph detail preview; these display gaps now have derivative-backed implementation.
Implemented in source: protected no-store thumbnails; clearer staff stages/filters/original comparison; configurable Gemini with shared grounding/citation checks and no fallback; real recording validation/native playback/cue revision review; source-backed learning publication, backend quiz scoring, certificates/verification, voluntary generated-pseudonym leaderboard and consent-based optional SMTP. Added isolated integration/browser checks and mocked provider/email tests. No real historical documents/recordings were imported and no live email or Gemini calls were made.
Initial local suite: 33 backend tests passed (15 integration tests deselected); Ruff passed. An initial frontend check found a duplicate AI suggestions declaration, which was corrected. Final local results will be recorded after the next check. PostgreSQL migration/workflow and browser tests remain pending because this task cannot access the Windows Docker named pipe. See HERITAGE_VERIFICATION.md. Do not mark the extension complete until runtime failures, if any, are fixed and retested.

## Second-session validation — 2026-09-29 (in progress)
Inspected project documents, migrations, tests and source. This directory has no Git metadata: git status/diff/log fail with “not a git repository”; no clean-tree or commit-history claim is possible. Baseline copies of edited files are retained in work/session2-baseline.

Initial actual checks: local backend `python -m pytest -p no:cacheprovider -p phase2_pytest_paths -q` with `PYTHONPATH=../work`: 35 passed, 15 integration tests skipped, one existing Starlette warning (37.51s). Ruff passed. Frontend lint and typecheck passed; Windows production build compiled then failed `spawn EPERM` at TypeScript worker. Docker permission denied inside sandbox, but approved elevated `docker info` succeeded (29.8.0). The existing isolated Docker/browser harness is now running; previous Docker-blocked statements are historical.

Found missing recording research integration: recording_revision was never fed to the text passage index. Added migration 005 and timestamp-bearing immutable text snapshots on explicit transcript verification; correction clears current text eligibility. No automatic publication/backfill of historical recordings. Regression and runtime verification of these changes remain pending until recorded below. No Gemini or SMTP requests made.

### Baseline runtime evidence (before second-session fixes)
Approved Docker execution overcame the sandbox named-pipe limitation. `scripts/check_phase3.ps1` built application images without deleting volumes. Backend: 49 passed, 1 skipped (real-model acceptance), 63.51 seconds. Docker Ruff, frontend lint, typecheck and production build passed. Browser: 5 passed / 5 failed in 1.2 minutes. Failures were stale staff heading, ambiguous Title/status/alert selectors and exact text-size label selection; traces retained in work/session2-baseline/browser-first-run. Corrected selectors target the intended forms/records/landmarks and accessible combobox roles. Rerun in progress.
Read-only production check: one record titled Letters, description “Dr Babasaheb Ambedkar’s letters”, verified/public (NOT published), original SHA-256 matches stored checksum. No models installed/configured; Gemini and SMTP are unconfigured. Live-model acceptance is blocked by missing models; no model downloads, Gemini calls or real email attempted.

### Second runtime pass
Backend with migration 005: 49 passed / 1 skipped in 84.82s; Ruff and Docker frontend lint/typecheck/production build passed. Browser execution confirmed the corrected quiz/certificate and transcript/time-locator flows. Remaining failures exposed (1) archive test treating “not published” as successful publication, now changed to exact lifecycle text, and (2) the mobile sticky footer intercepting End session; responsive footer fix is prepared for the final rebuild. Final counts follow after completion.


## 2026-09-30 master continuation in progress
See MASTER_CONTINUATION.md for current inspection, dataset inventory, current provider state and staged validation. Prior successful suite counts are historical, not acceptance of newer changes. Dataset remains unpublished; provenance and rights Not verified.

Stage update: guided upload, source reader/research and evidence connections implemented; full validation underway. Read-only audit confirms Letters unpublished and original checksum intact. Gemini generation returned HTTP 404; metadata access alone is not generation acceptance. Dataset sample only; all 31 files unchanged.


## 2026-09-30 resumed reconciliation
See RESUME_VERIFICATION.md for authoritative current runtime state and test results. Intervening corpus migrations 006–008 and restricted imports are preserved. Additive migration 009 provides scoped private streaming. Public upload limits and publication safeguards remain unchanged. Gemini candidate generation succeeded and chat model setting updated; embeddings unchanged. Experience tabs restored alongside collection browsing.


## 2026-09-30 — submission stabilization
Existing implementation rebuilt without resetting volumes. See SUBMISSION_VERIFICATION.md and outputs/deadline-final-validation-2.log: 77 backend passed / 2 optional live tests skipped; Ruff, lint, typecheck and production build passed; 12 browser tests passed. Foundation: 3 passed. Separate live Gemini + PostgreSQL synthetic cited-answer test: 1 passed; not archival acceptance. Playback panel-close revocation, placeholder-rights guard, provider timeout/parsing diagnostics and the Chrome upload-response regression are checked. All 31 original checksums matched the pre-change audit. No migration, model setting, original or corpus checkpoint was changed. Two attributed PIB source excerpts are reviewed and prepared, but publication and real-source acceptance await the owner's existing local credential-file path. BHASHINI remains unavailable; no integration is claimed.

## 2026-09-30 — renewed audit and authentication clarification

Owner clarified that no credential JSON exists. Read-only production account inspection found one active admin account, login `admin`; password hashes were not selected. No account was created or modified. Publication script now optionally prompts locally for the existing login and hidden password, without saving credentials; the existing JSON input remains supported. Authenticated publication and media validation still await the owner's local sign-in. No new content is published.

Fresh inventory: 92 files, including 36 PNG photographs and 25 JPEG letter images. All 61 images pass integrity and full decode checks; provenance/display rights remain unverified. No exact hash duplicates; all 31 previously inventoried originals retain identical SHA-256 values. PDF inspection results were reused only after freshly matching hashes; no large OCR processing was started. Host ffprobe is unavailable, so this inventory does not revalidate media playback.

Fresh validation: 16 provider/archive isolated regression tests passed; 3 foundation browser checks passed. Six public routes return 200; unauthenticated staff API returns 401. Public catalog is empty and research correctly returns `no_eligible_content`, without generation. Saved earlier full-suite/build results above were inspected, not rerun in this continuation. See SUBMISSION_VERIFICATION.md for exact commands and limits.

Owner subsequently confirmed the existing admin password is unknown and instructed that accounts remain unchanged. Authentication-dependent work is blocked; no account recovery, reset or provisioning was performed.

## 2026-09-30 — read-only Archive and Experience empty-state diagnosis

This inspection changed only this status document. Production SQL used `SET TRANSACTION READ ONLY`; no records, accounts, permissions, originals or publication states were changed.

Archive flow: `frontend/src/app/archive/page.tsx` initially fetches `/api/archive/catalog` without filters. Search submits `q`, `language`, `material_type`, `sort`; the component maps returned records without another visibility filter. Empty state requires loading complete, no request error and an empty records array. The Next route `frontend/src/app/api/archive/[...path]/route.ts` forwards path and query to `/archive/...` on the backend, preserves response status/body, and uses no-store. `backend/app/research.py:catalog` joins archival_item to source and original asset, requires `review_status='published' AND access_level='public'`, optionally filters exact language/material/volume and case-insensitive title/description substring, then sorts and applies limit/offset (defaults 200/0). Catalog visibility does not depend on Qdrant or embeddings. Full text in detail views separately requires verified text.

Fresh production result: 31 records; 30 uploaded/staff, one verified/public (Letters), zero published/public. All 31 have required source/original asset joins; zero qualify for catalog. Letters is verified but NOT published, and its rights statement remains `Allowed`; current publication guard rejects that placeholder. Neither frontend filtering nor missing original joins explains the empty Archive.

Experience flow: `frontend/src/app/experience/page.tsx` defaults to CollectionExplorer, whose initial request is `/api/archive/catalog?limit=24`. It shares the same zero-eligible-record cause. Its search adds q/material_type/optional volume, offset and limit 24. Timeline, Stories and Quizzes call `/api/archive/learning?kind=timeline|story|quiz`; only optional exact topic filtering occurs in the frontend, initially unset. Empty activity message appears after successful loading when entries.length is zero. KnowledgeMap fetches all three learning kinds, flattens them and optionally filters topic; it has no independent source of graph data.

`backend/app/learning.py:public_list` selects matching kind with status published (up to 200), then calls public_content/evidence. Evidence must exist and every referenced archive record must still be published/public. A referenced text revision must be verified and current, and any quote must match a text segment exactly. Entries failing those checks are omitted immediately, including after source withdrawal. Timeline results sort by date_label. Fresh database: zero curated_content rows of any kind/status and zero curated_evidence rows. Thus activity tabs/map are empty because activities have never been created, not because existing published activities were filtered out.

Live GET comparisons: direct backend localhost:8000 `/archive/catalog`, `/archive/catalog?limit=24`, and `/archive/learning?kind=timeline|story|quiz`, versus matching localhost:3000 `/api/archive/...` proxy requests, all returned HTTP 200 with identical JSON `[]`. Response bodies, not just status codes, were inspected. No proxy response mismatch was found.

Prepared content is filesystem-only: outputs/submission-sources/constitution-excerpt.txt (1091 bytes), biography-excerpt.txt (108 bytes), source captures and locators.json exist. No archival record matches PIB release IDs 1489909/2017835 or a PIB title; published-selection.json is absent. scripts/publish_submission_selection.py defines three timeline entries (birth, adoption, commencement), one story (From drafting to commencement), and one three-question quiz. None exists in curated_content. Preparation files are not automatically ingested or displayed.

Minimum safe population sequence, NOT performed: obtain legitimate staff authentication (existing password currently unknown; accounts must remain unchanged), confirm source attribution/rights and exact excerpts, upload through staff API, complete extraction and text review/verification, confirm metadata/provenance/rights, then explicitly publish with public access. Create the five source-linked activity drafts through staff learning APIs using the resulting record IDs/current verified revisions, review claims/quotes/answer keys, verify and publish. Confirm public API arrays and rendered entries afterward. Do not publish Letters or uncertain dataset/photos to fill the UI. No frontend change, indexing rebuild, database seeding or safeguard relaxation is required to resolve these empty states.

## 2026-09-30 — authenticated publication and real-source acceptance

This supersedes the earlier credential blocker and empty-state report. Owner supplied existing staff credentials; used through hidden local prompts without storing a credential file or changing any account. Two exact attributed PIB excerpts were uploaded, extracted, text-reviewed/verified, metadata-reviewed and published through authenticated application APIs. Public records: `d3607a2e-92fd-4886-9f29-56c9cd38d8d3` (2017 Constitution excerpt) and `8ce2df4c-c4e2-4ed1-bf9e-244881273e82` (2024 birth excerpt). Both are modern government accounts, not Ambedkar originals. Five source-linked activities are now published: three timeline entries, one story and one ten-question quiz. Full receipts: outputs/submission-sources/published-selection.json.

Actual Gemini `gemini-3.1-flash-lite` answered three real-source questions with exact supporting quotes, correct record IDs/current revision and working source readers. Unsupported-question abstention and empty-filter checks passed. Configured Qdrant collection has two stored vectors, embeddinggemma:latest/768 dimensions; two PostgreSQL passages. Indexed_vectors_count=0 is Qdrant's reported small-collection index count, not zero stored points. Separately forced PostgreSQL-only retrieval (in-memory config only) found the published Constitution passage. No synthetic fixture was used for these real-source checks.

Fresh validation: backend 77 passed/2 optional live tests skipped; Ruff, ESLint, typecheck, production build passed; isolated workflow browser 12 passed; actual public browser 8 custom checks passed including Archive search/filter/pagination, verified reader/original, live cited Gemini answer, responsive timeline/story/map, ten-question quiz score 10/10 and anonymous certificate download. All eight existing recordings passed actual authenticated native playback, range access, public exclusion and revocation. All 31 prior records remain publicly inaccessible; their original hashes and visibility states match the baseline. All 33 stored originals pass checksums. No real email, audible narration, synchronization or touchscreen acceptance is claimed.

Owner clarified DAIC supplied Dataset and authorized SIH prototype use; this is recorded as owner-attested supplier permission, not personal ownership or an unrestricted license. No separate DAIC permission document was found in searched project text/filenames. Prototype processing is authorized; broader distribution remains unestablished. Record-level identity and text review remain necessary. All 61 new images were processed locally using existing RapidOCR: 61 outputs, zero processing failures, 31 with detected text; all unverified. All 92 dataset file hashes are unchanged. A separate ten-question local draft based on Volume 1 PDF pages 12/18 references the existing record and exact extracted support. It is NOT published or a DB draft because no verified source revision exists yet. See outputs/daic-quiz-draft.json and outputs/daic-prototype-review.json. The published quiz instead uses the two reviewed PIB records.

Bounded existing corpus OCR resumed (25 pages for Volume_01, then a 100-page batch across named volumes) with read-only Dataset mounts. Existing records remain private, and the 13,824-page compilation remains held. Final batch counts and exact commands are recorded in SUBMISSION_VERIFICATION.md. No database reset, volume deletion, account change, migration edit or rights/access bypass occurred.

## 2026-09-30 — museum redesign: Phase 1 baseline
Read current architecture, requirements, implementation/database/deployment documentation, source routes/models/migrations, processing/checkpoint code and existing test reports. No .git directory exists; git status and diff fail (not a Git repository). Pre-edit frontend source/tests and status saved to work/redesign-baseline; all existing work retained.
Fresh Docker read-only inspection: six existing services running; no separate corpus job container active. Public API: two attributed modern PIB excerpts; three timeline entries, one story, one ten-question quiz, all under Life and Constitution. Database corpus report saved to outputs/redesign-corpus-before.json: 33 items, 2 published, 2 passages, 2 embedding checkpoints, 3466 revision segments. Letters remains verified/public but unpublished. 19 named volume/part PDFs are present; filenames are candidate mappings, not verified editions. Corpus compilation remains held. Prior 77 backend/12 browser passes are historical until rerun.
Actual stack: Next 16.3.6, React 19.3.0, FastAPI/psycopg, PostgreSQL 17, Qdrant 1.17.0, Ollama 0.17.7. Nine existing migrations. Existing authenticated transcript correction/verification and timestamp indexing are implemented; automatic ASR is absent. No BHASHINI settings or adapter found. Gemini configuration present (values not disclosed); live inference not yet rerun. No changes to secrets, accounts, permissions, originals, migrations or publication.
Plan: source catalogue and topic-led Experience using existing public APIs; shared reader and media refinements; quiz/learning accessibility; bounded checkpoint resume and eligibility coverage; official BHASHINI capability review; full isolated regression. Intended frontend files: archive/page.tsx, experience/page.tsx and new topic route/shared exhibition component, archive/[id]/page.tsx, RecordingPlayer, SourceResearch, quiz/[id]/page.tsx, KnowledgeMap, globals.css; relevant browser tests and status. Backend changes only if a verified gap requires them.

### Redesign Phases 2–4 — implementation and initial checks
Archive now has editorial record rows, existing title/language/material/sort filters plus supported volume filtering, 24-record pagination with lookahead, applied-filter stability and loading/error/empty states. Removed the redundant speeches promotion; /speeches and media filters remain. Experience landing now groups only published activities into topic plaques; /experience/[topic] presents stories, timeline, quizzes and existing source evidence. Only Life and Constitution is currently supported. No replacement archive or fabricated themes/images. Existing CollectionExplorer source retained but no longer mounted.
Reader retains original download/preview, page navigation and reviewed-only content; adds full reviewed text, separate AI mode, volume/part metadata and related public exhibitions. RecordingPlayer adds reviewed-cue highlighting and native video caption tracks; synchronization acceptance pending. Quiz adds source introduction, progress, unanswered count, spacious options and result-context leaderboard link; backend scoring/consent unchanged. SourceResearch explicitly labels AI output and offers key points.
Initial lint found an unescaped apostrophe, corrected. Docker frontend lint/typecheck/production build subsequently passed (outputs/redesign-frontend-checks.log). Docker Ruff passed. Only frontend service rebuilt/restarted; backend, worker and data services not restarted. Backend regression and new browser tests in progress. No completion claim for pending browser/manual checks.

### Phase 5 — private corpus and RAG verification
Existing locked importer checked Volume_01 with --max-pages 10 --ocr-pages 10: already awaiting review, no duplicate work. Then processed ten pending Volume_07 pages with the same limits/read-only Dataset mount. Volume_07 now 387/406 extracted, 19 OCR pending, 11 OCR pages total, 7 empty pages, zero failed pages. Blank detection is a review warning, not proof of successful transcription. Full corpus: 27,693 checkpointed PDF pages (includes the separately held 13,824-page compilation), 24,548 extracted, 3,145 OCR pending, 137 OCR-processed, 106 empty, zero failed. Counts overlap: OCR pages are included in extracted; empty pages are not verified text. Only 2 public records/2 passages remain eligible. Six named PDFs are awaiting text review; no private corpus text was approved/published/indexed in this turn. 61 prior image OCR JSON files remain unverified.
Fresh hashes: 92/92 Dataset files match DAIC review manifest; 33/33 stored originals match checksums and prior publication/access states. 124 access-denial checks pass for all 31 protected records (catalog, original, playback and staff text). Qdrant has two points with exact matching PostgreSQL passage IDs; no duplicate/stale point in this small complete scan. See outputs/redesign-preservation.json, redesign-dataset-hashes.json, redesign-corpus-before.json and redesign-corpus-after.json.
Existing backend suite: 77 passed, 2 optional live tests skipped (111.30s), outputs/redesign-backend-tests.log. Added backend/tests/test_research_coverage.py: real isolated PostgreSQL cross-volume retrieval, current citations, repeated indexing and immediate withdrawal exclusion; 1 passed (7.72s), explicitly mocked generation/no synthetic production content. Existing suite separately covers stale vectors/unreviewed text, revoked playback grants and publication authorization. No backend application or migration changes needed.

### Phase 6 — BHASHINI blocker verified, no integration claim
No BHASHINI credentials/configuration or ASR model exists in this deployment. Official documentation checked 2026-09-30: https://bhashini.gitbook.io/bhashini-apis/pipeline-config-call requires userID/ulcaApiKey; pipeline configuration response lists task/language/service support and supplies inference endpoint/authorization; https://bhashini.gitbook.io/bhashini-apis/pipeline-compute-call describes compute. Documentation examples do not establish enabled account capabilities or historical-media accuracy. Translation, ASR and remote TTS remain unavailable; existing honest notice/local system narration preserved. No credentials requested in chat, no guessed service/language IDs, no mock adapter portrayed as working. Integrating and live-testing these services requires authorized server-side credentials and discovered pipeline capabilities; Phase 6 is blocked, not complete.

### Regression failures and corrections retained
First new browser run used default 127.0.0.1 and failed because Next dev-origin protection blocked client resources; localhost fixed loading without weakening origin checks. Playwright default now uses localhost. A pagination-test alert selector was scoped to main to exclude Next route announcer. Existing workflow first pass: 9 passed/3 failed due old Experience tabs and ambiguous duplicated page-text selectors. Updated tests follow actual topic plaques and scope selected-page checks; quiz/scoring and extraction paths unchanged.
Second workflow: 11 passed/1 failed; remaining failure was Playwright ENOENT trace artifacts because two runs shared frontend/test-results. Future new UI runs use a separate --output directory; isolated workflow rerun pending. Native audio seek/highlighting passed against synthetic uploaded audio. Native video cue/caption test initially sought before playable data; actual playback after readyState check passed (1 test, 5.4s). That test uses a real self-created silent MP4 and mocked public API, not a real archival recording or live ASR.

### Phase 7 — accepted results and remaining boundaries
Existing isolated browser workflows now PASS: **12 passed in 1.9 minutes**, outputs/redesign-workflow-accepted.log. This includes actual synthetic upload/extraction/review/publication/withdrawal; protected image derivative; native recording playback/revocation and reviewed cue highlighting; server-scored correct/incorrect quiz attempts; anonymous certificate download; explicitly voluntary leaderboard; kiosk fullscreen/session and accessibility. Speech API behavior is simulated, not audible narration acceptance. No historical photograph or recording was published for testing.
Fresh public UI suite: **5 passed in 30.8s**, outputs/redesign-public-accepted.log, plus **1 large-text/high-contrast/reduced-motion keyboard test passed in 8.7s**, outputs/redesign-accessibility.log. Desktop/mobile widths 1366/768/390 verified and screenshots inspected. Native video test uses a real synthetic two-second black/silent MP4 with mocked reviewed transcript/API and confirms both caption active cue and transcript highlighting during playback. Not proof of archival synchronization, live ASR, or content accuracy. A final route refinement removes double percent-decoding of already-decoded Next topic params; final targeted rerun recorded below.
Live configured Gemini via public /research/ask: one Drafting Committee question answered with one exact supporting quote, matching published source/current revision; unsupported quantum-computing question returned insufficient_sources and zero paragraphs. outputs/redesign-live-research.json. This is separate from mocked provider regression tests. No real email or BHASHINI calls occurred; no new model installation or provider switch.
Final bounded OCR: finished the remaining 19 Volume_07 pages, totaling **29 new OCR checkpoints this continuation**. Volume_07: 406/406 processed, 30 OCR pages total, 25 empty pages flagged, state awaiting_review, zero failed. Corpus now **24,567 extracted / 27,693 PDF checkpoint pages**, **3,126 OCR pending**, **156 OCR-processed**, **124 empty**, zero failed. Seven named PDFs await review. See outputs/redesign-corpus-final.json. These totals include overlapping compilation contents and are not unique historical-page coverage. The held compilation was not processed this turn. No source review/publication/index expansion was performed because additional corpus content is not yet eligible.
Remaining: record-level provenance/display-rights decisions and curator text review; pending OCR batches and uncertain/empty page inspection; historical recording identity/transcript review; configured, authorized ASR/BHASHINI services; manual screen-reader/audible narration/touchscreen acceptance; live SMTP delivery. No claim that all requested phases are complete. Accounts, secrets, originals, access policy and migration files remain unchanged. Pre-edit code available at work/redesign-baseline. No Git commit/diff possible because this folder is not a repository.

### Exact repeatable PowerShell commands (project root)
```powershell
# Backend regression: isolated temporary schemas/storage, no live AI by default.
docker compose exec -T -e RUN_INTEGRATION=1 -e RUN_AI_ACCEPTANCE=0 backend python -m pytest -p no:cacheprovider -q
# Added cross-volume regression uses real isolated PostgreSQL, mocked generation.
docker compose exec -T -e RUN_INTEGRATION=1 backend python -m pytest -p no:cacheprovider -q tests/test_research_coverage.py
docker compose exec -T backend python -m ruff check --no-cache app tests
# Frontend static checks and actual production compilation (running service uses existing dev command).
docker compose exec -T frontend npm run lint
docker compose exec -T frontend npm run typecheck
docker compose run --rm --no-deps frontend npm run build
# Existing full isolated workflow harness; backend tests already run separately above.
.\scripts\check_phase3.ps1 -SkipBackendTests
# New public reads and explicitly labelled browser simulations. Separate output avoids collisions.
$env:ARCHIVE_E2E_BROWSER='C:/Program Files/Google/Chrome/Application/chrome.exe'
$env:PLAYWRIGHT_BASE_URL='http://localhost:3000'
node frontend/node_modules/@playwright/test/cli.js test --config frontend/playwright.config.ts frontend/tests/redesign.spec.ts --output work/redesign-complete-results --workers=1
# Read-only corpus and access/integrity reports.
Get-Content scripts/report_corpus.py | docker compose exec -T backend python -
Get-Content scripts/audit_redesign.py | docker compose exec -T backend python -
# Bounded private OCR commands actually executed, after checking for other jobs.
$datasetMount=(Join-Path (Get-Location).Path 'Dataset')+':/dataset:ro'
docker compose run --rm --no-deps -v $datasetMount backend python -m app.corpus /dataset --file Volume_01.pdf --max-pages 10 --ocr-pages 10
docker compose run --rm --no-deps -v $datasetMount backend python -m app.corpus /dataset --file Volume_07.pdf --max-pages 10 --ocr-pages 10
docker compose run --rm --no-deps -v $datasetMount backend python -m app.corpus /dataset --file Volume_07.pdf --max-pages 19 --ocr-pages 19
```
Manual acceptance: compare original and reviewed text; follow topic/source citations; listen to narration and exercise Pause/Resume/Stop; use a screen reader and physical touchscreen; confirm language selection does not translate source text; test captions against an authorized reviewed historical recording when available. Browser fullscreen is not Windows kiosk lockdown.
Final route check caught a version-specific assumption: this Next runtime passes encoded topic params, so removing decoding made topic bodies unavailable. Restored one guarded decode (not recursive decoding); literal-percent route is now part of regression tests. The intermediate six-test run was 4 passed/2 failed; not accepted. Source data/access unaffected. Final rerun follows.

### Final artifact and file manifest
Frontend application files changed: src/app/archive/page.tsx (catalogue and bounded pagination), src/app/experience/page.tsx and new experience/[topic]/page.tsx plus components/Exhibition.tsx (published-topic exhibitions), src/app/archive/[id]/page.tsx and new components/RelatedExhibitions.tsx (shared source reader and contextual links), components/RecordingPlayer.tsx (reviewed cues/captions), components/SourceResearch.tsx (explicit AI labeling/key points), src/app/quiz/[id]/page.tsx (source introduction/progress/results), components/KnowledgeMap.tsx (expandable evidence and activity links), src/app/globals.css (responsive catalogue/museum/reader/quiz styles).
Tests/config: frontend/tests/redesign.spec.ts added; heritage.spec.ts, processing.spec.ts and kiosk.spec.ts updated for intentional UI changes while retaining assertions; frontend/playwright.config.ts uses localhost by default. Added backend/tests/test_research_coverage.py and read-only scripts/audit_redesign.py. No backend application, model, dependency manifest, environment or migration changes. Final source-file hash comparison against saved baseline: outputs/redesign-changed-source-files.txt.
Latest production build/lint/typecheck PASS: outputs/redesign-topic-fix-validation.log. Final six-test run after topic correction passed five but its accessibility case timed out during a reported multi-hour runner interruption (trace shows layout moving while catalogue loaded). Added explicit loaded-record wait before footer interaction; final rerun in outputs/redesign-oct01-browser.log. Earlier dedicated accessibility pass remains documented, not used to conceal this failed run.
The caption fixture lives only at work/redesign-caption-fixture.mp4; never ingested. To recreate it for tests when missing (use a fresh temporary filename if one already exists):
```powershell
docker compose exec -T backend ffmpeg -hide_banner -loglevel error -f lavfi -i color=c=black:s=320x180:d=2 -f lavfi -i anullsrc=r=8000:cl=mono -t 2 -c:v libx264 -pix_fmt yuv420p -c:a aac -movflags +faststart /tmp/redesign-caption-fixture.mp4
docker compose cp backend:/tmp/redesign-caption-fixture.mp4 work/redesign-caption-fixture.mp4
```


Final acceptance — 2026-10-01: outputs/redesign-oct01-browser.log reports 6 passed (13.6s). This includes actual loaded catalogue, original/full-text reader, source-specific AI controls without inference in the browser suite, percent-encoded topic navigation, source links, error/pagination simulation, native synthetic video captions, responsive widths and 140% high-contrast keyboard traversal. The earlier interrupted run is retained. All changes are saved; services are running; no OCR batch remains active from this continuation.

## 2026-10-01 — content-completion continuation: fresh audit
Read attached request, current code/status, corpus extraction/finalization/locking, migrations and media/public retrieval paths. git status and git diff still fail: no Git repository. Earlier test outcomes are historical. New read-only reports: outputs/content-audit-before.json and content-preservation-before.json. Six services running; no active corpus importer. 33 stored records, 2 published PIB excerpts, 2 passages/vectors; no other eligible source.
Dataset: 92 files: 22 PDFs, 36 PNGs, 25 JPEGs, 7 MP4s, 1 MP3, 1 reference TXT. Nineteen named volume/part PDFs cover candidate Volumes 1–17; titles/editions still unverified. Letters-folder images are candidates, not verified correspondence. 61 standalone image OCR derivatives exist privately; these images are not registered by the current PDF/media importer. Pending PDF OCR is 3126: 1305 in the held 13824-page compilation, 1821 elsewhere. Existing >5000-page hold requires identity/scope review and is preserved.
Plan: merge per-file inventory with current DB/derivative/review/index state; resume existing eligible checkpoints in bounded 50-page batches; show existing confidence in staff checkpoint preview; improve empty/error states on /speeches; verify existing access/retrieval/workflows. No redesign, publication, rights approval, credential/account modification or migration changes. Saved planned UI edits/status in work/content-baseline. New scripts/resume_content_batches.py only selects already registered pending PDFs, skips held/failed/current-text records, invokes existing hash/lock/checkpoint logic, and stops on no progress/failures. Batch wrapper does not verify or publish anything.

### Content continuation — implementation and interim validation
Changed frontend/src/app/speeches/page.tsx: abortable loading, explicit service-error retry, true-empty versus filtered-empty states, result count, clear filters and description search. Changed frontend/src/components/CorpusStatus.tsx: existing extraction method and confidence displayed to staff, clearly machine estimates. Added frontend/tests/content-states.spec.ts with two explicitly mocked API scenarios. Existing museum/catalogue/reader design preserved.
Added scripts/content_inventory.py and render_content_inventory.py for 92-file hash/format/ingestion/review/index reporting, including private image derivative page arrays and page-quality flags. Added scripts/resume_content_batches.py for bounded checkpoint continuation; future invocations also reject any file whose current hash differs before the importer can register it. The already running invocation uses the importer's existing hash verification; initial per-file hashes matched.
Added optional -KeepRunningServices to scripts/check_phase3.ps1 so isolated workflow tests can use verified current images without restarting active OCR/services; default behavior unchanged.
Current results: backend 78 passed, 2 optional live tests skipped, 1 existing Starlette/httpx deprecation warning (outputs/content-backend-tests.log); frontend lint/typecheck/production build passed (outputs/content-frontend-validation.log). Focused browser suite 8 passed in 34.8s (outputs/content-ui-tests.log): 6 existing regressions + 2 new API simulations. Live Gemini: answered Drafting Committee question with exact source/revision/quote matches; unsupported quantum-computing question abstained with zero paragraphs (outputs/content-live-research.json). This is separate from mocked cross-volume/provider tests. Workflow suite still running at this entry.
OCR has completed pending pages in root Volumes 8–15 (including both Volume 14 parts), with no failed pages reported, and is processing Volume 16. Final counts will supersede this interim snapshot. Held compilation remains excluded; no review, rights, publication, original or embedding changes requested. Initial Ruff findings in the new scripts were formatting/style issues, corrected; final rerun follows.
### Content continuation — accepted regression results
Existing workflow suite: 12 passed in 1.6m (outputs/content-workflow-tests.log), using `./scripts/check_phase3.ps1 -SkipBackendTests -KeepRunningServices`. Fixtures use isolated database schemas and self-created media; production staff accounts and source publication were not changed. Actual synthetic audio timing and access revocation passed; browser speech API checks are simulated, not audible playback acceptance.
New wrapper safety tests: 4 passed in 1.11s (outputs/content-batch-tests.log), using `docker compose run --rm --no-deps -e PYTHONPATH=/app:/audit -v "${root}/scripts:/audit:ro" backend python -m pytest -p no:cacheprovider -q /audit/test_content_batches.py`. They exercise changed-file rejection, held/failed/current-text exclusions, no-progress abort and batch-limit continuation. No actual corpus writes occur in these tests.
Current working report: outputs/CONTENT_AUDIT.md, generated from outputs/content-inventory.json. Snapshot during OCR; final report pending. Private image derivative parsing confirms 61 hash-matched derivatives, 31 with extracted text and 30 empty; none is verified or published. Filename/classification uncertainty and the distinction between PIB supplementary content and original archives remain explicit.

### Content continuation — exact PowerShell commands
Run from the project root. Inspect existing corpus jobs before any new processing; never duplicate the active wrapper. `$root` below is a task variable, not a system variable.
```powershell
$root=(Get-Location).Path
# The active bounded continuation (started once, not a command to rerun concurrently).
docker compose run --rm --no-deps -e PYTHONPATH=/app -v "${root}/Dataset:/dataset:ro" -v "${root}/scripts:/audit:ro" backend python -u /audit/resume_content_batches.py /dataset --batch-pages 50 --max-batches 60 *> outputs/content-ocr-batches.log
# Read-only inventory; rerender Markdown after successful JSON generation.
docker compose run --rm --no-deps -e PYTHONPATH=/app -v "${root}/Dataset:/dataset:ro" -v "${root}/scripts:/audit:ro" -v "${root}/outputs/dataset-image-review:/image-ocr:ro" backend python /audit/content_inventory.py /dataset /image-ocr > outputs/content-inventory.json
python scripts/render_content_inventory.py outputs/content-inventory.json outputs/CONTENT_AUDIT.md
Get-Content scripts/report_corpus.py | docker compose exec -T backend python - > outputs/content-corpus-final.json
Get-Content scripts/audit_redesign.py | docker compose exec -T backend python - > outputs/content-preservation-final.json
# Tests actually executed in this continuation.
docker compose exec -T -e RUN_INTEGRATION=1 -e RUN_AI_ACCEPTANCE=0 backend python -m pytest -p no:cacheprovider -q
docker compose run --rm --no-deps -e PYTHONPATH=/app:/audit -v "${root}/scripts:/audit:ro" backend python -m pytest -p no:cacheprovider -q /audit/test_content_batches.py
docker compose run --rm --no-deps -v "${root}/scripts:/audit:ro" backend python -m ruff check --no-cache /audit/resume_content_batches.py /audit/content_inventory.py /audit/render_content_inventory.py /audit/test_content_batches.py
docker compose run --rm --no-deps frontend sh -c 'npm run lint && npm run typecheck && npm run build'
# Covers the new test file added after the image build, without another service restart.
docker compose run --rm --no-deps -v "${root}/frontend/tests:/app/tests:ro" frontend sh -c 'npm run lint && npm run typecheck'
.\scripts\check_phase3.ps1 -SkipBackendTests -KeepRunningServices
$env:ARCHIVE_E2E_BROWSER='C:/Program Files/Google/Chrome/Application/chrome.exe'
$env:PLAYWRIGHT_BASE_URL='http://localhost:3000'
node frontend/node_modules/@playwright/test/cli.js test --config frontend/playwright.config.ts frontend/tests/content-states.spec.ts frontend/tests/redesign.spec.ts --output work/content-ui-results --workers=1
```
Final new-script Ruff and static frontend checks including the latest test file passed (outputs/content-script-lint.log, content-final-static.log). Additional live public RAG checks against the private Volume 16 ID and Volume 16 filter returned insufficient_sources, zero sources/paragraphs and generation_attempted=false (outputs/content-private-rag.json). Cross-volume generation remains a synthetic isolated regression, not evidence that actual unreviewed volumes are publicly indexed. No model fine-tuning was performed.
BHASHINI and automatic ASR audit: no configured adapter or authorized service credentials; existing honest visitor notice retained. No live or mocked BHASHINI implementation is claimed. Manual acceptance still needed: screen reader, audible narration, physical touchscreen/kiosk and historical recording alignment once approved recordings/transcripts exist. SMTP delivery not tested; certificate email consent behavior covered in isolated workflow tests.

### Explicit compilation hold — user decision, 2026-10-01
The user confirmed that independently verified edition/identity documentation and processing scope are unavailable. `Br. Ambedkar/book by br. ambedkar/Collected Works of Ambedkar vol 1.pdf` (13,824 physical pages, 1,305 pending OCR checkpoints) is **awaiting curator identity and scope verification**. Do not OCR, import, index, publish or modify this compilation. Existing original, extracted checkpoints and database state remain untouched; the inventory operator-hold label does not change source metadata or imply verification.
Release prerequisites: (1) reliable source/publisher/library or equivalent documentation establishing identity and edition; (2) curator-documented assessment of its relationship to the separate volume/part files; (3) explicit curator decision on intended processing scope. Filename and apparent content overlap are not proof. Rights and text approval remain separate prerequisites for any later public release. Continue only the other eligible files in bounded resumable batches. No repeat authorization request is needed for this hold.


## Collection continuation — implementation and evidence, 2026-10-01

### Existing state inspected and preserved
Read current source/routes, `status.md`, `implementation.md`, `agent.md`, `requirements.md`, `architecture.md`, `database.md`, `deployment.md`, existing test configuration, Compose and inventory code/report. No AGENTS.md was found in the scoped project scan. Initial broad `rg --files` produced access-denied errors in pre-existing temporary/cache directories and excessive node_modules output; subsequent searches were scoped to application/test/script paths. `git status --short` and `git diff --stat` reported “not a git repository”; no Git metadata was created, initialized, reset or discarded. Existing source files were copied once to `work/collections-baseline` before edits. Existing prior checkpoints, datasets, migrations, originals and database volumes were preserved.

A default-permission `docker compose ps` initially failed on the Windows named pipe. Approved elevated execution succeeded; Docker is **available**, not blocked. All original services remained running. The existing `sih26096-backend-run-f7d808f93379` OCR wrapper was observed still running; its most recent inspected log was batch 34, `ambekar-life-mission.pdf`, 510 pending before that batch. It was not restarted/duplicated. The wrapper's inherited HTTP health check reports unhealthy because this batch container is not an API server; that label alone is not an OCR failure result. The log had zero failed pages in the inspected completed batch. No processing or publication was requested by this continuation.

### Changes and actual surfaced content
- Added four responsive, native-link homepage cards with existing focus treatment: Manuscripts & Letters, Photographs, Videos, Audio & Speeches. Layout is four/two/one columns; desktop and 390px mobile screenshots were inspected.
- Reused `/archive?collection=manuscripts|photographs|videos|audio`, `/archive/[id]`, protected thumbnail/original endpoints and the reviewed reader. Unknown collection values fall back safely to the ordinary catalogue. Audio/Speeches uses existing `audio` and `speech` types. Manuscripts uses the existing curator-assigned `manuscript` type; there is no separate letter type and no filename/title/folder-based classification.
- Added optional `origin=dataset|other` to the existing catalogue. A stored original checksum's membership in `corpus_file` establishes the partition; source URLs, folder names and descriptions do not. Existing `published` + `public` authorization is preserved before results are returned. Dataset and other sections are disjoint, independently paginated/searchable and have separate error/retry/empty states. No migrations or records were added.
- Individual authorized images use existing protected thumbnails and their own reader. Originals, source links and metadata remain accessible; approved page text retains source order. Missing text stays absent. Raw OCR is never returned by the public reader. These behaviors were exercised with **synthetic isolated** images/documents, since no eligible real letter/manuscript image exists.
- Replaced historical “SIH26096 / PHASE 0”, “Local foundation” and the Ollama probe's Phase 0 sentence with Service Status/current health wording. Authenticated PostgreSQL SELECT 1, Qdrant readiness/collection checks and Ollama connectivity/model-presence checks remain unchanged. The page explicitly does not certify inference, Gemini, OCR accuracy, transcript timing, SMTP or kiosk hardware.

**Actual public material:** still only “Ambedkar and the Constitution — PIB lecture excerpt (2017)” and “Ambedkar's birth — PIB biographical excerpt (2024)”, in the existing general archive. None of the 92 supplied files was newly surfaced publicly. The new requested collections are empty because no matching approved records exist. No placeholders or invented archival descriptions/text were introduced.

**Actual dataset:** 25 `Ambedkar_letters/*.jpeg` image candidates; 36 `Ambedkar_photos/*.png` image candidates; 22 PDFs; seven MP4s (six in `Br. Ambedkar/videos`, one in `Br. Ambedkar/voice`); `Br. Ambedkar/voice/track_1.mp3`; `Br. Ambedkar/refrences.txt`. Exact filenames, hashes, IDs, rights and source states are in the adjacent audit JSON/Markdown. All 61 image candidates are unregistered; all 61 private OCR derivatives match source hashes, 31 contain extracted text and 30 are empty. No image has been authenticated as a letter/manuscript from its folder. The pre-existing record “Letters” is actually registered as a photograph, remains unpublished and is excluded. Its “Allowed” rights text is not permission evidence.

At the inventory snapshot: 25,727/27,693 physical PDF pages extracted; 1,966 pending; 1,316 OCR-processed; zero failed; 433 empty and 785 low-confidence flags. Counts include the held compilation and are not unique historical-page coverage. The 13,824-page compilation remains awaiting curator identity/edition/scope verification, with 1,305 pending pages held. No hold release, import, OCR, index, rights or publication change was made by this task.

### Actual checks, failures and limits
| Check | Actual outcome / evidence |
|---|---|
| Current-source backend full suite | 79 passed, 2 optional live checks skipped, 120.80s. `outputs/collections-backend-tests.log`. Existing Starlette/httpx deprecation warning remains. |
| Added collection integration assertion | 1 passed after adding a distinct other-archive fixture; `outputs/collections-backend-focused.log`. Covers disjoint membership, filters, changed source URL, missing transcription, image originals/thumbnails and withdrawal. |
| Backend Ruff | Initial new-test line-length failure; corrected. Final all app/tests passed in `collections-backend-focused.log` and `collections-ruff-final.log`. |
| Frontend lint, typecheck, production build | Passed initially and after final responsive CSS; `outputs/collections-frontend-final.log`. No service image rebuild or production restart. |
| Initial current-preview browser suite | 13 passed / 1 failed. The new failure assertion counted Next.js's route-announcer alert. Scoped it to main content; all 3 collection tests passed in `collections-browser-final.log`. Eight existing content/redesign tests passed in the initial run. |
| Final build browser regression | 6 passed (collections + live Service Status) in 6.7s; `outputs/collections-final-build-browser.log`. Responsive links, image reader/fallback, empty/error/retry and health checks tested. Synthetic collection records/API failures are explicit mocks. |
| Existing development-image workflow harness | 11 passed / 1 failed: processing test exceeded its 5s initial-loading assertion before login. `outputs/collections-existing-workflow.log`. This run was against the existing images, not final source. No assertion was weakened. |
| Current-source production workflow harness | 12 passed in 1.2m; `outputs/collections-current-workflow.log`. Uses edited app/tests, existing images, preserved production build, isolated schema/storage and synthetic originals. Real OCR/review/revisions, publication/withdrawal, photograph access, synthetic recording playback, quiz/certificate/leaderboard and consent exercised. |
| Transcript-based RAG | Backend recording integration checks verify approved cue text, timestamps, citation reader links, byte ranges, correction invalidation and no retrieval before publication. Generation is mocked in these transcript tests. No real historical transcript/timing acceptance. |
| Gemini | Contract tests use SDK mocks (configuration, errors/redaction, timeout, malformed response and citation handling). Separately, one live call through `app.check_gemini --live` answered the Drafting Committee question with validated exact source quotes; `outputs/collections-live-gemini.log`. No new live transcript-based Gemini check or exhaustive factual evaluation claimed. |
| Quiz, certificates, optional email | Server scoring, certificate content/escaping, consent/address validation, SMTP contract and browser learning flow passed in backend/workflow tests. SMTP is mocked; **no actual email delivery**. |
| Preservation | All 92 dataset hashes equal the prior inventory; all 33 stored originals match checksums. `outputs/collections-preservation.json` also records 124 direct backend denials. |
| Public URL access | Final audit: **403 denied requests**, comprising 248 per-record proxy requests, all 92 actual dataset file paths, all 61 raw image OCR JSON paths and two operator-inventory paths. Covers catalog, original, thumbnail, playback, recording, staff text/original and corpus pages. `outputs/collections-url-audit.json`, `collections-url-audit-complete.log`. Public partitions are disjoint with zero dataset records and two other records. |
| Audit execution issue | Initial localhost audit was slow due to host connection behavior and was stopped by its exact process match after the IPv4 version passed 251 checks; the expanded IPv4 audit then passed 403. A non-elevated process-inspection command was denied; elevated task-specific cleanup succeeded. No unrelated Python/OCR process was stopped. |
| Audit Ruff | Initial 101-character line failure; fixed. Expanded audit passed in `outputs/collections-audit-lint-complete.log`. |
| Editing/inspection issues | First Python edit attempt failed on Windows default cp1252 before any edit; rerun explicitly with UTF-8 succeeded. Two Get-Content wildcard reads of bracketed routes failed and were replaced with `-LiteralPath`. No source/data loss. |
| Manual limits | Desktop/mobile screenshots and browser keyboard/responsive/fullscreen checks passed. Physical touch hardware, screen reader, audible narration, live ASR/BHASHINI, historical audio synchronization, backup restore and live email delivery were not tested. |

### Exact verification commands executed
Commands below were run in the existing project root. Docker commands used approved elevated execution after the initial named-pipe denial. Output files retain intermediate failures rather than replacing their logs.

```powershell
Get-Location
rg --files -g status.md -g AGENTS.md -g package.json -g pyproject.toml -g '*implementation*' -g '*inventory*' -g '*compose*' -g README.md
git status --short
git diff --stat
Get-Content status.md
Get-Content implementation.md
rg --files -g AGENTS.md -g '!node_modules' -g '!work' -g '!.venv' -g '!outputs'
Get-Content agent.md
Get-Content requirements.md,architecture.md,database.md,deployment.md
Get-Content outputs/CONTENT_AUDIT.md
rg --files frontend/src backend/app backend/tests frontend/tests scripts -g '!__pycache__'
docker compose ps
docker compose ps -a
$taskRoot=(Get-Location).Path
docker compose run --rm --no-deps -e PYTHONPATH=/app -v "${taskRoot}/Dataset:/dataset:ro" -v "${taskRoot}/scripts:/audit:ro" -v "${taskRoot}/outputs/dataset-image-review:/image-ocr:ro" backend python /audit/content_inventory.py /dataset /image-ocr > outputs/collections-inventory.json
python -X utf8 scripts/render_content_inventory.py outputs/collections-inventory.json outputs/COLLECTIONS_AUDIT.md
docker compose run --rm --no-deps -e RUN_INTEGRATION=1 -e RUN_AI_ACCEPTANCE=0 -e RUN_GEMINI_ACCEPTANCE=0 -v "${taskRoot}/backend/app:/app/app:ro" -v "${taskRoot}/backend/tests:/app/tests:ro" backend python -m pytest -p no:cacheprovider -q *> outputs/collections-backend-tests.log
docker compose run --rm --no-deps -v "${taskRoot}/backend/app:/app/app:ro" -v "${taskRoot}/backend/tests:/app/tests:ro" backend python -m ruff check --no-cache app tests *> outputs/collections-ruff.log
# Same Ruff command rerun after the formatting fix, output: outputs/collections-ruff-final.log.
docker compose run --rm --no-deps -e RUN_INTEGRATION=1 -e RUN_AI_ACCEPTANCE=0 -v "${taskRoot}/backend/app:/app/app:ro" -v "${taskRoot}/backend/tests:/app/tests:ro" backend sh -c 'python -m ruff check --no-cache app tests && python -m pytest -p no:cacheprovider -q tests/test_collections.py' *> outputs/collections-backend-focused.log
docker compose run --rm --no-deps -v "${taskRoot}/frontend/src:/app/src:ro" -v "${taskRoot}/frontend/tests:/app/tests:ro" -v "${taskRoot}/frontend:/result" frontend sh -c 'npm run lint && npm run typecheck && npm run build && cp -a .next /result/work-collections-next' *> outputs/collections-frontend-validation.log
docker compose run --rm --no-deps -v "${taskRoot}/frontend/src:/app/src:ro" -v "${taskRoot}/frontend/tests:/app/tests:ro" -v "${taskRoot}/frontend:/result" frontend sh -c 'npm run lint && npm run typecheck && npm run build && cp -a .next /result/work-collections-final-next' *> outputs/collections-frontend-final.log
Get-Content scripts/audit_redesign.py | docker compose exec -T backend python - > outputs/collections-preservation.json
.\scripts\check_phase3.ps1 -SkipBackendTests -KeepRunningServices *> outputs/collections-existing-workflow.log
.\scripts\check_collections.ps1 *> outputs/collections-current-workflow.log
# The latter harness explicitly runs the archived production build, current source,
# isolated OCR/learning fixtures and cleanup. Its complete nested commands are in the script.
docker compose run --rm --no-deps -v "${taskRoot}/backend/app:/app/app:ro" backend python -m app.check_gemini --live --question 'Who was Chairman of the Drafting Committee?' *> outputs/collections-live-gemini.log
$env:ARCHIVE_E2E_BROWSER='C:/Program Files/Google/Chrome/Application/chrome.exe'
$env:PLAYWRIGHT_BASE_URL='http://localhost:3002'
node frontend/node_modules/@playwright/test/cli.js test --config frontend/playwright.config.ts frontend/tests/collections.spec.ts frontend/tests/foundation.spec.ts frontend/tests/content-states.spec.ts frontend/tests/redesign.spec.ts --output work/collections-ui-results --workers=1 *> outputs/collections-browser.log
node frontend/node_modules/@playwright/test/cli.js test --config frontend/playwright.config.ts frontend/tests/collections.spec.ts --output work/collections-ui-final --workers=1 *> outputs/collections-browser-final.log
$env:PLAYWRIGHT_BASE_URL='http://127.0.0.1:3002'
node frontend/node_modules/@playwright/test/cli.js test --config frontend/playwright.config.ts frontend/tests/collections.spec.ts frontend/tests/foundation.spec.ts --output work/collections-final-build-results --workers=1 *> outputs/collections-final-build-browser.log
node scripts/preview_collections.cjs
python -X utf8 scripts/audit_collection_urls.py *> outputs/collections-url-audit.log
# IPv4 correction, then expansion to every dataset/OCR file:
python -X utf8 scripts/audit_collection_urls.py *> outputs/collections-url-audit-final.log
python -X utf8 scripts/audit_collection_urls.py *> outputs/collections-url-audit-complete.log
docker compose run --rm --no-deps -v "${taskRoot}/scripts:/audit:ro" backend python -m ruff check --no-cache /audit/audit_collection_urls.py *> outputs/collections-audit-lint.log
# Same command after fixes: collections-audit-lint-final.log, collections-audit-lint-complete.log.
$tokens=$null; $parseErrors=$null
[System.Management.Automation.Language.Parser]::ParseFile((Join-Path (Get-Location) 'scripts/check_collections.ps1'),[ref]$tokens,[ref]$parseErrors) | Out-Null
$parseErrors
if($parseErrors.Count){exit 1}
```

### Preview commands and reproducible local acceptance
Docker worked in this continuation. If a later restricted session cannot access its pipe, run these exact commands in ordinary authorized PowerShell; do not reset or remove volumes. Do not duplicate preview names if already running. Final build command is above; existing services at 3000/8000 are unchanged and do not show the edits. The final preview uses 3002/8002 and was intentionally left running for review.

```powershell
$taskRoot=(Get-Location).Path
# These preview creation commands were executed; API started once.
docker compose run --rm --no-deps -d --name sih26096-collections-api -p 127.0.0.1:8002:8000 -v "${taskRoot}/backend/app:/app/app:ro" backend
# Initial preview used work-collections-next. After final CSS/build, only the
# task-created preview was stopped and recreated with the final build:
docker stop sih26096-collections-web
docker compose run --rm --no-deps -d --name sih26096-collections-web -p 127.0.0.1:3002:3000 -e BACKEND_INTERNAL_URL=http://sih26096-collections-api:8000 -v "${taskRoot}/frontend/src:/app/src:ro" -v "${taskRoot}/frontend/work-collections-final-next:/app/.next:ro" frontend npm run start
# Reproduce isolated workflow acceptance without touching production or OCR:
.\scripts\check_collections.ps1
```

Manual acceptance checklist:
1. Open http://127.0.0.1:3002. Tab through all four collection cards; check 390px, tablet and desktop widths, zoom and focus visibility.
2. Open Photographs and Videos. Both headings must appear, no unpublished file or placeholder may appear, and search/retry/empty states must remain distinct. Open Manuscripts & Letters: candidate review notice, no invented letter list/text. Audio & Speeches must not list private media.
3. Use an approved record's reader to compare its preserved original with verified text; check provenance, ordering and citation links. Curators must independently identify/review/approve actual letter images before they can be displayed. Never approve from folder names or the legacy “Allowed” rights label.
4. Confirm Service Status reports connectivity while explicitly excluding inference/feature acceptance. Run the recorded API/URL tests to verify restricted originals, thumbnails, recordings and OCR stay inaccessible even by direct URLs.
5. Perform screen-reader, physical touchscreen and audible local narration checks. Historical audio alignment needs approved recordings and reviewed timed transcripts. Any real email test must use explicit consent and an authorized test recipient; none was sent here.

Remaining blockers: curator identity/edition/page-order documentation for image candidates; actual public-display rights and source review; registration/classification of individual images; review/correction of all raw image OCR and remaining PDF OCR; historical transcripts/timing; compilation hold; authorized ASR/BHASHINI setup; manual hardware/accessibility acceptance. No additional content can responsibly be surfaced publicly until these prerequisites are satisfied. No credentials, rights evidence or historical text were fabricated.


## Targeted UI correction audit — 2026-10-01

### Inspection and scope
Inspected the current homepage, CollectionBrowser, Archive routing, shared Kiosk navigation, CSS, tests, status.md, previous `outputs/collections-source.diff` and checkpoints. Inspected actual Dataset files by parent folder and extension; exact names/counts are recorded in `outputs/archive-navigation-folders.json`. Git status/diff again failed because this directory has no Git repository. No Git initialization/reset occurred. Existing sources and documentation were checkpointed once to `work/archive-navigation-baseline` before editing. No older checkpoint, test log, dataset, derivative, original, migration or volume was removed/overwritten. Only the temporary preview container was refreshed; no original running service or OCR process was restarted.

### Exact application/test/document files changed
1. `frontend/src/app/page.tsx`: removed the additional collection-card section; retained the established AI Research Assistant, The Archive, Timeline & stories and Speeches & recordings cards. The Archive card now contains three compact collection links, using an article plus separate links to avoid nested anchors.
2. `frontend/src/components/CollectionNavigation.tsx` (new): shared, accessible three-collection navigation; the Archive page additionally has All archive records and current-page indication.
3. `frontend/src/app/archive/page.tsx`: added shared navigation to the existing catalogue; legacy `collection=audio` redirects to relative `/speeches`. Existing search/language/material/volume/sort filters are retained.
4. `frontend/src/components/CollectionBrowser.tsx`: removed the separate Audio & Speeches collection; placed the existing collection views within shared Archive navigation; removed a redundant all-records breadcrumb. Existing two-part photo/video queries, paging, protected image links and reader routes are retained.
5. `frontend/src/app/globals.css`: replaced styles for the removed competing section with compact Archive navigation styles and card-primary alignment. Existing typography/colors, general grid breakpoints, accessibility controls and focus treatment retained.
6. `frontend/src/components/Kiosk.tsx`: Back uses browser history only when a previous same-origin entry is available; otherwise it navigates to Archive parent or Home. Browsers without the Navigation API use the safe parent/Home fallback. Home/reset links remain relative.
7. `frontend/tests/collections.spec.ts`: revised assertions for exactly four established cards and three nested collection links; desktop/tablet/mobile origin checks, Archive navigation, legacy-audio redirect, Home/Back and cross-origin entry regression; existing image-reader and retry tests retained. Screenshots use each run's own output directory.
8. `implementation.md`: appended current navigation/routing/provenance decisions, superseding the preceding layout description.
9. `status.md`: current outcome and this audit.

Supporting new artifacts: `work/audit_navigation_urls.py` is a copy of the existing read-only URL auditor with only its output filename changed, preserving the prior audit report. New builds, screenshots, logs, folder inventory and `outputs/archive-navigation-source.diff` are separate artifacts. No backend application, schema, dataset or publication logic changed.

### Routing findings
Source inspection found no hardcoded `localhost:3000` or `127.0.0.1:3002` internal href/redirect in frontend source. Existing internal links already used relative paths. The original Back handler used unrestricted browser history and could leave the app, including for a different local port. This identified risk is now guarded; no claim is made that a particular hardcoded homepage link was found. Browser tests confirmed the four original destinations, three collection routes, Home and Back stay on the active origin, including entry from a simulated external origin. Existing external provenance links and deployment URLs/configuration were not changed. `/archive?collection=audio` now reaches `/speeches`, not another audio catalogue.

### Actual dataset organization and UI representation
The actual folder is named `Dataset` (capital D):
- `Dataset/Ambedkar_letters`: 25 JPEG candidates for Manuscripts & Letters. All remain private; folder names do not establish identity, type, rights or publication approval.
- `Dataset/Ambedkar_photos`: 36 PNG candidates for supplied Photographs. The two existing collection groups remain “From the supplied dataset” and “Other archive content.”
- `Dataset/Br. Ambedkar/videos`: six MP4 candidates; `Dataset/Br. Ambedkar/voice`: one MP4 and one MP3. Eligible videos belong in Videos; approved audio/MP3 recordings continue through `/speeches`. Presence on disk does not establish playback permission.
- Preserved other holdings: 19 root volume PDFs, one PDF in `book by br. ambedkar`, two PDFs in `books on br. ambedkar`, one reference TXT in `Br. Ambedkar` (92 files total).

Existing corpus-relative paths/checksum relationships retain provenance; registered curator metadata chooses material type. No filename/description-based classification or folder-based publication was added. Unregistered image candidates were not converted into placeholder records. The public API still returned only the two approved PIB excerpts, with zero supplied-dataset public records. No eligible real letter/photograph/video was available to populate those collections; honest empty states remain. The protected Ambedkar photograph remains unpublished. Existing protected readers/playback, originals and verified-text ordering are unchanged.

### Actual validation
| Check | Result |
|---|---|
| Frontend lint/typecheck/production build | Passed initial and final builds. `outputs/archive-navigation-frontend.log`, `outputs/archive-navigation-frontend-final.log`. Separate saved builds; no service image rebuild. |
| Relevant browser suite | **13 passed, 23.0s**, no skips/failures; `outputs/archive-navigation-browser.log`. Includes 5 collection/navigation tests, 2 existing recording-state tests and 6 existing reader/exhibition/layout tests. |
| Final adjustments | After visual review fixed Archive icon alignment and removed a redundant link; lint/typecheck/build rerun passed, followed by **5 passed, 10.8s** in `outputs/archive-navigation-browser-final.log`. |
| Responsive/visual | Actual Chrome at 1366, 768 and 390px; four established cards, only three nested collection links, no Audio & Speeches section, no horizontal overflow. Screenshots inspected; final captures in `work/archive-navigation-final-results`. |
| Live public read paths | Existing published catalogue/reader/original flow passed. Direct URL audit denied **403** requests across restricted metadata/originals/thumbnails/recordings/staff text/corpus pages, all 92 dataset paths, all 61 raw image OCR paths and two operator reports. Public dataset/other partitions remained disjoint. `outputs/archive-navigation-url-audit.json`, `outputs/archive-navigation-url-audit.log`. |
| Backend collection authorization | **1 passed, 4.43s**, isolated synthetic schema/storage, no skip. Checks stored membership, publication/withdrawal, exact original/thumbnail access and disjoint partitions. `outputs/archive-navigation-authorization.log`. Existing Starlette/httpx deprecation warning only. |
| Mock boundaries | Photo-reader population, thumbnail failure, collection errors/retry, recording-state tests and video-caption API use explicitly synthetic/mocked data. External-entry page is simulated. These do not prove real unpublished material is approved or historical media timing is correct. |
| Not rerun | Full backend suite, live Gemini, real SMTP, ASR/BHASHINI, audible narration, screen-reader acceptance, backup restore and physical touchscreen. No new claims for these. No actual content publication/review attempted. |

No functional test failed in this correction. Expected/non-test failures: Git commands failed without a repository; final `rg` forbidden-string search returned exit 1 because it found **no matches**. Benign npm update/NO_COLOR notices and the backend dependency deprecation warning were preserved. Docker actually executed the build and isolated authorization test; that proves these commands ran, not all integrations or model behavior.

### Exact commands executed for inspection and verification
Run from the existing project root. Docker/browser subprocess commands used approved elevated execution. Local file edits/checkpoint copies used normal workspace access.

```powershell
Get-Content frontend/src/app/page.tsx
Get-Content frontend/src/components/CollectionBrowser.tsx
Get-Content frontend/src/app/archive/page.tsx
Get-Content status.md -TotalCount 22
git status --short
git diff --stat
Get-ChildItem work/collections-baseline -Name
Get-Content outputs/collections-source.diff -TotalCount 45
Get-Content frontend/src/components/Kiosk.tsx -TotalCount 95
Get-Content frontend/src/app/globals.css -TotalCount 15
Get-Content frontend/tests/collections.spec.ts
Get-ChildItem Dataset -Recurse -File | Group-Object DirectoryName | Select-Object Name,Count
rg -n 'localhost:3000|127\.0\.0\.1:3002|location\.(href|assign|replace)|redirect\(' frontend/src frontend/next.config.ts
$taskRoot=(Get-Location).Path
docker compose ps
docker compose run --rm --no-deps -v "${taskRoot}/frontend/src:/app/src:ro" -v "${taskRoot}/frontend/tests:/app/tests:ro" -v "${taskRoot}/frontend:/result" frontend sh -c 'npm run lint && npm run typecheck && npm run build && cp -a .next /result/work-archive-navigation-next' *> outputs/archive-navigation-frontend.log
# Initial preview refresh used work-archive-navigation-next; final refresh below
# uses the separately validated final build. Only the temporary preview is stopped.
docker compose run --rm --no-deps -v "${taskRoot}/frontend/src:/app/src:ro" -v "${taskRoot}/frontend/tests:/app/tests:ro" -v "${taskRoot}/frontend:/result" frontend sh -c 'npm run lint && npm run typecheck && npm run build && cp -a .next /result/work-archive-navigation-final-next' *> outputs/archive-navigation-frontend-final.log
docker stop sih26096-collections-web
docker compose run --rm --no-deps -d --name sih26096-collections-web -p 127.0.0.1:3002:3000 -e BACKEND_INTERNAL_URL=http://sih26096-collections-api:8000 -v "${taskRoot}/frontend/src:/app/src:ro" -v "${taskRoot}/frontend/work-archive-navigation-final-next:/app/.next:ro" frontend npm run start
$env:ARCHIVE_E2E_BROWSER='C:/Program Files/Google/Chrome/Application/chrome.exe'
$env:PLAYWRIGHT_BASE_URL='http://127.0.0.1:3002'
node frontend/node_modules/@playwright/test/cli.js test --config frontend/playwright.config.ts frontend/tests/collections.spec.ts frontend/tests/content-states.spec.ts frontend/tests/redesign.spec.ts --output work/archive-navigation-browser-results --workers=1 *> outputs/archive-navigation-browser.log
python -X utf8 work/audit_navigation_urls.py *> outputs/archive-navigation-url-audit.log
docker compose run --rm --no-deps -e RUN_INTEGRATION=1 -e RUN_AI_ACCEPTANCE=0 -v "${taskRoot}/backend/app:/app/app:ro" -v "${taskRoot}/backend/tests:/app/tests:ro" backend python -m pytest -p no:cacheprovider -q tests/test_collections.py *> outputs/archive-navigation-authorization.log
node frontend/node_modules/@playwright/test/cli.js test --config frontend/playwright.config.ts frontend/tests/collections.spec.ts --output work/archive-navigation-final-results --workers=1 *> outputs/archive-navigation-browser-final.log
rg -n 'collection-entry|Audio & Speeches|localhost:3000|127\.0\.0\.1:3002' frontend/src
```

Limitations remain content/rights review and manual integration acceptance, not permission to release files: 25 letter candidates and 36 photo candidates await individual identification, registration, rights and publication decisions. Raw OCR, private recordings and unreviewed transcripts stay inaccessible. Original services remain at 3000/8000; the exact updated preview is **http://127.0.0.1:3002/**. No additional features were introduced beyond the requested navigation/layout correction and same-origin Back safeguard.


## Main homepage correction details — 2026-10-01

Inspected homepage, CollectionBrowser, CollectionNavigation, Archive route, existing card CSS, status, prior diffs/checkpoints, Compose and Dockerfile. Previous approval-review usage-limit failure did not execute Docker inspection. New approved read-only Docker inspect/exec failed because Docker's daemon pipe was absent. HTTP localhost:3000 refused connections. There was no live process whose container source could be read; the configured frontend source is the local `frontend/src` directory copied to `/app/src` by frontend/Dockerfile. The verified current frontend is `npm run dev -- --port 3000` launched from that local frontend directory, with BACKEND_INTERNAL_URL=http://127.0.0.1:8000. Backend is unavailable; no replacement/backend startup was attempted.

Exact source/test/config files changed:
- `frontend/src/app/page.tsx`: retained hero, accessible-reading wording, four established cards and existing CSS classes. Removed prior nested plain collection links; restored Archive card as one Link. Added fully boxed Manuscripts & Letters and Media links in the same path-grid (six cards, desktop 3×2, existing responsive behavior). No new promotional section or Audio & Speeches card.
- `frontend/src/app/archive/page.tsx`: `collection=media` is a lightweight Archive navigation destination with distinct Photographs and Videos links to existing collection routes, plus the existing /speeches link for audio. It creates no duplicate catalogue or data query. Existing authorization/filter/reader/playback implementations remain unchanged.
- `frontend/tests/main-homepage.spec.ts` (new): actual localhost:3000 responsive six-card, border/radius, Media destination, manuscript destination, back/home and audio routing checks at 1366/768/390 widths.
- `frontend/tests/collections.spec.ts`: removed obsolete four-card/inline-navigation test, superseded by new six-card test; preserved remaining four collection reader/error/origin tests.
- `frontend/eslint.config.mjs`: ignore `work-*-next/**` preserved generated build snapshots, alongside existing .next ignore. Source/tests remain linted; no artifacts deleted.
- `status.md`: this current verification and blockers.

Checkpoints: `work/main-homepage-baseline`; diff: `outputs/main-homepage-source.diff`. Existing checkpoints/logs/data/originals/OCR/migrations/volumes are retained. Dataset provenance organization is unchanged: Ambedkar_letters contains candidate manuscripts/letters; Ambedkar_photos candidate photographs; Br. Ambedkar candidate video/voice files. Folder names grant neither identity nor publication eligibility. No classification, import, OCR, rights or publication change was made. Photo/video queries still rely on existing corpus/checksum grouping and published-record authorization; compatibility with the currently unavailable main backend cannot be newly established.

Actual results:
- Initial `npm run lint` scanned saved generated builds: 788 errors and 15,340 warnings (16,128 problems), preserved in `outputs/main-homepage-lint.log`. Scoped src/tests lint passed; adding the generated snapshot ignore allowed the normal `npm run lint` rerun to pass (`main-homepage-lint-final.log`).
- Initial production build compiled then failed at TypeScript worker spawn with EPERM (`main-homepage-build.log`). Approved subprocess execution rerun passed (`main-homepage-build-final.log`). This was the requested production validation, not a project/service rebuild.
- Typecheck passed (`main-homepage-typecheck-final.log`). A premature read of the first typecheck log found it had not yet been created; the subsequent completed check passed.
- Actual Chrome main-homepage + existing content-state tests: 4 passed in 12.3s (`main-homepage-browser.log`). Two tests are actual visible homepage/routing/responsive checks; two recording-state tests use mocked API responses.
- Remaining collection regressions: 4 passed in 7.1s (`main-homepage-collections.log`). Individual image reader and collection errors/retry use explicit synthetic/mocked responses; the external-entry page is simulated. No tests skipped in these two runs.
- Screenshots inspected under `work/main-homepage-results`, desktop/mobile; viewport tests also cover tablet. Existing sticky header/footer appear in full-page captures; this continuation did not redesign them.
- Final GET http://localhost:3000 returned 200. Only the frontend was started, on exactly port 3000; no other preview was used.
- NOT VERIFIED: real public record filtering, dataset/other results from the live backend, direct-file authorization, live media playback/transcript alignment, live Gemini/email/ASR, physical touchscreen or screen reader. Docker/backend unavailability prevents backend-dependent acceptance. Earlier test results are historical, not new evidence here. No content was published to populate the cards.

Exact inspection/runtime/check commands (project root unless stated):
```powershell
docker inspect sih26096-frontend-1 --format '{{json .Mounts}} {{json .Config.Cmd}} {{json .Config.WorkingDir}} {{json .NetworkSettings.Ports}}'
docker compose exec -T frontend sh -c 'pwd; cat src/app/page.tsx'
Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue | Select-Object LocalAddress,LocalPort,OwningProcess
# Initial request failed; final request returned 200.
(Invoke-WebRequest 'http://localhost:3000' -TimeoutSec 10).StatusCode
npm.cmd --prefix frontend run lint > outputs/main-homepage-lint.log 2>&1
npm.cmd --prefix frontend run typecheck > outputs/main-homepage-typecheck.log 2>&1
npm.cmd --prefix frontend run build > outputs/main-homepage-build.log 2>&1
# From frontend directory, start only the current application frontend:
$env:BACKEND_INTERNAL_URL='http://127.0.0.1:8000'
npm.cmd run dev -- --port 3000
# From frontend directory, approved subprocess execution:
node node_modules/eslint/bin/eslint.js src tests > ../outputs/main-homepage-lint-scoped.log 2>&1
npm.cmd run typecheck > ../outputs/main-homepage-typecheck-final.log 2>&1
npm.cmd run build > ../outputs/main-homepage-build-final.log 2>&1
# From project root, after generated snapshot ignore:
npm.cmd --prefix frontend run lint > outputs/main-homepage-lint-final.log 2>&1
$env:ARCHIVE_E2E_BROWSER='C:/Program Files/Google/Chrome/Application/chrome.exe'
$env:PLAYWRIGHT_BASE_URL='http://localhost:3000'
node frontend/node_modules/@playwright/test/cli.js test --config frontend/playwright.config.ts frontend/tests/main-homepage.spec.ts frontend/tests/content-states.spec.ts --output work/main-homepage-results --workers=1 > outputs/main-homepage-browser.log 2>&1
node frontend/node_modules/@playwright/test/cli.js test --config frontend/playwright.config.ts frontend/tests/collections.spec.ts --output work/main-homepage-collection-results --workers=1 > outputs/main-homepage-collections.log 2>&1
```

No backend/database restart was attempted. Restoring Docker/backend availability is outside this frontend-only task; after it is available, real publication/filter/direct-file checks still need verification. The corrected **UI** is running and browser-verified at **http://localhost:3000/**; full archival functionality is not claimed complete.

## Empty collections diagnosis and safe continuation — 2026-10-01 (Astra)

This entry supersedes earlier collection-runtime claims. Findings were reported before application changes. No archival record, metadata, classification, rights, review status, original, OCR output or transcript was changed. **Records newly registered: none. Records newly published: none.** No database reset, volume deletion, image build, alternate preview or port 3002 browser validation was performed.

### Verified initial state and root causes

Docker services were already running; ordinary named-pipe access failed, elevated inspection succeeded. The project is not a Git repository (`git status --short` failed); existing user changes were preserved with additive checkpoints in `work/astra-empty-baseline` and new diffs. Read project rules, requirements, architecture, database/deployment/implementation notes, current status entries, dataset review, existing audit scripts and relevant backend/frontend/tests. Historical results were not counted as new validation.

| Collection | Current database and supplied material | Why publicly empty |
|---|---|---|
| Manuscripts & Letters | No registered `manuscript` records. 25 JPEG candidates in Ambedkar_letters; no archival item/corpus checkpoint for these images. | No curator-supported manuscript classification or publication approval. Folder/filename is insufficient evidence. |
| Photographs | 36 PNG candidates in Ambedkar_photos unregistered. Separate record `509f9e25-2112-4737-887b-f5ce3202f17e`, filename `Screenshot 2026-09-29 010531.png`, stored title Letters/type photograph, verified/public **but unpublished**, zero publication audit events, rights `Allowed`, current text extracted/unverified. | No approved published photograph; the existing record's placeholder rights do not establish public-display permission. |
| Videos | Seven existing private MP4 imports (six video-folder files and one voice-folder MP4); uploaded/staff, pending source provenance, rights `Not verified`, no transcript revisions or publication events. | No approved public recordings. Legacy format-derived video labels are retained, not endorsed as curator-verified identities/classifications. |

Live material-type APIs returned HTTP 200 and `[]` for all three, not authorization failures, pagination loss or failed requests. Browser pages have distinct loading/error/empty paths. There are 33 stored records total: 30 uploaded/staff, one verified/public but unpublished photograph, two published/public documents. Dataset: 92 files (22 PDFs, 25 JPEGs, 36 PNGs, seven MP4s, one MP3, one reference TXT); 30 files already registered (22 PDFs and eight recordings). All 61 image candidates have hash-matched private OCR derivatives, review `unverified`; no raw text was exposed or reprocessed. No evidence sufficient for new image classification/provenance was found. Current importer treats unsupported image formats as reference files; staff upload requires confirmed provenance/URLs. Registration was deferred rather than fabricating those assertions or bypassing the workflow.

Current checkpoints: 26,388 extracted PDF pages, 1,305 OCR-pending, no failed pages. The remaining pages are in the held 13,824-page compilation; its hold and outputs were preserved. Existing text revision totals: 24 extracted, two verified; 24 processing jobs succeeded. These machine states do not establish curator acceptance.

`outputs/astra-empty-inventory.json` is a fresh read-only per-file/database snapshot. `outputs/astra-empty-review-evidence.json` records filenames, rights, verification timestamps, transcript states and publication event counts. `outputs/ASTRA_EMPTY_COLLECTIONS_REVIEW.md` lists all relevant existing recording/photo IDs and all 61 candidate image filenames/hashes, with exact curator actions and workflow limitations.

### Confirmed defects and changes

1. Running backend `research.py` lacked the already-completed workspace `origin=dataset|other` catalogue filter. Before correction both filters returned the same two non-dataset public documents. This would mislabel/duplicate collection groups but did **not** cause the empty material-type collections. Added a read-only mount for the existing `backend/app/research.py` in `compose.yml`, then recreated only backend with `--no-deps --no-build`. No backend application logic was rewritten. Published/public authorization remains intact. Live verification now returns dataset `[]`, other exactly the two approved documents; groups are disjoint.
2. Collection heading hydration warning: Kiosk focus code adds `tabindex=-1` before hydration, while the heading JSX omitted it. Added `tabIndex={-1}` to the collection h1 in `frontend/src/components/CollectionBrowser.tsx`. Current-source lint/typecheck/build passed. Docker's frontend watcher did not load the edit automatically; restarted only the existing frontend, then confirmed no hydration warning and reran the collection browser checks. A residual browser resource 404 remains recorded in `outputs/astra-empty-console.json`; it was not identified as the cause of empty collections and is not claimed fixed.
3. Added operator-only diagnostic/report scripts under `work/astra_empty_*`, new logs/snapshots under `outputs/astra-empty-*`, review manifest and this status section. Existing report/baseline files were not replaced. `outputs/astra-empty-compose.diff`, `astra-empty-heading.diff`, and `astra-empty-runtime-research.diff` preserve the reviewable differences.

Runtime detail: no image was built. Compose selected the existing local `sih26096-backend` image tag on recreation: image changed from `a462d2c503327a9fc83f65086c79c93c908aa2cfa8c8eeec2d8f67b3530b8d5e` to pre-existing `50df2c25279d4b2d93f634124d0d48e8405559767b2dc16b2ae993b9d64d1860`. The backend test suite ran using that existing Compose image. Before/after module hash snapshots are saved; after activation `research.py` matches workspace, with only the previously differing `health.py` still differing from workspace. The database, archive volume, worker and other dependencies were retained.

### Actual validation and limits

| Check | Actual result/evidence |
|---|---|
| Backend complete existing suite | **79 passed, 2 skipped, 1 deprecation warning**, 131.13s; `astra-empty-backend-tests.log`. Real PostgreSQL integration with isolated synthetic schemas/storage; unit/provider contracts use mocks. Covers ingestion, classification/origin, lifecycle/rights, protected media, OCR/revisions, RAG citation eligibility, transcript invalidation, learning/quiz/certificates. Live Ollama/Gemini acceptance explicitly disabled/skipped. |
| Frontend lint/typecheck | Passed initially and after heading correction; `astra-empty-lint-final.log`, `astra-empty-typecheck-final.log`. |
| Production build | Initial sandbox build failed at TypeScript worker spawn EPERM. Elevated retry passed; post-edit final build passed (`astra-empty-build-final.log`). This is build verification, not a claim that port 3000 serves a production build; the existing service uses development mode. |
| Existing browser regressions, localhost:3000 | **26 passed, 1 skipped**, 1.5m; `astra-empty-browser.log`. Live public archive/original/text/exhibition and dependency paths; collection errors/retry, image fallback, captions, scoped AI, quiz and voice cases include explicit mocks/synthetic media. The isolated authenticated upload/review/publication kiosk test skipped because no isolated fixture server/auth file was configured; it was not pointed at production. |
| Focused browser reruns | Four passed before frontend restart; **four passed after restart**, 15.0s (`astra-empty-browser-restarted.log`). No skips. |
| Actual three collection pages | `astra_empty_live.cjs`: no mocks, HTTP 200 empty lists, five expected empty panels, no main alerts/page errors, dataset/other partition correct. Passed again after frontend restart; `astra-empty-live-browser-restarted.log`, JSON report and screenshots in `work/astra-empty-*.png`. |
| Restricted live API/static URLs | **403 denied requests** (count, not HTTP status), actual HTTP 401/404; `astra-empty-access-final.log/json`. Includes all 31 nonpublic records' catalogue/original/thumbnail/playback/transcript/staff-text/checkpoint paths, all 92 Dataset file URLs, all 61 private OCR JSON paths and two inventory paths. API responses checked `Cache-Control: no-store`. |
| Additional direct/range access | **155 denied requests**, HTTP 401/404; `astra-empty-extra-access.log/json`. Actual storage-key URLs, staff corpus/transcript paths and Range requests to playback. Existing backend synthetic tests additionally exercise withdrawal, staff media session authorization and protected thumbnails. |
| Preservation and RAG | All 92 dataset hashes equal the prior inventory; all 33 stored originals match stored SHA-256 before/after activation. Stored original IDs/status/access/checksum snapshot unchanged. Only the two public documents are RAG-eligible; vector scan complete and vector IDs match passage IDs. 124 direct backend denials also recorded in both preservation snapshots. Final live database count remains 33 total/two public. |
| Interrupted audit | First sequential localhost URL audit was interrupted by the needed frontend restart with RemoteDisconnected; failure retained in `astra-empty-url-audit.log`. Replaced by bounded eight-worker read-only audit against the stable frontend; all 403 checks passed. No failure was counted as a pass. |

Other inspection errors: initial broad rg encountered inaccessible temporary caches and excessive generated files; subsequent inspection targeted source paths. Two guessed staff component filenames did not exist; located actual staff page/CorpusStatus instead. One inline Python source-inspection command had a quoting SyntaxError; reading the file with container `cat` succeeded. No record writes resulted from these attempts. No credentials were printed or used; staff prototype credentials were unnecessary.

NOT RUN/NOT CLAIMED: new live AI generation, live ASR/BHASHINI, SMTP delivery, independent historical identity/rights verification, historical transcript/audio alignment, physical touch/screen-reader/audible narration acceptance, backup restore, authenticated production curator interactions or publication. Backend integration is local synthetic data, not approval of historical records. No withdrawn production record exists to live-test; synthetic withdrawal regression passed.

### Curator actions / public selection

For existing MP4s: `/staff` → **Dataset ingestion and page checkpoints** → locate exact filename → **Review source and rights**. Independently document source URL, identity/classification and permission for intended display. Check public-display approval only with supporting evidence. In staff record pages/Needs Review, review original and current transcript (where applicable), verify text separately, confirm original/metadata/provenance/rights, then explicitly publish. Neither this audit nor successful format probing grants approval. Staff filters apply per page; use Next records.

For image candidates: obtain documented provenance, identity/type and rights first; preserve current originals and raw OCR. The current UI cannot honestly register pending-provenance images without mandatory confirmation. For the existing Letters photograph, keep it unpublished; the non-corpus record also lacks a general existing-record rights/metadata editor. An audited metadata correction workflow is needed after evidence is supplied; do not replace the original, duplicate the record or directly SQL-publish. These limitations are unresolved and recorded, not worked around.

**Approved public records in the three requested collections: none. All three remain correctly empty.** Elsewhere, the two existing documents have verified current text, recorded source/rights evidence, verification timestamps and one explicit publication audit event each, and remain publicly visible:
- `8ce2df4c-c4e2-4ed1-bf9e-244881273e82` — `pib-biography-excerpt.txt`.
- `d3607a2e-92fd-4886-9f29-56c9cd38d8d3` — `pib-constitution-excerpt.txt`.

Their existing approval evidence was checked in the database; this session did not independently re-adjudicate the external copyright policy or create new approvals.

### Reproducible commands actually executed

All commands from the project root; Docker and Chrome/build subprocess commands used elevated execution after sandbox limitations. Diagnostic scripts contain the exact read-only SQL/HTTP/hash checks. No `.env` or credential contents were printed.

```powershell
git status --short
docker compose ps -a
$taskRoot=(Get-Location).Path
docker compose run --rm --no-deps -e PYTHONPATH=/app -v "${taskRoot}/Dataset:/dataset:ro" -v "${taskRoot}/scripts:/audit:ro" -v "${taskRoot}/outputs/dataset-image-review:/image-ocr:ro" backend python /audit/content_inventory.py /dataset /image-ocr > outputs/astra-empty-inventory.json
docker compose run --rm --no-deps -e RUN_INTEGRATION=1 -e RUN_AI_ACCEPTANCE=0 -e RUN_GEMINI_ACCEPTANCE=0 -v "${taskRoot}/backend/app:/app/app:ro" -v "${taskRoot}/backend/tests:/app/tests:ro" backend python -m pytest -p no:cacheprovider -q > outputs/astra-empty-backend-tests.log 2>&1
Get-Content scripts/audit_redesign.py | docker compose exec -T backend python - > outputs/astra-empty-preservation.json
docker compose exec -T backend cat app/research.py > outputs/astra-empty-runtime-research.py
docker compose exec -T backend cat app/health.py > outputs/astra-empty-runtime-health.py
git diff --no-index -- outputs/astra-empty-runtime-research.py backend/app/research.py > outputs/astra-empty-runtime-research.diff
npm.cmd --prefix frontend run lint > outputs/astra-empty-lint.log 2>&1
npm.cmd --prefix frontend run typecheck > outputs/astra-empty-typecheck.log 2>&1
npm.cmd --prefix frontend run build > outputs/astra-empty-build.log 2>&1
npm.cmd --prefix frontend run build > outputs/astra-empty-build-retry.log 2>&1
docker compose up -d --no-deps --no-build backend
python -X utf8 work/astra_empty_url_audit.py > outputs/astra-empty-url-audit.log 2>&1
$env:ARCHIVE_E2E_BROWSER='C:/Program Files/Google/Chrome/Application/chrome.exe'
$env:PLAYWRIGHT_BASE_URL='http://localhost:3000'
node frontend/node_modules/@playwright/test/cli.js test --config frontend/playwright.config.ts frontend/tests/collections.spec.ts frontend/tests/main-homepage.spec.ts frontend/tests/content-states.spec.ts frontend/tests/reader-quiz.spec.ts frontend/tests/redesign.spec.ts frontend/tests/kiosk.spec.ts frontend/tests/foundation.spec.ts --output work/astra-empty-browser-results --workers=1 > outputs/astra-empty-browser.log 2>&1
node work/astra_empty_live.cjs > outputs/astra-empty-live-browser.log 2>&1
node work/astra_empty_console.cjs
Get-Content scripts/audit_redesign.py | docker compose exec -T backend python - > outputs/astra-empty-preservation-after.json
npm.cmd --prefix frontend run lint > outputs/astra-empty-lint-final.log 2>&1
npm.cmd --prefix frontend run typecheck > outputs/astra-empty-typecheck-final.log 2>&1
npm.cmd --prefix frontend run build > outputs/astra-empty-build-final.log 2>&1
python -X utf8 work/astra_empty_report.py
python -X utf8 work/astra_empty_extra_access.py > outputs/astra-empty-extra-access.log 2>&1
node work/astra_empty_live.cjs > outputs/astra-empty-live-browser-final.log 2>&1
node frontend/node_modules/@playwright/test/cli.js test --config frontend/playwright.config.ts frontend/tests/collections.spec.ts --output work/astra-empty-browser-final --workers=1 > outputs/astra-empty-browser-final.log 2>&1
docker compose restart frontend
python -X utf8 work/astra_empty_access_final.py > outputs/astra-empty-access-final.log 2>&1
node work/astra_empty_console.cjs
node work/astra_empty_live.cjs > outputs/astra-empty-live-browser-restarted.log 2>&1
node frontend/node_modules/@playwright/test/cli.js test --config frontend/playwright.config.ts frontend/tests/collections.spec.ts --output work/astra-empty-browser-restarted --workers=1 > outputs/astra-empty-browser-restarted.log 2>&1
git diff --no-index -- work/astra-empty-baseline/compose.yml compose.yml > outputs/astra-empty-compose.diff
git diff --no-index -- work/astra-empty-baseline/CollectionBrowser.tsx frontend/src/components/CollectionBrowser.tsx > outputs/astra-empty-heading.diff
docker inspect sih26096-backend-1 --format '{{.Image}}'
```

`git diff --no-index` returns 1 when differences are found; those saved diffs are expected, not failed implementation checks. Source inspection used Get-Content, rg, Get-ChildItem and Get-FileHash; database/module probes were read-only and saved to the review/hash snapshots above. Status append source is retained in `work/astra_empty_status_append.md`; the saved status file is checked for the complete appended entry and preservation of its prior contents.


## Dataset release checkpoint and Bhashini continuation — 2026-10-02

This entry supersedes the earlier empty-collection conclusions for the organizer dataset only. Detailed validation: `DATASET_RELEASE_VALIDATION.md` and `BHASHINI_VALIDATION.md`. Earlier reports remain historical evidence, not current publication counts.

### Verified checkpoint and initial findings

- Inspected existing code, migration history, dataset manifest/application report, original bytes, DB state, backup and prior test results before edits. Migration `010_dataset_release.sql` and release `sih26096-organizer-2026-10-01` had already completed. No release rerun, additional ingestion, OCR processing, record publication or archival data mutation was required in this continuation.
- Manifest SHA-256 `bf0d5f8e07997f76644e41a27799f3d31ab76d6be47a2a948216899a448efdde`: **92 registered dataset files, 91 public, one explicit exclusion**. Prior release: **62 newly registered, 30 retained**. New records in this continuation: **0**. Current archive: **95 records, 93 published/public, one uploaded/staff hold, one verified/public but unpublished external image**.
- Manuscripts: **25 public JPEG originals**; Photographs: **36 public PNG originals**; Videos: **7 public MP4s**. No requested collection remains empty. Image collections represent supplied grouping; image identity/date/authorship and historical classification remain unverified. This is owner-authorized SIH original display, not curator certification.
- Remaining public dataset: **21 PDFs, one MP3, one reference TXT**. All 92 supplied and stored-original SHA-256 values match manifest; exact IDs/filenames/statuses are recorded per file in `outputs/dataset-release-checkpoint-verified.json` and prior new/existing flags in `outputs/dataset-release-applied.json`.
- Dataset text: **21 extracted/unreviewed revisions, 71 without a revision; zero verified dataset text; zero recording transcript revisions**. Corpus labels: 90 awaiting_review, one reference, one preserved processing hold. Private image OCR and completed extraction outputs remain preserved and inaccessible publicly. Public original display does not enable unreviewed OCR/transcript retrieval or translation.
- Held PDF: `c5926726-5d27-4990-a08f-76a932fa57db`, `Br. Ambedkar/book by br. ambedkar/Collected Works of Ambedkar vol 1.pdf`, 13,824 pages/checkpoints. Explicit identity/scope exclusion remains; the historical processing label must not be treated as authorization to resume it.
- External photo: `509f9e25-2112-4737-887b-f5ce3202f17e`, `Screenshot 2026-09-29 010531.png`, remains unpublished. Dataset authorization does not extend to it. Only the existing PIB records `8ce2df4c-c4e2-4ed1-bf9e-244881273e82` and `d3607a2e-92fd-4886-9f29-56c9cd38d8d3` currently have public verified text eligible for RAG.
- Backup `work/dataset-release-baseline/database.dump` is present, 30,678,946 bytes. `pg_restore --list` succeeded; no restore drill performed. All volumes/originals/checkpoints/baselines preserved. No Git repository exists in this project directory; no commit/reset attempted.

### Root causes and minimal changes

Original empty states arose from unregistered/private records and the distinction between supplied grouping and verified classification. The preceding release introduced a frozen, scoped dataset publication grant and collection grouping. Current DB/API results prove the intended transaction completed; no repair publication was needed.

Added backend-only Bhashini translation in `backend/app/translation.py`, opt-in `check_translation.py`, Settings aliases for the existing environment keys, backend Compose wiring and documented placeholder settings. `llm.py` accepts a translation-specific system instruction for explicitly requested Gemini/Ollama fallbacks; RAG provider behavior is unchanged. No secret values are stored in source or reports. Official authentication/payload/service/language documentation and live/mocked distinctions are in `BHASHINI_VALIDATION.md`.

Translation requires current published/public, curator-verified text, holds eligibility through the bounded provider call, rejects arbitrary supplied text, returns machine-generated/unreviewed output with exact revision/sequence/text hash, and never indexes that output. Missing credentials/auth/provider failures are sanitized. Optional pipeline discovery is implemented/mocked; configured pre-issued inference credentials and documented `bhashini/iiith/nmt-all` were used for actual English→Hindi calls. Reverse direction, live config discovery, translation fallbacks and expert linguistic accuracy remain unverified.

Frontend: corrected stale “one Constitution result” test to compare the live filtered API count (now two); corrected kiosk's obsolete Bhashini availability description; fixed confirmed reader rendering of structured validation errors as `[object Object]` with a clear unavailable-state message. Added a focused regression. Current source is served via existing Docker bind mounts; frontend watcher required a service-only restart to discard stale compiled wording.

Files changed in this continuation: `.env.example`, `compose.yml`; backend `app/config.py`, `app/llm.py`, `app/main.py`, `app/translation.py`, `app/check_translation.py`, `tests/conftest.py`, `tests/test_translation.py`; frontend `src/components/Kiosk.tsx`, `src/app/archive/[id]/page.tsx`, `tests/redesign.spec.ts`, `tests/reader-quiz.spec.ts`; `scripts/verify_dataset_release.py`, `verify_dataset_release_browser.cjs`, `verify_release_checkpoint.py`, `verify_release_private_paths.py`, `verify_translation_api.py`; reports/status/implementation documentation. Existing release changes were preserved. Snapshot: `work/bhashini-baseline`.

### Validation results and failures retained

- Backend focused provider/translation: **29 passed** (`outputs/bhashini-focused.log`). Complete default invocation: **71 passed, 31 skipped** because integration flag omitted; not presented as integration success. Corrected full isolated-PostgreSQL invocation: **100 passed, 2 live AI acceptance tests skipped**, one existing Starlette/httpx deprecation warning (`outputs/bhashini-backend-integration.log`). These include ingestion/classification/publication/withdrawal/media/RAG/citation/transcript/quiz/certificate gates. External provider behavior is mocked except explicitly reported live tests.
- Initial formatter could not write the read-only `/app/app` mount; corrected writable `/edit` mount formatted the three changed modules. Initial Ruff found three long lines, fixed; final Ruff passed (`outputs/bhashini-backend-lint-final.log`).
- Frontend lint/typecheck/production build passed both before and after the reader fix; final logs `outputs/bhashini-frontend-{lint,typecheck,build}-final.log`. No preview server or new Docker image build used.
- Initial complete browser suite: **28 passed, 6 skipped, one stale-count failure**. Corrected keyboard test: **1 passed**. Dedicated live audit passed 25/36/7 collection pagination, two image viewers, PDF/text viewers and **8 actual muted media playback checks**. Fixture-based full lifecycle browser tests were skipped to avoid live corpus mutation; backend equivalents ran in isolated schemas. API failure/empty states, synthetic captions, speech API and some quiz contracts are explicitly mocked, not live provider proof.
- Per-file live public audit after backend activation passed **91 originals (1,320,155,886 streamed bytes with matching SHA-256)**, image thumbnails, recording range206 responses, details/collection pagination and protected held/external photo responses. `outputs/dataset-release-public-audit-resumed.json` preserves fresh results separately from the prior audit.
- Live retrieval succeeded for only the two approved PIB text sources; exact citation substring offsets verified, dataset-unreviewed scoped retrieval empty, no generation called (`outputs/dataset-release-research-resumed.json`). No new end-to-end live RAG generation acceptance claim.
- Actual Bhashini compute succeeded for an authored connectivity sentence (`outputs/bhashini-live.json`), then the localhost API succeeded for already-public verified PIB text with exact source hash, stale409 and ineligible404 (`outputs/bhashini-live-api.json`). Initial API audit script failed before sending text because it assumed an object revision; fixed to use the existing integer field and rerun successfully.
- Credential containment compared both configured Bhashini values in memory against 124 app/source/script/browser-asset files at the time of the check; none found (`outputs/bhashini-credential-containment.json`). This is scoped validation, not a claim of an exhaustive historical secret audit.
- Live prototype staff login was not rerun; anonymous staff401 checks and isolated authenticated role/lifecycle tests passed. No staff credentials/screenshots/traces were written.
- Initial direct-path audit falsely expected404 at `/archive/originals/`, which matches the public dynamic reader shell. It exposed a display error, not a file leak; API rejected the invalid UUID. Corrected the filesystem-path probe to `/originals/`, fixed the error message, and retained the failed log. Final private-path and focused browser results follow in the completion entry.

### Commands run (project root unless specified)

Read-only inspection used `Get-Content`, `rg`, `Get-ChildItem`, `Get-FileHash`, Docker status and SQL probes; no environment values were printed. `$taskRoot=(Get-Location).Path` in the commands below.

```powershell
docker compose config --quiet
docker compose run --rm --no-deps -v "${taskRoot}/work/dataset-release-baseline/database.dump:/backup.dump:ro" postgres pg_restore --list /backup.dump > outputs/dataset-release-backup-list.log
Get-Content scripts/verify_dataset_research.py | docker compose exec -T backend python - > outputs/dataset-release-research-resumed.json
docker compose run --rm --no-deps backend python -m app.check_translation --live > outputs/bhashini-live.json
docker compose run --rm --no-deps -v "${taskRoot}/backend/tests:/app/tests:ro" backend python -m pytest -q > outputs/bhashini-full-backend.log 2>&1
docker compose run --rm --no-deps -e RUN_INTEGRATION=1 -e RUN_AI_ACCEPTANCE=0 -e RUN_GEMINI_ACCEPTANCE=0 -v "${taskRoot}/backend/tests:/app/tests:ro" backend python -m pytest -p no:cacheprovider -q > outputs/bhashini-backend-integration.log 2>&1
docker compose run --rm --no-deps -v "${taskRoot}/backend:/edit" backend python -m ruff format /edit/app/translation.py /edit/app/check_translation.py /edit/app/config.py > outputs/bhashini-format-corrected.log 2>&1
docker compose run --rm --no-deps -v "${taskRoot}/backend/tests:/app/tests:ro" backend python -m ruff check --no-cache app tests > outputs/bhashini-backend-lint-final.log 2>&1
docker compose up -d --no-deps --no-build backend > outputs/bhashini-backend-activation.log 2>&1
Get-Content scripts/verify_release_checkpoint.py | docker compose run --rm --no-deps -T -v "${taskRoot}/Dataset:/dataset:ro" -v "${taskRoot}/outputs:/audit:ro" backend python - > outputs/dataset-release-checkpoint-verified.json
python scripts/verify_translation_api.py > outputs/bhashini-live-api-recheck.log 2>&1
python scripts/verify_dataset_release.py --output outputs/dataset-release-public-audit-resumed.json > outputs/dataset-release-public-audit-resumed.log 2>&1
python scripts/verify_release_private_paths.py > outputs/dataset-release-private-paths-recheck.log 2>&1
node scripts/verify_dataset_release_browser.cjs > outputs/dataset-release-live-browser.log 2>&1
$env:ARCHIVE_E2E_BROWSER='C:/Program Files/Google/Chrome/Application/chrome.exe'
$env:PLAYWRIGHT_BASE_URL='http://localhost:3000'
node frontend/node_modules/@playwright/test/cli.js test --config frontend/playwright.config.ts --output work/dataset-release-resumed-browser --workers=1 > outputs/dataset-release-resumed-browser.log 2>&1
node frontend/node_modules/@playwright/test/cli.js test --config frontend/playwright.config.ts frontend/tests/redesign.spec.ts --grep 'large text' --output work/dataset-release-keyboard-recheck --workers=1 > outputs/dataset-release-keyboard-recheck.log 2>&1
docker compose ps --format json > outputs/dataset-release-services-final.json
# From frontend/ (run again after reader fix):
npm run lint *> ../outputs/bhashini-frontend-lint-final.log
npm run typecheck *> ../outputs/bhashini-frontend-typecheck-final.log
npm run build *> ../outputs/bhashini-frontend-build-final.log
```

An initial backup-list attempt used unsupported PowerShell `<` redirection and failed parsing before execution; corrected mounted-path command above succeeded. Initial format/lint/API audit/private-path failures and browser failure remain in their respective logs; no failed check is described as a pass. Supplementary public browser shell and in-memory credential checks are documented in the report and output artifacts.

### Remaining review / unverified behavior

Curators should resolve the held compilation's identity and scope before any processing; review/correct extracted/OCR text in the staff text workspace and separately verify the revision before RAG; supply and verify timed transcripts where needed; establish image identity/date/authorship from evidence. External material still requires independently adequate rights/provenance and publication approval. Do not require redundant per-file rights approvals for the expressly authorized organizer dataset. No dataset text is currently certified for RAG. Expert translation accuracy, reverse-pair live inference, config-discovery live credentials, live fallback generation, backup restore, full production/load behavior and six isolated browser workflows remain unverified in this continuation.


### Completion verification — 2026-10-02

Final full browser regression on the restarted current frontend: **30 passed, 6 skipped**, no failures (`outputs/dataset-release-final-browser.log`). This supersedes the earlier combined-run count above. The new structured-reader-error test passed; actual invalid-ID reader and current kiosk wording also passed (`outputs/dataset-release-reader-shell-final.log`). Final frontend lint/typecheck/build all passed after that fix. Backend remains **100 passed, 2 skipped**.

The corrected direct-path audit passed **351** private original/text/static/OCR/authentication denials (`outputs/dataset-release-private-paths-recheck.log`, `outputs/dataset-release-private-paths.json`). The complete fresh public audit passed **91 original files and hashes, 61 image thumbnails, 8 recording range requests, collection/detail APIs and held/external-image denials**. Public original bytes streamed: **1,320,155,886**. All 92 supplied/stored original hashes also matched independently in the read-only DB checkpoint audit. No dataset registration/publication/OCR actions were repeated.

Final services: backend, frontend, Ollama and PostgreSQL running/healthy; Qdrant and worker running (no Compose healthcheck configured for those two). Existing Docker images, database volumes, originals, backup and earlier report/baseline history preserved. `status.md` and `implementation.md` were appended and checked against their original bytes; final reports saved as `DATASET_RELEASE_VALIDATION.md` and `BHASHINI_VALIDATION.md`.

Final commands:

```powershell
docker compose restart frontend > outputs/bhashini-frontend-restart.log 2>&1
$env:ARCHIVE_E2E_BROWSER='C:/Program Files/Google/Chrome/Application/chrome.exe'
$env:PLAYWRIGHT_BASE_URL='http://localhost:3000'
node frontend/node_modules/@playwright/test/cli.js test --config frontend/playwright.config.ts --output work/dataset-release-final-browser --workers=1 > outputs/dataset-release-final-browser.log 2>&1
docker compose ps --format json > outputs/dataset-release-services-final.json
```

Additional bounded public-only Playwright probe (piped to `node`) asserted the actual `/archive/originals/` unavailable alert, no reader content and current kiosk translation wording. In-memory Python append verification asserted that saved status and implementation retained their original byte prefixes and contained the complete new sections. No secrets or staff browser traces were included. Unverified items and curator actions listed above remain outstanding; successful infrastructure checks do not certify historical or translation accuracy.


## Interface-language continuation validation — 2026-10-02

This entry continues the existing project; it does not redo the dataset release. The prior session's interface-language implementation was present but had not been recorded in this status file. Prior validation reports remain historical evidence.

### Inspection and preservation

Inspected `agent.md`, requirements/architecture/database/deployment/implementation/status documentation, `BHASHINI_VALIDATION.md`, `DATASET_RELEASE_VALIDATION.md`, prior interface/backend/frontend/live logs, source, tests, Compose bind mounts and running services. `git status --short` and `git diff --stat` failed because this directory has **no Git repository**, as earlier reports also noted. No Git initialization/reset/checkout was performed.

Compared current backend application/tests and frontend source/tests to `work/interface-language-baseline`. The reported “13 recently changed files” is not an authoritative diff: the saved baseline comparison found **36 changed/added source and test files**, including shared language components, catalogs, visitor/staff pages and translation APIs. Full inventory: `outputs/resume-language-changes.json`; baseline diff: `outputs/resume-language-baseline-diff.txt`. These were captured before this continuation's new browser tests and frontend behavioral fix (the two lint formatting corrections were already present). Reviewed the broader change set instead of assuming only 13 files existed. Current timestamp listing: `outputs/resume-language-recent-files.json` (includes this continuation's edits; not the previous session's exact 13-file list).

No releases, ingestion, processing, publication, migration changes, database resets, Docker volume removals or destructive Git operations were performed. Existing credentials were neither printed nor edited. Browser staff interactions used mocked responses and synthetic entered data, with no real login or upload. The existing backend integration harness used isolated synthetic schemas and temporary storage, including its established cleanup of those test schemas only.

Read-only before/after snapshots matched all 11 checked tables: archival_item, asset, source, text_revision, text_segment, passage, corpus_file, corpus_page, dataset_release, dataset_member and schema_migration. Evidence: `outputs/resume-language-preservation-{before,after}.json`. Counts remain **95 archive records, 93 public/published, one staff/uploaded hold and one verified/public but unpublished external image; 92 dataset members; 10 migration entries**. The same two PIB revision-2 records remain RAG eligible. This is database-content fingerprint evidence; the entire original-byte corpus was not rehashed again in this continuation. No operation wrote originals. Interface cache derivatives may be updated by the existing translation API.

### Confirmed fixes and additions

- Backend lint: wrapped the overlong capability notice in `backend/app/interface_language.py` and sorted the interface-router import in `backend/app/main.py`. No backend behavior/access-rule change.
- Frontend: `frontend/src/components/InterfaceLanguage.tsx` now validates the capability response before storing it. A malformed successful response (reproduced by an existing broad quiz API mock returning `[]`) previously set `languages` to undefined and crashed the shared Kiosk layout. It now retains English and reports unavailability. Added a regression for that exact failure.
- Updated obsolete “Navigation language” selectors and fixed assumptions about translated labels in `frontend/tests/kiosk.spec.ts` and `frontend/tests/runtime-repair.spec.ts`. Kiosk speech/interface fixtures are explicitly mocked; the runtime accessibility check uses live interface/cache responses.
- Added `frontend/tests/interface-language.spec.ts`: five checks cover visitor/staff switching, dynamic labels, unchanged entered title, no automatic content translation, explicit labelled translation/source links, outage fallback and malformed capabilities. Synthetic staff/provider responses are explicitly identified.
- Added read-only/local validation scripts `scripts/verify_language_preservation.py`, `verify_language_api.py`, `verify_language_browser.cjs` and new uniquely named result logs. No source content or provider credentials are embedded in these scripts.
- Confirmed Windows bind-mount watcher staleness: container source had `useInterface`, while served HTML still contained “Navigation language.” Restarted **frontend service only**, twice (initial language activation and activation of the response-validation fix). No image rebuild, database restart or volume operation. The local production build is a validation build; localhost continues to use the existing development service.

### Results actually obtained

| Check | Result and evidence |
|---|---|
| Full backend suite, real isolated PostgreSQL; external translation providers mocked | **109 passed, 2 skipped**, one existing Starlette/httpx deprecation warning; `outputs/resume-language-backend-tests.log`. Skips are opt-in live Ollama/model acceptance and opt-in live Gemini acceptance. |
| Focused interface/content translation after lint fixes | **27 passed**, no skips; `outputs/resume-language-backend-focused-final.log`. Covers ID allowlist, arbitrary text/extra-field/unsupported-target rejection, provider and translation caches, placeholder rejection, English fallback, failure sanitization, unsafe callback rejection, explicit provider fallback, current-public-verified eligibility, stale revisions and withdrawal. Provider inference is mocked in these tests. |
| Backend Ruff | Initial two errors retained in `outputs/resume-language-backend-lint.log`; final **passed**, `outputs/resume-language-backend-lint-final.log`. |
| Frontend lint/typecheck | Passed after the application fix and test updates; final logs `outputs/resume-language-complete-lint.log` and `outputs/resume-language-complete-typecheck.log`. |
| Production build | Initial attempt compiled then failed `spawn EPERM` in sandbox. Elevated retry passed. Build including final application fix **passed**, `outputs/resume-language-build-after-fix.log`. No dependencies installed/upgraded. |
| Complete final browser regression | **35 passed, 6 skipped**, no failures; `outputs/resume-language-complete.log`. All five new language tests passed. Skipped workflows are listed below. |
| Real interface/browser audit | **11 routes passed** at localhost:3000, English/Hindi switching, Hindi large-text/high-contrast/reduced-motion controls and actual browser fullscreen. Anonymous staff route live; authenticated staff controls mocked in focused test. `outputs/resume-language-live-browser.json`, `.log` variants, `outputs/resume-language-hindi-home.png`. Interface translations may come from the existing server cache; this is not proof of 716 fresh provider calls. |
| Fresh live Bhashini inference | Authored connectivity sentence succeeded, explicitly en→hi; `outputs/resume-language-bhashini-live.log`. Separately the live browser invoked exactly **one explicit** translation of already-public verified PIB text and displayed machine/unreviewed labelling. No archive translation requests occurred during the preceding interface switches. |
| Live API security | **9 rejection checks passed**: five interface payload/ID/target/batch errors, three ineligible content requests (public unreviewed dataset, held compilation, unpublished external image), one stale revision; `outputs/resume-language-api.json`. No eligible translation or provider inference requested by this script. |
| Access-denial audit | **351 passed**, original/text/static/OCR/authentication denials; `outputs/resume-language-private-paths.log` and `.json`. Existing audit reused with a new output path so the prior JSON was preserved. |
| RAG/citations and preservation | Live retrieval still uses only two PIB sources, exact source-segment citation offsets verified, scoped unreviewed dataset retrieval empty; `outputs/resume-language-research.json`. No generation called. All 11 table fingerprints and publication/eligibility snapshots unchanged. |

The interface catalog still has 716 registered strings; prior live evidence had 715 valid translations and one placeholder-rejected quiz template. The live UI continues to disclose partial English fallback. No attempt was made to bypass placeholder validation or certify machine wording.

### Failures and interrupted checks retained

- Initial broad file search entered generated dependency/cache directories and encountered access-denied temporary folders; subsequent searches targeted source. Some PowerShell `rg` wildcard paths were invalid. These inspection errors did not change project data.
- Initial Docker access failed on the sandbox named pipe; approved elevated access succeeded. Initial build `spawn EPERM` is retained separately from its successful retry.
- First complete browser run returned **30 passed, 6 skipped**, but was found to target stale compiled frontend code. It is **not** acceptance of the new interface; retained as `outputs/resume-language-browser.log`. The first focused attempt was interrupted after proving stale runtime.
- Current-source focused run: **2 passed, 2 failed** (test assumed two recordings; staff initial-load race in test). Corrected run: **3 passed, 1 failed** (test used `getByLabel` for text-size select instead of its role/name). No archive code was changed for these test assumptions.
- Current-source kiosk run: **5 passed, 1 skipped, 2 failed** due to obsolete language selectors. The broader `resume-language-browser-final` run was interrupted after exposing the malformed-capability crash and obsolete test assumptions; no success total is claimed for it.
- `resume-language-regression-fixed.log`: **12 passed, 1 skipped, 3 failed**. The frontend watcher had not loaded the application fix; the speech fixture also clicked before its guide translation batch completed. Reloaded frontend and explicitly awaited batch completion.
- `resume-language-current-final.log`: **33 passed, 6 skipped, 2 failed**: disabled `<option>` assertion semantics and another obsolete selector in mobile accessibility. Changed the assertion to the actual DOM `disabled` property. `resume-language-accepted-browser.log`: **34 passed, 6 skipped, 1 failed**, the remaining mobile selector. Corrected focused mobile accessibility rerun **1 passed**, `outputs/resume-language-accessibility-final.log`.
- Live-browser audit first failed because it checked heading text before translation batches finished; second failed because it captured the reader before source text loaded. Added explicit completion/source-render waits. Final live audit passed; earlier logs are retained. These were audit synchronization errors, not translated archival content.

### Exact validation commands

Executed from this existing project root in PowerShell. Docker and Chrome/build subprocess invocations used approved elevation where required. `$taskRoot=(Get-Location).Path`. No environment contents were printed.

```powershell
git status --short
git diff --stat
docker compose ps
$taskRoot=(Get-Location).Path
docker compose run --rm --no-deps -e RUN_INTEGRATION=1 -e RUN_AI_ACCEPTANCE=0 -e RUN_GEMINI_ACCEPTANCE=0 -v "${taskRoot}/backend/tests:/app/tests:ro" backend python -m pytest -p no:cacheprovider -q *> outputs/resume-language-backend-tests.log
docker compose run --rm --no-deps -v "${taskRoot}/backend/tests:/app/tests:ro" backend python -m ruff check --no-cache app tests *> outputs/resume-language-backend-lint.log
docker compose run --rm --no-deps -v "${taskRoot}/backend/tests:/app/tests:ro" backend python -m ruff check --no-cache app tests *> outputs/resume-language-backend-lint-final.log
docker compose run --rm --no-deps -e RUN_INTEGRATION=1 -e RUN_AI_ACCEPTANCE=0 -e RUN_GEMINI_ACCEPTANCE=0 -v "${taskRoot}/backend/tests:/app/tests:ro" backend python -m pytest -p no:cacheprovider -q -rs tests/test_interface_language.py tests/test_translation.py *> outputs/resume-language-backend-focused-final.log
npm.cmd --prefix frontend run lint *> outputs/resume-language-lint.log
npm.cmd --prefix frontend run typecheck *> outputs/resume-language-typecheck.log
npm.cmd --prefix frontend run build *> outputs/resume-language-build.log
npm.cmd --prefix frontend run build *> outputs/resume-language-build-retry.log
npm.cmd --prefix frontend run build *> outputs/resume-language-build-after-fix.log
npm.cmd --prefix frontend run lint *> outputs/resume-language-complete-lint.log
npm.cmd --prefix frontend run typecheck *> outputs/resume-language-complete-typecheck.log
docker compose restart frontend *> outputs/resume-language-frontend-restart.log
docker compose restart frontend *> outputs/resume-language-frontend-restart-after-fix.log
docker compose run --rm --no-deps backend python -m app.check_translation --live *> outputs/resume-language-bhashini-live.log
Get-Content scripts/verify_language_preservation.py | docker compose exec -T backend python - > outputs/resume-language-preservation-before.json
Get-Content scripts/verify_dataset_research.py | docker compose exec -T backend python - > outputs/resume-language-research.json
node scripts/verify_language_browser.cjs *> outputs/resume-language-live-browser-final.log
python -X utf8 scripts/verify_language_api.py *> outputs/resume-language-api.json
Get-Content scripts/verify_language_preservation.py | docker compose exec -T backend python - > outputs/resume-language-preservation-after.json
$env:ARCHIVE_E2E_BROWSER='C:/Program Files/Google/Chrome/Application/chrome.exe'
$env:PLAYWRIGHT_BASE_URL='http://localhost:3000'
node frontend/node_modules/@playwright/test/cli.js test --config frontend/playwright.config.ts --output work/resume-language-complete --workers=1 *> outputs/resume-language-complete.log
node frontend/node_modules/@playwright/test/cli.js test --config frontend/playwright.config.ts frontend/tests/runtime-repair.spec.ts --grep 'accessibility controls' --output work/resume-language-accessibility-final --workers=1 *> outputs/resume-language-accessibility-final.log
```

Additional browser invocations used the same executable/config/`--workers=1`: full suite output/log stems `resume-language-browser`, `resume-language-browser-final`, `resume-language-current-final`, `resume-language-accepted-browser`; interface-only stems `resume-language-focused` (log `resume-language-focused-browser.log`), `resume-language-focused-current`, `resume-language-focused-corrected`; kiosk-only stem `resume-language-kiosk-current`; combined interface-language/kiosk/reader-quiz stem `resume-language-regression-fixed`. Output directories are `work/<stem>` and logs `outputs/<stem>.log` except the noted focused log. Live audit earlier commands used output logs `resume-language-live-browser.log` and `resume-language-live-browser-retry.log`. Intermediate lint/typecheck repetitions used stems `resume-language-*-final`, `resume-language-*-after-fix` and `resume-language-accepted-*`; their outputs remain preserved.

The existing denial script was executed without editing it:

```powershell
@'
from pathlib import Path
source=Path('scripts/verify_release_private_paths.py').read_text('utf-8').replace("outputs/dataset-release-private-paths.json", "outputs/resume-language-private-paths.json")
exec(compile(source,'scripts/verify_release_private_paths.py','exec'))
'@ | python -X utf8 - *> outputs/resume-language-private-paths.log
```

Before/after JSON snapshots were loaded with Python and asserted equal. Status is append-only; original prefix saved at `work/resume-language-status-before.md` and checked after append.

### Unverified / incomplete

Six browser lifecycle tests still require an isolated authenticated fixture server and were skipped: admin upload/publication, photograph withdrawal, quiz/certificate/leaderboard, recording transcript lifecycle, kiosk end-to-end workflow, processing/review. Their backend equivalents run in isolated schemas; this does not make the skipped browser tests passed. Live production staff authentication/workflows were not exercised. Real staff UI localization beyond the anonymous page is synthetic-response browser coverage.

Additional language pairs, reverse Hindi→English live inference, account configuration discovery, Bhashini TTS, live generation fallbacks, expert linguistic/historical translation accuracy, screen-reader/audible voice/touch-hardware acceptance, load/quota behavior, backup restore and full production deployment remain unverified. Local speech tests simulate the browser API; successful fullscreen is browser evidence only. No broader-language or TTS support is claimed. Some dynamic/API-returned status fragments remain English; the interface explicitly reports partial fallback. No new RAG-generation claim is made.

## Multilingual continuation - 2026-10-03 (Asia/Kolkata)

### Inspection and implementation checkpoint

Read existing project instructions, documentation, latest status, selector/provider/cache
code, tests, probe and saved logs. There is no Git repository. Hash comparison found no
changed/added application or test files against `work/multilingual-baseline` before edits.
The earlier 36-file localization change set and validation remain historical, not new results.
The baseline contains the unchanged starting status and source/tests; an additional copy
of status and the original probe is at `work/multilingual-continuation-20261003`.

The previous probe ran and saved all 34 candidates in `outputs/multilingual-probes.log`.
Its changed-text `verified` flags overclaimed support. Preserved that original evidence;
changed the probe to require explicit `--codes`, use sequential calls and distinguish
response success from quality. Full evidence/acceptance limits: `MULTILINGUAL_VALIDATION.md`.

Fresh live checks of **bn, gu, hi, kn, ml, mr, ne, or, pa, ta, te** against
**bhashini/iiith/nmt-all** returned both authored sentences, with no provider errors.
Exact outputs are in `outputs/multilingual-20261003-live.log`; no archival/private text
was used. Codex separately assessed the 22 returned sentences for intended language and
meaning. This is limited model review, not independent native-speaker or full-catalog
quality certification. The probe reports quality as unverified rather than inventing a score.
The remaining 23 candidates are unavailable; English is the original interface.

The backend-controlled reviewed list populates native/English selector labels. No live
health claim or account-level language discovery is made by the capability endpoint.
Configuration mismatch disables translated options; changed discovered service IDs are
rejected before interface inference. Account discovery still requires the missing user
and pipeline IDs. Archive translation, ASR and TTS remain separate and unchanged.
Added persisted validated interface selection, per-target browser/backend cache separation,
stale-request protection, malformed capability/translation/cache fallback and focused tests.

Docker initially failed on the sandbox named pipe; approved elevated access succeeded.
All six existing services were running (four healthy, two without Compose healthchecks).
Read-only before snapshot: `outputs/multilingual-20261003-preservation-before.json`.
Only backend/frontend were restarted to load bind-mounted source; no rebuild, migrations,
publication actions, dataset ingestion, volume deletion or database reset was requested.
Photograph rights restriction remains unchanged. Validation is in progress below.
