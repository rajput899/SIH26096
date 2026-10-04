import json
from types import SimpleNamespace

import httpx
import pytest
from google import genai
from pydantic import SecretStr

from app.llm import ProviderFailure, generate_grounded, provider_state
from app.research import Answer


def test_gemini_sdk_contract_is_mocked_and_key_never_in_prompt(settings, monkeypatch):
    settings.ai_provider = "gemini"
    settings.gemini_api_key = SecretStr("synthetic-secret-not-a-key")
    settings.gemini_model = "synthetic-test-model"
    calls = []

    class FakeClient:
        def __init__(self, **kwargs):
            assert kwargs["api_key"] == "synthetic-secret-not-a-key"
            assert kwargs["http_options"].timeout == 45000
            assert kwargs["http_options"].retry_options.attempts == 1
            self.models = self

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def generate_content(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(text='{"paragraphs": []}')

    monkeypatch.setattr(genai, "Client", FakeClient)
    result = generate_grounded(settings, [], "Synthetic question", [], Answer.model_json_schema())
    assert result == {"paragraphs": []}
    assert calls[0]["model"] == "synthetic-test-model"
    assert calls[0]["config"].response_mime_type == "application/json"
    assert "synthetic-secret" not in json.dumps(provider_state(settings))
    assert "synthetic-secret" not in calls[0]["contents"]


@pytest.mark.parametrize("code", [400, 401, 403, 404, 429, 503])
def test_provider_failure_redacts_upstream_secrets(settings, monkeypatch, caplog, code):
    settings.ai_provider = "gemini"
    settings.gemini_api_key = SecretStr("synthetic-private-key")
    settings.gemini_model = "test-model"

    def failed(**kwargs):
        error = RuntimeError("provider URL contains synthetic-private-key")
        error.code = code
        raise error

    monkeypatch.setattr(genai, "Client", failed)
    with pytest.raises(ProviderFailure) as caught:
        generate_grounded(settings, [], "test", [], Answer.model_json_schema())
    assert "synthetic-private-key" not in str(caught.value)
    assert "synthetic-private-key" not in caplog.text
    assert caught.value.__suppress_context__


def test_missing_key_never_initializes_sdk(settings, monkeypatch):
    settings.ai_provider = "gemini"
    settings.gemini_api_key = SecretStr("")
    monkeypatch.setattr(
        genai, "Client", lambda **_: pytest.fail("No network without configuration")
    )
    assert provider_state(settings)["state"] == "configuration_required"
    with pytest.raises(ProviderFailure):
        generate_grounded(settings, [], "test", [], Answer.model_json_schema())


@pytest.mark.parametrize("invalid", ["not json", "{unfinished"])
def test_gemini_invalid_json_is_a_parsing_failure(settings, monkeypatch, invalid):
    settings.ai_provider = "gemini"
    settings.gemini_api_key = SecretStr("synthetic-private-key")
    settings.gemini_model = "test-model"

    class Client:
        def __init__(self, **_):
            self.models = self

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def generate_content(self, **_):
            return SimpleNamespace(text=invalid)

    monkeypatch.setattr(genai, "Client", Client)
    with pytest.raises(json.JSONDecodeError):
        generate_grounded(settings, [], "test", [], Answer.model_json_schema())


def test_gemini_timeout_is_distinct_and_sanitized(settings, monkeypatch):
    settings.ai_provider = "gemini"
    settings.gemini_api_key = SecretStr("synthetic-private-key")
    settings.gemini_model = "test-model"

    def timeout(**_):
        raise httpx.ReadTimeout("synthetic-private-key must not escape")

    monkeypatch.setattr(genai, "Client", timeout)
    with pytest.raises(ProviderFailure) as caught:
        generate_grounded(settings, [], "test", [], Answer.model_json_schema())
    assert caught.value.reason == "provider_timeout"
    assert "synthetic-private-key" not in str(caught.value)
