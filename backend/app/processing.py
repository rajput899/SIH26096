"""Durable extraction requests and append-only curator text snapshots."""

import json
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from app.archive import audit, staff
from app.db import connect

router = APIRouter(prefix="/archive/staff/documents")
Staff = Annotated[dict, Depends(staff)]


def item_lock(db, item_id):
    item = db.execute("SELECT * FROM archival_item WHERE id=%s FOR UPDATE", (item_id,)).fetchone()
    if not item:
        raise HTTPException(404, "Document not found")
    return item


def invalidate_publication(db, item_id):
    # A changed text snapshot always requires a fresh, explicit publication decision.
    db.execute(
        """UPDATE archival_item SET review_status='uploaded', verified_by=NULL,
        verified_at=NULL, updated_at=now() WHERE id=%s""",
        (item_id,),
    )


class ExtractionRequest(BaseModel):
    mode: Literal["auto", "ocr"] = "auto"


@router.post("/{item_id}/processing", status_code=202)
def queue(item_id: UUID, data: ExtractionRequest, request: Request, user: Staff):
    with connect(request.app.state.config) as db:
        item_lock(db, item_id)
        existing = db.execute(
            "SELECT * FROM processing_job WHERE item_id=%s", (item_id,)
        ).fetchone()
        if existing:
            if existing["mode"] != data.mode:
                raise HTTPException(409, "A job already exists with a different extraction mode")
            return existing
        if db.execute("SELECT 1 FROM corpus_file WHERE item_id=%s", (item_id,)).fetchone():
            raise HTTPException(
                409, "Resume this large local import with the corpus operator command"
            )
        asset = db.execute(
            "SELECT * FROM asset WHERE item_id=%s AND role='original'", (item_id,)
        ).fetchone()
        if asset["mime_type"].startswith(("audio/", "video/")):
            raise HTTPException(415, "Recordings use curator transcripts, not OCR")
        if data.mode == "ocr" and asset["mime_type"] == "text/plain":
            raise HTTPException(422, "OCR requires a PDF or image original")
        job = db.execute(
            """INSERT INTO processing_job
            (id,item_id,asset_id,job_type,input_revision,mode,status,requested_by)
            VALUES (%s,%s,%s,'extraction',1,%s,'queued',%s) RETURNING *""",
            (uuid4(), item_id, asset["id"], data.mode, user["id"]),
        ).fetchone()
        invalidate_publication(db, item_id)
        audit(db, user["id"], "extraction_queued", item_id)
        return job


@router.get("/{item_id}/processing")
def job_status(item_id: UUID, request: Request, user: Staff):
    with connect(request.app.state.config) as db:
        item_lock(db, item_id)
        return db.execute("SELECT * FROM processing_job WHERE item_id=%s", (item_id,)).fetchone()


@router.post("/{item_id}/processing/retry", status_code=202)
def retry(item_id: UUID, request: Request, user: Staff):
    with connect(request.app.state.config) as db:
        item_lock(db, item_id)
        job = db.execute(
            """UPDATE processing_job SET status='queued', error=NULL,
            claim_token=NULL, updated_at=now() WHERE item_id=%s AND status='failed'
            AND attempts<3 RETURNING *""",
            (item_id,),
        ).fetchone()
        if not job:
            raise HTTPException(409, "Only failed jobs below the three-attempt limit can retry")
        audit(db, user["id"], "extraction_retry", item_id)
        return job


@router.get("/{item_id}/text")
def read_text(
    item_id: UUID,
    request: Request,
    user: Staff,
    revision: int | None = None,
    offset: int = Query(default=0, ge=0),
):
    with connect(request.app.state.config) as db:
        item = item_lock(db, item_id)
        revisions = db.execute(
            "SELECT * FROM text_revision WHERE item_id=%s ORDER BY revision DESC", (item_id,)
        ).fetchall()
        selected = revision if revision is not None else item["current_text_revision"]
        snapshot = next((row for row in revisions if row["revision"] == selected), None)
        if revision is not None and snapshot is None:
            raise HTTPException(404, "Text revision not found")
        segments = db.execute(
            "SELECT * FROM text_segment WHERE item_id=%s AND revision=%s ORDER BY sequence "
            "LIMIT 50 OFFSET %s",
            (item_id, selected, offset),
        ).fetchall()
        return {
            "current_revision": item["current_text_revision"],
            "revisions": revisions,
            "snapshot": snapshot,
            "segments": segments,
            "total_segments": db.execute(
                "SELECT count(*) n FROM text_segment WHERE item_id=%s AND revision=%s",
                (item_id, selected),
            ).fetchone()["n"],
        }


