"""Research checks use synthetic isolated material, never historical claims."""

import json
from uuid import UUID, uuid4

import httpx
import pytest
from test_archive import metadata

from app import research
from app.db import connect
from app.research import Question, citation, validate_answer
from app.research_index import chunks, index_once
from app.worker import run_once


def source():
    return dict(
        id=uuid4(),
        item_id=uuid4(),
        revision=2,
        page_number=3,
        sequence=3,
        title="SYNTHETIC TEST ONLY",
        text="Synthetic reading rooms have blue chairs.",
    )


def test_chunks_preserve_exact_offsets_and_never_drop_text():
    text = "अभिलेख archival test " * 300
    parts = list(chunks(text))
    assert parts[0][0] == 0 and parts[-1][1] == len(text)
    assert all(text[start:end] == piece for start, end, piece in parts)
    assert all(end - start <= 1200 for start, end, _ in parts)
    assert all(parts[i + 1][0] == parts[i][1] - 120 for i in range(len(parts) - 1))
    assert list(chunks("   ")) == []


def test_citations_require_real_passage_and_exact_quote():
    p = source()
    raw = {
        "paragraphs": [
            {
                "text": "The synthetic room has blue chairs.",
                "evidence": [{"passage_id": str(p["id"]), "quote": p["text"]}],
            }
        ]
    }
    assert validate_answer(raw, [p]).paragraphs
    raw["paragraphs"][0]["evidence"][0]["quote"] = "An invented historical claim"
    with pytest.raises(ValueError):
        validate_answer(raw, [p])
    raw["paragraphs"][0]["evidence"][0] = {"passage_id": str(uuid4()), "quote": p["text"]}
    with pytest.raises(ValueError):
        validate_answer(raw, [p])
    with pytest.raises(ValueError):
        validate_answer({"paragraphs": [{"text": "uncited", "evidence": []}]}, [p])
    assert validate_answer({"paragraphs": []}, [p]).paragraphs == []


def test_citation_links_use_database_locators():
    p = source()
    c = citation(p)
    assert c["title"] == p["title"] and c["page_number"] == 3
    assert c["reader_url"] == f"/archive/{p['item_id']}?revision=2#page-3"
    p["page_number"] = None
    assert citation(p)["page_number"] is None


def test_no_sources_never_calls_model(settings, monkeypatch):
    monkeypatch.setattr(research, "retrieve", lambda *_: ([], "Semantic search unavailable"))
    monkeypatch.setattr(
        research, "empty_reason", lambda *_: ("no_eligible_content", "No eligible text")
    )
    monkeypatch.setattr(research, "generate_grounded", lambda *_: pytest.fail("No evidence"))
    answer = research.answer_question(settings, Question(question="Any records?"))
    assert answer["status"] == "insufficient_sources"
    assert answer["sources"] == [] and answer["paragraphs"] == []


@pytest.mark.parametrize(
    "question,status",
    [
        ("Hi", "greeting"),
        ("Hello!", "greeting"),
        ("नमस्ते", "greeting"),
        ("What can you do?", "scope"),
        ("Tell me a joke", "scope"),
    ],
)
def test_conversation_never_searches_or_calls_provider(settings, monkeypatch, question, status):
    monkeypatch.setattr(research, "retrieve", lambda *_: pytest.fail("No archive search"))
    monkeypatch.setattr(
        research, "generate_grounded", lambda *_: pytest.fail("No external request")
    )
    answer = research.answer_question(settings, Question(question=question))
    assert answer["status"] == status and not answer["generation_attempted"]


@pytest.mark.integration
def test_source_scope_summary_and_empty_diagnostics(archive, monkeypatch):
    client, config, _, curator = archive
    empty = client.post("/archive/research/ask", json={"question": "Constitution"}).json()
    assert empty["reason"] == "no_eligible_content"
    item, base, _ = publish_fixture(archive)
    monkeypatch.setattr(research, "generate_grounded", lambda *args: {"paragraphs": []})
    summary = client.post(
        "/archive/research/ask", json={"question": "Summarize this source", "item_id": item}
    ).json()
    assert summary["sources"] and all(s["item_id"] == item for s in summary["sources"])
    missing = client.post("/archive/research/ask", json={"question": "unmatchablexyz"}).json()
    assert missing["reason"] == "no_matching_content"
    other = client.post(
        "/archive/research/ask", json={"question": "blue chairs", "item_id": str(uuid4())}
    ).json()
    assert other["sources"] == []
    client.post(base + "/transition", auth=curator, json={"action": "withdraw"})
    assert (
        client.post(
            "/archive/research/ask", json={"question": "Summarize", "item_id": item}
        ).json()["sources"]
        == []
    )


