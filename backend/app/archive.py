import hashlib
import json
import os
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, ValidationError

from app.db import connect
from app.staff import check_password, hash_password

router = APIRouter(prefix="/archive")
security = HTTPBasic(auto_error=False)
DUMMY_HASH = hash_password("non-account timing padding")
LIMIT = 10 * 1024 * 1024


class Metadata(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=200)
    source_name: str = Field(min_length=1, max_length=200)
    source_locator: HttpUrl
    source_record_locator: HttpUrl
    rights_statement: str = Field(min_length=1, max_length=1000)
    provenance_confirmed: Literal[True]
    material_type: Literal["document", "manuscript", "photograph", "audio", "video", "speech"] = (
        "document"
    )
    language: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=2000)
    access_level: Literal["staff", "public"] = "staff"
    original_filename: str = Field(min_length=1, max_length=200, pattern=r"^[^/\\\x00-\x1f]+$")


def staff(request: Request, credentials: Annotated[HTTPBasicCredentials | None, Depends(security)]):
    if credentials is None:
        raise HTTPException(401, "Staff credentials required")
    with connect(request.app.state.config) as db:
        user = db.execute(
            "SELECT * FROM staff_user WHERE login=%s", (credentials.username,)
        ).fetchone()
    valid = check_password(credentials.password, user["password_hash"] if user else DUMMY_HASH)
    if not user or not valid or not user["active"]:
        raise HTTPException(401, "Invalid staff credentials")
    return user


def admin(user: Annotated[dict, Depends(staff)]):
    if user["role"] != "admin":
        raise HTTPException(403, "Admin role required")
    return user


SELECT = """SELECT i.*, s.name AS source_name, s.verified_locator AS source_locator,
 a.id AS asset_id, a.original_filename, a.mime_type, a.byte_size, a.checksum,
 s.verification_status AS provenance_status,
 (SELECT m.collection FROM dataset_member m WHERE m.item_id=i.id) AS dataset_collection,
 (SELECT m.relative_path FROM dataset_member m WHERE m.item_id=i.id) AS dataset_path,
 (SELECT d.authorization_note FROM dataset_release d WHERE d.id=i.dataset_release_id)
 AS dataset_authorization
 FROM archival_item i JOIN source s ON s.id=i.source_id
 JOIN asset a ON a.item_id=i.id AND a.role='original' """


def audit(db, actor, action, item):
    db.execute(
        """INSERT INTO audit_event(id,actor_id,action,target_type,target_id,change_summary)
                VALUES (%s,%s,%s,'archival_item',%s,%s)""",
        (uuid4(), actor, action, item, f"Archive metadata/original: {action}"),
    )


@router.get("/documents")
def public_list(request: Request):
    with connect(request.app.state.config) as db:
        return db.execute(
            SELECT + "WHERE i.review_status='published' AND i.access_level='public' "
            "ORDER BY i.created_at DESC LIMIT 200"
        ).fetchall()


@router.get("/staff/documents")
def staff_list(
    request: Request,
    user: Annotated[dict, Depends(staff)],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=200),
):
    with connect(request.app.state.config) as db:
        return db.execute(
            SELECT.replace(
                "i.*,",
                "i.*, "
                "s.verification_status AS source_status, "
                "(SELECT state FROM corpus_file f WHERE f.item_id=i.id) AS corpus_state, "
                "(SELECT status FROM processing_job j WHERE j.item_id=i.id) AS job_status, "
                "(SELECT status FROM text_revision r WHERE r.item_id=i.id "
                "AND r.revision=i.current_text_revision) AS text_status,",
            )
            + "ORDER BY i.created_at DESC,i.id LIMIT %s OFFSET %s",
            (limit, offset),
        ).fetchall()


@router.get("/staff/me")
def me(user: Annotated[dict, Depends(staff)]):
    return {"login": user["login"], "role": user["role"]}