class PageCorrection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sequence: int = Field(ge=1)
    text: str = Field(max_length=100000)


class Review(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_revision: int = Field(ge=1)
    pages: list[PageCorrection] = Field(min_length=1, max_length=50)
    note: str = Field(min_length=1, max_length=1000)
    partial: bool = False


@router.post("/{item_id}/text/revisions", status_code=201)
def correct(item_id: UUID, data: Review, request: Request, user: Staff):
    with connect(request.app.state.config) as db:
        item = item_lock(db, item_id)
        if item["current_text_revision"] != data.base_revision:
            raise HTTPException(409, "Text changed; reload the current revision before saving")
        old = db.execute(
            "SELECT * FROM text_revision WHERE item_id=%s AND revision=%s",
            (item_id, data.base_revision),
        ).fetchone()
        if old["recording_revision"] is not None:
            raise HTTPException(415, "Use recording transcript review to preserve cue timestamps")
        segments = db.execute(
            "SELECT * FROM text_segment WHERE item_id=%s AND revision=%s ORDER BY sequence",
            (item_id, data.base_revision),
        ).fetchall()
        requested = [p.sequence for p in data.pages]
        valid_subset = len(set(requested)) == len(requested) and set(requested).issubset(
            {s["sequence"] for s in segments}
        )
        if not valid_subset or (
            not data.partial and sorted(requested) != [s["sequence"] for s in segments]
        ):
            raise HTTPException(
                422, "Supply each existing page exactly once; locators cannot change"
            )
        if not any(p.text.strip() for p in data.pages):
            raise HTTPException(422, "Cannot review an entirely empty transcription")
        revision = data.base_revision + 1
        db.execute(
            """INSERT INTO text_revision
            (item_id,revision,parent_revision,job_id,status,created_by,review_note,provenance)
            VALUES (%s,%s,%s,%s,'reviewed',%s,%s,%s)""",
            (
                item_id,
                revision,
                data.base_revision,
                old["job_id"],
                user["id"],
                data.note,
                json.dumps({"method": "curator_review", "source_revision": data.base_revision}),
            ),
        )
        corrected = {p.sequence: p.text for p in data.pages}
        for segment in segments:
            insert_segment(
                db,
                item_id,
                segment["asset_id"],
                revision,
                {**segment, "text": corrected.get(segment["sequence"], segment["text"])},
            )
        db.execute(
            "UPDATE archival_item SET current_text_revision=%s, content_revision=%s WHERE id=%s",
            (revision, revision, item_id),
        )
        invalidate_publication(db, item_id)
        audit(db, user["id"], f"text_reviewed_revision_{revision}", item_id)
        return {"revision": revision, "status": "reviewed"}


class Verification(BaseModel):
    revision: int = Field(ge=1)
    original_compared: Literal[True]


@router.post("/{item_id}/text/verify")
def verify(item_id: UUID, data: Verification, request: Request, user: Staff):
    with connect(request.app.state.config) as db:
        item = item_lock(db, item_id)
        if item["current_text_revision"] != data.revision:
            raise HTTPException(409, "Only the current reviewed revision can be verified")
        updated = db.execute(
            """UPDATE text_revision SET status='verified', verified_by=%s,
            verified_at=now() WHERE item_id=%s AND revision=%s AND status='reviewed'
            RETURNING revision,status""",
            (user["id"], item_id, data.revision),
        ).fetchone()
        if not updated:
            raise HTTPException(409, "Save a reviewed snapshot before verification")
        audit(db, user["id"], f"text_verified_revision_{data.revision}", item_id)
        return updated


def insert_segment(db, item_id, asset_id, revision, segment):
    db.execute(
        """INSERT INTO text_segment
        (id,item_id,asset_id,revision,sequence,text,extraction_method,page_number,confidence,warning)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (
            uuid4(),
            item_id,
            asset_id,
            revision,
            segment["sequence"],
            segment["text"],
            segment["extraction_method"],
            segment["page_number"],
            segment.get("confidence"),
            segment.get("warning"),
        ),
    )
