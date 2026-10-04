# Dataset release validation — resumed 2026-10-02

The interrupted session had completed migration 010 and its release transaction. This continuation verified that state and did **not** reapply the release, create duplicates, reprocess OCR, or change archival records. Bhashini activation reused existing Docker images and volumes.

## Counts and publication basis

| Scope | Registered | Public | Basis / outstanding review |
|---|---:|---:|---|
| Supplied Manuscripts grouping | 25 | 25 | Organizer-authorized JPEG originals; neutral image classification, historical identity unverified |
| Supplied Photographs grouping | 36 | 36 | Organizer-authorized PNG originals; neutral image classification, historical identity unverified |
| Videos | 7 | 7 | MP4 originals; no verified transcripts |
| Audio | 1 | 1 | MP3 original; no verified transcript |
| PDFs | 22 | 21 | One explicit compilation hold retained |
| Reference text | 1 | 1 | Original file, not a reviewed RAG source |
| **Dataset total** | **92** | **91** | Frozen project-level prototype authorization |
| Existing PIB sources outside dataset | 2 | 2 | Previously curator-reviewed/public; sole RAG-eligible records |
| External photograph outside dataset | 1 | 0 | Remains unpublished, no extension of dataset authorization |
| **Entire archive** | **95** | **93** | No collection remains empty |

Release ID: `sih26096-organizer-2026-10-01`. Manifest SHA-256: `bf0d5f8e07997f76644e41a27799f3d31ab76d6be47a2a948216899a448efdde`. Prior transaction registered **62 new** items and retained **30 existing** dataset records. This continuation registered **zero** additional records.

Exact filenames, stable IDs, hashes, exclusions and new/existing flags are in `outputs/dataset-release-applied.json`. The fresh `outputs/dataset-release-checkpoint-verified.json` reconciles every file against the current database, migration history, rights string, provenance, classification, original filename, ingestion/checkpoint counts, text revision and transcript counts. Both supplied-file and stored-original SHA-256 hashes matched all 92 manifest entries.

