"""Read-only production preservation and retrieval-eligibility audit; no secrets printed."""
import hashlib
import json
from pathlib import Path

import httpx

from app.config import Settings
from app.db import connect
from app.research_index import ELIGIBLE, collection_url

config = Settings()
with connect(config) as db:
    db.execute("SET TRANSACTION READ ONLY")
    originals = db.execute(
        "SELECT i.id,i.review_status,i.access_level,a.storage_key,a.checksum "
        "FROM archival_item i JOIN asset a ON a.item_id=i.id WHERE a.role='original'"
    ).fetchall()
    for row in originals:
        path = Path(config.archive_root) / row["storage_key"]
        with path.open("rb") as stream:
            row["checksum_matches"] = hashlib.file_digest(stream, "sha256").hexdigest() == row["checksum"]
    eligible = db.execute(
        "SELECT i.id,i.title,i.current_text_revision FROM archival_item i JOIN text_revision r "
        "ON r.item_id=i.id AND r.revision=i.current_text_revision WHERE " + ELIGIBLE
    ).fetchall()
    pages = db.execute(
        "SELECT status,count(*) FROM corpus_page GROUP BY status ORDER BY status"
    ).fetchall()
    revisions = db.execute(
        "SELECT status,count(*) FROM text_revision GROUP BY status ORDER BY status"
    ).fetchall()
    jobs = db.execute(
        "SELECT status,count(*) FROM processing_job GROUP BY status ORDER BY status"
    ).fetchall()
    passages = db.execute("SELECT id,item_id,revision FROM passage ORDER BY id").fetchall()
with httpx.Client(timeout=20, trust_env=False) as client:
    result = client.post(collection_url(config) + "/points/scroll", json={
        "limit": 1000, "with_payload": True, "with_vector": False
    })
    result.raise_for_status()
    vectors = result.json()["result"]
    points = vectors["points"]
    public_ids = {str(row["id"]) for row in eligible}
    restricted = [row for row in originals if str(row["id"]) not in public_ids]
    denials = []
    for row in restricted:
        for suffix in [f"catalog/{row['id']}", f"documents/{row['id']}/original",
                       f"documents/{row['id']}/playback", f"staff/documents/{row['id']}/text"]:
            response = client.get("http://127.0.0.1:8000/archive/" + suffix)
            denials.append({"path": suffix, "status": response.status_code})
    report = {"originals": originals, "eligible": eligible, "pages": pages,
              "revisions": revisions, "jobs": jobs, "passages": passages,
              "vector_ids": [str(p["id"]) for p in points],
              "vector_scan_complete": vectors.get("next_page_offset") is None,
              "vector_ids_match_passages": {str(p["id"]) for p in points}
              == {str(p["id"]) for p in passages}, "restricted_denials": denials}
    print(json.dumps(report, default=str, indent=2))
