"""Opt-in configured-service probes. Authored text only; never print credentials."""

import json
import argparse
from datetime import UTC, datetime

from app import translation
from app.config import Settings

# Candidates, NOT support declarations. Official service list and model-author aliases:
# https://dibd-bhashini.gitbook.io/bhashini-apis/available-models-for-usage
# https://github.com/vmujadia/onemtbig (language mapping)
CANDIDATES = {
    "as": ["Assamese", "অসমীয়া", "as"],
    "awa": ["Awadhi", "अवधी", "awa", "aw"],
    "bn": ["Bengali", "বাংলা", "bn"],
    "bho": ["Bhojpuri", "भोजपुरी", "bho", "bh"],
    "bra": ["Braj", "ब्रज", "bra", "br"],
    "brx": ["Bodo", "बड़ो", "brx", "bx"],
    "doi": ["Dogri", "डोगरी", "doi"],
    "gom": ["Konkani", "कोंकणी", "gom", "go"],
    "gon": ["Gondi", "गोंडी", "gon", "gn"],
    "gu": ["Gujarati", "ગુજરાતી", "gu"],
    "hi": ["Hindi", "हिन्दी", "hi"],
    "hi-Latn": ["Hinglish", "Hinglish", "hg"],
    "hoc": ["Ho", "𑢹𑣉", "hoc", "hc"],
    "kn": ["Kannada", "ಕನ್ನಡ", "kn"],
    "ks": ["Kashmiri (Arabic)", "کٲشُر", "ks"],
    "ks-Deva": ["Kashmiri (Devanagari)", "कॉशुर", "ka"],
    "kha": ["Khasi", "Khasi", "kha", "kh"],
    "lus": ["Mizo", "Mizo ṭawng", "lus", "lu"],
    "mai": ["Maithili", "मैथिली", "mai", "ma"],
    "mag": ["Magahi", "मगही", "mag", "mg"],
    "ml": ["Malayalam", "മലയാളം", "ml"],
    "mr": ["Marathi", "मराठी", "mr"],
    "mni": ["Manipuri", "মৈতৈলোন", "mni", "mn"],
    "ne": ["Nepali", "नेपाली", "ne", "np"],
    "or": ["Odia", "ଓଡ଼ିଆ", "or"],
    "pa": ["Punjabi", "ਪੰਜਾਬੀ", "pa"],
    "sa": ["Sanskrit", "संस्कृतम्", "sa"],
    "sat": ["Santali", "ᱥᱟᱱᱛᱟᱲᱤ", "sat", "st"],
    "sd": ["Sindhi", "سنڌي", "sd", "sn"],
    "ta": ["Tamil", "தமிழ்", "ta"],
    "tcy": ["Tulu", "ತುಳು", "tcy", "tc"],
    "te": ["Telugu", "తెలుగు", "te"],
    "ur": ["Urdu", "اردو", "ur"],
    "xnr": ["Kangri", "कांगड़ी", "xnr", "xr"],
}
PROBE = [
    "Choose a language to read this website.",
    "Search the archive and read the original document.",
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codes", nargs="+", choices=sorted(CANDIDATES), required=True)
    args = parser.parse_args()
    config = Settings()
    # This isolated validation process allows candidates, not the production content API.
    translation.PAIRS = {("en", code) for row in CANDIDATES.values() for code in row[2:]}

    def check(entry):
        code, row = entry
        attempts = []
        for provider_code in row[2:]:
            try:
                values, service = translation.bhashini_translate(config, PROBE, "en", provider_code)
                changed = all(
                    a.strip().casefold() != b.strip().casefold()
                    for a, b in zip(values, PROBE, strict=True)
                )
                attempts.append(
                    {
                        "provider_code": provider_code,
                        "response_success": True,
                        "source_changed": changed,
                        "reason": None if changed else "unchanged_source",
                        "translations": values,
                    }
                )
                if changed:
                    return {
                        "code": code,
                        "name": row[0],
                        "native_name": row[1],
                        "provider_code": provider_code,
                        "service_id": service,
                        "response_success": True,
                        "quality_verified": False,
                        "attempts": attempts,
                    }
            except translation.TranslationFailure as exc:
                attempts.append(
                    {
                        "provider_code": provider_code,
                        "response_success": False,
                        "reason": exc.reason,
                    }
                )
        return {
            "code": code,
            "name": row[0],
            "native_name": row[1],
            "response_success": False,
            "quality_verified": False,
            "attempts": attempts,
        }

    results = []
    for code in dict.fromkeys(args.codes):
        result = check((code, CANDIDATES[code]))
        results.append(result)
        print(
            json.dumps(
                {"progress": result["code"], "response_success": result["response_success"]}
            ),
            flush=True,
        )
    print(
        json.dumps(
            {
                "mocked": False,
                "checked_at": datetime.now(UTC).isoformat(),
                "service_id": config.bhashini_translation_service_id,
                "discovery_available": translation.configuration_ready(config),
                "source_kind": "authored interface sentences; no archival/private text",
                "source_sentences": PROBE,
                "quality_notice": "Response success and changed text do not verify language or meaning.",
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
