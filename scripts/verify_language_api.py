"""Live localhost rejection checks; no eligible content translation is requested."""
import json
import urllib.error
import urllib.request
from pathlib import Path

base = "http://localhost:3000/api/archive/"
catalog = json.loads(Path("frontend/src/interface-strings.json").read_text("utf-8"))
key = next(iter(catalog))
checks = []


def rejected(path, body, expected):
    req = urllib.request.Request(base + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            status = response.status
    except urllib.error.HTTPError as exc:
        status = exc.code
    assert status == expected, (path, status, expected)
    checks.append({"path": path, "status": status})


for body in [
    {"keys": ["unregistered private input"], "target_language": "hi"},
    {"keys": [key], "target_language": "hi", "text": "unregistered private input"},
    {"keys": [key], "target_language": "mr"},
    {"keys": [], "target_language": "hi"},
    {"keys": [key] * 31, "target_language": "hi"},
]:
    rejected("interface/translations", body, 422)
checkpoint = json.loads(Path("outputs/dataset-release-checkpoint-verified.json").read_text("utf-8-sig"))
public_unreviewed = next(row["id"] for row in checkpoint["files"] if not row["exclusion"])
for item in [public_unreviewed, "c5926726-5d27-4990-a08f-76a932fa57db",
             "509f9e25-2112-4737-887b-f5ce3202f17e"]:
    rejected(f"documents/{item}/translation",
             {"revision": 1, "sequence": 1, "target_language": "hi"}, 404)
rejected("documents/8ce2df4c-c4e2-4ed1-bf9e-244881273e82/translation",
         {"revision": 999, "sequence": 1, "target_language": "hi"}, 409)
print(json.dumps({"mocked": False, "eligible_translation_requested": False,
                  "checks": checks, "success": True}, indent=2))
