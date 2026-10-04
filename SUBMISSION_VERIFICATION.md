# SIH26096 submission verification — 30 September 2026

Work began at 07:13 UTC, with a two-hour limit ending at 09:13 UTC.
Continued the existing application in place. Other visible project chats were
idle, unloaded or stopped with a usage-limit error; this was the sole active chat.
There is no Git metadata. Pre-edit copies of the initial changed files are in
`work/deadline-baseline`.

## Preservation baseline

`outputs/deadline-preservation-before.json` records all 31 existing originals:
31/31 SHA-256 checks matched the database. The corpus has 27,693 checkpoints,
including 24,411 embedded-text pages, 2 OCR-completed pages and 3,280 OCR-pending
pages. Migrations 001–009 are applied. No corpus importer is active.

The 13,824-page compilation remains on identity-review hold. The existing
dataset's provenance and public-display rights remain uncleared. Letters remains
unpublished; “Allowed” is not permission evidence. The staff interface now warns
about placeholder rights and the backend rejects verification/publication with
“Allowed”, “Unknown” or “Not verified”. This does not establish rights for any
other record merely because it has a longer statement.

## Reviewed source selection

Two small, government-authored PIB text excerpts were checked against official
pages. Saved HTML captures, normalized source-page text, selected excerpts and
SHA-256 hashes are in `outputs/submission-sources`.

- President's Secretariat, 15 May 2017, *History of Parliamentary Democracy in
  India*, paragraph 42: https://www.pib.gov.in/PressReleasePage.aspx?PRID=1489909
- Ministry of Social Justice & Empowerment, 13 April 2024, *The journey of Baba
  Saheb Ambedkar – Life, History & Works*, opening biographical bullet:
  https://www.pib.gov.in/PressReleasePage.aspx?PRID=2017835
- PIB reuse policy:
  https://www.pib.gov.in/content/3604_2_CopyrightPolicy.aspx?lang=1&reg=3

The policy permits accurate, attributed reproduction without prior approval,
excluding third-party material. These selections contain government release
text only, with no photographs or third-party quotations. They are explicitly
described as modern government accounts and unpaginated excerpts, not original
Ambedkar manuscripts or speeches. No clearance is inferred for the old dataset.

`scripts/publish_submission_selection.py` uses authenticated staff upload,
extraction, reviewed revision, text verification, metadata verification and
separate publication APIs. It then uses the existing learning draft, verification
and publication APIs. It has no database writes or authentication overrides.
Execution requires the owner's existing local credential file, whose path has
been requested. Preparation is not publication; final receipts will determine
which records and activities actually became public.

## Focused fixes

- Staff upload consumes the response body. The browser regression now resolves
  the uploaded ID through the authenticated staff API, avoiding Chrome's
  evicted-inspector-cache error while still requiring HTTP 201 and the rendered
  saved record.
- Recording panel collapse revokes playback and removes the media URL;
  unmount/sign-out revocation is retained. The expiry regression now uses the
  renewed token, so it genuinely tests expiration rather than an already revoked
  grant.
- Provider timeout, provider errors, malformed JSON/citation response and model
  abstention remain distinguishable. No pretrained-knowledge or web fallback was
  added. All generation still requires eligible public evidence.
- Prior-session transcript-history, Experience and UTF-8 fixes were retained
  and included in the rebuilt application.

## Evidence recorded so far

- `outputs/deadline-validation.log`: backend 74 passed / 2 optional live tests
  skipped; Ruff, lint, typecheck and build passed; browser 11 passed / 1 failed
  on Chrome response-body eviction.
- `outputs/deadline-ui-final.log`: Ruff, lint, typecheck and production build
  passed; browser **12 passed**, including OCR review, withdrawal, timeline,
  stories, quiz/certificate, protected playback, panel-close/sign-out revocation,
  responsive kiosk controls and simulated speech API controls.
- The first placeholder-rights regression run exposed an invalid isolated
  legacy-record fixture (missing required verification metadata), not a production
  data change. The fixture was corrected; final results follow in the final log.

BHASHINI: no implemented calls or configuration variables were found. The UI
states that translation is unavailable. English/Hindi navigation and installed
local browser/system speech are separate existing capabilities. Automated speech
simulation does not verify audible output, touch hardware or screen-reader use.

No real email was sent. Public-source Gemini answers, production selection,
actual-media replay and final integrity comparison must be reported separately
from isolated synthetic regression tests.

## Final code validation