def publish_fixture(archive):
    client, config, admin, curator = archive
    content = b"SYNTHETIC TEST ONLY. Synthetic reading rooms have blue chairs."
    response = client.post(
        "/archive/staff/documents",
        params={"metadata": json.dumps(metadata(access_level="public"))},
        content=content,
        headers={"Content-Type": "text/plain"},
        auth=admin,
    )
    assert response.status_code == 201, response.text
    item = response.json()["id"]
    base = f"/archive/staff/documents/{item}"
    assert client.post(base + "/processing", json={}, auth=curator).status_code == 202
    assert run_once(config)
    extracted = client.get(base + "/text", auth=curator).json()
    pages = [{"sequence": p["sequence"], "text": p["text"]} for p in extracted["segments"]]
    assert (
        client.post(
            base + "/text/revisions",
            auth=curator,
            json={"base_revision": 1, "pages": pages, "note": "Synthetic test review"},
        ).status_code
        == 201
    )
    assert (
        client.post(
            base + "/text/verify", auth=curator, json={"revision": 2, "original_compared": True}
        ).status_code
        == 200
    )
    assert (
        client.post(
            base + "/transition", auth=curator, json={"action": "verify", "metadata_reviewed": True}
        ).status_code
        == 200
    )
    assert client.get(f"/archive/catalog/{item}").status_code == 404
    assert (
        client.post(base + "/transition", auth=curator, json={"action": "publish"}).status_code
        == 200
    )
    assert index_once(config)
    return item, base, content


@pytest.mark.integration
def test_real_search_review_publication_citations_and_withdrawal(archive, monkeypatch):
    client, config, _, curator = archive
    # Exercise real PostgreSQL FTS fallback without requiring an installed model.
    config.ollama_embedding_model = ""
    item, base, content = publish_fixture(archive)
    detail = client.get(f"/archive/catalog/{item}?revision=2").json()
    assert detail["pages"][0]["text"].encode() == content
    assert detail["pages"][0]["page_number"] is None
    assert client.get(f"/archive/catalog/{item}?revision=1").status_code == 409
    assert client.get(f"/archive/documents/{item}/original").content == content
    configured_generation = config.ollama_generation_model
    config.ollama_generation_model = ""
    missing = client.post("/archive/research/ask", json={"question": "blue chairs"}).json()
    assert missing["status"] == "model_unavailable" and missing["sources"]
    config.ollama_generation_model = configured_generation
    captured = []

    def generate(_config, passages, question, history, schema):
        captured.append(history)
        return {
            "paragraphs": [
                {
                    "text": "The synthetic source describes blue chairs.",
                    "evidence": [
                        {"passage_id": passages[0]["passage_id"], "quote": passages[0]["text"]}
                    ],
                }
            ]
        }

    monkeypatch.setattr(research, "generate_grounded", generate)
    payload = {"question": "What about blue chairs?", "history": ["Reading rooms?"]}
    answer = client.post("/archive/research/ask", json=payload).json()
    assert answer["status"] == "answered", answer
    assert captured == [["Reading rooms?"]]
    assert answer["sources"][0]["item_id"] == item
    assert answer["sources"][0]["revision"] == 2
    assert "PostgreSQL" in answer["warning"]
    assert (
        client.post("/archive/research/ask", json={**payload, "language": "no-match"}).json()[
            "status"
        ]
        == "insufficient_sources"
    )
    with connect(config) as db:
        assert db.execute("SELECT count(*) AS n FROM artifact_evidence").fetchone()["n"] == 1
    monkeypatch.setattr(
        research,
        "generate_grounded",
        lambda *_: (_ for _ in ()).throw(httpx.ConnectError("Synthetic service outage")),
    )
    unavailable = client.post("/archive/research/ask", json=payload).json()
    assert unavailable["status"] == "model_unavailable" and unavailable["sources"]
    assert (
        client.post(base + "/transition", json={"action": "withdraw"}, auth=curator).status_code
        == 200
    )
    assert client.get(f"/archive/catalog/{item}").status_code == 404
    assert client.get(f"/archive/documents/{item}/original").status_code == 404
    assert client.post("/archive/research/ask", json=payload).json()["sources"] == []
    with connect(config) as db:
        assert (
            db.execute("SELECT status FROM generated_artifact").fetchone()["status"]
            == "invalidated"
        )


