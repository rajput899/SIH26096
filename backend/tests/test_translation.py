"""Bhashini contracts use mocks; archival access tests use isolated real PostgreSQL."""

import json

import httpx
import pytest
from pydantic import SecretStr
from test_research import publish_fixture

from app import translation
from app.db import connect
from app.translation import TranslationFailure, bhashini_translate


def provider(settings, monkeypatch, handler):
    settings.bhashini_inference_key = SecretStr("synthetic-inference-secret")
    real_client = httpx.Client
    monkeypatch.setattr(
        translation.httpx,
        "Client",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs),
    )


def test_missing_credentials_never_calls_network(settings, monkeypatch):
    monkeypatch.setattr(translation.httpx, "Client", lambda **kwargs: pytest.fail("network called"))
    with pytest.raises(TranslationFailure, match="configuration_required"):
        bhashini_translate(settings, "Synthetic text", "en", "hi")


def test_interface_pairs_do_not_expand_archive_adapter(settings, monkeypatch):
    from app.interface_languages import PAIRS, SERVICE

    def handler(request):
        body = json.loads(request.content)
        assert body["pipelineTasks"][0]["config"]["language"]["targetLanguage"] == "mr"
        return httpx.Response(
            200,
            json={
                "pipelineResponse": [
                    {"taskType": "translation", "output": [{"target": "कृत्रिम पाठ"}]}
                ]
            },
        )

    provider(settings, monkeypatch, handler)
    with pytest.raises(TranslationFailure, match="unsupported_language_pair"):
        bhashini_translate(settings, "Synthetic text", "en", "mr")
    assert (
        bhashini_translate(
            settings, "Synthetic text", "en", "mr", allowed_pairs=PAIRS, required_service=SERVICE
        )[1]
        == SERVICE
    )
    with pytest.raises(TranslationFailure, match="unverified_interface_service"):
        bhashini_translate(
            settings,
            "Synthetic text",
            "en",
            "mr",
            allowed_pairs=PAIRS,
            required_service="different/service",
        )


def test_direct_inference_contract_and_success(settings, monkeypatch):
    def handler(request):
        assert str(request.url) == translation.COMPUTE_URL
        assert request.headers["Authorization"] == "synthetic-inference-secret"
        body = json.loads(request.content)
        assert "synthetic-inference-secret" not in request.content.decode()
        assert body["pipelineTasks"] == [
            {
                "taskType": "translation",
                "config": {
                    "language": {"sourceLanguage": "en", "targetLanguage": "hi"},
                    "serviceId": "bhashini/iiith/nmt-all",
                },
            }
        ]
        assert body["inputData"] == {"input": [{"source": "Synthetic text"}]}
        return httpx.Response(
            200,
            json={
                "pipelineResponse": [
                    {"taskType": "translation", "output": [{"target": "परीक्षण पाठ"}]}
                ]
            },
        )

    provider(settings, monkeypatch, handler)
    text, service = bhashini_translate(settings, "Synthetic text", "en", "hi")
    assert text == "परीक्षण पाठ" and service == translation.DOCUMENTED_SERVICE


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        (401, "authentication_failed"),
        (403, "authentication_failed"),
        (429, "provider_rate_limit"),
        (500, "provider_error"),
        (302, "provider_error"),
    ],
)
def test_provider_errors_redact_body_and_secrets(settings, monkeypatch, status, reason):
    provider(
        settings,
        monkeypatch,
        lambda request: httpx.Response(
            status,
            text="synthetic-inference-secret sensitive server body",
            headers={"Location": "https://example.invalid/steal"},
        ),
    )
    with pytest.raises(TranslationFailure) as error:
        bhashini_translate(settings, "Synthetic text", "en", "hi")
    assert str(error.value) == reason
    assert "secret" not in str(error.value)


def test_timeout_and_malformed_success_are_safe(settings, monkeypatch):
    def timeout(request):
        raise httpx.ReadTimeout("synthetic-inference-secret")

    provider(settings, monkeypatch, timeout)
    with pytest.raises(TranslationFailure, match="provider_timeout"):
        bhashini_translate(settings, "Synthetic text", "en", "hi")


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"pipelineResponse": []},
        {"pipelineResponse": [{"taskType": "translation", "output": [{"target": ""}]}]},
        {"pipelineResponse": [{"taskType": "translation", "output": [{"target": 42}]}]},
    ],
)
def test_invalid_payloads(settings, monkeypatch, body):
    provider(settings, monkeypatch, lambda request: httpx.Response(200, json=body))
    with pytest.raises(TranslationFailure, match="invalid_provider_response"):
        bhashini_translate(settings, "Synthetic text", "en", "hi")


