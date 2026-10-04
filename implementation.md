# SIH26096 — Phased Implementation

## Working agreement

Follow requirements.md for scope, architecture.md for boundaries, database.md for entities, deployment.md for local operation and agent.md for development rules. Phases below commit only to categories A/B. Category C remains optional and outside completion criteria.

## Phase 0 foundation — authorized scope update (2026-09-24)

The owner's follow-up moves infrastructure scaffolding from Phase 1 into Phase 0. Implement only the Next.js/React/TypeScript/Tailwind shell, FastAPI backend, PostgreSQL, Qdrant, Compose, environment configuration, an Ollama-first provider interface, health checks and minimum frontend/backend connection. Implement → run → test → fix for each layer.

Foundation exit: start all five services; verify the browser, backend health, authenticated PostgreSQL query, Qdrant API and Ollama configuration/connectivity; run Pytest, Playwright, lint, type checks and a frontend build. Record actual evidence and blockers in status.md. No model download or inference is required for this exit.

Do not implement source ingestion, archive schema, OCR, RAG, assistant, timeline, crawling, voice or translation. Worker jobs and staff authentication also remain Phase 1 work. The original source/model feasibility tasks below remain pending and are not implied complete by infrastructure readiness.

## Phase 0 — Verify inputs and implementation feasibility

- Inspect all three acquisition targets SRC-01–03; record verified locators, permissions, supported acquisition methods and blockers. Do not invent APIs or download unpermitted material.
- Select the smallest real, permitted item suitable for the first slice, preferably a scan that exercises OCR. Confirm its provenance and original-source access. If no lawful sample is available, mark acquisition blocked and keep infrastructure tests explicitly synthetic.
- Confirm local hardware, Ollama generation/embedding models, RapidOCR script suitability, language pair, narration voice/service and BHASHINI access where appropriate. Choose versions after compatibility checks.
- Define a minimal staff review/access policy and document source limitations. No assumed historical facts or language support.

Exit: a documented acquisition path and a feasible local processing/model plan; unavailable targets remain visible as blockers. No claim of full source coverage from a single sample.

## Phase 1 - Archive Foundation (owner scope override, 2026-09-24)

Phase 0 is complete, runtime-verified by the owner. Do not repeat setup or feasibility work as a prerequisite to this authorized implementation.

Implement only admin upload -> immutable original -> PostgreSQL metadata -> lifecycle -> ARCHIVE listing. Add minimum staff credentials/roles, provenance and rights, separate verification/publication, original download with access/integrity checks, real persistence tests and a persistent Compose archive volume.

Exit: test the actual upload, persisted metadata and bytes, staff/public visibility and lifecycle separation. Synthetic fixtures must be isolated from archival holdings. A legitimate source holding remains dependent on owner-provided permission and material.

OCR/extraction, workers, embeddings, Qdrant indexing, search/RAG, Ollama answering, citations, translation, voice, crawler, timeline, graph and advanced EXPERIENCE remain deferred. The previously planned broad vertical slice is not authorized in this phase. Stop after Archive Foundation.

## Phase 2 - OCR / Document Processing (owner scope override, 2026-09-27)

Phase 1 is COMPLETE and is not to be recreated. Implement only:

1. Preserve the existing original and verify its SHA-256 before/after processing.
2. Queue durable PostgreSQL extraction jobs, claim with a fenced lease, track failures and allow bounded retries.
3. Extract embedded PDF text or recognize scanned PDF/image pages with RapidOCR through ONNX Runtime CPU. Use pypdfium2 for PDF parsing/rendering; do not introduce another service or paid API.
4. Store page-located extracted text in PostgreSQL revision snapshots, separately from original files.
5. Allow curator review/corrections as new snapshots and explicit verification. Keep document publication separate and block publication of unverified processing output.
6. Test actual OCR, storage, locators, version history, access, retry and review behavior. Keep test content isolated.

Use one permitted real document only if suitable provenance/reuse can be established. Otherwise use explicitly synthetic local fixtures and disclose that real archival OCR acceptance remains unproven. No scraping/bulk import. No embeddings, Qdrant indexing, search, RAG, answering, chat, crawler, translation, speech, timeline, graph or experience work.

Exit requires actual processing-to-verified-text evidence, not only code/UI. Environment-blocked integration checks remain BLOCKED. Stop after Phase 2.

The older archive-breadth/audio-video/preservation phase is deferred and is not authorized now. Later phase descriptions below are backlog, not authority to begin them.

