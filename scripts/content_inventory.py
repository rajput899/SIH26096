"""Read-only per-file content audit. Run with Dataset and prior OCR outputs mounted read-only."""
import argparse
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pypdfium2 as pdfium
from PIL import Image

from app.config import Settings
from app.db import connect


def inventory(root, derivatives):
    observed_at = datetime.now(UTC).isoformat()
    config = Settings()
    with connect(config) as db:
        db.execute("SET TRANSACTION READ ONLY")
        records = db.execute("""
            SELECT i.id,i.title,i.material_type,i.language,i.review_status,i.access_level,
              i.volume_number,i.part_number,i.rights_statement,i.source_record_locator,
              i.current_text_revision,r.status AS text_status,s.name AS source_name,
              s.verification_status AS provenance_status,a.checksum,a.mime_type,
              x.status AS index_status,
              (SELECT count(*) FROM passage p WHERE p.item_id=i.id) AS passages,
              (SELECT count(*) FROM passage p JOIN passage_embedding e ON e.passage_id=p.id
               WHERE p.item_id=i.id) AS embeddings
            FROM archival_item i JOIN asset a ON a.item_id=i.id AND a.role='original'
            JOIN source s ON s.id=i.source_id
            LEFT JOIN text_revision r ON r.item_id=i.id AND r.revision=i.current_text_revision
            LEFT JOIN search_index_state x ON x.item_id=i.id ORDER BY i.title
        """).fetchall()
        corpus = db.execute("""
            SELECT f.checksum,f.relative_path,f.state,f.page_count,f.metadata,
              count(p.page_number) AS checkpointed,
              count(*) FILTER(WHERE p.status='extracted') AS extracted,
              count(*) FILTER(WHERE p.status='ocr_pending') AS ocr_pending,
              count(*) FILTER(WHERE p.status='failed') AS failed,
              count(*) FILTER(WHERE p.result->>'extraction_method'='rapidocr') AS ocr_processed,
              count(*) FILTER(WHERE p.status='extracted' AND trim(p.result->>'text')='') AS empty,
              count(*) FILTER(WHERE (p.result->>'confidence')::float<0.8) AS low_confidence,
              min((p.result->>'confidence')::float) AS minimum_confidence
            FROM corpus_file f LEFT JOIN corpus_page p USING(checksum)
            GROUP BY f.checksum ORDER BY f.relative_path
        """).fetchall()
        quality = db.execute("""
            SELECT f.relative_path,p.page_number,p.status,p.error,p.attempts,
              p.result->>'confidence' AS confidence,p.result->>'warning' AS warning
            FROM corpus_page p JOIN corpus_file f USING(checksum)
            WHERE p.status='failed' OR (p.status='extracted' AND trim(p.result->>'text')='')
              OR (p.result->>'confidence')::float<0.8
            ORDER BY f.relative_path,p.page_number
        """).fetchall()
    by_hash = {r["checksum"]: r for r in records}
    checkpoints = {r["checksum"]: r for r in corpus}
    files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        record = by_hash.get(digest)
        entry = {"path": path.relative_to(root).as_posix(), "sha256": digest,
                 "bytes": path.stat().st_size, "format": path.suffix.lower(),
                 "record": record, "corpus": checkpoints.get(digest),
                 "ingested": record is not None,
                 "public": bool(record and record["review_status"] == "published"
                                and record["access_level"] == "public")}
        if path.suffix.lower() == ".pdf":
            with pdfium.PdfDocument(path) as pdf:
                entry["physical_pages"] = len(pdf)
            if entry["physical_pages"] > 5000:
                entry["operator_hold"] = {
                    "status": "awaiting curator identity and scope verification",
                    "release_requires": [
                        "Reliable documentation establishing source, identity and edition",
                        "Curator assessment of relationship to the separate volume files",
                        "Explicit curator decision defining intended processing scope"],
                    "restriction": "No OCR, import, indexing, publication or modification",
                    "evidence_note": "Filename and apparent overlap are not identity evidence"}
        elif path.suffix.lower() in {".png", ".jpeg", ".jpg"}:
            with Image.open(path) as img:
                entry["image_size"] = img.size
                img.verify()
            derivative = derivatives / f"{digest}.json"
            if derivative.exists():
                data = json.loads(derivative.read_text(encoding="utf-8-sig"))
                if data["sha256"] == digest:
                    pages = data["extraction"]["pages"]
                    confidence = [p["confidence"] for p in pages
                                  if p.get("confidence") is not None]
                    entry["private_image_ocr"] = {
                        "hash_matched": True, "review": data["review"],
                        "pages": len(pages),
                        "minimum_confidence": min(confidence) if confidence else None,
                        "warnings": [p["warning"] for p in pages if p.get("warning")],
                        "has_text": any(p.get("text", "").strip() for p in pages)}
        files.append(entry)
    with httpx.Client(base_url="http://backend:8000/archive/", timeout=30) as client:
        published = client.get("catalog").raise_for_status().json()
        media = client.get("recordings").raise_for_status().json()
        activities = {kind: client.get("learning", params={"kind": kind}).raise_for_status().json()
                      for kind in ["timeline", "story", "quiz"]}
    expected = {str(r["id"]) for r in records
                if r["review_status"] == "published" and r["access_level"] == "public"}
    return {"observed_at": observed_at,
            "files": files, "records": records, "page_quality_issues": quality,
            "summary": {"files": len(files), "formats": dict(Counter(f["format"] for f in files)),
                        "physical_pdf_pages": sum(f.get("physical_pages", 0) for f in files),
                        "dataset_ingested_files": sum(f["ingested"] for f in files),
                        "registered_material_types": dict(Counter(
                            r["material_type"] for r in records)),
                        "public_records": len(published), "public_recordings": len(media),
                        "public_activities": {k: len(v) for k, v in activities.items()},
                        "public_catalog_matches_database": (
                            expected == {r["id"] for r in published})},
            "classification_note": (
                "File formats are exact. Letter/photograph/speech identities and "
                "volume editions require curator review; folder names are candidates.")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("derivatives", type=Path)
    args = parser.parse_args()
    print(json.dumps(inventory(args.root, args.derivatives), indent=2, default=str))
