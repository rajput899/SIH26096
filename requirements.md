# SIH26096 — Requirements

## Scope and authority

This baseline uses only the SIH26096 problem-statement requirements supplied by the project owner in this conversation. No independently retrieved full PS, source holdings, access permissions, APIs, or historical content have been verified. Amend this baseline if an authoritative full PS reveals additional constraints; do not infer them now.

AI | ARCHIVE | EXPERIENCE are three views of one shared archive, with shared records, permissions, provenance, and citations. They are not separate products.

## A. Explicit PS requirements

The acceptance evidence below operationalizes the supplied requirements without asserting that functionality or content already exists.

| ID | Requirement | View(s) | Required evidence when implemented |
|---|---|---|---|
| PS-01 | AI-powered semantic search | AI, ARCHIVE | A meaning-based query retrieves relevant verified archival passages and opens their records. |
| PS-02 | Intelligent knowledge mapping | EXPERIENCE | Evidence-backed relationships between archival subjects/items are navigable and traceable to sources. |
| PS-03 | Full-text and summarized access | AI, ARCHIVE | Visitors can study extracted full text and a clearly labeled source-grounded summary alongside the original. |
| PS-04 | OCR digitization of old documents/manuscripts | ARCHIVE | A real permitted scan is processed; extracted text can be reviewed and corrected without altering the original. |
| PS-05 | Multilingual translation | AI, ARCHIVE | Selected supported languages translate archival text, preserve access to the original, and label translations as derivatives. |
| PS-06 | Audio narration | AI, ARCHIVE | Visitors can listen to narration generated from archival text with its source identified. |
| PS-07 | Audio-video archival system | ARCHIVE | Authorized audio/video can be ingested, described, preserved, and played. |
| PS-08 | Interactive timeline | EXPERIENCE | Visitors navigate supported dates/events and open their archival evidence. |
| PS-09 | Memorial storytelling | EXPERIENCE | A navigable narrative links its factual claims to archival evidence. |
| PS-10 | AI Research Assistant | AI | Questions produce source-grounded answers, with explicit insufficient-evidence responses when needed. |
| PS-11 | Secure digital preservation | ARCHIVE | Originals remain intact; access controls, integrity checks, backup and a tested restore protect the archive. |
| PS-12 | Metadata tagging | ARCHIVE | Curators can review and maintain descriptive metadata and tags used in discovery. |
| PS-13 | Institutional archival management | ARCHIVE | Authorized staff can ingest, review, publish, restrict, and maintain archival records. |
| PS-14 | Interactive kiosks / smart displays | EXPERIENCE | A shared-archive touch-oriented display supports visitor exploration and clears visitor session state. |
| PS-15 | Visitors can search, study, listen to, and compile archival material | All | Visitors complete these actions, including saving a source-linked compilation of selected material. |

### PS-specified source/data targets

| ID | Target | Initial status |
|---|---|---|
| SRC-01 | Dr. Ambedkar Foundation | Access method, holdings, permissions and reusable content unverified. |
| SRC-02 | Constituent Assembly Debates Archive | Access method, holdings, permissions and reusable content unverified. |
| SRC-03 | National Digital Library of India | Access method, holdings, permissions and reusable content unverified. |

These are required acquisition targets, not claims of available datasets or integrations. Record a verified source locator and permitted use before importing any item. Do not invent documents, APIs, credentials, historical facts, or source content. A blocked target remains explicitly blocked rather than being represented by fabricated material.

## B. Necessary implementation/supporting capabilities

These support A and are engineering decisions, not additional quoted PS requirements.

- SUP-01: Preserve acquisition provenance, rights/access decisions, originals and stable page/time locators; citations must resolve to supporting material and original sources.
- SUP-02: Ingest and extract/OCR, review metadata and text, verify, then index only published, permitted content. Corrected or withdrawn content must invalidate stale derived results.
- SUP-03: Use retrieval-augmented generation (RAG) with Ollama as the primary local LLM. No paid external LLM API dependency. Generate answers and summaries from retrieved evidence; abstain on insufficient support.
- SUP-04: Provide staff authentication, minimal curator/admin roles, publication/access controls, processing status, retryable jobs and audit records.
- SUP-05: Provide language-service interfaces, declared supported languages and voice input for multilingual/voice interaction. Speech recognition and text-to-speech are distinct capabilities; failed services must not be presented as success.
- SUP-06: Maintain backups, integrity verification, functional tests and reproducible local startup. Support visitor compilations with stable source references without requiring visitor accounts initially.
- SUP-07: Share archival IDs and access checks across AI, ARCHIVE and EXPERIENCE. Curator verification is required before publishing generated relationships, dated events or narrative claims.

The owner's planned technologies are implementation constraints documented in architecture.md, not PS requirements. Language coverage, model choice, resource limits, kiosk hardware, dataset scale and institutional policies remain to be validated rather than assumed.

## C. Optional enhancements

Optional and outside the committed baseline: visitor accounts and cross-device compilation sync, bulk compilation export, recommendations, advanced graph analytics, and offline kiosk caching. None gates completion of A or B. Adoption requires an explicit scope decision and corresponding document updates.

## Scope control

No blockchain, Kubernetes, microservice split, additional vector database, or AR/VR is planned. A UI placeholder is not acceptance evidence. Completion requires working behavior with legitimate source material; test fixtures must be clearly labeled synthetic and never presented as archival holdings.

## Approved heritage expansion — 2026-09-29
Owner-authorized continuation: visitor thumbnails and image readers; staff review clarity; recordings with protected native playback and reviewed timestamped transcripts; curator-managed source-backed timeline/stories/quizzes; server-authoritative scoring; optional pseudonymous leaderboard; validated completion certificates with public verification; optional consent-based SMTP delivery. Earlier exclusions for these features are superseded for this work only.
Gemini is now an explicitly selected optional cloud generation provider. `AI_PROVIDER=ollama` remains the default. Neither missing configuration nor provider errors may cause an implicit provider switch. Only retrieved, current, published public verified text can enter a generation request. Embeddings remain the existing local Ollama/Qdrant implementation. Never send staff-only material to Gemini.
A configured provider is not a tested live connection. No Google model is assumed installed or available. No AI, email, timeline or quiz content may be fabricated to populate the live system. Verification remains distinct from publication. The photograph with rights recorded only as “Allowed” stays unpublished pending independent rights confirmation.
