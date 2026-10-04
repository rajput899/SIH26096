import hashlib
import secrets
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field, model_validator

from app.archive import SELECT, audit, original_response, staff
from app.db import connect
from app.processing import invalidate_publication, item_lock

router = APIRouter(prefix="/archive")
Staff = Annotated[dict, Depends(staff)]


class Cue(BaseModel):
    start: float = Field(ge=0, allow_inf_nan=False)
    end: float = Field(gt=0, allow_inf_nan=False)
    text: str = Field(min_length=1, max_length=5000)

    @model_validator(mode="after")
    def order(self):
        if not self.text.strip():
            raise ValueError("Cue text must not be blank")
        if self.end <= self.start:
            raise ValueError("Cue end must follow start")
        return self


class Transcript(BaseModel):
    base_revision: int = Field(default=0, ge=0)
    cues: list[Cue] = Field(min_length=1, max_length=200)


@router.get("/recordings")
def recordings(request: Request):
    with connect(request.app.state.config) as db:
        return db.execute(
            SELECT + "WHERE i.review_status='published' AND i.access_level='public' "
            "AND a.mime_type IN ('audio/wav','audio/mpeg','video/mp4') ORDER BY i.title LIMIT 200"
        ).fetchall()


@router.get("/documents/{item_id}/playback")
def playback(item_id: UUID, request: Request):
    return original_response(item_id, request, False, True)


def playback_cookie(item_id):
    return f"archive_playback_{item_id.hex}"


@router.post("/staff/documents/{item_id}/playback-session")
def start_playback(item_id: UUID, request: Request, response: Response, user: Staff):
    token = secrets.token_urlsafe(32)
    with connect(request.app.state.config) as db:
        asset = db.execute(
            "SELECT mime_type FROM asset WHERE item_id=%s AND role='original'", (item_id,)
        ).fetchone()
        if not asset or asset["mime_type"] not in {"audio/wav", "audio/mpeg", "video/mp4"}:
            raise HTTPException(404, "Recording not found")
        # Only expired ephemeral grants are removed; archive/audit records are untouched.
        db.execute("DELETE FROM staff_playback_session WHERE expires_at<now()")
        db.execute(
            "INSERT INTO staff_playback_session(token_hash,item_id,user_id,expires_at) "
            "VALUES(%s,%s,%s,now()+interval '30 minutes')",
            (hashlib.sha256(token.encode()).hexdigest(), item_id, user["id"]),
        )
    response.set_cookie(
        playback_cookie(item_id),
        token,
        max_age=1800,
        httponly=True,
        samesite="strict",
        path=f"/api/archive/staff/documents/{item_id}/playback",
        secure=request.headers.get("x-forwarded-proto") == "https",
    )
    return {"playback_url": f"/api/archive/staff/documents/{item_id}/playback", "minutes": 30}


@router.post("/staff/documents/{item_id}/playback-stop")
def stop_playback(item_id: UUID, request: Request, user: Staff):
    with connect(request.app.state.config) as db:
        db.execute(
            "DELETE FROM staff_playback_session WHERE item_id=%s AND user_id=%s",
            (item_id, user["id"]),
        )
    return {"status": "closed"}


@router.get("/staff/documents/{item_id}/playback")
def private_playback(item_id: UUID, request: Request):
    token = request.cookies.get(playback_cookie(item_id), "")
    if not token:
        raise HTTPException(401, "Open the recording from the staff workspace")
    with connect(request.app.state.config) as db:
        valid = db.execute(
            "SELECT 1 FROM staff_playback_session p JOIN staff_user u ON u.id=p.user_id "
            "WHERE p.token_hash=%s AND p.item_id=%s AND p.expires_at>now() AND u.active",
            (hashlib.sha256(token.encode()).hexdigest(), item_id),
        ).fetchone()
    if not valid:
        raise HTTPException(401, "Staff playback expired. Open the recording again.")
    return original_response(item_id, request, True, True)


