"""Mocked provider tests; no real text, credentials or archive mutations."""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app import interface_language as interface
from app.main import create_app
from app.translation import TranslationFailure


@pytest.fixture
def provider(settings, tmp_path, monkeypatch):
    settings.archive_root = str(tmp_path)
    settings.bhashini_inference_key = SecretStr("synthetic-interface-key")
    interface.requests.clear()
    calls = []

    def translate(config, text, source, target, **kwargs):
        calls.append(text)
        return (
            [f"हिन्दी {s}" for s in text] if isinstance(text, list) else "भाषा",
            "synthetic-service",
        )

    monkeypatch.setattr(interface, "bhashini_translate", translate)
    return calls


def test_reviewed_allowlist_does_not_probe_on_page_load(settings, provider):
    result = interface.supported(settings)
    assert result["confirmed_pairs"] == [["en", code] for code in interface.LANGUAGES]
    assert result["discovery"] == "reviewed_service_allowlist"
    assert result["live_health_checked"] is False
    assert result["account_discovery_available"] is False
    interface.supported(settings)
    assert provider == []


@pytest.mark.parametrize(
    "reason",
    [
        "configuration_required",
        "authentication_failed",
        "provider_timeout",
        "provider_rate_limit",
        "provider_error",
    ],
)
def test_discovery_failure_no_claim(settings, provider, monkeypatch, reason):
    def fail(*args, **kwargs):
        raise TranslationFailure(reason)

    monkeypatch.setattr(interface, "bhashini_translate", fail)
    key = next(iter(interface.CATALOG))
    result = interface.translate_keys(settings, [key])
    assert result["translations"] == {} and result["missing"] == [key]
    assert result["reason"] == reason


def test_allowlist_batch_cache_and_no_private_text(settings, provider):
    keys = list(interface.CATALOG)[:2]
    result = interface.translate_keys(settings, keys)
    assert not result["missing"]
    assert provider[-1] == [interface.CATALOG[key] for key in keys]
    count = len(provider)
    assert interface.translate_keys(settings, keys)["translations"] == result["translations"]
    assert len(provider) == count
    with pytest.raises(HTTPException):
        interface.translate_keys(settings, ["private user text"])
    assert len(provider) == count


def test_api_rejects_arbitrary_text_and_unsupported_target(settings, provider):
    with TestClient(create_app(settings)) as client:
        key = next(iter(interface.CATALOG))
        for body in [
            {"keys": [key], "target_language": "bra"},
            {"keys": [key], "target_language": "hi", "text": "private input"},
            {"keys": ["private input"], "target_language": "hi"},
        ]:
            assert client.post("/archive/interface/translations", json=body).status_code == 422
        response = client.post(
            "/archive/interface/translations", json={"keys": [key], "target_language": "hi"}
        )
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store"


def test_provider_failure_retains_english_and_bad_placeholders_rejected(
    settings, provider, monkeypatch
):
    interface.supported(settings)

    def fail(*args, **kwargs):
        raise TranslationFailure("provider_timeout")

    monkeypatch.setattr(interface, "bhashini_translate", fail)
    key = next(iter(interface.CATALOG))
    result = interface.translate_keys(settings, [key])
    assert result["missing"] == [key] and result["translations"] == {}
    key = next(k for k, v in interface.CATALOG.items() if "{0}" in v)
    monkeypatch.setattr(
        interface, "bhashini_translate", lambda *args, **kwargs: (["lost placeholder"], "mock")
    )
    assert interface.translate_keys(settings, [key])["missing"] == [key]


@pytest.mark.parametrize("code", list(interface.LANGUAGES))
def test_each_reviewed_target_and_provider_contract(settings, provider, monkeypatch, code):
    def translated(config, text, source, target, **kwargs):
        assert source == "en" and target == code
        assert kwargs == {"allowed_pairs": interface.PAIRS, "required_service": interface.SERVICE}
        return [f"{code} {value}" for value in text], interface.SERVICE

    monkeypatch.setattr(interface, "bhashini_translate", translated)
    with TestClient(create_app(settings)) as client:
        key = next(iter(interface.CATALOG))
        response = client.post(
            "/archive/interface/translations", json={"keys": [key], "target_language": code}
        )
        assert response.status_code == 200
        assert response.json()["target_language"] == code
        assert response.json()["translations"][key].startswith(code)


def test_configuration_service_and_capability_boundaries(settings, provider):
    with TestClient(create_app(settings)) as client:
        body = client.get("/archive/interface/languages").json()
        assert len(body["languages"]) == len(interface.LANGUAGES) + 1
        assert all(row["native_name"] and row["name"] for row in body["languages"][1:])
        assert "synthetic-interface-key" not in str(body)
    settings.bhashini_translation_service_id = "unreviewed/service"
    assert interface.supported(settings)["confirmed_pairs"] == []
    with pytest.raises(HTTPException) as error:
        interface.translate_keys(settings, [next(iter(interface.CATALOG))], "mr")
    assert error.value.status_code == 503
    settings.bhashini_translation_service_id = interface.SERVICE
    settings.bhashini_inference_key = SecretStr("")
    assert interface.supported(settings)["confirmed_pairs"] == []
    assert provider == []


def test_cache_separates_target_and_account_and_rejects_corruption(settings, provider, monkeypatch):
    from pathlib import Path

    def translated(config, text, source, target, **kwargs):
        provider.append(target)
        return [f"{target} {value}" for value in text], interface.SERVICE

    monkeypatch.setattr(interface, "bhashini_translate", translated)
    key = next(iter(interface.CATALOG))
    for code in ["hi", "mr", "hi", "mr"]:
        assert interface.translate_keys(settings, [key], code)["translations"][key].startswith(code)
    assert provider == ["hi", "mr"]
    settings.bhashini_user_id = SecretStr("different-account")
    interface.translate_keys(settings, [key], "mr")
    assert provider == ["hi", "mr", "mr"]
    for path in (Path(settings.archive_root) / "interface-translations").glob("*.json"):
        path.write_text("[]", encoding="utf-8")
    assert interface.translate_keys(settings, [key], "mr")["translations"][key].startswith("mr")


@pytest.mark.parametrize("code", ["en", "ur", "bra", "awa", "zz", "../hi", "MR"])
def test_unaccepted_targets_do_not_call_provider(settings, provider, code):
    with pytest.raises(HTTPException) as error:
        interface.translate_keys(settings, [next(iter(interface.CATALOG))], code)
    assert error.value.status_code == 422 and provider == []
