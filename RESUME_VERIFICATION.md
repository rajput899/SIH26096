# Resume reconciliation — 2026-09-30

## Exact starting state
No project or parent Git metadata. Preserve in-place edits; no commit/diff recovery claim. Read current docs, source, migrations, tests and runtime rather than relying on old handoffs.
Earlier master-validation.log completed: 58 passed / 1 skipped backend, 11 passed browser, lint/typecheck/build passed. Later inline source panel edits were not in that build.
Intervening corpus implementation already exists: migrations 006–008, corpus.py, CorpusStatus, reporting/provider scripts, local imports and model installations. Existing corpus-backend-tests.log reports 64 passed / 5 failed; it is historical. Current runtime before edits: 31 archive records (30 uploaded/staff, Letters verified/public but unpublished), 31 corpus file rows, 27,693 page checkpoints (24,411 extracted, 3,282 OCR pending), 0 OCR-completed corpus pages, 0 passages, 0 embeddings, no Qdrant collections. All eight actual media files already imported with hashes, durations/codecs/resolutions; never re-imported here. The 13,824-page compilation already has checkpoints; preserved without further processing.

## Gemini diagnosis
Official Google deprecation table https://ai.google.dev/gemini-api/docs/deprecations lists gemini-2.0-flash shutdown June 1, 2026. Its prior generation 404 is consistent with retirement; metadata access is not generation success. Current SDK google-genai 2.25.0 uses the Google generativelanguage endpoint and structured JSON schema through the SDK. Official candidate docs: https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite ; structured output docs: https://ai.google.dev/gemini-api/docs/structured-output .
One live candidate request through GeminiGeneration succeeded with validated Answer structure and no archival/personal data. Changed only GEMINI_MODEL in existing .env to gemini-3.1-flash-lite. Keys never output; chat change does not alter embeddings. Existing saved synthetic cited Gemini test also shows success, but that is not real archival acceptance. No quota/billing error observed; billing/free-tier entitlement is not established by success.
Ollama already configured qwen2.5:1.5b and embeddinggemma:latest (768 dimensions reported by existing probe); do not redownload or re-embed.

## Current changes
- Additive migration 009_private_playback.sql: item-scoped, expiring, hashed staff playback grants. Explicit staff authentication issues grants; HttpOnly SameSite cookie used only by private GET playback; all mutations still use Authorization. Revoke on staff component close, active-user and expiry checks each request; protected byte ranges enable large-video streaming without whole-file browser blobs. Original hashes still checked.
- Corpus CLI now bounded to 100 checkpoint pages by default (maximum 1000) and 100 OCR pages maximum, optional exact --file selector; PDFs over 5000 pages held for identity review. Existing compilation checkpoints preserved. Original upload limits unchanged (10 MiB/50 pages).
- Restore Experience tabs alongside existing collection explorer; reviewed Timeline/Stories/Quizzes and evidence-only Knowledge Map. No historical content invented or published.
- Staff record pagination, source/rights review form, imported/extracted/review state descriptions and recording technical metadata.
- AI volume/page controls use existing authorized backend filters. Added filter and private-playback regression tests.
- Baseline fixtures now disable live model inference unless RUN_AI_ACCEPTANCE=1. No cloud calls in baseline fixtures.

## Validation so far
Focused current-image check: 45 passed, 1 failed, 1 skipped (43.41s). Mock timeout expectation inherited runtime timeout; source fixture fixes already existed but image lagged. Rebuild completed.
Full current backend suite: **71 passed, 1 skipped**, 102.11s. Harness then failed Ruff on an earlier copied unsorted import; fixed without changing behavior. No test process was actually interrupted (it had completed before the process check).
Continuation command: `./scripts/check_phase3.ps1 -SkipBackendTests` runs Ruff/frontend/build/browser validation without repeating completed backend tests. Log outputs/resume-ui-validation.log; pending.

## Outstanding at checkpoint
Actual-media private streaming browser check, dedicated live embedding/Qdrant and Ollama test, final new browser assertions and foundation checks, production checksum audit, documentation finalization. No real email; physical touchscreen, audio listening and screen-reader tests still require a person. No source verification/publication authorized for the dataset or Letters. No actual archival RAG acceptance possible with zero eligible published source text.
