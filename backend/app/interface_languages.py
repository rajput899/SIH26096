"""Configured-service allowlist; evidence and review limits: MULTILINGUAL_VALIDATION.md.

Two authored sentences were checked live and reviewed for language/meaning by Codex.
This is bounded sample acceptance, NOT expert or full-catalog linguistic certification.
Never populate this list from changed text, provider success, or model metadata alone.
"""

SERVICE = "bhashini/iiith/nmt-all"
LANGUAGES = {
    "hi": ("Hindi", "हिन्दी"),
    "bn": ("Bengali", "বাংলা"),
    "gu": ("Gujarati", "ગુજરાતી"),
    "kn": ("Kannada", "ಕನ್ನಡ"),
    "ml": ("Malayalam", "മലയാളം"),
    "mr": ("Marathi", "मराठी"),
    "ne": ("Nepali", "नेपाली"),
    "or": ("Odia", "ଓଡ଼ିଆ"),
    "pa": ("Punjabi", "ਪੰਜਾਬੀ"),
    "ta": ("Tamil", "தமிழ்"),
    "te": ("Telugu", "తెలుగు"),
}
PAIRS = frozenset(("en", code) for code in LANGUAGES)
