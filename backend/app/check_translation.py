"""Explicit opt-in live Bhashini smoke test using authored non-archival text only."""

import argparse
import json

from app.config import Settings
from app.translation import TranslationFailure, bhashini_translate, configuration_ready


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    config = Settings()
    configured = bool(config.bhashini_inference_key.get_secret_value()) or configuration_ready(
        config
    )
    result = {
        "configured": configured,
        "live_attempted": False,
        "source_language": "en",
        "target_language": "hi",
        "source_kind": "authored connectivity test, not archival text",
    }
    if args.live and configured:
        result["live_attempted"] = True
        try:
            text, service = bhashini_translate(
                config, "This is a translation connectivity test.", "en", "hi"
            )
            result.update(
                success=True,
                service_id=service,
                translation=text,
                historical_accuracy_verified=False,
            )
        except TranslationFailure as exc:
            result.update(success=False, reason=exc.reason)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