@router.post("/staff/documents", status_code=201)
async def upload(request: Request, metadata: str, user: Annotated[dict, Depends(admin)]):
    try:
        data = Metadata.model_validate_json(metadata)
    except ValidationError:
        raise HTTPException(
            422, "Invalid metadata; source, rights and provenance confirmation required"
        ) from None
    mime = request.headers.get("content-type", "").split(";")[0]
    if mime not in {
        "application/pdf",
        "image/png",
        "image/jpeg",
        "text/plain",
        "audio/wav",
        "audio/mpeg",
        "video/mp4",
    }:
        raise HTTPException(415, "Supported: PDF, PNG, JPEG, text, WAV, MP3, H.264/AAC MP4")
    item, asset, source = uuid4(), uuid4(), uuid4()
    root = Path(request.app.state.config.archive_root)
    key = f"originals/{item}/{asset}"
    path = root / key
    path.parent.mkdir(parents=True, exist_ok=False)
    digest, size, prefix = hashlib.sha256(), 0, b""
    committed = False
    try:
        with path.open("xb") as output:
            async for chunk in request.stream():
                size += len(chunk)
                if size > LIMIT:
                    raise HTTPException(413, "Maximum original size is 10 MiB")
                prefix = (prefix + chunk)[:1024]
                digest.update(chunk)
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
        valid = size > 0
        signatures = {
            "application/pdf": b"%PDF-",
            "image/png": b"\x89PNG\r\n\x1a\n",
            "image/jpeg": b"\xff\xd8\xff",
        }
        media_info = {}
        if mime.startswith(("audio/", "video/")):
            from app.recording_probe import inspect_recording

            try:
                media_info = inspect_recording(path, mime)
            except ValueError as exc:
                raise HTTPException(415, str(exc)) from None
        elif mime in signatures:
            valid = valid and prefix.startswith(signatures[mime])
        else:
            try:
                valid = valid and "\x00" not in path.read_text(encoding="utf-8")
            except UnicodeError:
                valid = False
        if not valid:
            raise HTTPException(415, "Empty file or content does not match declared format")
        path.chmod(0o444)
        with connect(request.app.state.config) as db:
            db.execute(
                """INSERT INTO source(id,name,verified_locator,rights_notes,verification_status)
                          VALUES (%s,%s,%s,%s,'verified')""",
                (source, data.source_name, str(data.source_locator), data.rights_statement),
            )
            db.execute(
                """INSERT INTO archival_item(id,source_id,source_record_locator,title,
                material_type,language,description,rights_statement,access_level)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    item,
                    source,
                    str(data.source_record_locator),
                    data.title,
                    data.material_type,
                    data.language,
                    data.description,
                    data.rights_statement,
                    data.access_level,
                ),
            )
            db.execute(
                """INSERT INTO asset(id,item_id,role,storage_key,original_filename,mime_type,
                byte_size,checksum,processing_provenance)
                VALUES (%s,%s,'original',%s,%s,%s,%s,%s,%s)""",
                (
                    asset,
                    item,
                    key,
                    data.original_filename,
                    mime,
                    size,
                    digest.hexdigest(),
                    json.dumps(
                        {"method": "admin_upload", "actor_id": str(user["id"]), **media_info}
                    ),
                ),
            )
            audit(db, user["id"], "uploaded", item)
        committed = True
        return {"id": item, "review_status": "uploaded", "checksum": digest.hexdigest()}
    finally:
        if not committed:
            if path.exists():
                path.chmod(0o600)
                path.unlink()
            path.parent.rmdir()


class Transition(BaseModel):
    action: Literal["verify", "publish", "withdraw"]
    metadata_reviewed: bool = False


@router.post("/staff/documents/{item_id}/transition")
def transition(
    item_id: UUID, data: Transition, request: Request, user: Annotated[dict, Depends(staff)]
):
    with connect(request.app.state.config) as db:
        item = db.execute(
            "SELECT * FROM archival_item WHERE id=%s FOR UPDATE", (item_id,)
        ).fetchone()
        if not item:
            raise HTTPException(404, "Document not found")
        allowed = {
            "verify": {"uploaded", "withdrawn"},
            "publish": {"verified"},
            "withdraw": {"published", "verified"},
        }
        if item["review_status"] not in allowed[data.action]:
            raise HTTPException(409, "Invalid lifecycle transition")
        if data.action in {"verify", "publish"} and item["rights_statement"].strip().casefold() in {
            "allowed",
            "unknown",
            "not verified",
        }:
            raise HTTPException(
                409, "A placeholder rights statement does not establish public-display permission"
            )
        if (
            data.action in {"verify", "publish"}
            and db.execute(
                "SELECT verification_status FROM source WHERE id=%s", (item["source_id"],)
            ).fetchone()["verification_status"]
            != "verified"
        ):
            raise HTTPException(409, "Review imported source provenance and rights first")
        corpus = db.execute("SELECT state FROM corpus_file WHERE item_id=%s", (item_id,)).fetchone()
        if data.action in {"verify", "publish"} and corpus and corpus["state"] != "awaiting_review":
            raise HTTPException(409, "Complete all local import pages before verification")
        if data.action == "publish":
            transcript = db.execute(
                "SELECT status FROM recording_revision WHERE item_id=%s "
                "ORDER BY revision DESC LIMIT 1",
                (item_id,),
            ).fetchone()
            if transcript and transcript["status"] != "verified":
                raise HTTPException(
                    409, "Verify the current recording transcript before publication"
                )
            job = db.execute(
                "SELECT status FROM processing_job WHERE item_id=%s", (item_id,)
            ).fetchone()
            if job:
                text = db.execute(
                    "SELECT status FROM text_revision WHERE item_id=%s AND revision=%s",
                    (item_id, item["current_text_revision"]),
                ).fetchone()
                if job["status"] != "succeeded" or not text or text["status"] != "verified":
                    raise HTTPException(
                        409,
                        "Processing must succeed and current text must be verified "
                        "before publication",
                    )
        if data.action == "verify":
            if not data.metadata_reviewed:
                raise HTTPException(
                    422, "Confirm review of original, metadata, provenance and rights"
                )
            db.execute(
                "UPDATE archival_item SET verified_by=%s, verified_at=now() WHERE id=%s",
                (user["id"], item_id),
            )
        status = {"verify": "verified", "publish": "published", "withdraw": "withdrawn"}[
            data.action
        ]
        db.execute(
            "UPDATE archival_item SET review_status=%s, updated_at=now() WHERE id=%s",
            (status, item_id),
        )
        audit(db, user["id"], status, item_id)
    return {"id": item_id, "review_status": status}


def original_response(item_id, request, is_staff, playback=False):
    with connect(request.app.state.config) as db:
        row = db.execute(
            """SELECT a.* FROM asset a JOIN archival_item i ON i.id=a.item_id
             WHERE i.id=%s AND a.role='original' AND (%s OR
             (i.review_status='published' AND i.access_level='public'))""",
            (item_id, is_staff),
        ).fetchone()
    if not row:
        raise HTTPException(404, "Document not found")
    if playback and row["mime_type"] not in {"audio/wav", "audio/mpeg", "video/mp4"}:
        raise HTTPException(415, "Not a supported recording")
    path = Path(request.app.state.config.archive_root) / row["storage_key"]
    from app.corpus import checksum

    if not path.is_file() or checksum(path) != row["checksum"]:
        raise HTTPException(503, "Original unavailable or integrity check failed")
    return FileResponse(
        path,
        filename=row["original_filename"],
        media_type=row["mime_type"] if playback else "application/octet-stream",
        content_disposition_type="inline" if playback else "attachment",
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.get("/documents/{item_id}/original")
def public_original(item_id: UUID, request: Request):
    return original_response(item_id, request, False)


@router.get("/staff/documents/{item_id}/original")
def staff_original(item_id: UUID, request: Request, user: Annotated[dict, Depends(staff)]):
    return original_response(item_id, request, True)
