# Interface multilingual continuation - 2026-10-03 (Asia/Kolkata)

## Evidence and acceptance limits

The previous probe DID run. Its complete output is preserved at
`outputs/multilingual-probes.log` (provider timestamp 2026-10-02T15:10:23Z).
All 34 candidates were marked `verified` solely because both responses differed
from English. Those flags are NOT accepted as language or translation-quality evidence.
For example, `bra` returned a Bodo-like first sentence and mixed second sentence;
`awa` returned standard Hindi-like text. These are reasons to reject automatic promotion.

The provider's published service list includes the languages below for
`bhashini/iiith/nmt-all`:
https://dibd-bhashini.gitbook.io/bhashini-apis/available-models-for-usage
Model-author reference inspected: https://github.com/vmujadia/onemtbig
Neither reference proves access through this account or linguistic correctness.

Fresh checks used the existing account and exactly these authored sentences:

1. Choose a language to read this website.
2. Search the archive and read the original document.

`outputs/multilingual-20261003-live.log` preserves the source, every exact returned
translation, provider code, service, outcome and sanitized errors. Its provider
timestamp is 2026-10-02T18:47:14Z, which is 2026-10-03 00:17:14 IST. Calls were
sequential; no archive/private text, real user input, generation or speech requests
were sent. All eleven requests returned two nonempty strings with no reported errors.
Every fresh output matched the corresponding saved output exactly.

Codex separately reviewed each of these 22 sentences for language/script and the
two intended meanings. This is a model's bounded semantic assessment, NOT independent
native-speaker review, a quality score, historical accuracy, or full-catalog acceptance.
The probe itself correctly records `quality_verified: false`; response success alone
never approves a language. The following list is accepted for machine-translated
interface use on that explicitly limited evidence.

| Interface/provider code | Language | Sample assessment |
|---|---|---|
| hi | Hindi | Hindi wording; language selection and archive/original-document instructions retained. |
| bn | Bengali | Bengali wording; both instructions retained. |
| gu | Gujarati | Gujarati wording; both instructions retained. |
| kn | Kannada | Kannada wording; both instructions retained; document uses a loanword. |
| ml | Malayalam | Malayalam wording; both instructions retained. |
| mr | Marathi | Marathi wording; both instructions retained; archive rendered as collection. |
| ne | Nepali | Nepali wording; both instructions retained. |
| or | Odia | Odia wording; both instructions retained. |
| pa | Punjabi | Punjabi wording; both instructions retained; typography merits native review. |
| ta | Tamil | Tamil wording; both instructions retained. |
| te | Telugu | Telugu wording; both instructions retained; loanword/spacing merits native review. |

English (`en`) is the original interface, not a provider translation. The remaining
23 previous candidates stay unavailable: `as`, `awa`, `bho`, `bra`, `brx`, `doi`,
`gom`, `gon`, `hi-Latn`, `hoc`, `ks`, `ks-Deva`, `kha`, `lus`, `mai`, `mag`, `mni`,
`sa`, `sat`, `sd`, `tcy`, `ur`, `xnr`. They have NOT all failed inference; they lack
accepted language/meaning and/or interface evidence in this continuation. In particular,
Urdu and other RTL candidates need RTL interface review as well as linguistic review.
No speculative aliases were enabled.

## Capability and cache contract

`backend/app/interface_languages.py` is the sole reviewed list. GET
`/archive/interface/languages` returns native/English labels from it, enabled only
when backend credentials and the exact reviewed service are configured. It is a
documented capability list, NOT a live health check: `live_health_checked=false`.
`confirmed_pairs` denotes saved bounded sample evidence, not fresh inference on GET.
An outage after selection leaves missing strings in English. Page loads do not
trigger eleven repeated inference probes. Missing/malformed capabilities leave English.

`BHASHINI_USER_ID` and `BHASHINI_PIPELINE_ID` remain missing. Account discovery is
unavailable; no discovery result is invented. If account configuration is later added,
the existing adapter resolves the exact requested pair, but interface inference rejects
a returned service ID other than the reviewed service before sending authored strings.
Account configuration does not automatically expand the reviewed list.

POST `/archive/interface/translations` accepts only registered catalog IDs and one
accepted target. It does not accept caller text. The archive-content API retains its
separate English/Hindi pair restriction and explicit user action. Bhashini ASR and TTS
are not enabled or tested. Local browser speech remains a separate existing feature.

Backend cache identity includes catalog version, provider service, account/credential
identity and target. The existing Hindi filename is retained for cache reuse; all new
targets have distinct suffixes. Account fingerprints remain internal. Malformed cache
entries and damaged placeholders fall back to English. Browser dictionaries are also
separated by target and aborted responses cannot populate a subsequent selection.

Only the language code is persisted in localStorage (`archive-interface-language`).
It is restored after backend validation and survives reload/navigation. Unsupported or
disabled saved values use English. Denied storage does not prevent current-page use.
No archival text, entered staff data, citations or credentials are persisted by this change.

## Remaining acceptance

Native-speaker review of all interface strings, especially staff terminology and
placeholders, remains outstanding for every machine-translated language. Two sentences
cannot establish full-catalog quality. No live reverse-pair, discovery, ASR, TTS,
email, new RAG generation, load/quota or production deployment acceptance is claimed.
The Ambedkar photograph remains unpublished pending independently verified display rights.

Exact validation commands/results and preservation evidence are appended to `status.md`.
