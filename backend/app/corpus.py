"""Local, resumable ingestion. This operator CLI never verifies or publishes content."""

import argparse
import hashlib
import json
import os
import re
import shutil
from pathlib import Path
from typing import Annotated
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field, HttpUrl

from app.archive import admin, audit, staff
from app.config import Settings
from app.db import connect, migrate
from app.extraction import MAX_PIXELS, recognized
from app.processing import insert_segment
from app.recording_probe import inspect_recording

router = APIRouter(prefix="/archive/staff/corpus")
VERSION = "local-pages-v1"


def checksum(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


@router.get("")
def inventory(request: Request, user: Annotated[dict, Depends(staff)]):
    with connect(request.app.state.config) as db:
        return db.execute("""SELECT f.*,i.title,i.volume_number,i.part_number,
          i.review_status,i.access_level,i.current_text_revision,
          (SELECT count(*) FROM corpus_page p WHERE p.checksum=f.checksum
           AND p.status='extracted') AS extracted_pages,
          (SELECT count(*) FROM corpus_page p WHERE p.checksum=f.checksum
           AND p.status='ocr_pending') AS ocr_pending_pages,
          (SELECT count(*) FROM corpus_page p WHERE p.checksum=f.checksum
           AND p.status='failed') AS failed_pages,
          x.status AS index_status FROM corpus_file f
          LEFT JOIN archival_item i ON i.id=f.item_id
          LEFT JOIN search_index_state x ON x.item_id=i.id
          ORDER BY f.relative_path LIMIT 500""").fetchall()


@router.get("/{item_id}/pages")
def pages(
    item_id: UUID,
    request: Request,
    user: Annotated[dict, Depends(staff)],
    offset: int = Query(default=0, ge=0),
):
    with connect(request.app.state.config) as db:
        return db.execute(
            """SELECT p.* FROM corpus_page p JOIN corpus_file f USING(checksum)
          WHERE f.item_id=%s ORDER BY page_number LIMIT 25 OFFSET %s""",
            (item_id, offset),
        ).fetchall()


class SourceReview(BaseModel):
    source_locator: HttpUrl
    rights_statement: str = Field(min_length=10, max_length=1000)
    public_display_approved: bool = False
    volume_number: int | None = Field(default=None, ge=1, le=100)
    part_number: int | None = Field(default=None, ge=1)
    language: str = Field(default="Unknown", min_length=1, max_length=80)


@router.post("/{item_id}/source-review")
def review_source(
    item_id: UUID, data: SourceReview, request: Request, user: Annotated[dict, Depends(admin)]
):
    with connect(request.app.state.config) as db:
        item = db.execute(
            """SELECT i.* FROM archival_item i JOIN corpus_file f
            ON f.item_id=i.id WHERE i.id=%s FOR UPDATE OF i""",
            (item_id,),
        ).fetchone()
        if not item:
            raise HTTPException(404, "Local import not found")
        if item["review_status"] == "published":
            raise HTTPException(409, "Withdraw the record before changing its rights")
        db.execute(
            """UPDATE source SET verified_locator=%s,rights_notes=%s,
          verification_status='verified' WHERE id=%s""",
            (str(data.source_locator), data.rights_statement, item["source_id"]),
        )
        db.execute(
            """UPDATE archival_item SET source_record_locator=%s,rights_statement=%s,
          access_level=%s,review_status='uploaded',verified_by=NULL,verified_at=NULL WHERE id=%s""",
            (
                str(data.source_locator),
                data.rights_statement,
                "public" if data.public_display_approved else "staff",
                item_id,
            ),
        )
        audit(db, user["id"], "local_source_rights_reviewed", item_id)
        db.execute(
            """UPDATE archival_item SET volume_number=%s,part_number=%s,language=%s
                   WHERE id=%s""",
            (data.volume_number, data.part_number, data.language, item_id),
        )
    return {"status": "reviewed", "published": False}


def register(db, config, root, path, actor):
    digest = checksum(path)
    existing = db.execute("SELECT * FROM corpus_file WHERE checksum=%s", (digest,)).fetchone()
    if existing:
        return existing
    relative = path.relative_to(root).as_posix()
    suffix = path.suffix.lower()
    mime = {
        ".pdf": "application/pdf",
        ".mp3": "audio/mpeg",
        ".mp4": "video/mp4",
        ".wav": "audio/wav",
    }.get(suffix)
    if not mime:
        db.execute(
            "INSERT INTO corpus_file(checksum,relative_path,state) VALUES(%s,%s,'reference')",
            (digest, relative),
        )
        db.commit()
        return None
    details = {
        "method": VERSION,
        "relative_path": relative,
        "rights": "Not verified",
        "authenticity": "Not verified",
    }
    page_count = None
    if suffix == ".pdf":
        import pypdfium2 as pdfium

        with pdfium.PdfDocument(path) as pdf:
            page_count = len(pdf)
            # Store actual content evidence separately from filename-derived candidate mapping.
            evidence = []
            for number in range(min(8, len(pdf))):
                page = pdf[number]
                text = page.get_textpage()
                try:
                    evidence.append(text.get_text_range()[:3000])
                finally:
                    text.close()
                    page.close()
            details["opening_text_evidence"] = evidence
            details["mapping_status"] = "Filename candidate; content/edition review required"
    else:
        try:
            details.update(inspect_recording(path, mime))
            details["playback_status"] = "format validated; staff only"
        except ValueError as exc:
            details["playback_status"] = str(exc)
        details["transcript_status"] = "unavailable; no speech recognition model configured"
    item, asset, source = [
        uuid5(NAMESPACE_URL, f"local-corpus:{digest}:{role}")
        for role in ("item", "asset", "source")
    ]
    key = f"originals/{item}/{asset}"
    target = Path(config.archive_root) / key
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        temporary = target.with_suffix(".partial")
        with path.open("rb") as original, temporary.open("wb") as preserved:
            shutil.copyfileobj(original, preserved, 1024 * 1024)
            preserved.flush()
            os.fsync(preserved.fileno())
        temporary.replace(target)
    if checksum(target) != digest or checksum(path) != digest:
        raise ValueError("Original checksum changed during import")
    target.chmod(0o444)
    db.execute(
        """INSERT INTO source(id,name,verified_locator,rights_notes,verification_status)
        VALUES(%s,'Local dataset; provenance pending',%s,'Not verified','pending')""",
        (source, f"local-dataset:{relative}"),
    )
    match = re.fullmatch(r"Volume_(\d+)(?:_(\d+))?", path.stem)
    # Candidate numbers are deliberately not asserted as verified bibliographic metadata.
    if match:
        details["candidate_volume"] = int(match[1])
        details["candidate_part"] = int(match[2]) if match[2] else None
    db.execute(
        """INSERT INTO archival_item(id,source_id,source_record_locator,title,
        material_type,language,rights_statement,access_level,description)
        VALUES(%s,%s,%s,%s,%s,'Unknown','Not verified','staff',%s)""",
        (
            item,
            source,
            f"local-dataset:{relative}",
            path.stem,
            "document" if suffix == ".pdf" else "audio" if suffix in {".mp3", ".wav"} else "video",
            "Local dataset import. Filename title; provenance, edition and rights require review.",
        ),
    )
    db.execute(
        """INSERT INTO asset(id,item_id,role,storage_key,original_filename,mime_type,
        byte_size,checksum,processing_provenance) VALUES(%s,%s,'original',%s,%s,%s,%s,%s,%s)""",
        (asset, item, key, path.name, mime, path.stat().st_size, digest, Jsonb(details)),
    )
    row = db.execute(
        """INSERT INTO corpus_file(checksum,relative_path,item_id,page_count,metadata,state)
        VALUES(%s,%s,%s,%s,%s,%s) RETURNING *""",
        (
            digest,
            relative,
            item,
            page_count,
            Jsonb(details),
            "registered" if suffix == ".pdf" else "awaiting_review",
        ),
    ).fetchone()
    audit(db, actor, "local_dataset_imported_restricted", item)
    db.commit()
    return row


def pdf_pages(path, count, known, budget):
    import pypdfium2 as pdfium

    for start in range(0, count, 50):
        needed = [
            n
            for n in range(start + 1, min(start + 50, count) + 1)
            if n not in known or (budget > 0 and known[n]["status"] != "extracted")
        ]
        if not needed:
            continue
        with pdfium.PdfDocument(path) as pdf:
            for number in needed:
                yield number, pdf[number - 1]


def extract_pages(db, path, row, ocr_budget, page_budget=100):

    known = {
        p["page_number"]: p
        for p in db.execute(
            "SELECT page_number,status FROM corpus_page WHERE checksum=%s", (row["checksum"],)
        )
    }
    for number, page in pdf_pages(path, row["page_count"], known, ocr_budget):
        if page_budget <= 0:
            page.close()
            break
        previous = known.get(number)
        if previous and (previous["status"] == "extracted" or ocr_budget <= 0):
            page.close()
            continue
        status, result, error = "extracted", None, None
        try:
            textpage = page.get_textpage()
            try:
                text = textpage.get_text_range().strip()
            finally:
                textpage.close()
            result = dict(
                sequence=number,
                page_number=number,
                text=text,
                extraction_method="pdf_text",
                warning="Machine extraction; physical PDF page, not printed label",
            )
            if len(text) <= 30:
                status = "ocr_pending"
                if ocr_budget > 0:
                    width, height = page.get_size()
                    if width * height * 4 > MAX_PIXELS:
                        raise ValueError("Rendered page exceeds pixel limit")
                    ocr_budget -= 1
                    bitmap = page.render(scale=2)
                    try:
                        result = recognized(bitmap.to_pil().convert("RGB"), number)
                    finally:
                        bitmap.close()
                    status = "extracted"
            if len(result["text"]) > 100000 or "\x00" in result["text"]:
                raise ValueError("Extracted text exceeds limits or contains NUL")
        except Exception as exc:
            status, error = "failed", type(exc).__name__
        finally:
            page.close()
        db.execute(
            """INSERT INTO corpus_page(checksum,page_number,status,result,error,attempts)
            VALUES(%s,%s,%s,%s,%s,1) ON CONFLICT(checksum,page_number) DO UPDATE SET
            status=EXCLUDED.status,result=EXCLUDED.result,error=EXCLUDED.error,
            attempts=corpus_page.attempts+1,updated_at=now()""",
            (row["checksum"], number, status, Jsonb(result), error),
        )
        db.commit()  # A crash loses at most this page, never earlier completed work.
        page_budget -= 1
    return ocr_budget, page_budget


def finalize(db, row, actor):
    item = db.execute(
        "SELECT * FROM archival_item WHERE id=%s FOR UPDATE", (row["item_id"],)
    ).fetchone()
    if item["current_text_revision"] is not None:
        db.commit()
        return
    counts = db.execute(
        """SELECT count(*) AS n,count(*) FILTER(WHERE status<>'extracted') AS pending
        FROM corpus_page WHERE checksum=%s""",
        (row["checksum"],),
    ).fetchone()
    if counts["n"] != row["page_count"] or counts["pending"]:
        db.execute(
            "UPDATE corpus_file SET state='processing',updated_at=now() WHERE checksum=%s",
            (row["checksum"],),
        )
        db.commit()
        return
    asset = db.execute(
        "SELECT id FROM asset WHERE item_id=%s AND role='original'", (item["id"],)
    ).fetchone()
    job = uuid4()
    db.execute(
        """INSERT INTO processing_job
        (id,item_id,asset_id,job_type,input_revision,mode,status,requested_by)
        VALUES(%s,%s,%s,'extraction',1,'auto','succeeded',%s)""",
        (job, item["id"], asset["id"], actor),
    )
    db.execute(
        """INSERT INTO text_revision(item_id,revision,job_id,status,created_by,provenance)
        VALUES(%s,1,%s,'extracted',%s,%s)""",
        (item["id"], job, actor, Jsonb({"method": VERSION, "original_sha256": row["checksum"]})),
    )
    # Server cursor keeps even the 13,824-page compilation bounded in memory.
    with db.cursor(name="corpus_finalize") as cursor:
        cursor.execute(
            "SELECT result FROM corpus_page WHERE checksum=%s ORDER BY page_number",
            (row["checksum"],),
        )
        for page in cursor:
            insert_segment(db, item["id"], asset["id"], 1, page["result"])
    db.execute("UPDATE processing_job SET output_reference=1 WHERE id=%s", (job,))
    db.execute("UPDATE archival_item SET current_text_revision=1 WHERE id=%s", (item["id"],))
    db.execute(
        "UPDATE corpus_file SET state='awaiting_review',updated_at=now() WHERE checksum=%s",
        (row["checksum"],),
    )
    audit(db, actor, "local_extraction_completed_unverified", item["id"])
    db.commit()


def run(config, root, ocr_pages=0, volumes_only=False, max_pages=100, relative_path=None):
    if not 1 <= max_pages <= 1000 or not 0 <= ocr_pages <= 100:
        raise ValueError("Use 1–1000 checkpoint pages and 0–100 OCR pages per invocation")
    root = root.resolve(strict=True)
    with connect(config) as db:
        if not db.execute(
            "SELECT pg_try_advisory_lock(hashtext(current_schema()),261006) AS ok"
        ).fetchone()["ok"]:
            raise ValueError("Another corpus importer is running")
        actor = db.execute(
            "SELECT id FROM staff_user WHERE active AND role='admin' ORDER BY created_at LIMIT 1"
        ).fetchone()
        if not actor:
            raise ValueError("Create an administrator before local operator ingestion")
        actor = actor["id"]
        # Main volume files first. Nested compilation is retained independently, never relabelled.
        files = sorted(root.rglob("*"), key=lambda p: (len(p.relative_to(root).parts), str(p)))
        if relative_path:
            files = [p for p in files if p.relative_to(root).as_posix() == relative_path]
            if not files:
                raise ValueError("Requested dataset path was not found")
        if volumes_only:
            files = [
                p
                for p in files
                if p.parent == root and re.fullmatch(r"Volume_\d+(?:_\d+)?\.pdf", p.name)
            ]
        registered = []
        for path in files:
            if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root):
                continue
            row = register(db, config, root, path, actor)
            registered.append((path, row))
        for path, row in registered:
            if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root):
                continue
            try:
                if row and row["page_count"] and row["state"] != "awaiting_review":
                    if row["page_count"] > 5000:
                        print(
                            json.dumps(
                                {
                                    "file": row["relative_path"],
                                    "held": "Identity and scope review required",
                                }
                            ),
                            flush=True,
                        )
                        continue
                    ocr_pages, max_pages = extract_pages(db, path, row, ocr_pages, max_pages)
                    if checksum(path) != row["checksum"]:
                        raise ValueError("Dataset changed during extraction")
                    finalize(db, row, actor)
                print(
                    json.dumps(
                        {
                            "file": path.relative_to(root).as_posix(),
                            "checkpoint_pass_finished": True,
                            "remaining_page_budget": max_pages,
                        }
                    ),
                    flush=True,
                )
            except Exception as exc:
                db.rollback()
                print(
                    json.dumps(
                        {"file": path.relative_to(root).as_posix(), "error": type(exc).__name__}
                    ),
                    flush=True,
                )
        db.execute("SELECT pg_advisory_unlock(hashtext(current_schema()),261006)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--volumes-only", action="store_true")
    parser.add_argument("--file", help="Exact relative path; limits registration and extraction")
    parser.add_argument("--max-pages", type=int, default=100, choices=range(1, 1001))
    parser.add_argument("--ocr-pages", type=int, default=0, choices=range(0, 101), metavar="0..100")
    args = parser.parse_args()
    settings = Settings()
    migrate(settings)
    run(settings, args.root, args.ocr_pages, args.volumes_only, args.max_pages, args.file)
