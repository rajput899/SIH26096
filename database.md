# SIH26096 — Initial Database Design

## Boundaries

This is the conceptual PostgreSQL design. Phase 1 implements only the acquisition and minimal management subset described below. It supports requirements.md A/B only. UUID identifiers, creation/update timestamps, foreign keys and explicit review/access states are the initial conventions. Store files on a managed volume and embeddings in Qdrant; PostgreSQL owns canonical metadata, text and authorization. Do not duplicate whole source archives or model arbitrary institutional processes.

## Core acquisition and discovery entities

| Entity | Essential fields and purpose |
|---|---|
| source | id, name, verified locator (nullable until checked), access/rights notes, verification status; represents SRC-01–03 without implying content exists. |
| archival_item | id, source_id, source_record_locator, title, material_type, language, description, date value/precision (nullable), rights_statement, access_level, review_status, content_revision, verified_by/at; one shared record across the three views. |
| asset | id, item_id, role (original/derivative), parent_asset_id, storage_key, original_filename, MIME type, byte_size, checksum, processing provenance; immutable original files and separately tracked derivatives. |
| text_segment | id, item_id, asset_id, revision, sequence, text, extraction_method, page_number or start/end milliseconds, review_status; reviewed full text assembled in sequence. Preserve extraction versions on correction. |
| tag / item_tag | tag id, label; item_id/tag_id association; reviewed metadata tagging. |
| passage | id, item_id, revision, sequence, text, text_hash, index_status, embedding_model/version; units of retrieval. |
| passage_segment | passage_id, segment_id, character_start/end; maps a passage to exact source segments and locators. |
| processing_job | id, item_id, job_type, input_revision, status, attempts, claimed_at, heartbeat_at, error, output_reference; durable extraction/index/language jobs with retry and stale-claim recovery. |
| generated_artifact | id, item_id (nullable for multi-source answers), kind (answer/summary/translation/narration), text or asset_id, language, input_revision(s), model/provider/version, status, created_at; clearly labeled derivatives. |
| artifact_evidence | artifact_id, passage_id, cited_revision; citations supporting generated text; resolve through passage_segment to the original. |

Use nullable historical dates and explicit precision (year/month/day or range); never manufacture exact dates. Material types cover documents, manuscripts, speeches, debates, photographs, audio and video without claiming holdings in any category.

## Management and visitor workflow

| Entity | Essential fields and purpose |
|---|---|
| staff_user | id, unique login, password_hash, role (curator/admin), active; no plaintext passwords or seeded credentials. |
| audit_event | id, actor_id, action, target_type/id, timestamp, change summary; records publication, corrections, rights and access changes without storing secrets. |
| compilation | id, anonymous_session_token_hash, title, created_at, expires_at; source-linked visitor collection without an account requirement. |
| compilation_entry | id, compilation_id, item_id, optional passage_id, cited_revision, position, optional visitor_note; ordered selected material with source links. |

Institutional management initially uses one deployment for one institution, public versus staff-only access, and curator/admin roles. Multi-tenant institutions and granular departmental policy engines are not assumed. Public compilation entries must still pass current access checks; a compilation does not grant access to withdrawn content. Define session retention during implementation and clear kiosk session ownership on reset.

## Minimal experience entities

| Entity | Essential fields and purpose |
|---|---|
| knowledge_entity | id, label, type, description, review_status; verified archival subjects for mapping. |
| knowledge_relation | id, from_entity_id, to_entity_id, relation_label, review_status; evidence-backed map edges. |
| timeline_event | id, title, date_start/end, date_precision, description, review_status; events linked to source evidence. |
| story / story_section | story id, title, review_status; section id, story_id, position, title, body, review_status; ordered memorial storytelling. |
| evidence_link | id, item_id, optional passage_id, cited_revision, and exactly one target FK: entity_id, relation_id, timeline_event_id or story_section_id; source support for reviewed experience content. |

These tables are introduced only in their implementation phase. No graph database, visitor social profiles, recommendation tables or optional export system is required.

## Constraints and index policy

