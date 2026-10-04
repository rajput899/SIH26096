"""Local PostgreSQL synthetic fixtures; no organizer data or historical approval in tests."""

import hashlib
import json

import psycopg
import pytest
from test_archive import metadata
from test_media import image_fixture

from app.dataset_release import release
from app.db import connect
from app.research_index import ELIGIBLE


def manifest(root, held=False):
    content = image_fixture()
    (root / "candidate.png").write_bytes(content)
    return {
        "id": "synthetic-release",
        "authorization": "Synthetic software fixture authorization only",
        "files": [
            {
                "path": "candidate.png",
                "sha256": hashlib.sha256(content).hexdigest(),
                "bytes": len(content),
                "mime": "image/png",
                "collection": "manuscripts",
                "exclusion": "Explicit synthetic hold" if held else "",
            }
        ],
    }


@pytest.mark.integration
def test_scoped_publication_originals_not_verification_or_future_uploads(archive, tmp_path):
    client, config, admin, curator = archive
    root = tmp_path / "dataset"
    root.mkdir()
    data = manifest(root)
    dry = release(config, root, data, admin[0])
    assert dry["apply"] is False
    assert client.get("/archive/catalog").json() == []
    result = release(config, root, data, admin[0], True)
    item = result["files"][0]["id"]
    assert release(config, root, data, admin[0], True)["files"][0]["new"] is False
    detail = client.get(f"/archive/catalog/{item}").json()
    assert detail["document"]["material_type"] == "image"
    assert detail["document"]["provenance_status"] == "pending"
    assert detail["document"]["verified_at"] is None
    assert detail["document"]["rights_statement"] == "Not verified"
    assert detail["document"]["dataset_authorization"] == data["authorization"]
    assert detail["pages"] == []
    assert (
        client.get(f"/archive/documents/{item}/original").content
        == (root / "candidate.png").read_bytes()
    )
    assert client.get(f"/archive/documents/{item}/thumbnail").status_code == 200
    assert len(client.get("/archive/catalog?collection=manuscripts&origin=dataset").json()) == 1
    assert client.get("/archive/catalog?collection=photographs").json() == []
    assert client.get("/archive/catalog?material_type=manuscript").json() == []
    assert client.get("/archive/catalog?collection=invalid").status_code == 422
    with connect(config) as db:
        assert db.execute("SELECT count(*) AS n FROM dataset_release").fetchone()["n"] == 1
        assert (
            db.execute(
                "SELECT count(*) AS n FROM audit_event WHERE action='organizer_dataset_published'"
            ).fetchone()["n"]
            == 1
        )
        assert (
            db.execute(
                "SELECT i.id FROM archival_item i JOIN text_revision r "
                "ON r.item_id=i.id WHERE " + ELIGIBLE
            ).fetchall()
            == []
        )
    assert client.get("/archive/staff/documents").status_code == 401
    assert (
        client.post(
            f"/archive/staff/documents/{item}/transition", json={"action": "withdraw"}
        ).status_code
        == 401
    )
    # A future upload, even with identical bytes, does not inherit dataset authorization.
    uploaded = client.post(
        "/archive/staff/documents",
        auth=admin,
        params={"metadata": json.dumps(metadata(access_level="public"))},
        headers={"Content-Type": "image/png"},
        content=(root / "candidate.png").read_bytes(),
    ).json()["id"]
    assert client.get(f"/archive/catalog/{uploaded}").status_code == 404
    with connect(config) as db:
        with pytest.raises(psycopg.errors.RaiseException):
            db.execute(
                "UPDATE archival_item SET dataset_release_id='synthetic-release',"
                "review_status='published',access_level='public' WHERE id=%s",
                (uploaded,),
            )
    # Existing withdrawal applies immediately across APIs, and rerunning cannot restore it.
    assert (
        client.post(
            f"/archive/staff/documents/{item}/transition", auth=curator, json={"action": "withdraw"}
        ).status_code
        == 200
    )
    for suffix in ("original", "thumbnail", "playback", "recording"):
        assert client.get(f"/archive/documents/{item}/{suffix}").status_code == 404
    assert client.get(f"/archive/catalog/{item}").status_code == 404


@pytest.mark.integration
def test_held_file_and_manifest_integrity(archive, tmp_path):
    client, config, admin, _ = archive
    root = tmp_path / "dataset"
    root.mkdir()
    data = manifest(root, held=True)
    result = release(config, root, data, admin[0], True)
    item = result["files"][0]["id"]
    assert result["files"][0]["exclusion"]
    assert client.get(f"/archive/catalog/{item}").status_code == 404
    assert client.get(f"/archive/documents/{item}/original").status_code == 404
    data["authorization"] = "Cannot overwrite a frozen release"
    with pytest.raises(ValueError, match="immutable"):
        release(config, root, data, admin[0], True)
    (root / "extra.txt").write_text("SYNTHETIC added later")
    with pytest.raises(ValueError, match="file set"):
        release(config, root, data, admin[0], True)


@pytest.mark.integration
def test_withdrawn_release_is_not_republished(archive, tmp_path):
    client, config, admin, curator = archive
    root = tmp_path / "dataset"
    root.mkdir()
    data = manifest(root)
    item = release(config, root, data, admin[0], True)["files"][0]["id"]
    client.post(
        f"/archive/staff/documents/{item}/transition", auth=curator, json={"action": "withdraw"}
    ).raise_for_status()
    result = release(config, root, data, admin[0], True)
    assert result["files"][0]["exclusion"]
    assert client.get(f"/archive/catalog/{item}").status_code == 404