@pytest.mark.integration
def test_withdraw_during_generation_discards_response(archive, monkeypatch):
    client, config, _, curator = archive
    config.ollama_embedding_model = ""
    _, base, _ = publish_fixture(archive)

    def withdraw(*_):
        assert (
            client.post(base + "/transition", json={"action": "withdraw"}, auth=curator).status_code
            == 200
        )
        return {"paragraphs": []}

    monkeypatch.setattr(research, "generate_grounded", withdraw)
    result = client.post("/archive/research/ask", json={"question": "blue chairs"}).json()
    assert result["status"] == "sources_changed" and result["sources"] == []


@pytest.mark.integration
def test_real_configured_ollama_qdrant_answer(archive):
    """Opt-in acceptance: real models, vectors, DB and generated cited answer; never a mock."""
    import os

    if os.getenv("RUN_AI_ACCEPTANCE") != "1":
        pytest.skip("Set RUN_AI_ACCEPTANCE=1 after configuring both installed models")
    client, config, _, _ = archive
    assert config.ollama_generation_model and config.ollama_embedding_model
    item, _, _ = publish_fixture(archive)
    with connect(config) as db:
        state = db.execute(
            "SELECT status FROM search_index_state WHERE item_id=%s", (UUID(item),)
        ).fetchone()
    assert state["status"] == "ready", state
    result = client.post(
        "/archive/research/ask",
        json={"question": "What color are the chairs in the synthetic reading rooms?"},
    ).json()
    assert result["status"] == "answered", result
    assert result["warning"] == ""
    assert result["sources"][0]["item_id"] == item
    assert "blue" in " ".join(p["text"] for p in result["paragraphs"]).lower()


def test_local_ollama_generation_contract(settings, monkeypatch):
    from app.llm import generate_grounded

    settings.ollama_generation_model = "synthetic-contract-model"
    calls = []
    real_client = httpx.Client

    def handler(request):
        calls.append(json.loads(request.content))
        assert request.url.path == "/api/chat"
        return httpx.Response(200, json={"message": {"content": '{"paragraphs": []}'}})

    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs),
    )
    assert generate_grounded(settings, [], "test", [], research.Answer.model_json_schema()) == {
        "paragraphs": []
    }
    assert calls[0]["model"] == "synthetic-contract-model"
    assert calls[0]["stream"] is False
    assert calls[0]["format"]["type"] == "object"
    assert calls[0]["messages"][0]["role"] == "system"


def test_multilingual_embedding_identity_and_no_truncation(settings):
    from app.research_index import embeddings, model_identity

    settings.ollama_embedding_model = "synthetic-multilingual-model"

    def handler(request):
        if request.url.path == "/api/tags":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {"name": "synthetic-multilingual-model:latest", "digest": "test-digest"}
                    ]
                },
            )
        payload = json.loads(request.content)
        assert payload["input"] == ["अभिलेख test"] and payload["truncate"] is False
        return httpx.Response(200, json={"embeddings": [[0.1, 0.2]]})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert len(model_identity(client, settings)) == 64
        assert embeddings(client, settings, ["अभिलेख test"]) == [[0.1, 0.2]]


@pytest.mark.integration
def test_unverified_text_and_stale_vector_ids_are_never_sources(archive, monkeypatch):
    client, config, _, curator = archive
    config.ollama_embedding_model = ""
    item, base, _ = publish_fixture(archive)
    with connect(config) as db:
        passage = db.execute("SELECT id FROM passage WHERE item_id=%s", (UUID(item),)).fetchone()
    assert (
        client.post(
            base + "/text/revisions",
            auth=curator,
            json={
                "base_revision": 2,
                "pages": [{"sequence": 1, "text": "SYNTHETIC UNVERIFIED TEXT"}],
                "note": "New unverified version",
            },
        ).status_code
        == 201
    )
    real_client = httpx.Client
    monkeypatch.setattr(research, "model_identity", lambda *_: "synthetic-model")
    monkeypatch.setattr(research, "embeddings", lambda *_: [[0.1, 0.2]])
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: real_client(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(
                    200, json={"result": {"points": [{"id": str(passage["id"])}]}}
                )
            ),
            **kwargs,
        ),
    )
    result = client.post("/archive/research/ask", json={"question": "blue chairs"}).json()
    assert result["status"] == "insufficient_sources" and result["sources"] == []
    assert client.get(f"/archive/catalog/{item}").status_code == 404


