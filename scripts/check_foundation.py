"""Probe the real foundation; fail if any required service is unavailable."""

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frontend-url", default="http://127.0.0.1:3000")
    parser.add_argument("--backend-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    opener = build_opener(ProxyHandler({}))
    checks = [
        ("frontend", args.frontend_url, None),
        ("backend liveness", f"{args.backend_url}/health/live", "ok"),
        ("backend dependency readiness", f"{args.backend_url}/health/ready", "ready"),
        ("frontend/backend connection", f"{args.frontend_url}/api/health", "ready"),
    ]
    failed = False
    for name, url, expected in checks:
        try:
            with opener.open(Request(url), timeout=15) as response:
                body = response.read().decode("utf-8")
                if expected is not None:
                    data = json.loads(body)
                    if data.get("status") != expected:
                        raise ValueError("Unexpected health status")
                    if expected == "ready":
                        for service in ("postgres", "qdrant", "ollama"):
                            if data["checks"][service]["status"] != "ok":
                                raise ValueError(f"{service} is not connected")
                elif "Local foundation" not in body:
                    raise ValueError("Unexpected frontend page")
            print(f"PASS: {name}")
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError) as exc:
            print(f"FAIL: {name} ({type(exc).__name__})")
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
