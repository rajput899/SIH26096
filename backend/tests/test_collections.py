"""Collection membership and image readers use isolated synthetic records only."""
import hashlib
import json

import pytest
from test_archive import metadata
from test_media import image_fixture
from test_research import publish_fixture

from app.db import connect


@pytest.mark.integration
def test_collection_origin_does_not_grant_access_or_guess_identity(archive):
    client, config, admin, curator = archive
    content = image_fixture()
    data = metadata(access_level="public", material_type="manuscript")
    data["original_filename"] = "SYNTHETIC-letter.png"
    item = client.post(
        "/archive/staff/documents", auth=admin,
        params={"metadata": json.dumps(data)}, content=content,
        headers={"Content-Type": "image/png"},
    ).json()["id"]
    base = f"/archive/staff/documents/{item}"
    with connect(config) as db:
        db.execute(
            "INSERT INTO corpus_file(checksum,relative_path,item_id,state) "
            "VALUES(%s,'synthetic/unclassified.png',%s,'awaiting_review')",
            (hashlib.sha256(content).hexdigest(), item),
        )
    for origin in ("", "dataset", "other"):
        assert client.get("/archive/catalog", params={"origin": origin}).json() == []
    for action in ({"action": "verify", "metadata_reviewed": True}, {"action": "publish"}):
        assert client.post(base + "/transition", auth=curator, json=action).status_code == 200
    dataset = client.get("/archive/catalog?origin=dataset&material_type=manuscript").json()
    assert [r["id"] for r in dataset] == [item]
    assert client.get("/archive/catalog?origin=other").json() == []
    other, _, _ = publish_fixture(archive)
    assert [r["id"] for r in client.get("/archive/catalog?origin=other").json()] == [other]
    assert [r["id"] for r in client.get("/archive/catalog?origin=dataset").json()] == [item]
    assert client.get("/archive/catalog?origin=dataset&material_type=photograph").json() == []
    assert client.get("/archive/catalog?origin=invalid").status_code == 422
    detail = client.get(f"/archive/catalog/{item}").json()
    assert detail["pages"] == []  # Never invent transcription for a published image.
    assert client.get(f"/archive/documents/{item}/original").content == content
    assert client.get(f"/archive/documents/{item}/thumbnail").status_code == 200
    # Corpus membership is independent of curator-changed source locators.
    with connect(config) as db:
        db.execute(
            "UPDATE archival_item SET source_record_locator=%s WHERE id=%s",
            ("https://example.invalid/reviewed", item),
        )
    assert len(client.get("/archive/catalog?origin=dataset").json()) == 1
    assert client.post(base + "/transition", auth=curator,
                       json={"action": "withdraw"}).status_code == 200
    assert client.get("/archive/catalog?origin=dataset").json() == []
    for suffix in ("original", "thumbnail", "playback"):
        assert client.get(f"/archive/documents/{item}/{suffix}").status_code == 404
    assert client.get(f"/archive/catalog/{item}").status_code == 404
