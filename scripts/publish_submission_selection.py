"""Publish two reviewed PIB excerpts through authenticated staff APIs only.

Run from the project root with a local JSON credential-file path. Secrets are never
logged. This script does not access the database, override auth, or touch Dataset.
Source pages and their reuse policy must first be captured and reviewed.
"""
import argparse
import getpass
import hashlib
import json
import sys
import time
from pathlib import Path

import httpx

from prepare_submission_quiz import prepare

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("credentials", type=Path, nargs="?", help="Optional existing credential JSON; omit for private interactive prompts")
args = parser.parse_args()
if args.credentials:
    auth = json.loads(args.credentials.read_text(encoding="utf-8-sig"))
else:
    if not sys.stdin.isatty():
        raise SystemExit("Run in an interactive terminal for hidden password entry, or supply an existing local credential JSON path")
    auth = {"login": input("Existing staff login: ").strip(),
            "password": getpass.getpass("Existing staff password (hidden): ")}
root = Path("outputs/submission-sources")
locators = json.loads((root / "locators.json").read_text())
policy = locators["rights"]["url"]
rights = (
    "PIB copyright policy permits accurate, attributed reproduction without prior approval; "
    "third-party material excluded. This selection contains only government release text, "
    "no photographs or third-party quotations. Policy checked 2026-09-30: " + policy
)
specs = [
    ("constitution", "Ambedkar and the Constitution — PIB lecture excerpt (2017)",
     "President's Secretariat / Press Information Bureau, Government of India",
     "Exact paragraph 42 from President Pranab Mukherjee's 15 May 2017 lecture, "
     "History of Parliamentary Democracy in India. A modern government account, "
     "not an original Ambedkar speech or a 1949 manuscript. Unpaginated text excerpt; "
     "the complete official release is linked as the source."),
    ("biography", "Ambedkar's birth — PIB biographical excerpt (2024)",
     "Ministry of Social Justice & Empowerment / Press Information Bureau",
     "Exact opening biographical bullet from The journey of Baba Saheb Ambedkar – "
     "Life, History & Works, PIB, 13 April 2024. A modern government biographical "
     "account, not a birth certificate. Unpaginated text excerpt; the complete "
     "official release is linked as the source."),
]
manifest_path = root / "published-selection.json"
manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {"records": [], "activities": []}


def save():
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


