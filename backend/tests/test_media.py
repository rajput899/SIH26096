import hashlib
import io
import json

import pytest
from PIL import Image
from test_archive import metadata

from app.db import connect
from app.media import thumbnail_bytes


def image_fixture():
    output = io.BytesIO()
    Image.new("RGB", (1200, 900), "#194b75").save(output, "PNG")
    return output.getvalue()


def test_thumbnail_is_separate_and_bounded():
    original = image_fixture()
    checksum = hashlib.sha256(original).hexdigest()
    result = thumbnail_bytes(original)
    with Image.open(io.BytesIO(result)) as image:
        assert image.format == "JPEG" and image.size == (800, 600)
    assert hashlib.sha256(original).hexdigest() == checksum
    with pytest.raises(ValueError):
        thumbnail_bytes(b"not an image")


@pytest.mark.integration
@pytest.mark.parametrize("access", ["public", "staff"])
def test_thumbnail_publication_permissions_and_original_integrity(archive, access):
    client, config, admin, curator = archive
    original = image_fixture()
    data = metadata(access_level=access, material_type="photograph")
    data["original_filename"] = "SYNTHETIC-rights-cleared.png"
    response = client.post(
        "/archive/staff/documents",
        auth=admin,
        params={"metadata": json.dumps(data)},
        content=original,
        headers={"Content-Type": "image/png"},
    )
    assert response.status_code == 201
    item = response.json()["id"]
    public = f"/archive/documents/{item}/thumbnail"
    staff = f"/archive/staff/documents/{item}/thumbnail"
    transition = f"/archive/staff/documents/{item}/transition"
    assert client.get(public).status_code == 404
    assert client.get(staff).status_code == 401
    assert client.get(staff, auth=curator).status_code == 200
    assert (
        client.post(
            transition, auth=curator, json={"action": "verify", "metadata_reviewed": True}
        ).status_code
        == 200
    )
    assert client.get(public).status_code == 404  # verified + public is not published
    assert client.post(transition, auth=curator, json={"action": "publish"}).status_code == 200
    assert client.get(public).status_code == (200 if access == "public" else 404)
    assert client.get(f"/archive/staff/documents/{item}/original", auth=admin).content == original
    with connect(config) as db:
        assert (
            db.execute(
                "SELECT count(*) AS n FROM asset WHERE item_id=%s AND role='derivative'", (item,)
            ).fetchone()["n"]
            == 1
        )
    assert client.post(transition, auth=curator, json={"action": "withdraw"}).status_code == 200
    assert client.get(public).status_code == 404  # cached derivative does not grant access
