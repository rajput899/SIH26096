# Master continuation — 2026-09-30

## Preservation and baseline
Existing project continued in place; no Git metadata available. No original or production record modified. Letters remains unpublished (last read-only check); rights `Allowed` is insufficient. Dataset provenance and redistribution rights are **Not verified**, confirmed by owner; only local inventory/extraction/sample review authorized pending curator rights confirmation.

Earlier validation: `scripts/check_phase3.ps1` completed with 51 backend passed / 1 optional live-model test skipped, Ruff/lint/typecheck/build passed, 10 browser tests passed. Exact log: `outputs/session2-final-verification.log`. These counts precede the current AI/reader changes.

## Current inspection
Six Compose services running. PostgreSQL has one Letters record, no published records or research passages. Gemini configured (secret presence checked, value never reported), model gemini-2.0-flash; no Ollama generation/embedding models installed/configured. Qdrant service running does not prove semantic retrieval. Empty Archive is expected.
AI previously routed greetings through retrieval and used one insufficient-evidence response for distinct cases. No explicit source scope. Current changes add local greeting/scope handling, source scope, bounded excerpt summaries, reason codes, safer provider diagnostics and clearer frontend states. Verification ongoing.

## Commands and actual results
- `backend/.venv/Scripts/python.exe -m pytest -p no:cacheprovider -p phase2_pytest_paths -q` from backend with `PYTHONPATH=../work`: **40 passed, 18 skipped**, 64.31 seconds (local, no integration). Provider tests mocked.
- `backend/.venv/Scripts/ruff.exe check backend`: passed.
- `npm run typecheck` from frontend: passed after reader/media edits.
- Foundation Playwright on localhost with Chrome: **3 passed**, 4.8 seconds. Earlier 127.0.0.1 run failed 2/3; localhost retry passed. Sandbox invocation initially blocked subprocess (EPERM); elevated run passed.
- One live Gemini request with no archival/personal data: **failed**, sanitized generic unavailable response. Not grounded acceptance. No real email sent.
- `backend/.venv/Scripts/python.exe scripts/inventory_dataset.py Dataset outputs/dataset-inventory.json`: 31 files inventoried, SHA-256 for each, no exact duplicates, 171.81s. Initial PDF context-manager implementation failed; fixed and all 22 PDFs successfully inspected. Local media probe blocked (no host ffprobe), Docker probe pending.

## Dataset sample
Read-only Volume_01.pdf: 516 pages, 469 with >30 embedded-text characters. Sample PDF pages 1/5/20/100 rendered; text chars 0/1084/2137/1960. Extraction/render 0.62s, original hash unchanged, no database writes. `outputs/dataset-sample/review.json` records checksum and sample. Page 5 visually states Volume 1, first edition 14 April 1979, second reprint August 2019, Dr. Ambedkar Foundation, ISBN 978-93-5109-172-1. These are source-internal statements, not independent authentication or a redistribution license. OCR sample pending.
19 volume files map by filename to 1–17, with parts of 14 and 17. Volume 16 largely scanned. Two biographical books scanned. Collected Works filename says vol 1 but contains 13,824 pages; identity/overlap needs review. No silently skipped files. Full inventory JSON contains every path/size/checksum/page count/sparse pages.

## Blockers and pending work
Production ingestion deferred: rights/provenance not confirmed, existing 10 MiB upload and 50-page processing limits incompatible with full dataset. Do not raise limits and enqueue thousands of OCR pages without bounded durable processing validation. No actual eligible archival source exists for grounded AI acceptance. Semantic/live Ollama blocked by missing models. Reader source research, media transcript search implemented but browser verification pending. Staff wizard, knowledge map and broader validation still pending.


## Stage update — source experience and validation
Files changed in this master continuation so far: `backend/app/research.py`, `backend/app/llm.py`, `backend/tests/test_research.py`, `backend/tests/test_providers.py`; `frontend/src/app/ai/page.tsx`, `frontend/src/app/archive/[id]/page.tsx`, `frontend/src/app/staff/page.tsx`, `frontend/src/app/experience/page.tsx`, `frontend/src/app/globals.css`, `frontend/src/components/RecordingPlayer.tsx`; new `SourceResearch.tsx`, `UploadSteps.tsx`, `KnowledgeMap.tsx`; `frontend/tests/archive.spec.ts`, `processing.spec.ts`, `kiosk.spec.ts`, `heritage.spec.ts`; `frontend/eslint.config.mjs`, `frontend/.dockerignore`; new `scripts/inventory_dataset.py`, `scripts/probe_dataset_sample.py`, `DATASET_REVIEW.md`, this handoff and outputs. Earlier-session changes are listed in SESSION2_VERIFICATION.md.

Implemented source-scoped AI requests, bounded summaries, explicit diagnostics and local greeting/scope handling. Reader now compares immutable original with one verified page, supports page selection and PDF/image zoom, preserves citation links, and has an inline source-scoped question/summary panel. Recordings retain protected native playback and add verified transcript search; main research links carry explicit source scope. Upload now guides file → basic details → source/rights while preserving backend attestation, RBAC, defaults, limits and separate publication. Knowledge map connects published curated topics/activities with eligible evidence using existing endpoints; no inferred historical entity relationships or new graph database.

Regression discovered in new SQL string concatenation: missing leading space caused six integration failures (51 passed, 6 failed, 1 skipped). Fixed; focused research/recording run now **20 passed, 1 skipped**, 32.54s. An intermediate retry did not apply the fix due to Windows text encoding; the subsequent UTF-8-safe patch and rerun passed. Full suite underway; never treat intermediate failures as passing.

Gemini: one generation connectivity request failed generically; model metadata request succeeded; one bounded diagnostic generation returned **HTTP 404 ClientError**. Configured model metadata access does not prove generation availability. Backend now distinguishes 400/401/403/404/429/503 without exposing upstream error content. No model setting changed, no archive/personal content sent, no live successful generation. No further retries needed pending model configuration.

Read-only runtime checks after rebuild: Hello → greeting, joke request → scope, archive question → no_eligible_content, all generation_attempted=false. Production records=1, staff accounts=1, published=0. Letters remains verified/public but unpublished; original checksum matches. Public detail/original/thumbnail/playback each 404; unauthenticated staff original 401.

All 8 media inspected with FFprobe, zero probe failures. Cover OCR succeeded (538 chars, confidence 0.95442, 3.95s), with an observed spelling error despite high confidence. All 31 original dataset checksums rechecked unchanged. See DATASET_REVIEW.md for every file and source/rights caveats.
