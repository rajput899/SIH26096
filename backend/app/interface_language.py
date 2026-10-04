"""Translate only a versioned application-string allowlist, never browser/page input."""

import hashlib
import json
import re
import threading
import time
from collections import deque
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from app.interface_languages import LANGUAGES, PAIRS, SERVICE
from app.translation import TranslationFailure, bhashini_translate, configuration_ready

router = APIRouter(prefix="/archive/interface")
CATALOG = json.loads(Path(__file__).with_name("interface_strings.json").read_text("utf-8"))
VERSION = hashlib.sha256(json.dumps(CATALOG, sort_keys=True).encode()).hexdigest()
lock = threading.Lock()
requests = deque()


def identity(config):
    # Credential fingerprint stays internal; never returned or logged.
    return hashlib.sha256(
        (
            config.bhashini_inference_key.get_secret_value()
            + config.bhashini_udyat_key.get_secret_value()
            + config.bhashini_pipeline_id
            + config.bhashini_translation_service_id
            + config.bhashini_user_id.get_secret_value()
        ).encode()
    ).hexdigest()


def supported(config):
    configured = bool(config.bhashini_inference_key.get_secret_value()) or configuration_ready(
        config
    )
    enabled = configured and config.bhashini_translation_service_id == SERVICE
    return {
        "source_language": "en",
        "confirmed_pairs": [["en", code] for code in LANGUAGES] if enabled else [],
        "discovery": "reviewed_service_allowlist",
        "account_discovery_available": configuration_ready(config),
        "service_id": SERVICE,
        "reason": None if enabled else "configuration_required",
        "live_health_checked": False,
        "quality_scope": "two_authored_sentences_model_reviewed_not_expert_certified",
    }


@router.get("/languages")
def languages(request: Request):
    with lock:
        result = supported(request.app.state.config)
    return {
        **result,
        "version": VERSION,
        "languages": [
            {"code": "en", "label": "English", "enabled": True, "basis": "original_interface"},
            *[
                {
                    "code": code,
                    "label": f"{native} - {name}",
                    "name": name,
                    "native_name": native,
                    "provider_code": code,
                    "enabled": ["en", code] in result["confirmed_pairs"],
                    "basis": "live_sample_and_bounded_semantic_review",
                }
                for code, (name, native) in LANGUAGES.items()
            ],
        ],
        "notice": (
            "Only English-source interface translation is offered. "
            "Machine translation is not expert-reviewed. Archive translation is separate; "
            "Bhashini ASR and TTS are not enabled."
        ),
    }


class InterfaceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_language: str = Field(min_length=2, max_length=16)
    keys: list[str] = Field(min_length=1, max_length=30)


def translate_keys(config, keys, target="hi"):
    if target not in LANGUAGES:
        raise HTTPException(422, "Unsupported interface language")
    if any(key not in CATALOG for key in keys):
        raise HTTPException(422, "Unknown interface key; arbitrary text is not accepted")
    with lock:
        capability = supported(config)
        if ["en", target] not in capability["confirmed_pairs"]:
            raise HTTPException(503, "Interface translation unavailable; retain English")
        directory = Path(config.archive_root) / "interface-translations"
        # Preserve the existing Hindi cache; every other target has a separate file.
        suffix = "" if target == "hi" else f"-{target}"
        path = directory / f"{VERSION}-{identity(config)}{suffix}.json"
        try:
            cached = json.loads(path.read_text("utf-8"))
        except (OSError, ValueError):
            cached = {}
        if not isinstance(cached, dict):
            cached = {}
        cached = {
            key: value
            for key, value in cached.items()
            if key in CATALOG and valid_translation(key, value)
        }
        missing = list(dict.fromkeys(key for key in keys if key not in cached))
        reason = None
        if missing:
            now = time.monotonic()
            while requests and requests[0] < now - 60:
                requests.popleft()
            if len(requests) >= 30:
                raise HTTPException(429, "Translation rate limit; retain English and retry later")
            requests.append(now)
            try:
                values, _ = bhashini_translate(
                    config,
                    [CATALOG[key] for key in missing],
                    "en",
                    target,
                    allowed_pairs=PAIRS,
                    required_service=SERVICE,
                )
                for key, value in zip(missing, values, strict=True):
                    # Reject damaged template placeholders; never interpolate user data remotely.
                    if valid_translation(key, value):
                        cached[key] = value
                directory.mkdir(parents=True, exist_ok=True)
                temporary = path.with_suffix(".tmp")
                temporary.write_text(json.dumps(cached, ensure_ascii=False), encoding="utf-8")
                temporary.replace(path)
            except (TranslationFailure, OSError, ValueError, TypeError) as exc:
                reason = (
                    exc.reason
                    if isinstance(exc, TranslationFailure)
                    else "invalid_translation_cache_or_response"
                )
        return {
            "translations": {key: cached[key] for key in keys if key in cached},
            "missing": [key for key in keys if key not in cached],
            "reason": reason,
            "version": VERSION,
            "provider": "bhashini",
            "machine_generated": True,
            "target_language": target,
        }


def valid_translation(key, value):
    return (
        isinstance(value, str)
        and bool(value.strip())
        and len(value) <= 24000
        and sorted(re.findall(r"\{\d+\}", CATALOG[key])) == sorted(re.findall(r"\{\d+\}", value))
    )


@router.post("/translations")
def translations(data: InterfaceRequest, request: Request):
    return translate_keys(request.app.state.config, data.keys, data.target_language)