def test_config_flow_uses_udyat_and_discovers_exact_pair(settings, monkeypatch):
    settings.bhashini_udyat_key = SecretStr("synthetic-config-secret")
    settings.bhashini_user_id = SecretStr("synthetic-user")
    settings.bhashini_pipeline_id = "synthetic-pipeline"
    calls = []

    def handler(request):
        calls.append(str(request.url))
        if str(request.url) == translation.CONFIG_URL:
            assert request.headers["ulcaApiKey"] == "synthetic-config-secret"
            assert request.headers["userID"] == "synthetic-user"
            assert (
                json.loads(request.content)["pipelineRequestConfig"]["pipelineId"]
                == "synthetic-pipeline"
            )
            return httpx.Response(
                200,
                json={
                    "pipelineInferenceAPIEndPoint": {
                        "callbackUrl": translation.COMPUTE_URL,
                        "inferenceApiKey": {
                            "name": "Authorization",
                            "value": "synthetic-derived-key",
                        },
                    },
                    "pipelineResponseConfig": [
                        {
                            "taskType": "translation",
                            "config": [
                                {
                                    "serviceId": "synthetic/verified-service",
                                    "language": {"sourceLanguage": "en", "targetLanguage": "hi"},
                                }
                            ],
                        }
                    ],
                },
            )
        assert request.headers["Authorization"] == "synthetic-derived-key"
        return httpx.Response(
            200,
            json={
                "pipelineResponse": [{"taskType": "translation", "output": [{"target": "परीक्षण"}]}]
            },
        )

    provider(settings, monkeypatch, handler)
    assert (
        bhashini_translate(settings, "Synthetic text", "en", "hi")[1]
        == "synthetic/verified-service"
    )
    assert calls == [translation.CONFIG_URL, translation.COMPUTE_URL]


def test_untrusted_callback_cannot_receive_key_or_text(settings, monkeypatch):
    settings.bhashini_udyat_key = SecretStr("synthetic-config-secret")
    settings.bhashini_user_id = SecretStr("synthetic-user")
    settings.bhashini_pipeline_id = "synthetic-pipeline"
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(
            200,
            json={
                "pipelineInferenceAPIEndPoint": {
                    "callbackUrl": "http://127.0.0.1/private",
                    "inferenceApiKey": {"name": "Authorization", "value": "do-not-forward"},
                }
            },
        )

    provider(settings, monkeypatch, handler)
    with pytest.raises(TranslationFailure, match="unsafe_provider_configuration"):
        bhashini_translate(settings, "Synthetic text", "en", "hi")
    assert calls == [translation.CONFIG_URL]


@pytest.mark.parametrize("fallback", ["ollama", "gemini"])
def test_fallback_requires_explicit_selection(settings, monkeypatch, fallback):
    calls = []

    class MockProvider:
        def __init__(self, config, instruction):
            assert instruction == translation.INSTRUCTION

        def generate(self, content, schema):
            calls.append(json.loads(content))
            return {"translation": "Synthetic translated fixture"}

    monkeypatch.setattr(translation, "GeminiGeneration", MockProvider)
    monkeypatch.setattr(translation, "OllamaGeneration", MockProvider)
    with pytest.raises(TranslationFailure, match="configuration_required"):
        translation.translate(settings, "Synthetic text", "en", "hi")
    assert not calls
    result = translation.translate(settings, "Synthetic text", "en", "hi", fallback)
    assert result[1] == fallback and result[3] == "configuration_required"
    assert calls[0]["source_text"] == "Synthetic text"


@pytest.mark.integration
def test_only_current_public_verified_segments_leave_backend(archive, monkeypatch):
    client, config, admin, curator = archive
    item, _, _ = publish_fixture(archive)
    with connect(config) as db:
        record = db.execute(
            "SELECT current_text_revision FROM archival_item WHERE id=%s", (item,)
        ).fetchone()
    revision = record["current_text_revision"]
    calls = []
    monkeypatch.setattr(
        translation,
        "translate",
        lambda *args: (
            calls.append(args)
            or ("Translated synthetic text", "bhashini", "synthetic-service", None)
        ),
    )
    body = {"revision": revision, "sequence": 1, "target_language": "hi"}
    path = f"/archive/documents/{item}/translation"
    response = client.post(path, json=body)
    assert response.status_code == 200
    assert response.json()["review_status"] == "unreviewed"
    assert response.json()["machine_generated"] is True
    assert response.json()["source"]["reader_url"].endswith(f"?revision={revision}#page-1")
    assert response.headers["Cache-Control"] == "no-store"
    assert len(calls) == 1
    assert client.post(path, json={**body, "source_text": "arbitrary input"}).status_code == 422
    assert client.post(path, json={**body, "revision": revision + 1}).status_code == 409
    client.post(
        f"/archive/staff/documents/{item}/transition", auth=curator, json={"action": "withdraw"}
    ).raise_for_status()
    assert client.post(path, json=body).status_code == 404
    assert len(calls) == 1
    safe = client.get("/archive/translation/status").json()
    assert "key" not in json.dumps(safe)


@pytest.mark.integration
def test_published_original_without_reviewed_text_is_not_exported(archive, monkeypatch):
    client, config, _, _ = archive
    item, _, _ = publish_fixture(archive)
    with connect(config) as db:
        # Synthetic regression: publication alone does not certify a text revision.
        db.execute(
            "UPDATE text_revision SET status='extracted',verified_by=NULL,verified_at=NULL "
            "WHERE item_id=%s",
            (item,),
        )
    monkeypatch.setattr(
        translation, "translate", lambda *args: pytest.fail("unreviewed text exported")
    )
    assert (
        client.post(
            f"/archive/documents/{item}/translation",
            json={"revision": 1, "sequence": 1, "target_language": "hi"},
        ).status_code
        == 404
    )
