"""Durable, retryable derivatives in the existing worker; PostgreSQL is the authority."""

import hashlib
import math
from uuid import NAMESPACE_URL, uuid5

import httpx

from app.db import connect

ELIGIBLE = """i.review_status='published' AND i.access_level='public'
 AND r.status='verified' AND r.revision=i.current_text_revision"""
PASSAGES = (
    """SELECT p.*,i.title,i.language,i.material_type,i.volume_number,i.part_number,
 s.page_number,s.sequence,
 s.start_seconds,s.end_seconds
 FROM passage p JOIN archival_item i ON i.id=p.item_id
 JOIN text_revision r ON r.item_id=p.item_id AND r.revision=p.revision
 JOIN text_segment s ON s.id=p.segment_id WHERE """
    + ELIGIBLE
)


def chunks(text, size=1200, overlap=120):
    """Exact offsets within one page; never manufacture or merge page locators."""
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError("Chunk overlap must be nonnegative and smaller than size")
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if text[start:end].strip():
            yield start, end, text[start:end]
        if end == len(text):
            break
        start = end - overlap


def model_identity(client, config):
    model = config.ollama_embedding_model
    if not model:
        raise ValueError("Embedding model not configured")
    response = client.get(f"{str(config.ollama_base_url).rstrip('/')}/api/tags")
    response.raise_for_status()
    for installed in response.json()["models"]:
        if installed["name"] in {model, model + ":latest"}:
            return hashlib.sha256(f"{model}:{installed['digest']}".encode()).hexdigest()
    raise ValueError("Embedding model not installed")


def embeddings(client, config, texts):
    response = client.post(
        f"{str(config.ollama_base_url).rstrip('/')}/api/embed",
        json={
            "model": config.ollama_embedding_model,
            "input": texts,
            "truncate": False,
            "keep_alive": "30m",
            "options": {"num_thread": 2},
        },
    )
    response.raise_for_status()
    vectors = response.json()["embeddings"]
    if not isinstance(vectors, list) or len(vectors) != len(texts) or not vectors:
        raise ValueError("Invalid embeddings")
    dimension = len(vectors[0]) if isinstance(vectors[0], list) else 0
    if not dimension or any(
        not isinstance(vector, list)
        or len(vector) != dimension
        or any(type(value) not in (int, float) or not math.isfinite(value) for value in vector)
        or not any(value != 0 for value in vector)
        for vector in vectors
    ):
        raise ValueError("Embeddings must have equal dimensions and finite nonzero vectors")
    return vectors


def collection_url(config):
    return f"{str(config.qdrant_url).rstrip('/')}/collections/{config.research_collection}"


