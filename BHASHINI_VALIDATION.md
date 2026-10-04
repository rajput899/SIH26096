# Bhashini translation validation — 2026-10-02

Backend translation is implemented and live English → Hindi inference succeeded. This does not certify translation accuracy, enable public unreviewed OCR, or change RAG generation providers.

## Verified protocol and configuration

Official [pipeline configuration documentation](https://bhashini.gitbook.io/bhashini-apis/pipeline-config-call) specifies POST `https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline` with `userID` and `ulcaApiKey` headers. The [request](https://bhashini.gitbook.io/bhashini-apis/pipeline-config-call/request-payload) supplies translation languages and the account's pipeline ID. The [response](https://bhashini.gitbook.io/bhashini-apis/pipeline-config-call/response-payload) supplies service ID, callback URL and an inference API-key header/value.

The configured local environment already contains a pre-issued `Inference` credential and `Udyat_Key`. They map to backend-only `BHASHINI_INFERENCE_KEY` and `BHASHINI_UDYAT_KEY`; values are never recorded here. No configured user ID/pipeline ID was available. Consequently the live test used the pre-issued inference credential directly, not an invented account ID or pipeline. Optional discovery is implemented and mocked, but was not live-tested.

The [compute request protocol](https://bhashini.gitbook.io/bhashini-apis/pipeline-compute-call/request-payload) uses `pipelineTasks` with `taskType=translation`, `config.language`, `config.serviceId`, and `inputData.input[].source`. The [response protocol](https://bhashini.gitbook.io/bhashini-apis/pipeline-compute-call/response-payload) returns `pipelineResponse[].output[].target`. The implementation uses only `https://dhruva-api.bhashini.gov.in/services/inference/pipeline`, with the credential in `Authorization`; redirects and arbitrary callback URLs are rejected.

The official [available-model list](https://dibd-bhashini.gitbook.io/bhashini-apis/available-models-for-usage) documents `bhashini/iiith/nmt-all` and English/Hindi support. This implementation limits requests to `en → hi` and `hi → en`. Only `en → hi` has been exercised live. Direct-credential mode rejects undocumented alternative service IDs; optional configuration mode requires a matching language pair from the provider response.

## API and content boundary

- `GET /api/archive/translation/status`: safe configuration/capability flags, no credentials. Configuration is not proof of live availability.
- `POST /api/archive/documents/{id}/translation`: `{ "revision": 2, "sequence": 1, "target_language": "hi", "fallback": "none" }`. Revision/sequence must refer to the actual current public verified section. No arbitrary input text or provider URL is accepted.
- Published/public item **and** current `text_revision.status=verified` are required. Database share locks hold that eligibility through the bounded provider call; a concurrent withdrawal then blocks subsequent calls.
- Unknown language, unsupported pair, stale revision, missing or unreviewed text are refused before transmission. Maximum input: 6,000 characters; two concurrent calls and 30 requests/minute per backend process.
- Responses explicitly say machine-generated, unreviewed; include exact text SHA-256, revision, sequence and original reader citation. Translations are not written into text revisions or RAG indexes.
- Bhashini failure returns a sanitized unavailable code. Only explicit `fallback=ollama` or `fallback=gemini` enables those existing providers. RAG's existing provider selection remains unchanged. Translation fallbacks were mocked, not live-tested.
- `TRANSLATION_TIMEOUT_SECONDS` defaults to 20. Optional configuration needs both `BHASHINI_USER_ID` and `BHASHINI_PIPELINE_ID`. Do not fabricate them or place secrets in `NEXT_PUBLIC_*`.

## Actual validation

- `docker compose run --rm --no-deps backend python -m app.check_translation --live`: live success, authored connectivity sentence only; `outputs/bhashini-live.json`.
- `python scripts/verify_translation_api.py`: first audit-script attempt failed before translation because it assumed an object rather than the existing integer revision field. Corrected and rerun successfully; `outputs/bhashini-live-api-recheck.log` and `outputs/bhashini-live-api.json`. The real endpoint translated a previously public, curator-verified PIB passage, verified the exact source hash, returned 409 for stale revision and 404 for unreviewed/unpublished records.
- Mocked provider tests cover success, missing credentials, 401/403, 429, provider errors, timeout, malformed responses, config discovery, unsafe callback rejection and explicit Gemini/local fallbacks. PostgreSQL integration tests cover visibility/revision gates and withdrawal without exporting ineligible text.
- Complete backend suite: **100 passed, 2 live-AI acceptance tests skipped**. Isolated PostgreSQL schemas; provider calls mocked except the two explicit live checks above. One pre-existing Starlette/httpx deprecation warning.
- Backend lint and frontend lint/typecheck/build passed. Actual configured Bhashini values were compared in memory against application source, scripts and generated browser assets: no matches; `outputs/bhashini-credential-containment.json`. No secret values were saved by the check.

Not verified: live reverse translation, live pipeline-discovery credentials, expert linguistic/historical accuracy, live translation fallbacks, quota/load behavior or production deployment. No frontend translation controls were added; integration is backend-only. No unpublished archival content was used in the live calls.