## Deferred backlog — Shared-archive experience (not current Phase 3)

- Implement reviewed knowledge entities/relations and evidence-linked interactive mapping (PS-02).
- Implement dated, source-linked timeline navigation with uncertain dates shown honestly (PS-08).
- Implement curator-reviewed memorial storytelling with supporting evidence for factual claims (PS-09).
- Add touch-friendly kiosk/smart-display mode, visitor session reset/inactivity clearing, and working compilation interactions (PS-14/15).

Exit: each interaction opens the same archive records and supporting sources; unverified facts are not published. Validate on available touch hardware or record browser-only verification as a remaining hardware limitation.

## Phase 4 — End-to-end acceptance and handoff

- Run Pytest for processing, revision/access checks, retrieval/citation validation, job retries and service-failure handling. Use isolated labeled fixtures for automated tests and legitimate material for archival acceptance.
- Run Playwright for staff ingestion/review, visitor search/study/listen/compile, original-source navigation and experience/kiosk workflows.
- Test actual Ollama inference, OCR, translation, narration, media processing and backup restoration. Mock-only tests do not establish integration completion.
- Reproduce local setup from deployment.md. Review every PS/SRC row, limitations, rights, supported languages and capacity; update status.md with evidence.

Exit: all claimed functionality passes real acceptance checks; incomplete requirements and blocked targets remain clearly recorded. No optional enhancement is needed for baseline acceptance.

## Requirement traceability

| Requirements | Primary phase(s) |
|---|---|
| PS-01, PS-03, PS-05, PS-06, PS-10 | 1, validated in 4 |
| PS-04, PS-12 | 1–2, validated in 4 |
| PS-07, PS-11, PS-13 | 2, validated in 4 |
| PS-02, PS-08, PS-09, PS-14 | 3, validated in 4 |
| PS-15 | 1 and 3, validated in 4 |
| SRC-01, SRC-02, SRC-03 | 0 assessment, 1 first sample, 2 acquisition coverage, 4 disclosure |
| SUP-01–07 | 1–3 as needed, validated in 4 |

## Phase 3 — Kiosk UI + AI Research Assistant (owner override, 2026-09-28)

This current scope supersedes the older phase numbering above. Phases 0–2 are accepted; preserve their workflows.

1. Accessible responsive home/navigation, AI/ARCHIVE/EXPERIENCE, staff separation, fullscreen and session reset.
2. Durable verified-page passage indexing, PostgreSQL FTS + optional local Ollama embeddings/Qdrant hybrid retrieval.
3. Configurable local model generation, exact source-quote validation, current-publication rechecks, persisted artifact evidence and invalidation.
4. Visitor public catalogue/detail/original/verified reader; real source metadata and locators, no live fixture content.
5. Browser local voice read-aloud controls, text size/contrast/reduced motion, semantic controls and keyboard flow. No voice input or content translation.
6. Regression and acceptance tests, including no-source/model-outage cases and actual model/vector checks when configured. EXPERIENCE is introduction/navigation only.

Exit: run `scripts/check_phase3.ps1` and its `-RunAI` acceptance path; verify a legitimate permitted published source, actual audio output, screen-reader navigation and target touch/fullscreen behavior. Pending or environment-blocked checks must remain pending in status.md. Do not advance beyond this phase.

## Heritage master-request implementation — 2026-09-29
Code paths are implemented for secure thumbnails; staff review stages and filters; explicit Gemini generation; WAV/MP3/MP4 validation and playback; versioned curator transcripts; source-backed timeline/story/quiz publication; server-scored attempts; printable completion certificates; opt-in pseudonymous leaderboard and SMTP certificate delivery. No approved historical content has been added or published. These additions are not runtime-accepted until the owner runs the isolated PostgreSQL/browser suite.
New visitor routes: /speeches, expanded /experience, /quiz/[id], /certificate/[id], /leaderboard. Existing /, /archive, /ai, /staff and /system remain. Staff learning UI begins with one complete question per quiz; API accepts up to ten. Advanced graphs, automated transcription, translation, difficulty/timed challenges and visitor identity systems remain out of scope.
Corrections: document OCR keeps existing immutable page snapshots; recording corrections create new cue snapshots; learning corrections withdraw and replace the approved entry. Historical source truth still needs curator judgment; exact quote validation does not prove every narrative claim semantically follows from a source.

