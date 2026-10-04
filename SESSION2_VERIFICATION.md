# Second-session verification — 2026-09-29

This continues the existing application. No Git metadata exists in the supplied project folder, so Git status/diff/history were unavailable. Edited-file baselines and earlier browser failure traces are retained under `work/session2-baseline`. The final full run is recorded in `outputs/session2-final-verification.log`.

## Changes
- Migration 005 connects explicitly verified recording cues to the existing immutable text/passage pipeline, with start/end seconds and recording-revision provenance. Correction clears eligibility and invalidates existing answers. Document text correction cannot bypass transcript review.
- Recording validation rejects truncated WAV data and mismatched declared MP3/MP4 containers. Self-created silent/black-frame FFmpeg fixtures test the real parser; they are not archival audio/video.
- AI citations and archive readers display recording time ranges. Garbled AI punctuation is corrected.
- Narrow/short-screen accessibility footer no longer overlays reading content or intercepts End session. Experience audio-guide wording matches the implemented interface.
- Browser tests target the current staff heading, correct form/record/status/alert regions and accessible text-size combobox. Publication assertions wait for exact lifecycle state rather than matching “not published”.
- Regression checks cover timestamped transcript research and invalidation, actual playback time advancement, certificate delivery retries and the hourly cap with mocked SMTP.

## Exact commands
From the project root:

```powershell
Set-Location 'C:\Users\Hackathon\Documents\Codex\2026-09-24\we-are-starting-sih26096-completely-from'
.\backend\.venv\Scripts\python.exe -m ruff check --no-cache backend/app backend/tests
.\scripts\check_phase3.ps1
# Final run was captured with:
.\scripts\check_phase3.ps1 *> outputs/session2-final-verification.log
```

Local backend baseline (existing local temporary-directory fixture workaround):

```powershell
Push-Location backend
$env:PYTHONPATH='../work'
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -p phase2_pytest_paths -q
Pop-Location
```

Local frontend checks: `npm run lint`, `npm run typecheck`, `npm run build` from `frontend`. Lint/typecheck passed; local build compiled then failed `spawn EPERM` during TypeScript worker startup. Docker builds passed independently.

The harness runs:

```powershell
docker compose up -d --build --wait --wait-timeout 240 backend frontend worker
docker compose exec -e RUN_INTEGRATION=1 -e RUN_AI_ACCEPTANCE=0 backend python -m pytest -p no:cacheprovider -q
docker compose exec backend python -m ruff check --no-cache app tests
docker compose exec frontend npm run lint
docker compose exec frontend npm run typecheck
docker compose run --rm --no-deps frontend npm run build
# Then, with isolated fixture API/storage/schema and temporary browser environment:
# node node_modules/@playwright/test/cli.js test tests/archive.spec.ts tests/processing.spec.ts tests/kiosk.spec.ts tests/heritage.spec.ts --workers=1
```

## Evidence boundaries
Initial local suite: 35 passed, 15 skipped, one existing Starlette deprecation warning, 37.51s. First Docker backend suite: 49 passed, one real-model test skipped, 63.51s. First browser run: five passed, five failed. Second backend run with migration 005: 49 passed, one skipped, 84.82s. Second browser run: eight passed, two failed; remaining publication-test race and footer overlay were corrected. Final results will be appended below.

Generation SDK/Ollama contracts and SMTP are mocked. PostgreSQL, migrations, original files, extraction/OCR, HTTP endpoints, browser navigation, native WAV playback and fullscreen use actual local runtimes. The test recording is silence; browser playback does not establish audible speech, historical authenticity, synchronized captions or codec support on all devices.

## Still outstanding and Windows manual procedure
1. Open `http://localhost:3000` and hard-refresh. Traverse Home, Archive, AI, Experience and Staff using keyboard and the actual touchscreen. Test portrait/landscape, 140% text, high contrast and End session. Check screen-reader landmarks, names, focus, errors and announcements with the intended screen reader. Browser automation cannot certify physical touch or screen-reader use.
2. Enter/exit browser fullscreen. Escape must return to the browser. This does not lock Windows into kiosk mode.
3. With an installed local system voice, use Audio guide and read-aloud; listen and verify Pause/Resume/Stop. Test permitted MP3 and H.264/AAC MP4 with native controls on the intended browser. No synchronized captions or automatic ASR is implemented.
4. Keep the production record titled Letters (description “Dr Babasaheb Ambedkar’s letters”) unpublished. Verify its rights independently before any publication. Use a different clearly rights-cleared source for historical research acceptance.
5. No local models are installed/configured. To perform real Ollama/Qdrant acceptance, deliberately install/select suitable local generation and embedding models, retain existing credentials, set their exact names in `.env`, then run `.\scripts\check_phase3.ps1 -RunAI`. Model downloads were not performed in this session. Review answer quotations, page/time locations and factual support against a permitted original; also test an unsupported question.
6. Gemini remains unconfigured and was never called. If deliberately chosen, privately set `AI_PROVIDER=gemini`, `GEMINI_API_KEY`, `GEMINI_MODEL`, recreate the backend and run one explicit acceptance question as documented in HERITAGE_VERIFICATION.md. It may incur usage. Do not expose credentials. Restore `AI_PROVIDER=ollama` for local generation.
7. SMTP remains unconfigured; no real email was sent. Only after explicit authorization, configure the backend SMTP settings and a usable certificate public URL, create a completed activity/certificate, then use the UI with the authorized test address and explicit consent. Confirm server acceptance separately from actual inbox delivery. Download remains available without email.
8. Curate permitted timeline/story/quiz content and inspect its source links and withdrawal behavior. Check downloaded certificate HTML and Windows Print-to-PDF layout. No authentic historical learning corpus was supplied or manufactured. Advanced graph, translation, ASR, visitor compilations and tested backup restoration remain deferred; they are not completed by this validation pass.

## Preservation and deployment
Existing `.env` and credentials were not changed. No dependency was added in this session. Existing heritage dependencies (including FFmpeg and google-genai) were installed by rebuilding the preexisting Docker definition. Migrations 001–004 were not rewritten. Migration 005 is applied by the normal backend startup ledger; repeat migration application is exercised in isolated integration fixtures. Existing recording snapshots are not backfilled or republished automatically; a pre-005 transcript requires a new reviewed/verified revision to enter research.

No database reset, volume deletion, production upload/publication, or original replacement was performed. The production photograph was verified/public but unpublished and its checksum matched its original asset record. Direct public detail/original/thumbnail/playback and raw storage paths returned 404; unauthenticated staff-original access returned 401. Test records live only in disposable schemas/storage. Final preservation/cleanup checks follow below.
