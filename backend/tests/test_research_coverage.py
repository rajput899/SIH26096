"""Cross-volume retrieval checks in isolated synthetic schemas; no live generation."""
from uuid import UUID

import pytest

from app import research
from app.db import connect
from app.research_index import index_once
from tests.test_research import publish_fixture


@pytest.mark.integration
def test_cross_volume_citations_idempotency_and_withdrawal(archive, monkeypatch):
    client, config, _, curator = archive
    first, first_base, _ = publish_fixture(archive)
    second, _, _ = publish_fixture(archive)
    with connect(config) as db:
        for item, volume in [(first, 1), (second, 2)]:
            db.execute(
                "UPDATE archival_item SET volume_number=%s WHERE id=%s", (volume, UUID(item))
            )
        before = db.execute("SELECT id FROM passage ORDER BY id").fetchall()
        db.execute("UPDATE search_index_state SET retry_at=now()")
    assert index_once(config)
    assert index_once(config)
    with connect(config) as db:
        assert db.execute("SELECT id FROM passage ORDER BY id").fetchall() == before

    def generate(_config, passages, *_args):
        return {"paragraphs": [{"text": "Synthetic reading-room evidence.", "evidence": [
            {"passage_id": p["passage_id"], "quote": p["text"]} for p in passages
        ]}]}

    monkeypatch.setattr(research, "generate_grounded", generate)
    answer = client.post("/archive/research/ask", json={"question": "blue chairs"}).json()
    assert answer["status"] == "answered"
    assert {s["item_id"] for s in answer["sources"]} == {first, second}
    assert {s["volume_number"] for s in answer["sources"]} == {1, 2}
    for source in answer["sources"]:
        assert source["revision"] == 2 and source["page_number"] is None
        reader = client.get(source["reader_url"].replace("/archive/", "/archive/catalog/"))
        assert reader.status_code == 200
        assert source["excerpt"] in reader.json()["pages"][0]["text"]
    filtered = client.post(
        "/archive/research/ask", json={"question": "blue chairs", "volume": 2}
    ).json()
    assert {s["item_id"] for s in filtered["sources"]} == {second}
    assert client.post(first_base + "/transition", auth=curator,
                       json={"action": "withdraw"}).status_code == 200
    remaining = client.post("/archive/research/ask", json={"question": "blue chairs"}).json()
    assert {s["item_id"] for s in remaining["sources"]} == {second}
    assert client.get(f"/archive/documents/{first}/original").status_code == 404