## Second-session stabilization
The recording research gap is corrected through migration 005 and the existing immutable text/passage pipeline; no additional database or service. Transcript verification produces timestamped source segments, corrections revoke eligibility, and citation/reader responses retain time locators. Original recording snapshots and bytes remain separate. Truncated WAV files and mismatched MP3/MP4 containers are rejected. See status.md for actual acceptance evidence.


## 2026-09-30 resumed reconciliation
See RESUME_VERIFICATION.md for authoritative current runtime state and test results. Intervening corpus migrations 006–008 and restricted imports are preserved. Additive migration 009 provides scoped private streaming. Public upload limits and publication safeguards remain unchanged. Gemini candidate generation succeeded and chat model setting updated; embeddings unchanged. Experience tabs restored alongside collection browsing.


## Collection entry and publication-safe browsing — 2026-10-01
Homepage collection cards use the existing `/archive` route with `collection=manuscripts|photographs|videos|audio`. They reuse the existing public catalogue, protected thumbnails and individual `/archive/[id]` original/text/media readers. Manuscripts use curator-assigned `material_type=manuscript`; letters-folder membership is not classification. Audio & Speeches queries the existing audio and speech material types.
Photographs and Videos have independently paginated, searchable “From the supplied dataset” and “Other archive content” sections. The additive catalogue `origin=dataset|other` filter partitions records by original SHA-256 membership in `corpus_file`, retaining public/published checks. Filenames, descriptions and editable source URLs do not establish dataset membership. Unregistered candidates remain private and do not become placeholder records. No schema, ingestion, publication, source or rights changes were made.
Service Status replaces old Phase 0 wording in the frontend and the Ollama probe detail; every existing health probe is retained. Reachability is explicitly distinct from model/feature acceptance.
Current-source production preview: http://127.0.0.1:3002 (temporary `sih26096-collections-web` and `sih26096-collections-api`). Original services at ports 3000/8000 were not rebuilt/restarted. `scripts/check_collections.ps1` runs existing workflows with current source, a preserved production build, isolated schemas/storage and no live cloud/email calls. See status.md and outputs/COLLECTIONS_AUDIT.md for actual results and publication gaps.


## Targeted Archive navigation correction — 2026-10-01
Supersedes the preceding collection-card layout: the homepage retains exactly its four established cards. Three compact links (Manuscripts & Letters, Photographs, Videos) sit inside The Archive card, and shared collection navigation appears on the existing Archive route and its collection views. The separate homepage collection section and Audio & Speeches collection are removed. Legacy `/archive?collection=audio` redirects relatively to `/speeches`; its published audio/MP3/recording experience is unchanged.
All internal links use relative paths. Source inspection found no hardcoded port-3000 internal href; the previous Back handler could leave the preview through browser history. It now returns through history only when the browser exposes a same-origin previous entry; otherwise it uses the Archive parent or Home. Browsers without the Navigation API use that safe parent/Home fallback. External source links and deployment settings are unchanged.
The actual folders remain provenance clues: Dataset/Ambedkar_letters (25 JPEG candidates), Dataset/Ambedkar_photos (36 PNG candidates), Dataset/Br. Ambedkar/videos (six MP4s) and Dataset/Br. Ambedkar/voice (one MP4, one MP3). Existing stored checksums/corpus relationships determine supplied membership; curator metadata and publication authorization determine visible material. No folder-based classification, ingestion, publication, OCR, backend filtering or access changes were made. Details and current validation are in status.md.


## 2026-10-02 continuation: release and translation

Migration 010 and the organizer-dataset release are complete: 92 files registered, 91 originals public, one explicit compilation hold retained. Supplied collection grouping is distinct from verified historical identity; 25 Manuscripts images, 36 Photographs images and 7 Videos are public. Existing unknown metadata, originals and OCR are preserved. Dataset display authorization does not verify text: only the two existing PIB sources remain RAG eligible. No release or ingestion rerun occurred in this continuation.

Backend-only Bhashini translation accepts current public verified sections with revision/sequence checks, marks output machine-generated and unreviewed, and never indexes it. English-to-Hindi was verified live using configured inference credentials. Optional discovery and explicit Gemini/Ollama fallbacks have mocked coverage; reverse translation and fallback live behavior remain unverified. Details, official protocol references, commands and test distinctions: DATASET_RELEASE_VALIDATION.md, BHASHINI_VALIDATION.md and the 2026-10-02 status.md entry.