@router.get("/staff/documents/{item_id}/media-metadata")
def media_metadata(item_id: UUID, request: Request, user: Staff):
    with connect(request.app.state.config) as db:
        row = db.execute(
            "SELECT mime_type,byte_size,checksum,processing_provenance FROM asset "
            "WHERE item_id=%s AND role='original'",
            (item_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Recording not found")
        return row


@router.get("/staff/documents/{item_id}/recording")
def staff_recording(
    item_id: UUID, request: Request, user: Staff, revision: int | None = Query(default=None, ge=1)
):
    with connect(request.app.state.config) as db:
        item_lock(db, item_id)
        history = db.execute(
            "SELECT revision,status FROM recording_revision WHERE item_id=%s "
            "ORDER BY revision DESC",
            (item_id,),
        ).fetchall()
        row = db.execute(
            "SELECT * FROM recording_revision WHERE item_id=%s "
            "AND (%s::integer IS NULL OR revision=%s) ORDER BY revision DESC LIMIT 1",
            (item_id, revision, revision),
        ).fetchone()
        if revision is not None and not row:
            raise HTTPException(404, "Transcript revision not found")
        return (
            {**row, "revisions": history, "current_revision": history[0]["revision"]}
            if row
            else None
        )


@router.get("/documents/{item_id}/recording")
def public_recording(item_id: UUID, request: Request):
    with connect(request.app.state.config) as db:
        item = db.execute(
            "SELECT id FROM archival_item WHERE id=%s AND review_status='published' "
            "AND access_level='public'",
            (item_id,),
        ).fetchone()
        if not item:
            raise HTTPException(404, "Recording not public")
        latest = db.execute(
            "SELECT revision,transcript,status FROM recording_revision "
            "WHERE item_id=%s ORDER BY revision DESC LIMIT 1",
            (item_id,),
        ).fetchone()
        return latest if latest and latest["status"] == "verified" else None


@router.post("/staff/documents/{item_id}/recording")
def save_transcript(item_id: UUID, data: Transcript, request: Request, user: Staff):
    with connect(request.app.state.config) as db:
        item_lock(db, item_id)
        asset = db.execute(
            "SELECT * FROM asset WHERE item_id=%s AND role='original'", (item_id,)
        ).fetchone()
        if not asset or not asset["mime_type"].startswith(("audio/", "video/")):
            raise HTTPException(415, "A recording original is required")
        duration = asset["processing_provenance"]["duration_seconds"]
        if any(cue.end > duration + 0.1 for cue in data.cues):
            raise HTTPException(422, "Transcript timestamps exceed original duration")
        if any(b.start < a.end for a, b in zip(data.cues, data.cues[1:], strict=False)):
            raise HTTPException(422, "Transcript cues must be ordered without overlap")
        latest = db.execute(
            "SELECT coalesce(max(revision),0) AS revision FROM recording_revision WHERE item_id=%s",
            (item_id,),
        ).fetchone()["revision"]
        if latest != data.base_revision:
            raise HTTPException(409, "Transcript changed. Reload before saving.")
        db.execute(
            "INSERT INTO recording_revision(item_id,revision,transcript,status,created_by) "
            "VALUES(%s,%s,%s,'reviewed',%s)",
            (item_id, latest + 1, Jsonb(data.model_dump()["cues"]), user["id"]),
        )
        # Clear eligibility immediately; retained verified snapshots remain immutable.
        db.execute("UPDATE archival_item SET current_text_revision=NULL WHERE id=%s", (item_id,))
        invalidate_publication(db, item_id)
        audit(db, user["id"], "recording_transcript_reviewed", item_id)
        return {"revision": latest + 1, "status": "reviewed"}


class TranscriptVerification(BaseModel):
    revision: int = Field(ge=1)
    compared_with_recording: Literal[True]


@router.post("/staff/documents/{item_id}/recording/verify")
def verify_transcript(item_id: UUID, data: TranscriptVerification, request: Request, user: Staff):
    with connect(request.app.state.config) as db:
        item_lock(db, item_id)
        row = db.execute(
            "SELECT * FROM recording_revision WHERE item_id=%s ORDER BY revision DESC LIMIT 1",
            (item_id,),
        ).fetchone()
        if not row or row["revision"] != data.revision or row["status"] != "reviewed":
            raise HTTPException(409, "Only the current reviewed transcript can be verified")
        db.execute(
            "UPDATE recording_revision SET status='verified',verified_by=%s,"
            "verified_at=now() WHERE item_id=%s AND revision=%s",
            (user["id"], item_id, data.revision),
        )
        asset = db.execute(
            "SELECT id,checksum FROM asset WHERE item_id=%s AND role='original'", (item_id,)
        ).fetchone()
        revision = db.execute(
            "SELECT coalesce(max(revision),0)+1 AS n FROM text_revision WHERE item_id=%s",
            (item_id,),
        ).fetchone()["n"]
        db.execute(
            "INSERT INTO text_revision(item_id,revision,recording_revision,status,created_by,"
            "verified_by,verified_at,review_note,provenance) "
            "VALUES(%s,%s,%s,'verified',%s,%s,now(),%s,%s)",
            (
                item_id,
                revision,
                data.revision,
                row["created_by"],
                user["id"],
                "Curator compared timestamped cues with recording",
                Jsonb({"method": "curator_transcript", "original_sha256": asset["checksum"]}),
            ),
        )
        for sequence, cue in enumerate(row["transcript"], 1):
            db.execute(
                "INSERT INTO text_segment(id,item_id,asset_id,revision,sequence,text,"
                "extraction_method,start_seconds,end_seconds) "
                "VALUES(%s,%s,%s,%s,%s,%s,'curator_transcript',%s,%s)",
                (
                    uuid4(),
                    item_id,
                    asset["id"],
                    revision,
                    sequence,
                    cue["text"],
                    cue["start"],
                    cue["end"],
                ),
            )
        db.execute(
            "UPDATE archival_item SET current_text_revision=%s,content_revision=%s WHERE id=%s",
            (revision, revision, item_id),
        )
        audit(db, user["id"], "recording_transcript_verified", item_id)
    return {"status": "verified"}
