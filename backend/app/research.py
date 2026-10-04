"""Public verified-text reading and source-grounded, permission-checked research."""

import re
import threading
import time
from collections import deque
from typing import Literal
from uuid import UUID, uuid4

import httpx
import psycopg
from fastapi import APIRouter, HTTPException, Query, Request
from psycopg.types.json import Jsonb
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.archive import SELECT
from app.db import connect
from app.llm import ProviderFailure, generate_grounded, provider_state
from app.research_index import ELIGIBLE, PASSAGES, collection_url, embeddings, model_identity

router = APIRouter(prefix="/archive")
capacity = threading.BoundedSemaphore(2)
request_times = deque()
rate_lock = threading.Lock()


class Question(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    question: str = Field(min_length=2, max_length=1200)
    history: list[str] = Field(default_factory=list, max_length=4)
    item_id: UUID | None = None
    volume: int | None = Field(default=None, ge=1, le=100)
    page: int | None = Field(default=None, ge=1)
    language: str = Field(default="", max_length=80)
    material_type: Literal[
        "", "document", "manuscript", "photograph", "audio", "video", "speech"
    ] = ""


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    passage_id: UUID
    quote: str = Field(min_length=8, max_length=1200)


class Paragraph(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=1800)
    evidence: list[Evidence] = Field(min_length=1, max_length=6)


class Answer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    paragraphs: list[Paragraph] = Field(max_length=5)


def intent(question):
    text = question.casefold().strip(" !?.")
    if text in {"hi", "hello", "hey", "namaste", "नमस्ते", "good morning", "good evening"}:
        return "greeting"
    if text in {"thanks", "thank you", "help", "what can you do", "how are you"}:
        return "scope"
    if re.search(
        r"\b(weather|stock price|sports score|write code|tell me a joke)\b", text
    ) and not re.search(r"\b(ambedkar|archive|source|document|speech|recording)\b", text):
        return "scope"
    if re.search(r"\b(summarize|summarise|summary)\b", text):
        return "summary"
    return "archive"


def empty_reason(config, data):
    # Counts are scoped to public eligible text; no restricted metadata is disclosed.
    with connect(config) as db:
        count = db.execute(
            "SELECT count(*) AS n FROM archival_item i JOIN text_revision r "
            "ON r.item_id=i.id AND r.revision=i.current_text_revision WHERE "
            + ELIGIBLE
            + " AND (%s::uuid IS NULL OR i.id=%s)",
            (data.item_id, data.item_id),
        ).fetchone()["n"]
        if not count:
            return (
                "no_eligible_content",
                "No verified, published public text is available in this scope. "
                "Curator verification and publication are separate requirements.",
            )
        indexed = db.execute(
            PASSAGES + " AND (%s::uuid IS NULL OR i.id=%s) LIMIT 1", (data.item_id, data.item_id)
        ).fetchone()
        if not indexed:
            return (
                "index_pending",
                "Eligible text exists, but its research index is not ready. Browse "
                "the verified reader or try again after indexing.",
            )
    return (
        "no_matching_content",
        "No matching verified passages were found for this question and its "
        "filters. Try a source title or different wording.",
    )


def validate_answer(raw, passages):
    answer = Answer.model_validate(raw)
    lookup = {str(p["id"]): p for p in passages}
    for paragraph in answer.paragraphs:
        for evidence in paragraph.evidence:
            source = lookup.get(str(evidence.passage_id))
            if not source or evidence.quote not in source["text"]:
                raise ValueError("Unsupported citation")
    return answer


def citation(p):
    return {
        "passage_id": str(p["id"]),
        "item_id": str(p["item_id"]),
        "title": p["title"],
        "volume_number": p.get("volume_number"),
        "part_number": p.get("part_number"),
        "revision": p["revision"],
        "page_number": p["page_number"],
        "start_seconds": p.get("start_seconds"),
        "end_seconds": p.get("end_seconds"),
        "sequence": p["sequence"],
        "excerpt": p["text"],
        "reader_url": f"/archive/{p['item_id']}?revision={p['revision']}#page-{p['sequence']}",
        "original_url": f"/api/archive/documents/{p['item_id']}/original",
    }


@router.get("/catalog")
def catalog(
    request: Request,
    q: str = Query(default="", max_length=200),
    language: str = Query(default="", max_length=80),
    material_type: str = Query(default="", max_length=30),
    origin: Literal["", "dataset", "other"] = "",
    collection: Literal["", "manuscripts", "photographs", "videos"] = "",
    sort: Literal["title", "newest", "oldest"] = "title",
    volume: int | None = Query(default=None, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
    limit: int = Query(default=200, ge=1, le=200),
):
    with connect(request.app.state.config) as db:
        return db.execute(
            SELECT + "WHERE i.review_status='published' AND i.access_level='public' "
            "AND (%s='' OR i.language=%s) AND (%s='' OR i.material_type=%s) "
            "AND (%s::integer IS NULL OR i.volume_number=%s) "
            "AND (%s='' OR strpos(lower(i.title || ' ' || i.description),"
            "lower(%s))>0) "
            "AND (%s='' OR EXISTS (SELECT 1 FROM corpus_file f "
            "WHERE f.checksum=a.checksum) = (%s='dataset')) "
            "AND (%s='' OR EXISTS (SELECT 1 FROM dataset_member m "
            "WHERE m.item_id=i.id AND m.collection=%s) OR "
            "(i.dataset_release_id IS NULL AND i.material_type=%s)) "
            "ORDER BY "
            + {"title": "i.title", "newest": "i.created_at DESC", "oldest": "i.created_at ASC"}[
                sort
            ]
            + ",i.id LIMIT %s OFFSET %s",
            (language, language, material_type, material_type, volume, volume, q, q,
             origin, origin, collection, collection,
             {"manuscripts": "manuscript", "photographs": "photograph", "videos": "video"}
             .get(collection, ""), limit, offset),
        ).fetchall()


@router.get("/catalog/{item_id}")
def detail(item_id: UUID, request: Request, revision: int | None = Query(default=None, ge=1)):
    with connect(request.app.state.config) as db:
        item = db.execute(
            SELECT + ("WHERE i.id=%s AND i.review_status='published' AND i.access_level='public'"),
            (item_id,),
        ).fetchone()
        if not item:
            raise HTTPException(404, "This document is not currently public")
        current = item["current_text_revision"]
        if revision is not None and revision != current:
            raise HTTPException(409, "This citation refers to an older text revision; search again")
        pages = db.execute(
            "SELECT s.sequence,s.page_number,s.text,s.extraction_method,"
            "s.start_seconds,s.end_seconds FROM text_segment s "
            "JOIN text_revision r ON r.item_id=s.item_id AND r.revision=s.revision "
            "WHERE s.item_id=%s AND s.revision=%s AND r.status='verified' ORDER BY s.sequence",
            (item_id, current),
        ).fetchall()
        return {"document": item, "pages": pages, "text_revision": current if pages else None}


def retrieve(config, data):
    query = " ".join([*data.history[-2:], data.question])[-2400:]
    # OR terms retain useful keyword matches when semantic services are unavailable.
    stopwords = set("a an the what which do does say about find tell me in of on is are".split())
    terms = [t for t in re.findall(r"[^\W_]+", query.lower()) if t not in stopwords]
    lexical_query = " OR ".join(terms[:80])
    if '"' in data.question:
        lexical_query = data.question  # PostgreSQL websearch preserves explicit phrase queries.
    with connect(config) as db:
        if data.item_id is None:
            matches = db.execute(
                "SELECT i.id FROM archival_item i JOIN text_revision r ON r.item_id=i.id "
                "AND r.revision=i.current_text_revision WHERE "
                + ELIGIBLE
                + " AND length(i.title)>=4 AND strpos(lower(%s),lower(i.title))>0 LIMIT 2",
                (query,),
            ).fetchall()
            if len(matches) == 1:
                data.item_id = matches[0]["id"]
        filters = (
            " AND (%s='' OR i.language=%s) AND (%s='' OR i.material_type=%s) AND "
            "(%s::uuid IS NULL OR i.id=%s) "
            "AND (%s::integer IS NULL OR i.volume_number=%s) "
            "AND (%s::integer IS NULL OR s.page_number=%s)"
        )
        params = (
            data.language,
            data.language,
            data.material_type,
            data.material_type,
            data.item_id,
            data.item_id,
            data.volume,
            data.volume,
            data.page,
            data.page,
        )
        if intent(data.question) == "summary" and data.item_id is not None:
            return (
                db.execute(
                    PASSAGES + filters + " ORDER BY s.sequence,p.char_start LIMIT 6", params
                ).fetchall(),
                "Source summary uses up to six verified excerpts; it is not a "
                "complete-volume summary.",
            )
        lexical = db.execute(
            PASSAGES + filters + " AND p.search_vector @@ websearch_to_tsquery('simple',%s) "
            "ORDER BY "
            "ts_rank_cd(p.search_vector,websearch_to_tsquery('simple',%s)) DESC "
            "LIMIT 6",
            (*params, lexical_query, lexical_query),
        ).fetchall()
    semantic = []
    warning = ""
    phase = "Embedding model unavailable or not configured"
    try:
        with httpx.Client(timeout=12, trust_env=False) as client:
            identity = model_identity(client, config)
            vector = embeddings(client, config, [query])[0]
            phase = "Qdrant collection unavailable or not indexed for the configured model"
            must = [{"key": "model", "match": {"value": identity}}]
            for key, value in [
                ("item_id", str(data.item_id) if data.item_id else None),
                ("language", data.language),
                ("material_type", data.material_type),
                ("volume_number", data.volume),
                ("page_number", data.page),
            ]:
                if value:
                    must.append({"key": key, "match": {"value": value}})
            response = client.post(
                collection_url(config) + "/points/query",
                json={
                    "query": vector,
                    "filter": {"must": must},
                    "limit": 30,
                    "with_payload": False,
                    "score_threshold": 0.45,
                },
            )
            response.raise_for_status()
            ids = [UUID(p["id"]) for p in response.json()["result"]["points"]]
            if ids:
                with connect(config) as db:
                    # Never trust vector payloads or stale vector visibility.
                    rows = db.execute(
                        PASSAGES + filters + " AND p.id=ANY(%s)", (*params, ids)
                    ).fetchall()
                lookup = {row["id"]: row for row in rows}
                semantic = [lookup[id_] for id_ in ids if id_ in lookup]
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        warning = f"Semantic search unavailable: {phase}. Using PostgreSQL text search only."
    # Reciprocal-rank fusion makes both lexical and semantic matches useful.
    scores, lookup = {}, {}
    for results in [lexical, semantic]:
        for rank, row in enumerate(results):
            lookup[row["id"]] = row
            scores[row["id"]] = scores.get(row["id"], 0) + 1 / (60 + rank)
    ordered = sorted(scores, key=scores.get, reverse=True)
    return [lookup[key] for key in ordered[:6]], warning


@router.post("/research/ask")
def ask(data: Question, request: Request):
    with rate_lock:
        now = time.monotonic()
        while request_times and request_times[0] < now - 60:
            request_times.popleft()
        if len(request_times) >= 30:
            raise HTTPException(429, "Kiosk research limit reached. Please wait a minute.")
        request_times.append(now)
    if any(len(message) > 1200 for message in data.history):
        raise HTTPException(422, "Prior questions must be at most 1200 characters")
    if not capacity.acquire(blocking=False):
        raise HTTPException(429, "The local assistant is busy. Please try again shortly.")
    try:
        return answer_question(request.app.state.config, data)
    except psycopg.Error:
        return {
            "status": "retrieval_unavailable",
            "reason": "postgresql_error",
            "message": "Archive database search is unavailable. Please retry later.",
            "paragraphs": [],
            "sources": [],
            "warning": "",
            "generation_attempted": False,
        }
    finally:
        capacity.release()


def answer_question(config, data):
    kind = intent(data.question)
    if kind in {"greeting", "scope"}:
        return {
            "status": kind,
            "reason": kind,
            "paragraphs": [],
            "sources": [],
            "warning": "",
            "generation_attempted": False,
            "message": (
                "Hello! I can help you explore the archive. Ask about a published "
                "source, or choose a document or recording to study."
                if kind == "greeting"
                else (
                    "I help with this archive’s documents and recordings. Choose a "
                    "published source, ask a source-based question, or request a "
                    "summary. No archive search was performed for this message."
                )
            ),
        }
    passages, warning = retrieve(config, data)
    result = {
        "status": "insufficient_sources",
        "paragraphs": [],
        "sources": [],
        "warning": warning,
        "generation_attempted": False,
        "scope_item_id": str(data.item_id) if data.item_id else None,
        "message": "The archive does not currently contain enough "
        "verified, published information to answer this question.",
    }
    if not passages:
        reason, message = empty_reason(config, data)
        result.update(reason=reason, message=message)
        return result
    with connect(config) as db:
        eligible = db.execute(
            PASSAGES + " AND p.id=ANY(%s)", ([p["id"] for p in passages],)
        ).fetchall()
    if len(eligible) != len(passages):
        result.update(status="sources_changed", message="Sources changed. Please ask again.")
        return result
    try:
        result["generation_attempted"] = True
        raw = generate_grounded(
            config,
            [
                {
                    "passage_id": str(p["id"]),
                    "text": p["text"],
                    "title": p["title"],
                    "page_number": p["page_number"],
                    "start_seconds": p.get("start_seconds"),
                    "end_seconds": p.get("end_seconds"),
                    "revision": p["revision"],
                }
                for p in passages
            ],
            data.question,
            data.history,
            Answer.model_json_schema(),
        )
        answer = validate_answer(raw, passages)
    except ProviderFailure as exc:
        result.update(status="model_unavailable", reason=exc.reason, message=str(exc))
        answer = None
    except httpx.TimeoutException:
        result.update(
            status="model_unavailable",
            reason="provider_timeout",
            message="The configured provider timed out. Read the verified excerpts or retry.",
        )
        answer = None
    except httpx.HTTPError:
        result.update(
            status="model_unavailable",
            reason="provider_network_error",
            message=(
                "The configured provider could not be reached. Read the verified excerpts or retry."
            ),
        )
        answer = None
    except (ValueError, KeyError, TypeError, ValidationError):
        result.update(
            status="invalid_response",
            reason="citation_or_response_invalid",
            message=(
                "The provider returned an invalid response or unsupported "
                "citations. No generated answer is shown; read the verified "
                "excerpts."
            ),
        )
        answer = None
    # Lock records while reauthorizing and saving. Publication changes must wait until commit.
    with connect(config) as db:
        ids = sorted({p["item_id"] for p in passages})
        db.execute("SELECT id FROM archival_item WHERE id=ANY(%s) ORDER BY id FOR SHARE", (ids,))
        current = db.execute(
            PASSAGES + " AND p.id=ANY(%s)", ([p["id"] for p in passages],)
        ).fetchall()
        if len(current) != len(passages):
            result.update(
                status="sources_changed",
                message="Source availability changed during this request. Please ask again.",
            )
            return result
        result["sources"] = [citation(p) for p in passages]
        if answer is not None and not answer.paragraphs:
            result.update(
                reason="provider_abstained",
                message="Verified excerpts were found, but the provider did not produce a "
                "supported answer. Read the excerpts or ask a more specific question.",
            )
        if answer and answer.paragraphs:
            artifact = uuid4()
            db.execute(
                "INSERT INTO generated_artifact(id,model,content) VALUES(%s,%s,%s)",
                (
                    artifact,
                    config.ai_provider
                    + ":"
                    + (
                        config.gemini_model
                        if config.ai_provider == "gemini"
                        else config.ollama_generation_model
                    ),
                    Jsonb(answer.model_dump(mode="json")),
                ),
            )
            for paragraph in answer.paragraphs:
                for evidence in paragraph.evidence:
                    db.execute(
                        "INSERT INTO artifact_evidence VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",
                        (artifact, evidence.passage_id, evidence.quote),
                    )
            result.update(
                status="answered",
                message="AI-generated summary. Check the original sources before relying on it.",
                artifact_id=str(artifact),
                paragraphs=answer.model_dump(mode="json")["paragraphs"],
            )
    return result


@router.get("/research/provider")
def generation_status(request: Request):
    config = request.app.state.config
    return {
        **provider_state(config),
        "semantic_configured": bool(config.ollama_embedding_model),
        "retrieval_message": (
            "Semantic search configured, not live-verified. PostgreSQL remains the fallback."
            if config.ollama_embedding_model
            else "No embedding model configured. Research uses PostgreSQL text search."
        ),
    }