@pytest.mark.integration
def test_pdf_page_locator_survives_retrieval_and_reader(archive, monkeypatch):
    from test_processing import upload_pdf

    client, config, admin, curator = archive
    config.ollama_embedding_model = ""
    item, original = upload_pdf(client, admin)
    base = f"/archive/staff/documents/{item}"
    assert client.post(base + "/processing", auth=curator, json={}).status_code == 202
    assert run_once(config)
    snapshot = client.get(base + "/text", auth=curator).json()
    assert (
        client.post(
            base + "/text/revisions",
            auth=curator,
            json={
                "base_revision": 1,
                "pages": [
                    {"sequence": p["sequence"], "text": p["text"]} for p in snapshot["segments"]
                ],
                "note": "Synthetic page review",
            },
        ).status_code
        == 201
    )
    assert (
        client.post(
            base + "/text/verify", auth=curator, json={"revision": 2, "original_compared": True}
        ).status_code
        == 200
    )
    assert (
        client.post(
            base + "/transition", auth=curator, json={"action": "verify", "metadata_reviewed": True}
        ).status_code
        == 200
    )
    assert (
        client.post(base + "/transition", auth=curator, json={"action": "publish"}).status_code
        == 200
    )
    assert index_once(config)
    monkeypatch.setattr(research, "generate_grounded", lambda *_: {"paragraphs": []})
    response = client.post("/archive/research/ask", json={"question": "ALPHA"}).json()
    assert response["sources"][0]["page_number"] == 1
    assert "#page-1" in response["sources"][0]["reader_url"]
    pages = client.get(f"/archive/catalog/{item}?revision=2").json()["pages"]
    assert [page["page_number"] for page in pages] == [1, 2]
    assert client.get(f"/archive/documents/{item}/original").content == original


@pytest.mark.integration
def test_volume_and_page_filters_never_broaden_source(archive, monkeypatch):
    client, config, _, _ = archive
    config.ollama_embedding_model = ""
    item, _, _ = publish_fixture(archive)
    with connect(config) as db:
        db.execute("UPDATE archival_item SET volume_number=7 WHERE id=%s", (UUID(item),))
    monkeypatch.setattr(research, "generate_grounded", lambda *_: {"paragraphs": []})
    assert client.post(
        "/archive/research/ask", json={"question": "blue chairs", "volume": 7}
    ).json()["sources"]
    assert (
        client.post("/archive/research/ask", json={"question": "blue chairs", "volume": 8}).json()[
            "sources"
        ]
        == []
    )
    assert (
        client.post(
            "/archive/research/ask", json={"question": "blue chairs", "item_id": item, "page": 999}
        ).json()["sources"]
        == []
    )


@pytest.mark.integration
def test_opt_in_real_gemini_cited_answer(archive):
    import os

    from app.config import Settings

    if os.getenv("RUN_GEMINI_ACCEPTANCE") != "1":
        pytest.skip("Explicit live Gemini opt-in; synthetic sources only")
    client, config, _, _ = archive
    actual = Settings()
    config.ai_provider = "gemini"
    config.gemini_api_key = actual.gemini_api_key
    config.gemini_model = actual.gemini_model
    config.ollama_embedding_model = ""
    item, _, _ = publish_fixture(archive)
    result = client.post(
        "/archive/research/ask",
        json={"question": "What color are the chairs? Answer in one sentence.", "item_id": item},
    ).json()
    assert result["status"] == "answered", result
    assert result["sources"][0]["item_id"] == item
    for paragraph in result["paragraphs"]:
        for evidence in paragraph["evidence"]:
            match = next(s for s in result["sources"] if s["passage_id"] == evidence["passage_id"])
            assert evidence["quote"] in match["excerpt"]
