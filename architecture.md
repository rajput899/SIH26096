# SIH26096 — Architecture

## Scope

Implements requirements.md sections A and B. Section C remains optional. The architecture is a lean modular monolith: one frontend, one backend codebase, one relational database, one vector database, and local model serving.

Phase 0 implements only the five-service local foundation: frontend, backend, PostgreSQL, Qdrant and Ollama. A same-origin Next.js health route calls FastAPI over the internal network; no browser-exposed database secrets or permissive CORS are needed. The LLM protocol initially exposes a connectivity probe only. Phase 1 adds archival storage, acquisition metadata/schema, staff access and a minimal ARCHIVE view. Phase 2 adds one worker from this backend codebase and document-processing/review modules; see status.md for runtime evidence. AI and experience modules remain planned.

## Views over the same archive

- **AI:** Research Assistant, semantic search, summaries, citations and multilingual/voice interaction.
- **ARCHIVE:** Documents, manuscripts, speeches, debates, photographs, audio/video, OCR, metadata, preservation and institutional management.
- **EXPERIENCE:** Timeline, memorial storytelling, knowledge mapping and interactive/kiosk access.

All views resolve the same item IDs through the backend; restricted records are never exposed through an alternate view.

## Implementation choices (not PS requirements)

| Concern | Choice and boundary |
|---|---|
| Frontend | Next.js, React, TypeScript, Tailwind CSS; shared archive UI with three navigation views. |
| Backend | FastAPI and Python; modules for acquisition, processing, curation, discovery, research and experience. |
| Source of truth | PostgreSQL for metadata, extracted text, review state, access policy, compilations and evidence references. PostgreSQL full-text search complements semantic retrieval. |
| Semantic index | Qdrant, one initial collection for passage embeddings; derived and rebuildable from approved PostgreSQL text. |
| LLM and embeddings | Ollama as primary local inference server; select and validate local generation and embedding models before indexing. Store model/version and embedding dimensions. No paid external LLM API dependency. |
| OCR | RapidOCR behind an extraction interface; assess supported scripts and manuscript quality on real permitted samples. Manual correction is part of review; unsupported handwriting must remain flagged. |
| Speech recognition | faster-whisper for audio transcription and visitor voice input; it does not generate narration. |
| Language services | Translation and text-to-speech interfaces, using BHASHINI where suitable and available. Verify access, terms and language support first. A local adapter may be selected if needed; no TTS engine or BHASHINI API availability is assumed. |
| Media | FFmpeg for media probing, compatible playback derivatives and audio extraction. |
| Original/derived files | Backend-managed filesystem storage on a persistent volume; immutable originals, separate derivatives. No new object-storage platform initially. |
| Deployment and tests | Docker Compose; Pytest backend/integration tests and Playwright visitor/staff flows. |

## Processing and retrieval

1. Register a verified source locator and rights/access decision; accept a permitted upload or verified acquisition method. No speculative crawler or invented API.
2. Store the original with checksum and provenance, then create a durable processing job.
3. Extract existing text or run RapidOCR on scanned pages; process media with FFmpeg and faster-whisper as appropriate. Keep page or timestamp locators.
4. Capture metadata/tags. A curator reviews text, metadata, rights and evidence before publication.
5. Chunk the approved text and embed locally through Ollama. Store passage payload IDs in Qdrant and record the indexed revision.
6. Search published content using lexical/semantic retrieval, then recheck publication, revision and access in PostgreSQL before returning any passages or sending context to Ollama.
7. Generate answers/summaries with evidence IDs. The backend validates citation references against retrieved passages. Visitors follow citations to the passage, preserved original and verified external source locator.
8. Translate or narrate approved text through language adapters; label outputs and retain source links. Keep canonical text and original evidence visible.

Audio/video without reviewed text can be browsed and played after verification; passage retrieval/RAG requires reviewed transcripts. Photographs can use reviewed descriptive text without pretending that an image has an authoritative transcript.

## Background work without distributed infrastructure

Use a PostgreSQL job table and a single worker process from the same backend codebase, launched separately in Compose. Claim jobs transactionally, record failures, and retry idempotently. No Redis, message broker, independent worker service codebase, or microservices are required. Long-running OCR, media processing and model calls do not block HTTP requests.

## Evidence and experience

Knowledge entities and relationships, timeline events and ordered story sections use curator-reviewed evidence links to archival items/passages. Ollama may suggest mappings and narrative drafts, but suggestions are not published as fact. A minimal interactive graph, timeline and source-linked story fulfill the core experience without advanced analytics.

Compilations contain ordered references to published items/passages. Anonymous sessions suffice initially; kiosk sessions are isolated and cleared on explicit reset or inactivity. Kiosk mode uses the same frontend with touch-friendly controls and no staff interface.

## Integrity and security

Staff authentication and curator/admin permissions protect management routes. Validate uploads and paths, restrict formats/size, keep storage outside the public web root and authorize media reads. Log curation and access-policy changes. Treat source text as untrusted evidence, never as instructions to the assistant.

Originals are never overwritten by OCR, translation or transcoding. PostgreSQL and file backups must be restored and checksum-verified together. Qdrant is rebuildable. Edits/unpublication immediately prevent retrieval through backend revision/access checks, then enqueue removal or reindexing; cached summaries/translations/narration for the prior revision become stale.

## Open implementation decisions

Verify machine capacity, model licenses/resources, script quality, languages, BHASHINI availability, source permissions and kiosk device constraints in phase 0. Language service outages leave text/source access usable but PS-05/PS-06 incomplete until demonstrated. Local startup must not require external paid LLM services.

