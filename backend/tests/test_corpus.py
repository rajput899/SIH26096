"""Synthetic fixtures exercise real local import/checkpoints without publishing originals."""

import httpx
import pytest
from test_processing import scanned_fixture

from app.corpus import checksum, run
from app.db import connect
from app.research_index import chunks, embeddings


@pytest.mark.parametrize(
    "vectors",
    [[], [[]], [[float("nan")]], [[float("inf")]], [[True]], [[0, 0]], [[1], [1, 2]], [["1"]]],
)
def test_invalid_vectors_are_rejected(settings, vectors):
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"embeddings": vectors}))
    ) as client:
        with pytest.raises(ValueError):
            embeddings(client, settings, ["test"] * max(1, len(vectors)))


def test_invalid_chunk_configuration():
    with pytest.raises(ValueError):
        list(chunks("text", 10, 10))


@pytest.mark.integration
def test_import_resume_review_and_publication_gate(archive, tmp_path):
    client, config, admin, curator = archive
    root = tmp_path / "dataset"
    root.mkdir()
    path = root / "Volume_01.pdf"
    path.write_bytes(scanned_fixture())
    digest = checksum(path)
    run(config, root, 0)
    assert client.get("/archive/staff/corpus").status_code == 401
    rows = client.get("/archive/staff/corpus", auth=curator).json()
    assert len(rows) == 1 and rows[0]["ocr_pending_pages"] == 2
    item = rows[0]["item_id"]
    base = f"/archive/staff/documents/{item}"
    assert (
        client.post(
            base + "/transition", auth=curator, json={"action": "verify", "metadata_reviewed": True}
        ).status_code
        == 409
    )
    run(config, root, 1)
    rows = client.get("/archive/staff/corpus", auth=curator).json()
    assert rows[0]["extracted_pages"] == 1 and rows[0]["ocr_pending_pages"] == 1
    run(config, root, 1)
    run(config, root, 1)
    rows = client.get("/archive/staff/corpus", auth=curator).json()
    assert len(rows) == 1 and rows[0]["state"] == "awaiting_review"
    assert checksum(path) == digest
    with connect(config) as db:
        assert db.execute("SELECT count(*) n FROM text_segment").fetchone()["n"] == 2
        assert db.execute("SELECT count(*) n FROM processing_job").fetchone()["n"] == 1
        assert db.execute("SELECT count(*) n FROM passage").fetchone()["n"] == 0
    assert client.get(f"/archive/catalog/{item}").status_code == 404
    assert client.get(f"/archive/documents/{item}/original").status_code == 404
    review = {
        "source_locator": "https://example.org/synthetic-test",
        "rights_statement": "Self-created synthetic test only",
        "public_display_approved": False,
    }
    endpoint = f"/archive/staff/corpus/{item}/source-review"
    assert client.post(endpoint, json=review, auth=curator).status_code == 403
    assert client.post(endpoint, json=review, auth=admin).status_code == 200
    assert client.get("/archive/catalog").json() == []


@pytest.mark.integration
def test_page_budget_and_compilation_hold(archive, tmp_path):
    client, config, _, curator = archive
    root = tmp_path / "bounded"
    root.mkdir()
    path = root / "Volume_01.pdf"
    path.write_bytes(scanned_fixture())
    run(config, root, 0, max_pages=1)
    with connect(config) as db:
        assert db.execute("SELECT count(*) n FROM corpus_page").fetchone()["n"] == 1
        db.execute("UPDATE corpus_file SET page_count=13824")
    run(config, root, 1, max_pages=1)
    with connect(config) as db:
        assert db.execute("SELECT count(*) n FROM corpus_page").fetchone()["n"] == 1
    assert client.get("/archive/catalog").json() == []