def index_once(config):
    # A session advisory lock survives commits and is released on worker crash.
    with connect(config) as db, httpx.Client(timeout=30, trust_env=False) as client:
        if not db.execute(
            "SELECT pg_try_advisory_lock(hashtext(current_schema()),260963) AS locked"
        ).fetchone()["locked"]:
            return False
        try:
            state = db.execute(
                "SELECT * FROM search_index_state WHERE retry_at<=now() "
                "AND status<>'withdrawn' ORDER BY retry_at LIMIT 1"
            ).fetchone()
            if not state:
                return False
            item = state["item_id"]
            db.execute("SELECT id FROM archival_item WHERE id=%s FOR SHARE", (item,))
            row = db.execute(
                "SELECT i.current_text_revision FROM archival_item i JOIN text_revision r "
                "ON r.item_id=i.id AND r.revision=i.current_text_revision WHERE i.id=%s AND "
                + ELIGIBLE,
                (item,),
            ).fetchone()
            if not row:
                # SQL permission checks already make any old vectors inaccessible.
                try:
                    response = client.post(
                        collection_url(config) + "/points/delete?wait=true",
                        json={
                            "filter": {"must": [{"key": "item_id", "match": {"value": str(item)}}]}
                        },
                    )
                    if response.status_code != 404:
                        response.raise_for_status()
                except httpx.HTTPError:
                    db.execute(
                        "UPDATE search_index_state SET retry_at=now()+interval '1 minute' "
                        "WHERE item_id=%s",
                        (item,),
                    )
                    return True
                db.execute(
                    "UPDATE search_index_state SET status='withdrawn' WHERE item_id=%s", (item,)
                )
                return True
            revision = row["current_text_revision"]
            segments = db.execute(
                "SELECT * FROM text_segment WHERE item_id=%s AND revision=%s", (item, revision)
            ).fetchall()
            for segment in segments:
                for start, end, text in chunks(segment["text"]):
                    passage_id = uuid5(NAMESPACE_URL, f"{segment['id']}:{start}")
                    db.execute(
                        "INSERT INTO passage(id,item_id,revision,segment_id,"
                        "char_start,char_end,text)"
                        " VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                        (passage_id, item, revision, segment["id"], start, end, text),
                    )
            db.execute(
                "UPDATE search_index_state SET revision=%s,status='lexical',"
                "retry_at=now()+interval '1 minute' WHERE item_id=%s",
                (revision, item),
            )
            db.commit()  # Lexical search works even when model/vector services are offline.
            try:
                identity = model_identity(client, config)
                registered = db.execute(
                    "SELECT * FROM vector_index_registry WHERE collection=%s",
                    (config.research_collection,),
                ).fetchone()
                if registered and registered["model_identity"] != identity:
                    raise ValueError("Changed embedding model requires a new collection")
                passages = db.execute(PASSAGES + " AND p.item_id=%s", (item,)).fetchall()
                # Periodically inspect the model digest, but avoid embedding unchanged text.
                if (
                    state["status"] == "ready"
                    and state["revision"] == revision
                    and state["model_identity"] == identity
                ):
                    existing = client.get(collection_url(config))
                    if existing.is_success:
                        passages = []
                existing = client.get(collection_url(config))
                if existing.status_code == 404:
                    db.execute(
                        "DELETE FROM passage_embedding WHERE collection=%s",
                        (config.research_collection,),
                    )
                elif not registered:
                    existing.raise_for_status()
                    if existing.json()["result"].get("points_count", 0):
                        raise ValueError("Existing unregistered vectors require a new collection")
                done = {
                    r["passage_id"]
                    for r in db.execute(
                        "SELECT passage_id FROM passage_embedding WHERE collection=%s "
                        "AND model_identity=%s",
                        (config.research_collection, identity),
                    )
                }
                passages = [p for p in passages if p["id"] not in done]
                for offset in range(0, len(passages), 8):
                    batch = passages[offset : offset + 8]
                    vectors = embeddings(client, config, [p["text"] for p in batch])
                    url = collection_url(config)
                    existing = client.get(url)
                    if existing.status_code == 404:
                        created = client.put(
                            url, json={"vectors": {"size": len(vectors[0]), "distance": "Cosine"}}
                        )
                        created.raise_for_status()
                    else:
                        existing.raise_for_status()
                        size = existing.json()["result"]["config"]["params"]["vectors"]["size"]
                        if size != len(vectors[0]):
                            raise ValueError("Different dimensions require a new collection")
                    db.execute(
                        """INSERT INTO vector_index_registry
                        (collection,model_identity,model_name,dimensions) VALUES(%s,%s,%s,%s)
                        ON CONFLICT DO NOTHING""",
                        (
                            config.research_collection,
                            identity,
                            config.ollama_embedding_model,
                            len(vectors[0]),
                        ),
                    )
                    result = client.put(
                        url + "/points?wait=true",
                        json={
                            "points": [
                                {
                                    "id": str(p["id"]),
                                    "vector": vector,
                                    "payload": {
                                        "item_id": str(item),
                                        "revision": revision,
                                        "model": identity,
                                        "language": p["language"],
                                        "material_type": p["material_type"],
                                        "volume_number": p["volume_number"],
                                        "page_number": p["page_number"],
                                    },
                                }
                                for p, vector in zip(batch, vectors, strict=True)
                            ]
                        },
                    )
                    result.raise_for_status()
                    for passage in batch:
                        db.execute(
                            """INSERT INTO passage_embedding(passage_id,collection,model_identity)
                            VALUES(%s,%s,%s) ON CONFLICT(passage_id,collection) DO UPDATE SET
                            model_identity=EXCLUDED.model_identity,indexed_at=now()""",
                            (passage["id"], config.research_collection, identity),
                        )
                    db.commit()  # Confirm each batch; deterministic IDs prevent duplicates.
                db.execute(
                    "UPDATE search_index_state SET status='ready',model_identity=%s,"
                    "error=NULL,updated_at=now(),retry_at=now()+interval '5 minutes' "
                    "WHERE item_id=%s AND revision=%s AND status='lexical'",
                    (identity, item, revision),
                )
            except (httpx.HTTPError, ValueError, KeyError, TypeError):
                db.execute(
                    "UPDATE search_index_state SET attempts=attempts+1,"
                    "error='Semantic indexing unavailable; lexical search retained',"
                    "retry_at=now()+interval '1 minute' WHERE item_id=%s",
                    (item,),
                )
            return True
        finally:
            db.execute("SELECT pg_advisory_unlock(hashtext(current_schema()),260963)")