with httpx.Client(base_url="http://127.0.0.1:8000/archive/", auth=(auth["login"], auth["password"]),
                  timeout=30, trust_env=False) as client:
    def call(method, path, **kwargs):
        response = client.request(method, path, **kwargs)
        if not response.is_success:
            raise RuntimeError(f"Staff workflow stopped: {method} {path.split('?')[0]} HTTP {response.status_code}")
        return response.json()

    assert call("GET", "staff/me")["role"] == "admin", "Existing admin authorization required for upload"
    for key, title, source_name, description in specs:
        content = (root / f"{key}-excerpt.txt").read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        # Reuse only an exact previous upload of this reviewed excerpt, never a dataset record.
        existing = next((r for r in call("GET", "staff/documents", params={"limit": 200})
                         if r["title"] == title and r["checksum"] == digest
                         and r["source_record_locator"] == locators[key]["url"]), None)
        if existing:
            item = existing["id"]
        else:
            metadata = dict(title=title, source_name=source_name, source_locator=locators[key]["url"],
                            source_record_locator=locators[key]["url"], rights_statement=rights,
                            provenance_confirmed=True, material_type="document", language="English",
                            description=description, access_level="public", original_filename=f"pib-{key}-excerpt.txt")
            item = call("POST", "staff/documents", params={"metadata": json.dumps(metadata)},
                        headers={"Content-Type": "text/plain"}, content=content)["id"]
        base = f"staff/documents/{item}"
        snapshot = call("GET", base + "/text")
        if not snapshot["snapshot"]:
            call("POST", base + "/processing", json={"mode": "auto"})
            for _ in range(45):
                snapshot = call("GET", base + "/text")
                if snapshot["snapshot"]:
                    break
                time.sleep(2)
        assert len(snapshot["segments"]) == 1, "Expected one unpaginated text segment"
        assert snapshot["segments"][0]["text"].strip() == content.decode("utf-8").strip(), "Extraction differs from reviewed source"
        revision = snapshot["snapshot"]["revision"]
        if snapshot["snapshot"]["status"] == "extracted":
            reviewed = call("POST", base + "/text/revisions", json={
                "base_revision": revision,
                "pages": [{"sequence": s["sequence"], "text": s["text"]} for s in snapshot["segments"]],
                "note": "Compared exact excerpt against captured official PIB release and preserved UTF-8 original; no historical wording added. Reuse policy and government attribution checked 2026-09-30.",
            })
            revision = reviewed["revision"]
        if snapshot["snapshot"]["status"] != "verified":
            call("POST", base + "/text/verify", json={"revision": revision, "original_compared": True})
        current = next(r for r in call("GET", "staff/documents", params={"limit": 200}) if r["id"] == item)
        if current["review_status"] in ["uploaded", "withdrawn"]:
            call("POST", base + "/transition", json={"action": "verify", "metadata_reviewed": True})
        if current["review_status"] != "published":
            call("POST", base + "/transition", json={"action": "publish"})
        record = dict(key=key, id=item, title=title, revision=revision, sha256=digest,
                      source_url=locators[key]["url"], rights_url=policy)
        manifest["records"] = [r for r in manifest["records"] if r["key"] != key] + [record]
        save()
        print("Published reviewed PIB excerpt:", title)

    records = {r["key"]: r for r in manifest["records"]}
    constitution = dict(item_id=records["constitution"]["id"], revision=records["constitution"]["revision"],
                        quote=(root / "constitution-excerpt.txt").read_text(encoding="utf-8").strip())
    biography = dict(item_id=records["biography"]["id"], revision=records["biography"]["revision"],
                     quote="Baba Saheb Dr. Bhim Rao Ambedkar was born on 14 April 1891")
    activities = [
        dict(kind="timeline", title="Birth of B. R. Ambedkar", date_label="1891-04-14", topic="Life and Constitution",
             description="PIB's 2024 biographical account records Ambedkar's birth on 14 April 1891. This entry cites that modern account, not a contemporary birth record.", sources=[biography]),
        dict(kind="timeline", title="Constitution adopted", date_label="1949-11-26", topic="Life and Constitution",
             description="The 2017 President's Secretariat lecture records the adoption of the Constitution on 26 November 1949. Its paragraph 42 identifies Ambedkar as Chairman of the Drafting Committee.", sources=[constitution]),
        dict(kind="timeline", title="Constitution comes into force", date_label="1950-01-26", topic="Life and Constitution",
             description="Paragraph 42 of the 2017 lecture states that the Constitution came into force on 26 January 1950. Adoption and commencement are distinct dates.",
             sources=[{**constitution, "quote": "The Constitution which came into force on 26 January 1950"}]),
        dict(kind="story", title="From drafting to commencement", topic="Life and Constitution",
             description="The President's Secretariat account identifies Dr. B. R. Ambedkar as Chairman of the Drafting Committee and Dr. Rajendra Prasad as President of the Constituent Assembly.\n\nIt distinguishes adoption on 26 November 1949, members' signatures on 24 January 1950, and commencement on 26 January 1950. Read the linked paragraph to compare these milestones. This is a curator-written reading guide to a 2017 government account, not a quotation from Ambedkar.", sources=[constitution]),
        dict(kind="quiz", title="Read the sources: Ambedkar and the Constitution", topic="Life and Constitution",
             description="Ten source-supported questions combining factual recall and comparison of constitutional milestones. Read the two attributed PIB excerpts before answering.", sources=[constitution, biography], questions=prepare()["questions"]),
    ]
    for activity in activities:
        old = next((a for a in call("GET", "staff/learning") if a["title"] == activity["title"]), None)
        if old:
            id_, state = old["id"], old["status"]
        else:
            draft = call("POST", "staff/learning", json=activity)
            id_, state = draft["id"], "draft"
        if state in ["draft", "withdrawn"]:
            call("POST", f"staff/learning/{id_}/transition", json={"action": "verify", "evidence_reviewed": True})
        if state != "published":
            call("POST", f"staff/learning/{id_}/transition", json={"action": "publish"})
        manifest["activities"] = [a for a in manifest["activities"] if a["id"] != id_]
        manifest["activities"].append({"id": id_, "kind": activity["kind"], "title": activity["title"]})
        save()
        print("Published source-backed", activity["kind"], activity["title"])
