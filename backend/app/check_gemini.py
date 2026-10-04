"""Explicit owner-run live acceptance; never collected by pytest or invoked automatically."""

import argparse
import json

from app.config import Settings
from app.research import Question, answer_question


def main():
    parser = argparse.ArgumentParser(description="Send one grounded question to configured Gemini")
    parser.add_argument(
        "--live", action="store_true", help="Explicit consent to a live provider call"
    )
    parser.add_argument(
        "--question", required=True, help="Question about published verified material"
    )
    args = parser.parse_args()
    if not args.live:
        parser.error("Use --live only when you intend to send the question and public excerpts")
    config = Settings()
    if config.ai_provider != "gemini":
        parser.error("Set AI_PROVIDER=gemini on the backend first")
    try:
        result = answer_question(config, Question(question=args.question))
    except Exception:
        print(
            "FAIL: Check database, published verified sources and backend provider configuration."
        )
        raise SystemExit(1) from None
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    if result["status"] != "answered":
        print("NOT PASSED: No validated live Gemini answer was produced.")
        raise SystemExit(1)
    print(
        "PASS: Live Gemini response with validated archive citations. "
        "Review factual support manually."
    )


if __name__ == "__main__":
    main()
