"""Real PostgreSQL + filesystem tests. Isolated schema and synthetic fixtures only."""

import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from app.db import connect
from app.main import create_app

pytestmark = pytest.mark.integration


def metadata(**overrides):
    return dict(
        title="SYNTHETIC TEST ONLY",
        source_name="Synthetic test source",
        source_locator="https://example.invalid/test",
        source_record_locator="https://example.invalid/test/item",
        rights_statement="Synthetic fixture; not an archival holding",
        provenance_confirmed=True,
        language="en",
        original_filename="synthetic.txt",
        **overrides,
    )


def upload(client, auth, **overrides):
    return client.post(
        "/archive/staff/documents",
        params={"metadata": json.dumps(metadata(**overrides))},
        content=b"SYNTHETIC TEST ONLY\n",
        headers={"Content-Type": "text/plain"},
        auth=auth,
    )


@pytest.mark.parametrize("rights", ["Allowed", "Unknown", "Not verified"])
def test_placeholder_rights_cannot_verify_or_publish_even_legacy_records(archive, rights):
    client, config, admin, curator = archive
    data = metadata(access_level="public")
    data["rights_statement"] = rights
    uploaded = client.post(
        "/archive/staff/documents",
        auth=admin,
        params={"metadata": json.dumps(data)},
        content=b"SYNTHETIC RIGHTS GUARD TEST ONLY",
        headers={"Content-Type": "text/plain"},
    )
    assert uploaded.status_code == 201
    item = uploaded.json()["id"]
    route = f"/archive/staff/documents/{item}/transition"
    assert (
        client.post(
            route, auth=curator, json={"action": "verify", "metadata_reviewed": True}
        ).status_code
        == 409
    )
    # Model an older verified record inside this isolated test schema only.
    with connect(config) as db:
        db.execute(
            "UPDATE archival_item SET review_status='verified',verified_at=now(),"
            "verified_by=(SELECT id FROM staff_user WHERE login=%s) WHERE id=%s",
            (curator[0], item),
        )
    assert client.post(route, auth=curator, json={"action": "publish"}).status_code == 409
    assert client.get(f"/archive/documents/{item}/original").status_code == 404


def test_real_upload_persistence_lifecycle_and_permissions(archive):
    client, config, admin, curator = archive
    assert upload(client, None).status_code == 401
    assert upload(client, curator).status_code == 403
    response = upload(client, admin, access_level="public")
    assert response.status_code == 201, response.text
    item = response.json()["id"]
    route = f"/archive/staff/documents/{item}/transition"
    original = f"/archive/documents/{item}/original"
    assert client.get("/archive/documents").json() == []
    assert client.get(original).status_code == 404
    assert client.post(route, json={"action": "publish"}, auth=curator).status_code == 409
    assert client.post(route, json={"action": "verify"}, auth=curator).status_code == 422
    assert (
        client.post(
            route, json={"action": "verify", "metadata_reviewed": True}, auth=curator
        ).status_code
        == 200
    )
    assert client.get("/archive/documents").json() == []
    assert client.post(route, json={"action": "publish"}, auth=curator).status_code == 200
    assert client.get("/archive/documents").json()[0]["id"] == item
    assert client.get(original).content == b"SYNTHETIC TEST ONLY\n"
    # Recreate the app, then query PostgreSQL through a fresh connection.
    with TestClient(create_app(config)) as restarted:
        assert restarted.get("/archive/documents").json()[0]["id"] == item
        assert restarted.get(original).content == b"SYNTHETIC TEST ONLY\n"
    with connect(config) as db:
        asset = db.execute("SELECT * FROM asset WHERE item_id=%s", (item,)).fetchone()
        assert asset["checksum"] == hashlib.sha256(b"SYNTHETIC TEST ONLY\n").hexdigest()
        assert asset["storage_key"].startswith(f"originals/{item}/")
        assert db.execute("SELECT count(*) AS n FROM audit_event").fetchone()["n"] == 3
    import psycopg

    with pytest.raises(psycopg.errors.RaiseException), connect(config) as db:
        db.execute("UPDATE asset SET checksum=repeat('0',64) WHERE item_id=%s", (item,))
    assert client.post(route, json={"action": "withdraw"}, auth=curator).status_code == 200
    assert client.get(original).status_code == 404
    assert client.get("/archive/documents").json() == []
    assert client.get(f"/archive/staff/documents/{item}/original", auth=admin).status_code == 200


def test_validation_cleanup_staff_only_and_integrity(archive):
    client, config, admin, curator = archive
    from pathlib import Path

    invalid = metadata()
    invalid["original_filename"] = "../escape.txt"
    assert (
        client.post(
            "/archive/staff/documents",
            params={"metadata": json.dumps(invalid)},
            content=b"test",
            headers={"Content-Type": "text/plain"},
            auth=admin,
        ).status_code
        == 422
    )
    for content, mime, expected in [
        (b"", "text/plain", 415),
        (b"not pdf", "application/pdf", 415),
        (b"x" * (10 * 1024 * 1024 + 1), "text/plain", 413),
    ]:
        result = client.post(
            "/archive/staff/documents",
            params={"metadata": json.dumps(metadata())},
            content=content,
            headers={"Content-Type": mime},
            auth=admin,
        )
        assert result.status_code == expected
    assert list(Path(config.archive_root).rglob("*/*/*")) == []
    with connect(config) as db:
        assert db.execute("SELECT count(*) AS n FROM archival_item").fetchone()["n"] == 0
    item = upload(client, admin).json()["id"]
    route = f"/archive/staff/documents/{item}/transition"
    for action in ["verify", "publish"]:
        assert (
            client.post(
                route, json={"action": action, "metadata_reviewed": True}, auth=curator
            ).status_code
            == 200
        )
    assert client.get("/archive/documents").json() == []
    assert client.get(f"/archive/documents/{item}/original").status_code == 404
    with connect(config) as db:
        asset = db.execute("SELECT * FROM asset WHERE item_id=%s", (item,)).fetchone()
    path = Path(config.archive_root) / asset["storage_key"]
    path.chmod(0o600)
    path.write_bytes(b"SYNTHETIC CORRUPTION")
    assert client.get(f"/archive/staff/documents/{item}/original", auth=admin).status_code == 503