- `outputs/deadline-final-validation-2.log`: **77 backend passed, 2 skipped**
  (optional Ollama/Gemini live tests); Ruff, frontend ESLint, typecheck and full
  production build passed; **12 browser tests passed, 0 failed**.
- `outputs/deadline-foundation.log`: **3 passed, 0 failed** against the running
  local deployment, including real dependency readiness.
- `outputs/deadline-gemini-isolated.log`: the separately opted-in Gemini cited
  answer test **1 passed** using real `gemini-3.1-flash-lite`, PostgreSQL-only
  retrieval and an isolated synthetic fixture. This is not real archival RAG
  acceptance. No live Ollama success is claimed.

Pending owner input: path to an existing local staff credential JSON file.
No new staff account was provisioned, as the owner chose existing credentials.

## Renewed continuation: 2026-09-30, after 10:36 UTC

The owner clarified there is no credential JSON. Production has one active
`admin` account with the admin role. Only login, role, active and creation time
were queried; no password/hash was read or printed. `app.archive.staff` uses
HTTP Basic authentication and the PBKDF2 password verifier in `app.staff`.
Migration 001 defines unique logins, admin/curator roles and active status.
The documented provisioning CLI is `docker compose exec backend python -m
app.staff NEW_LOGIN --role admin`; it prompts twice and inserts a new account.
It was NOT run. No automatic/default account bootstrap was found in the inspected
application. No account or credential changes are authorized or performed.

Changed in this continuation only:

- `scripts/inventory_dataset.py`: image integrity/full decode inspection and
  optional reuse of prior PDF metrics only after a fresh identical SHA-256.
- `scripts/verify_submission_research.py`: pending live acceptance now includes
  an unsupported question without an artificial language filter, in addition to
  the deterministic empty-filter check. These real-source checks have NOT run.
- `scripts/publish_submission_selection.py`: optional credential path; otherwise
  interactive login and hidden password prompts, no credential persistence.
  Non-interactive input without a credential file is refused.
- `status.md` and this report: current evidence and authentication blocker.

Dataset inventory command, run from project root:

```powershell
& .\backend\.venv\Scripts\python.exe .\scripts\inventory_dataset.py Dataset outputs/continuation-dataset-inventory.json --reuse outputs/dataset-inventory.json
```

92 files: 22 PDF, 7 MP4, 1 MP3, 36 PNG, 25 JPEG, 1 TXT. All 61 images
decoded, zero reported file errors or exact duplicates. All 31 original hashes
match the prior inventory. Media probing is explicitly blocked by missing host
ffprobe; decoding images is not identity or rights verification. The reference
notes list document/media links but do not independently establish rights for
the new photographs or letter images. All remain unpublished. The 13,824-page
compilation remains held. No originals/checkpoints were modified.

Fresh commands/results:

```powershell
docker compose exec -T backend python -m pytest -p no:cacheprovider tests/test_providers.py tests/test_archive.py -q
# 11 passed, 5 integration tests skipped; outputs/continuation-targeted-tests.log
docker compose exec -T -e RUN_INTEGRATION=1 backend python -m pytest -p no:cacheprovider tests/test_providers.py tests/test_archive.py -q
# 16 passed, 0 failed/skipped; outputs/continuation-targeted-integration.log
# Existing isolated schema/storage harness; mocked provider tests, no live Gemini.

Set-Location frontend
$env:ARCHIVE_E2E_BROWSER='C:/Program Files/Google/Chrome/Application/chrome.exe'
$env:PLAYWRIGHT_BASE_URL='http://localhost:3000'
node node_modules/@playwright/test/cli.js test tests/foundation.spec.ts --workers=1
# 3 passed; outputs/continuation-foundation-elevated.log
Set-Location ..
```

The initial browser command used an incorrect working directory and did not run;
the corrected sandbox attempt was blocked by child-process `spawn EPERM`.
The approved elevated run passed all three checks. The failure-simulation test
is explicitly simulated; the readiness checks query the actual deployment.
Python AST parsing passed for all three modified scripts. No application source
changed in this continuation, so the earlier full lint/typecheck/build was not
repeated. Fresh public HTTP checks (outputs/continuation-public-checks.json):
/, /archive, /ai, /experience, /staff and /system all 200; staff documents API
401 without auth; catalog empty; AI `no_eligible_content`, generation not attempted.

PIB release IDs 1489909 and 2017835 and the PIB copyright policy were rechecked
online. The selected paragraph/bullet match their official sources. Only the two
attributed government-text excerpts are prepared for publication, no photographs
or third-party material. They remain modern government accounts, not original
Ambedkar manuscripts or speeches. No publication receipt exists yet.