## Phase 2 processing boundary

One `worker` Compose process shares the backend image and PostgreSQL database. It mounts archive_data read-only. Each claimed job runs PDF/OCR in a bounded child process (default 180 seconds), with a 5-second heartbeat, 90-second expired-lease recovery and three-attempt limit. Claim tokens fence late results from crashed/reclaimed attempts. Queueing and review operations are transactional; extracted pages and successful job status commit together. No Redis, external queue, new model server or paid service is introduced.

Pinned RapidOCR 3.9.2 uses its bundled PP-OCRv6 small detection/recognition and mobile orientation models through ONNX Runtime 1.30.0 CPU. Explicit installed-file paths disable fallback model downloads in processing. pypdfium2 5.13.0 supplies PDF text extraction and rasterization. Automatic mode trusts nonempty embedded text enough to present it for review; scanned pages use OCR. Force-OCR mode handles suspect text layers. Neither mode automatically verifies text. Only clean printed English fixtures have current OCR evidence; other scripts, handwriting and damaged scans are unvalidated.

Text revisions are staff-only in this phase. A curator saves an append-only reviewed snapshot, then separately verifies it. Corrections reset the document to uploaded/unpublished and clear metadata verification; retained historical verified snapshots do not grant publication. No retrieval, answer generation or public full-text endpoint is introduced.

## Phase 3 implementation boundary (2026-09-28)

The owner's current scope authorizes the kiosk and research assistant and supersedes the earlier Phase 2-only restriction. Existing extraction, staff authentication, originals and curator review remain in place.

- Next.js provides visitor routes `/`, `/ai`, `/archive`, `/archive/[id]`, `/experience`; existing staff tools are retained at `/staff`, and the existing dependency dashboard at `/system`.
- The existing PostgreSQL worker also polls durable `search_index_state`. It derives page-bounded passages from CURRENT verified, public, published text. PostgreSQL `simple` FTS remains usable independently of vector/model availability.
- Ollama HTTP `/api/embed` supplies configurable multilingual embeddings; Qdrant holds disposable vectors with model-digest identity. No LlamaIndex/second orchestration framework is added. `/api/chat` uses the existing local-provider module with a structured answer schema.
- Hybrid retrieval merges lexical and semantic candidates, then checks all candidate IDs against PostgreSQL current publication/revision rules. Qdrant payloads are never permission authorities. Generation is bounded to two concurrent requests, six source passages, four prior questions and five response paragraphs.
- Each generated paragraph must cite a retrieved passage and an exact contiguous quote. Title, revision, page and original URL are resolved by the server. Publication is checked again under row locks before saving/returning. This validates attribution; it cannot mathematically prove that every model paraphrase is entailed, so summaries remain labelled and sources accessible.
- Revision/publication changes invalidate generated artifacts and enqueue index maintenance. Old vectors may temporarily remain physically present during an outage but cannot pass PostgreSQL authorization. A replacement collection is required for a changed embedding dimension; no destructive automatic collection recreation occurs.
- Browser speech uses installed local system voices; it is distinct from screen-reader semantics. No ASR, remote TTS, translation or voice-command service is introduced. English/Hindi main navigation is partial UI localization, not content translation.
- Model names stay empty until explicitly configured. There is no hidden model download, paid provider or external archive integration.

## Heritage extension decisions — 2026-09-29
Continue FastAPI + PostgreSQL + Next.js; no overlapping orchestration framework. The generation interface in `llm.py` selects Ollama or Google's official `google-genai` SDK explicitly. Gemini credentials exist only in backend settings; structured output passes the same exact-citation validation and database eligibility checks as Ollama. PostgreSQL full-text fallback and local embeddings are retained. Generation has bounded input, concurrency, timeout and a per-process request limit. Provider status discloses configuration, not live readiness.
Pillow creates bounded JPEG thumbnails in derivative storage with a parent-original reference and checksum provenance. Both public and staff thumbnail requests authorize against current database state and verify original integrity. Derivatives are never a public static directory; responses are no-store.
Recording uploads retain original bytes; stdlib wave validates PCM WAV and ffprobe validates MP3/H.264-AAC MP4. Native browser players receive authorized byte-range responses through the existing proxy. Curator transcript cues are versioned separately and are not automatically transcribed. Migration 005 connects explicitly verified cues to the existing immutable text/passage index with timestamp locators; publication remains separate and corrections revoke eligibility.
Curated learning bodies and answer keys live in PostgreSQL JSONB with relational source/revision references. Public question payloads exclude keys. Attempts, scoring, certificates and opt-in leaderboard entries are server validated. Source withdrawal/revision invalidates public access to dependent learning and certificates. Certificates are printable HTML with a verification ID, not cryptographically signed or accredited documents.
SMTP uses stdlib smtplib, mandatory STARTTLS, explicit consent, a private attempt token, per-certificate retry limits and a global hourly bound. Raw addresses are used transiently, never stored in the archive database; delivery stores a salted-by-certificate fingerprint, consent and status. Success means SMTP acceptance, not confirmed inbox delivery. A crash after SMTP acceptance but before database commit may permit a duplicate retry; this is not an exactly-once mail system.


## 2026-09-30 resumed reconciliation
See RESUME_VERIFICATION.md for authoritative current runtime state and test results. Intervening corpus migrations 006–008 and restricted imports are preserved. Additive migration 009 provides scoped private streaming. Public upload limits and publication safeguards remain unchanged. Gemini candidate generation succeeded and chat model setting updated; embeddings unchanged. Experience tabs restored alongside collection browsing.