Dataset text states: **21 extracted/unreviewed revisions, 71 without a text revision**; no dataset record has verified text. Ingestion labels are 90 awaiting_review, one reference, one processing (the held PDF's preserved historical state, not permission to resume it). Private image OCR artifacts remain private; existing outputs were not recomputed. No new transcripts were invented or certified.

The held file is `Br. Ambedkar/book by br. ambedkar/Collected Works of Ambedkar vol 1.pdf`, ID `c5926726-5d27-4990-a08f-76a932fa57db`, 13,824 pages/checkpoints, staff/uploaded. The explicit identity/scope exclusion remains. External image `509f9e25-2112-4737-887b-f5ce3202f17e` (`Screenshot 2026-09-29 010531.png`) remains verified but unpublished. A rights string alone is not publication approval for that external image.

## Root cause and changes

The original empty pages were real publication gaps: supplied items were unregistered or private/unreviewed, and collection grouping needed to be separate from asserted historical classification. The earlier session implemented frozen dataset membership, migration 010 and owner-authorized original display. The resumed session confirmed successful publication; it did not weaken external-upload, text-review or access rules.

The saved pre-release backup `work/dataset-release-baseline/database.dump` remains present (30,678,946 bytes). `pg_restore --list` successfully inspected it; **no restore/recovery drill was performed**. Baselines/diffs and previous reports remain preserved. This directory has no Git repository, so no commit was made.

This continuation added backend-only Bhashini translation, configuration aliases, opt-in live checks, mocked/integration tests and read-only release verification scripts. It corrected one stale browser test that expected only one “Constitution” match; there are now two real matches, and the assertion uses the live filtered API count. The kiosk description now accurately distinguishes navigation/voice language from backend translation. See `BHASHINI_VALIDATION.md` for official protocol references and limits.

Changed files: `.env.example`, `compose.yml`; backend `app/config.py`, `app/llm.py`, `app/main.py`, new `app/translation.py` and `app/check_translation.py`; `tests/conftest.py`, new `tests/test_translation.py`; frontend `src/components/Kiosk.tsx`, `src/app/archive/[id]/page.tsx`, `tests/redesign.spec.ts`, `tests/reader-quiz.spec.ts`; verification scripts `verify_dataset_release.py`, `verify_dataset_release_browser.cjs`, `verify_release_checkpoint.py`, `verify_release_private_paths.py`, `verify_translation_api.py`; this report, Bhashini report, `status.md` and `implementation.md`. Earlier release changes are preserved in the release baseline and manifest, not falsely attributed to this continuation.

## Validation and limitations

- Full backend integration: **100 passed, 2 skipped**, real isolated PostgreSQL test schemas. Covers ingestion, classification, publication/withdrawal, media/text authorization, RAG/citations, transcripts, learning/quiz/certificate and translation contracts. Provider errors/success/fallbacks use mocks. Two live generation acceptance tests remain skipped.
- Initial backend invocation without integration opt-in: 71 passed, 31 skipped; superseded by the complete run. Initial Ruff run found three long lines; corrected, final lint passed. Formatting initially hit the read-only app mount; corrected with a separate writable workspace mount. No archive storage was affected.
- Frontend lint, typecheck, production build passed. No separate preview server started.
- Initial browser run on localhost:3000: 28 passed, 6 skipped, 1 stale-count failure. Corrected affected test rerun: 1 passed. After the additional structured-reader-error fix and frontend-only restart, **the complete final browser run passed 30 tests with 6 skipped** (`outputs/dataset-release-final-browser.log`). Six isolated-fixture tests were not run against the live corpus (upload/review/withdrawal, processing, photograph lifecycle, quiz/certificate, recording workflow); their backend counterparts passed. Simulated API error/empty/pagination, synthetic captions and speech API tests are explicitly mocked in test names.
- Dedicated live browser audit passed all three collections, complete 12-record pagination, two original-image viewers, PDF/text viewers and **eight actual muted media playback checks**. Muted playback verifies technical decoding/time advancement, not listening quality or historical identity. `outputs/dataset-release-live-browser.json`.
- Live retrieval and exact citation segment offsets passed for the two PIB sources; dataset-scoped unreviewed retrieval was empty. `outputs/dataset-release-research-resumed.json`. No new live RAG generation call was made.
- Staff login with prototype credentials was not rerun in the live browser script. Anonymous staff denials and authenticated role/lifecycle tests in isolated PostgreSQL schemas were exercised. No credentials, staff screenshots or authentication traces were saved.
- Fresh post-activation public URL audit passed all **91 original downloads (1,320,155,886 bytes)** with matching hashes, image thumbnails, media range206, per-file detail/API checks and protected held/external-photo denials: `outputs/dataset-release-public-audit-resumed.json`. **351 private original/text/static/OCR/authentication denial checks passed**: `outputs/dataset-release-private-paths.json`. Earlier per-file audit is preserved separately.
- The first direct-path audit incorrectly expected `/archive/originals/` to be a filesystem route; it is a dynamic reader shell returning200 while its invalid-ID API fails. It revealed `[object Object]` error rendering, not a file leak. The reader now presents a clear unavailable message; both the mocked regression and actual invalid-ID browser check passed. The corrected `/originals/` filesystem-style probe returns404. Stale compiled kiosk wording required restarting only the existing frontend; actual current wording is now verified (`outputs/dataset-release-reader-shell-final.log`).

Remaining curator work: resolve the held compilation identity/scope explicitly before any ingestion resumes; identify/date/attribute images using evidence; review extracted/OCR text in the staff text workspace and verify a revision before RAG eligibility; create and verify recording transcripts where needed. Independently review rights/provenance and publication for external uploads. Organizer dataset display does **not** require per-file rights checkboxes, and does not claim historical identity or text accuracy. Linguistic review of machine translations remains outstanding.