Secure owner action from project root (does publish the reviewed selection):

```powershell
& .\backend\.venv\Scripts\python.exe .\scripts\publish_submission_selection.py
```

Enter existing login `admin` and its password locally at the hidden prompt; do
not send the password to chat. This uses normal authenticated staff APIs for
upload, extraction, text comparison/review, verification and publication.
No synthetic account or auth override is used. If the password is unknown,
stop; account provisioning or changes need the owner's separate approval.

After successful publication and worker indexing, public acceptance commands:

```powershell
& .\backend\.venv\Scripts\python.exe .\scripts\verify_submission_research.py
node .\scripts\verify_submission_browser.cjs
```

Those commands have NOT run against published content. Auth specifically remains
required for upload/review/publication, private media playback grants/revocation,
and real curator workflow checks. Public catalog/research/browser checks need no
staff credentials after eligible sources are published. Real archival Gemini
citations and production Qdrant indexing remain unverified; the earlier live
Gemini success used an isolated synthetic fixture. BHASHINI remains unavailable.

Final owner clarification: the existing admin password is unknown; leave accounts
unchanged. No reset/recovery/provisioning was attempted. The interactive command
above is usable only when the legitimate existing credentials become available.
Publication, real-source RAG and authenticated media checks remain blocked.

## Authorized bulk-processing continuation — actual publication and live acceptance

Supersedes earlier authentication blocker: owner subsequently supplied valid
existing staff credentials. Used hidden local prompts, no credential file,
account creation, permission change or password reset. Production workflow used
ordinary authenticated HTTP APIs; no synthetic credentials or auth overrides.

### Published selection

- Constitution excerpt: d3607a2e-92fd-4886-9f29-56c9cd38d8d3, verified text revision 2,
  https://www.pib.gov.in/PressReleasePage.aspx?PRID=1489909 (paragraph 42).
- Birth excerpt: 8ce2df4c-c4e2-4ed1-bf9e-244881273e82, verified text revision 2,
  https://www.pib.gov.in/PressReleasePage.aspx?PRID=2017835 (opening bullet).
- Eligibility: exact government-text excerpts with prominent attribution under
  https://www.pib.gov.in/content/3604_2_CopyrightPolicy.aspx?lang=1&reg=3;
  no photos or third-party quotations. Modern source accounts, not primary
  Ambedkar manuscripts. Captures/hashes retained in outputs/submission-sources.
- Published three timeline entries (birth/adoption/commencement), one story
  (From drafting to commencement) and one ten-question quiz. Questions combine
  recall with comparison of milestones; all ten support quotes checked against
  the captured text before authenticated draft -> verify -> publish transitions.
- Receipt: outputs/submission-sources/published-selection.json. 33 archival
  records total: 2 newly published/public; 31 prior statuses/access levels unchanged.

### Executed commands and results

From project root unless stated otherwise:

```powershell
docker compose exec -T -e RUN_INTEGRATION=1 backend python -m pytest -p no:cacheprovider -q
# outputs/bulk-authorization-backend.log: 77 passed, 2 skipped, 1 deprecation warning.
# Optional live model tests skipped; isolated schemas/storage, mocked provider tests.
& ./scripts/check_phase3.ps1 -SkipBackendTests
# outputs/bulk-authorization-ui.log: Ruff, lint, typecheck, production build passed;
# 12 isolated workflow browser tests passed. Includes withdrawal, direct file access,
# scoring/certificates and consent safeguards. No real email delivery.
& backend/.venv/Scripts/python.exe scripts/prepare_dataset_image_text.py
# outputs/bulk-image-ocr.log: all 61 images extracted locally, no failures.
# 31 contain recognized text; 30 have no recognized text. Every output unverified.
& backend/.venv/Scripts/python.exe scripts/prepare_submission_quiz.py
# Ten PIB questions prepared; ten exact support quotes checked.
& backend/.venv/Scripts/python.exe scripts/prepare_daic_quiz.py
# Ten separate Dataset questions drafted locally, exact normalized quotes checked.
# Physical PDF page numbers 12/18; source record 179956fd-df91-4b4e-99b1-63d21dc174a4.
# No verified revision available: not a DB draft and not published.
& backend/.venv/Scripts/python.exe scripts/publish_submission_selection.py
# Hidden interactive existing-account login. Two records and five activities published.
& backend/.venv/Scripts/python.exe scripts/verify_submission_research.py
# outputs/bulk-live-research-accepted.log and outputs/deadline-live-research.json:
# 3 real Gemini cited answers; 1 unsupported-question abstention; 1 empty-filter check.
node scripts/verify_submission_browser.cjs
# outputs/bulk-public-browser-certificate.log: 8 custom acceptance checks passed.
# Real source/browser Gemini, archive, responsive experience, quiz 10/10,
# anonymous certificate generation and HTML download; no email sent.
& backend/.venv/Scripts/python.exe scripts/verify_submission_media.py
# Hidden local prompt; auth passed to child process stdin, never saved.
# outputs/deadline-media.json: 8 passed/0 failed real private recordings, 206 ranges,
# muted native playback advances, public endpoint 404, grant revocation 401.
```

