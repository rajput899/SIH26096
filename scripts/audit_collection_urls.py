"""Read-only public HTTP audit; never logs source text or staff credentials."""
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def request(path):
    try:
        with urllib.request.urlopen("http://127.0.0.1:3002" + path, timeout=25) as response:
            return response.status, response.read(), response.headers
    except urllib.error.HTTPError as error:
        return error.code, error.read(), error.headers


inventory = json.loads(Path("outputs/collections-inventory.json").read_text(encoding="utf-8-sig"))
checks = []
for row in inventory["records"]:
    if row["review_status"] == "published" and row["access_level"] == "public":
        continue
    item = row["id"]
    for path in [f"catalog/{item}", *[f"documents/{item}/{suffix}" for suffix in
                ("original", "thumbnail", "playback", "recording")],
                 f"staff/documents/{item}/original", f"staff/documents/{item}/text",
                 f"corpus/{item}/pages"]:
        status, _, headers = request("/api/archive/" + path)
        checks.append({"path": path, "status": status})
        assert status in (401, 404), (path, status)
        assert headers.get("Cache-Control") == "no-store"

static_paths = ["/outputs/dataset-image-review/inventory.json",
                "/outputs/collections-inventory.json"]
for entry in inventory["files"]:
    static_paths.append("/Dataset/" + urllib.parse.quote(entry["path"], safe="/"))
    if entry.get("private_image_ocr"):
        static_paths.append(f"/outputs/dataset-image-review/{entry['sha256']}.json")
for path in static_paths:
    status, _, _ = request(path)
    checks.append({"path": path, "status": status})
    assert status == 404, (path, status)

groups = {}
for origin in ("dataset", "other"):
    status, body, _ = request("/api/archive/catalog?origin=" + origin)
    assert status == 200
    groups[origin] = [row["id"] for row in json.loads(body)]
assert not set(groups["dataset"]) & set(groups["other"])
assert len(groups["other"]) == inventory["summary"]["public_records"]
assert groups["dataset"] == []

report = {"restricted_and_static_url_checks": checks, "public_groups": groups}
Path("outputs/collections-url-audit.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)
print(f"PASS: {len(checks)} direct/proxy/static URL denials; public groups are disjoint.")
