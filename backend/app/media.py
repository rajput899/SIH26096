"""Authorized image derivatives; preserved originals are never modified."""

import hashlib
import io
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from PIL import Image, ImageOps, UnidentifiedImageError
from psycopg.types.json import Jsonb

from app.archive import staff
from app.db import connect

router = APIRouter(prefix="/archive")


def thumbnail_bytes(original: bytes) -> bytes:
    try:
        with Image.open(io.BytesIO(original)) as image:
            if image.width * image.height > 20_000_000:
                raise ValueError("Image exceeds preview pixel limit")
            image = ImageOps.exif_transpose(image)
            image.thumbnail((800, 800))
            canvas = Image.new("RGB", image.size, "white")
            if image.mode in {"RGBA", "LA"}:
                canvas.paste(image, mask=image.getchannel("A"))
            else:
                canvas.paste(image.convert("RGB"))
            output = io.BytesIO()
            canvas.save(output, format="JPEG", quality=85)
            return output.getvalue()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("Cannot decode image for preview") from exc


def thumbnail(item_id, request, is_staff=False):
    config = request.app.state.config
    with connect(config) as db:
        # Serialize derivative generation; permission is always checked before serving cache.
        db.execute("SELECT pg_advisory_xact_lock(hashtext(%s),260964)", (str(item_id),))
        row = db.execute(
            "SELECT a.* FROM archival_item i JOIN asset a ON a.item_id=i.id "
            "AND a.role='original' WHERE i.id=%s AND (%s OR "
            "(i.review_status='published' AND i.access_level='public')) FOR SHARE OF i",
            (item_id, is_staff),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Image not available")
        if row["mime_type"] not in {"image/png", "image/jpeg"}:
            raise HTTPException(415, "This original is not a supported image")
        original = Path(config.archive_root) / row["storage_key"]
        if not original.is_file():
            raise HTTPException(503, "Original unavailable")
        content = original.read_bytes()
        if hashlib.sha256(content).hexdigest() != row["checksum"]:
            raise HTTPException(503, "Original integrity check failed")
        derivative = db.execute(
            "SELECT * FROM asset WHERE parent_asset_id=%s AND role='derivative' "
            "AND processing_provenance->>'kind'='thumbnail-v1'",
            (row["id"],),
        ).fetchone()
        if derivative:
            path = Path(config.archive_root) / derivative["storage_key"]
            if (
                not path.is_file()
                or hashlib.sha256(path.read_bytes()).hexdigest() != derivative["checksum"]
            ):
                raise HTTPException(503, "Thumbnail unavailable; original is retained")
        else:
            try:
                data = thumbnail_bytes(content)
            except ValueError:
                raise HTTPException(
                    422, "Preview unavailable; download the preserved original"
                ) from None
            asset_id = uuid4()
            key = f"derivatives/{item_id}/{asset_id}.jpg"
            path = Path(config.archive_root) / key
            path.parent.mkdir(parents=True, exist_ok=True)
            try:
                with path.open("xb") as output:
                    output.write(data)
                db.execute(
                    "INSERT INTO asset(id,item_id,role,parent_asset_id,storage_key,"
                    "original_filename,mime_type,byte_size,checksum,processing_provenance) "
                    "VALUES(%s,%s,'derivative',%s,%s,'thumbnail.jpg','image/jpeg',%s,%s,%s)",
                    (
                        asset_id,
                        item_id,
                        row["id"],
                        key,
                        len(data),
                        hashlib.sha256(data).hexdigest(),
                        Jsonb(
                            {
                                "kind": "thumbnail-v1",
                                "source_checksum": row["checksum"],
                                "engine": "Pillow",
                            }
                        ),
                    ),
                )
                db.commit()
            except Exception:
                path.unlink(
                    missing_ok=True
                )  # Only this uncommitted derivative, never the original.
                raise
    return FileResponse(
        path,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.get("/documents/{item_id}/thumbnail")
def public_thumbnail(item_id: UUID, request: Request):
    return thumbnail(item_id, request)


@router.get("/staff/documents/{item_id}/thumbnail")
def staff_thumbnail(item_id: UUID, request: Request, user: Annotated[dict, Depends(staff)]):
    return thumbnail(item_id, request, True)