The media test confirms playback advances; it does not certify audible quality,
speaker identity, lip synchronization or transcription. BHASHINI remains unavailable.

Live research uses real `gemini-3.1-flash-lite` and actual public records.
Question coverage: Drafting Committee chair, Constitution commencement date,
Ambedkar birth date. Each answer has current source revision, exact quote and
resolving reader link; plain text has no invented page number. The unsupported
quantum-computing question abstains. Worker created two passages and two vectors
in verified_embeddinggemma_v1, embeddinggemma:latest, 768 dimensions. Collection
green, points_count=2, indexed_vectors_count=0 (do not confuse stored points with
that index counter). In-memory PostgreSQL-only retrieval separately returned the
real Constitution passage; persistent provider/model settings were unchanged.

Acceptance-script failures retained honestly: an exact date-string assertion
rejected correct "April 14, 1891"; a material filter selector did not match its
accessible name; an unscoped pre selector matched original and transcription;
a Windows script rewrite briefly damaged an arrow selector's encoding. Only
acceptance scripts were corrected, with UTF-8 restored. Final runs above passed.
No application behavior was weakened to satisfy tests.

### DAIC scope and preservation

The owner states DAIC supplied the Dataset and permitted SIH prototype use.
Recorded as owner-attested provenance/permission, not independent correspondence
or personal copyright ownership. No DAIC-specific written permission was located
in searched project text or permission-related filenames. Do not infer broader
public redistribution/commercial rights. Processing and private review proceed;
individual identification, source review and verified text remain outstanding.
Letters' placeholder rights and all original visibility states remain unchanged.

outputs/daic-prototype-review.json lists all 92 files, hashes and scope limitations.
All 92 hashes match the prior inventory. outputs/dataset-image-review contains
61 derivative OCR JSON files with original hashes, engine/model provenance and
warnings. The new image derivatives have NOT been ingested into production or
published; the importer does not register images as archival records, and the
staff upload requires accurate source metadata. No fabricated source URLs were used.

Existing corpus workflow resumed using read-only original mount:

```powershell
docker compose run --rm --no-deps -v 'C:/Users/Hackathon/Documents/Codex/2026-09-24/we-are-starting-sih26096-completely-from/Dataset:/dataset:ro' backend python -m app.corpus /dataset --file Volume_01.pdf --max-pages 1000 --ocr-pages 25
# outputs/bulk-volume01-ocr.log: completed 25 checkpoint pages.
docker compose run --rm --no-deps -v 'C:/Users/Hackathon/Documents/Codex/2026-09-24/we-are-starting-sih26096-completely-from/Dataset:/dataset:ro' backend python -m app.corpus /dataset --volumes-only --max-pages 1000 --ocr-pages 100
# outputs/bulk-volumes-ocr.log; final count recorded below after completion.
```

No auto-publication; no old checkpoints deleted. The held compilation is excluded.
No ASR model is configured; no transcript was invented. Native media originals
remain unchanged. Actual public-denial checks passed for all 31 prior records:
reader/original 404 and unauthenticated staff text 401 (93 assertions), saved in
outputs/bulk-restricted-access.json. Read-only checksum audit in
outputs/bulk-preservation-after.json: all 33 stored originals match checksums;
31 baseline originals retain their checksums, statuses and access levels.

Changed files this continuation: scripts/prepare_submission_quiz.py,
scripts/prepare_daic_quiz.py, scripts/prepare_dataset_image_text.py,
scripts/publish_submission_selection.py, scripts/verify_submission_research.py,
scripts/verify_submission_browser.cjs, scripts/verify_submission_media.cjs,
scripts/verify_submission_media.py, status.md, SUBMISSION_VERIFICATION.md;
new review/test artifacts under outputs. No application source or migrations changed.
