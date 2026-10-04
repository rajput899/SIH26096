"""Read-only model/vector checks; never claim an index exists from configuration alone."""

import json

import httpx

from app.config import Settings
from app.db import connect
from app.research_index import ELIGIBLE, collection_url, embeddings, model_identity


def check(config):
    report = {
        "embedding_model": config.ollama_embedding_model,
        "collection": config.research_collection,
        "semantic_ready": False,
    }
    with connect(config) as db:
        report["eligible_passages"] = db.execute(
            "SELECT count(*) n FROM passage p JOIN archival_item i ON i.id=p.item_id "
            "JOIN text_revision r ON r.item_id=p.item_id AND r.revision=p.revision WHERE "
            + ELIGIBLE
        ).fetchone()["n"]
    try:
        with httpx.Client(timeout=60, trust_env=False) as client:
            report["model_identity"] = model_identity(client, config)
            vector = embeddings(client, config, ["Archive research: equality and education."])[0]
            report["vector_dimensions"] = len(vector)
            report["embedding_verified"] = True
            response = client.get(collection_url(config))
            if response.status_code == 404:
                report["collection_state"] = "not_created; no eligible indexed content"
            else:
                response.raise_for_status()
                state = response.json()["result"]
                report["collection_dimensions"] = state["config"]["params"]["vectors"]["size"]
                query = client.post(
                    collection_url(config) + "/points/query",
                    json={
                        "query": vector,
                        "limit": 1,
                        "with_payload": False,
                        "filter": {
                            "must": [{"key": "model", "match": {"value": report["model_identity"]}}]
                        },
                    },
                )
                query.raise_for_status()
                report["query_verified"] = True
                report["semantic_ready"] = bool(
                    report["eligible_passages"] and query.json()["result"]["points"]
                )
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        report["error"] = type(exc).__name__
    return report


if __name__ == "__main__":
    print(json.dumps(check(Settings()), indent=2))
