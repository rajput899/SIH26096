"""Operator-only frozen dataset release. No HTTP grant endpoint or implicit future grants."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from psycopg.types.json import Jsonb

from app.archive import audit
from app.config import Settings
from app.corpus import checksum
from app.db import connect


def manifest_hash(manifest):
    return hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()


def release(config, root, manifest, login, apply=False):
    root = root.resolve(strict=True)
    expected = {entry["path"] for entry in manifest["files"]}
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    if actual != expected or len(expected) != len(manifest["files"]):
        raise ValueError("Dataset file set differs from frozen manifest")
    if len({entry["sha256"] for entry in manifest["files"]}) != len(expected):
        raise ValueError("Duplicate hashes require explicit reconciliation before release")
    # Validate ALL inputs before making any database/storage changes.
    for entry in manifest["files"]:
        path = root / entry["path"]
        if (
            path.is_symlink()
            or not path.resolve().is_relative_to(root)
            or checksum(path) != entry["sha256"]
            or path.stat().st_size != entry["bytes"]
        ):
            raise ValueError("Dataset path, size or checksum differs from frozen manifest")
    report = []
    with connect(config) as db:
        db.execute("SELECT pg_advisory_xact_lock(hashtext(current_schema()),261010)")
        actor = db.execute(
            "SELECT id FROM staff_user WHERE login=%s AND active AND role='admin'", (login,)
        ).fetchone()
        if not actor:
            raise ValueError("Active administrator required")
        prior = db.execute(
            "SELECT * FROM dataset_release WHERE id=%s", (manifest["id"],)
        ).fetchone()
        digest = manifest_hash(manifest)
        if prior and prior["manifest_sha256"] != digest:
            raise ValueError("Release manifest is immutable; do not replace its file set")
        if apply and not prior:
            db.execute(
                "INSERT INTO dataset_release(id,manifest_sha256,authorization_note,"
                "manifest,authorized_by) "
                "VALUES(%s,%s,%s,%s,%s)",
                (manifest["id"], digest, manifest["authorization"], Jsonb(manifest), actor["id"]),
            )
        for entry in manifest["files"]:
            rows = db.execute(
                "SELECT i.*,a.storage_key,a.checksum,a.byte_size FROM archival_item i "
                "JOIN asset a ON a.item_id=i.id AND a.role='original' WHERE a.checksum=%s",
                (entry["sha256"],),
            ).fetchall()
            if len(rows) > 1:
                raise ValueError("Ambiguous duplicate originals; resolve without merging records")
            row = rows[0] if rows else None
            exclusion = entry.get("exclusion", "")
            if row:
                stored = Path(config.archive_root) / row["storage_key"]
                if checksum(stored) != entry["sha256"]:
                    raise ValueError("Stored original integrity failure")
                withdrawn = db.execute(
                    "SELECT 1 FROM audit_event WHERE target_id=%s AND action='withdrawn' LIMIT 1",
                    (row["id"],),
                ).fetchone()
                if row["review_status"] == "withdrawn" or withdrawn:
                    exclusion = "Explicit withdrawal history; requires separate curator resolution"
                if (
                    prior
                    and row["dataset_release_id"] == manifest["id"]
                    and (row["review_status"] != "published" or row["access_level"] != "public")
                ):
                    exclusion = (
                        "Previously released record was subsequently restricted; not republished"
                    )
            item = (
                row["id"] if row else uuid5(NAMESPACE_URL, f"local-corpus:{entry['sha256']}:item")
            )
            report.append(
                {
                    "path": entry["path"],
                    "sha256": entry["sha256"],
                    "id": str(item),
                    "new": row is None,
                    "exclusion": exclusion,
                    "collection": entry["collection"],
                    "applied": apply,
                }
            )
            if not apply:
                continue
            if not row:
                # Existing corpus import handles PDFs/media. New image/text originals use the
                # same immutable storage/schema without fabricated provenance or extraction.
                source = uuid5(NAMESPACE_URL, f"local-corpus:{entry['sha256']}:source")
                asset = uuid5(NAMESPACE_URL, f"local-corpus:{entry['sha256']}:asset")
                key = f"originals/{item}/{asset}"
                target = Path(config.archive_root) / key
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    with (root / entry["path"]).open("rb") as src, target.open("xb") as dst:
                        shutil.copyfileobj(src, dst)
                if checksum(target) != entry["sha256"]:
                    raise ValueError("Preserved original integrity failure")
                target.chmod(0o444)
                name = Path(entry["path"]).name
                db.execute(
                    "INSERT INTO source(id,name,verified_locator,rights_notes,verification_status) "
                    "VALUES(%s,'Organizer dataset; historical provenance unverified',%s,"
                    "'Individual rights unverified; see separate prototype dataset authorization',"
                    "'pending')",
                    (source, "local-dataset:" + entry["path"]),
                )
                db.execute(
                    "INSERT INTO archival_item(id,source_id,source_record_locator,"
                    "title,material_type,"
                    "language,description,rights_statement,access_level) "
                    "VALUES(%s,%s,%s,%s,%s,'Unknown',%s,'Not verified','staff')",
                    (
                        item,
                        source,
                        "local-dataset:" + entry["path"],
                        name,
                        "image" if entry["mime"].startswith("image/") else "document",
                        "Supplied filename label. Identity, authorship, date and historical "
                        "provenance are unverified. Collection follows supplied organization, "
                        "not authentication.",
                    ),
                )
                db.execute(
                    "INSERT INTO asset(id,item_id,role,storage_key,original_filename,mime_type,"
                    "byte_size,checksum,processing_provenance) "
                    "VALUES(%s,%s,'original',%s,%s,%s,%s,%s,%s)",
                    (
                        asset,
                        item,
                        key,
                        name,
                        entry["mime"],
                        entry["bytes"],
                        entry["sha256"],
                        Jsonb(
                            {
                                "method": "organizer-dataset-original-v1",
                                "relative_path": entry["path"],
                            }
                        ),
                    ),
                )
                db.execute(
                    "INSERT INTO corpus_file(checksum,relative_path,item_id,state,metadata) "
                    "VALUES(%s,%s,%s,'awaiting_review',%s) ON CONFLICT(checksum) DO UPDATE "
                    "SET item_id=EXCLUDED.item_id WHERE corpus_file.item_id IS NULL",
                    (
                        entry["sha256"],
                        entry["path"],
                        item,
                        Jsonb(
                            {"identity": "unverified", "text_review": "unverified; no reprocessing"}
                        ),
                    ),
                )
                audit(db, actor["id"], "dataset_original_registered", item)
            db.execute(
                "INSERT INTO dataset_member(release_id,relative_path,checksum,byte_size,item_id,"
                "collection,exclusion) VALUES(%s,%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT(release_id,relative_path) DO NOTHING",
                (
                    manifest["id"],
                    entry["path"],
                    entry["sha256"],
                    entry["bytes"],
                    item,
                    entry["collection"],
                    exclusion,
                ),
            )
            if exclusion:
                continue
            if row and row["review_status"] == "published" and row["access_level"] == "public":
                continue
            db.execute(
                "UPDATE archival_item SET dataset_release_id=%s,review_status='published',"
                "access_level='public',updated_at=now() WHERE id=%s",
                (manifest["id"], item),
            )
            # No verified_by/verified_at, source status, OCR or transcript approval is changed.
            audit(db, actor["id"], "organizer_dataset_published", item)
    return {"release": manifest["id"], "manifest_sha256": digest, "apply": apply, "files": report}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--admin-login", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    result = release(
        Settings(),
        args.root,
        json.loads(args.manifest.read_text(encoding="utf-8-sig")),
        args.admin_login,
        args.apply,
    )
    print(json.dumps(result, indent=2, default=str))