- Foreign keys enforce item/asset/segment/passage ownership; verify that citations reference the same approved revision and item. Use a check constraint for exactly one experience target on evidence_link.
- Keep original assets immutable. Do not cascade-delete originals or cited evidence during routine edits; withdraw content and retain an audit trail. Handle any authorized final deletion through an explicit policy.
- Publication requires curator verification, valid provenance, a recorded rights/access decision and appropriate reviewed text/metadata. Experience facts require reviewed evidence; generated content is never its own historical source.
- Unique item revision/segment sequence and passage sequence prevent duplicate extraction/index records. Job identity includes type, item and input revision to support idempotency.
- Index source IDs, status/access, tags, language and passage ownership; use PostgreSQL full-text indexing for reviewed text. Choose language-specific text configuration only after validating the selected languages.
- Qdrant points use passage IDs and include item_id, revision, language and model identity. Never trust Qdrant payload access flags alone; enforce current PostgreSQL policy before use. An embedding model/dimension change requires a controlled full rebuild, not an additional permanent vector database.
- Generated artifacts track every input revision via structured provenance; invalidate them when any supporting input changes. Store citation references for answers that are shown, without requiring a persistent conversation-history feature.

## Deferred decisions

Finalize exact SQL types, migrations, authentication/session mechanics, retention and backup policy while implementing the relevant phase. This document defines no real records, historical content, credentials or source API contracts.

## Phase 1 implemented subset and storage contract

`backend/app/migrations/001_archive.sql` introduces `staff_user`, `source`, `archival_item`, `asset`, `audit_event`, plus a `schema_migration` ledger. SQL migrations run transactionally under a PostgreSQL advisory lock on backend startup; psycopg is the existing database driver. Pydantic validates upload metadata and lifecycle requests; no ORM is added.

UUIDs identify records. Source locators/rights are explicitly attested by the uploader, not automatically researched. Unknown historical dates remain NULL (date entry/editing is deferred). Only documents, manuscripts and photographs are accepted in Phase 1. No tag, extraction, job, passage, AI, compilation or experience tables are created prematurely.

Lifecycle: uploaded -> verified -> published; verified/published -> withdrawn; withdrawn records require verification again. Verification records reviewer/time and requires explicit review of the original, descriptive metadata, provenance and rights. Publication in this phase covers metadata and original only, never extracted/verified text. Staff-only records remain inaccessible publicly even after publication. Verification does not publish. Transition updates and audit inserts share a row-locked transaction.

Persistent volume `archive_data`, backend root `/app/archive` (`ARCHIVE_ROOT` for isolated tests):

- `originals/<item UUID>/<asset UUID>`: original bytes, exclusive-create, SHA-256, read-only after writing; uploaded names are metadata only.
- `derivatives/`: reserved, empty; future derivative files have separate asset records.
- `text/`: reserved, empty; no extracted, OCR or verified text is produced. Canonical future text belongs to separate PostgreSQL text-segment revisions.

No original update/delete API exists. A database trigger rejects original asset updates/deletes. Downloads recheck current access and checksum. Application immutability is not OS-admin-proof WORM storage. Normal failed uploads remove uncommitted files and roll back metadata. A process/power crash between file write and database commit can leave an unreferenced original; preserve it for administrative reconciliation, never auto-delete originals. Filesystem and PostgreSQL are not one atomic storage system. Backups and crash reconciliation tooling are deferred.

## Phase 2 schema extension

Migration `002_processing.sql` adds `processing_job`, `text_revision`, `text_segment` and `archival_item.current_text_revision`. Existing originals and migration 001 are unchanged. The existing `content_revision` follows the current text revision once text exists.

- One extraction job per item/original revision: queued -> running -> succeeded or failed. The immutable original is input revision 1; retries reuse the job. Completed jobs cannot overwrite text or silently rerun. Mode is auto or ocr. Attempts, timestamps, claim token, sanitized error, requesting staff and output revision are durable.
- First output is text revision 1 (extracted). Saving curator review creates revision N+1 (reviewed), retaining parent revision, job, author, note and provenance. Verify records reviewer/time on the current reviewed revision. Every earlier text snapshot remains readable to staff.
- Text segment content is immutable by trigger. Corrections copy all segments to a new revision with the same asset, physical page number and sequence. Empty individual pages remain represented, with warnings. An entirely empty transcription cannot be reviewed/verified until text is supplied.
- Composite foreign keys enforce item/asset/job/revision ownership. Unique revision/sequence and revision/page pairs prevent duplicated locators. PDF page numbers are one-based physical pages, not inferred printed folio numbers. Images are page 1. Plain text has a NULL page locator and whole-document sequence 1.
- Extraction provenance records original SHA-256, engine/library versions, rendering scale and hashes of installed OCR model files. OCR confidence/warnings survive corrections as information about the original extraction, not confidence assigned to curator text.
- Queueing processing and every correction revoke document publication. Once a processing job exists, publication requires successful processing and verified current text in addition to existing metadata verification. Text verification never publishes by itself. Phase 1 records with no processing request retain their metadata/original-only publication behavior.

All canonical text is in PostgreSQL. No OCR output writes into originals, and no text-derived files or embeddings are created. Future extraction-policy changes/reprocessing after a successful job require an explicit extension; this phase intentionally supports one extraction and correction history per original.

## Phase 3 schema implementation (migration 003)

`003_research.sql` extends the existing schema without rewriting originals or text snapshots:

- `passage`: immutable-source-derived, page-bounded chunks with exact character offsets, item/revision/segment ownership constraints and a generated `simple` tsvector + GIN index. One segment supplies each passage, so a separate many-to-many `passage_segment` table is not needed for this bounded implementation. Existing page numbers remain on the referenced segment; plain text keeps a null page locator.
- `search_index_state`: durable per-item pending/lexical/ready/withdrawn status, revision, embedding model identity, retries and safe errors. Existing worker handles it when extraction is idle; session advisory locks prevent competing index writers within a schema. Retry scheduling survives restart. No Redis or additional worker service.
- `generated_artifact`: generated answer JSON, configured model, timestamp and current/invalidated state. Visitor questions and conversation histories are not persisted here.
- `artifact_evidence`: artifact-to-passage links and supporting source quote; the full paragraph/evidence structure is retained in artifact JSON. Titles/pages/URLs are never taken from model output.
- A visibility trigger marks index work pending and invalidates dependent artifacts when publication/access/current revision changes. Every retrieval, reader and answer response also checks live permissions; invalidation is not the sole access barrier.

Qdrant collection is `RESEARCH_COLLECTION` (default `verified_archive_v1`). It contains vectors and identifiers, not original files or canonical text. Embedding model name+installed digest is hashed into the vector identity; mismatched models cannot silently mix vectors. Reindexing is idempotent. Test schemas use separately named collections and temporary file storage; no synthetic record is seeded in production.

## Migration 004 — heritage extensions (runtime application pending)
`004_heritage.sql` expands archival_item.material_type to include audio, video and speech without changing original assets or existing records. Additive tables:
- recording_revision: ordered timestamped cue snapshots, revision, reviewer, verified status/time. New revisions withdraw publication until reviewed and explicitly republished.
- curated_content: timeline/story/quiz bodies, topic, draft/verified/published/withdrawn status and approval metadata. The minimal editor corrects an entry by withdrawal and replacement; in-place revision editing is not implemented.
- curated_evidence: actual archive item + optional text revision + exact quote. Quiz sources require a current verified text revision and a matching quote at verification/publication and visitor access.
- quiz_attempt: opaque UUID capability, activity revision, submitted options, server-computed result and completion time. Repeated identical submissions are idempotent; changed resubmissions are rejected.
- certificate: one certificate per completed attempt, display name/pseudonym and public verification UUID. Verification rechecks activity/source approval. Display names are visible to holders of the verification link; UI offers “Archive visitor”.
- leaderboard_entry: opt-in, generated Reader pseudonym, unique attempt. No visitor names or email addresses in leaderboard output. Ranking is score proportion per attempt, all-time only.
- certificate_delivery: one per certificate, consent timestamp, recipient fingerprint, attempt count and sending/accepted/failed status. No raw email column.
Thumbnail derivatives use the existing asset table and `derivatives/<item-id>/<asset-id>.jpg`; immutable original paths and checksums remain unchanged. Originals are never overwritten or resized.

## Recording research correction — second session, 2026-09-29
Migration 005 extends existing immutable text snapshots with recording_revision provenance and start/end seconds. A snapshot has exactly one source: an extraction job or recording revision. Explicit recording verification copies the reviewed cue text and timestamps into new verified text segments; it does not publish. Saving corrections clears current text eligibility and withdraws the item, invalidating dependent answers through the existing trigger. Document correction APIs reject recording snapshots so timestamps cannot be bypassed. Existing recording snapshots are preserved; no automatic backfill or publication occurs. A pre-005 verified transcript needs a new reviewed revision, comparison and verification before research indexing.
The original file and its checksum remain unchanged. No synchronized captions or automatic transcription is implemented. The existing worker/index supports these approved segments using the same PostgreSQL and Qdrant eligibility rules. Migration 005 and transcript retrieval/citation/invalidation regression passed in the real PostgreSQL suite (49 passed, one live-model test skipped; 84.82s). Further media/email checks and final browser rerun are pending.
