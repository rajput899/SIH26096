import os
import secrets
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from psycopg import sql

from app.config import Settings
from app.db import connect, migrate
from app.main import create_app
from app.staff import hash_password


@pytest.fixture
def settings():
    # Synthetic configuration, never used as real service credentials.
    return Settings(
        _env_file=None,
        ai_provider="ollama",
        gemini_api_key="",
        bhashini_inference_key="",
        bhashini_udyat_key="",
        bhashini_user_id="",
        smtp_host="",
        ollama_generation_model="",
        ollama_embedding_model="",
        generation_timeout_seconds=45,
        research_collection="synthetic_unit_test",
        postgres_db="test_fixture",
        postgres_user="test_fixture",
        postgres_password=secrets.token_hex(16),
    )


@pytest.fixture
def archive(tmp_path, monkeypatch):
    if os.getenv("RUN_INTEGRATION") != "1":
        pytest.skip("Set RUN_INTEGRATION=1 for real PostgreSQL")
    config = Settings(
        archive_root=str(tmp_path),
        ai_provider="ollama",
        gemini_api_key="",
        smtp_host="",
        bhashini_inference_key="",
        bhashini_udyat_key="",
        bhashini_user_id="",
    )
    if os.getenv("RUN_AI_ACCEPTANCE") != "1":
        config.ollama_generation_model = ""
        config.ollama_embedding_model = ""
    from app import research

    research.request_times.clear()
    schema = "test_archive_" + uuid4().hex
    config.research_collection = schema
    with connect(config) as db:
        db.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    monkeypatch.setenv("PGOPTIONS", f"-c search_path={schema}")
    try:
        migrate(config)
        migrate(config)  # Repeat migration must preserve the existing schema/data.
        password = uuid4().hex
        with connect(config) as db:
            for login, role in [("synthetic-admin", "admin"), ("synthetic-curator", "curator")]:
                db.execute(
                    "INSERT INTO staff_user(id,login,password_hash,role) VALUES (%s,%s,%s,%s)",
                    (uuid4(), login, hash_password(password), role),
                )
        with TestClient(create_app(config)) as client:
            yield client, config, ("synthetic-admin", password), ("synthetic-curator", password)
    finally:
        if config.ollama_embedding_model:
            try:
                httpx.delete(
                    f"{str(config.qdrant_url).rstrip('/')}/collections/{schema}",
                    timeout=5,
                    trust_env=False,
                ).raise_for_status()
            except httpx.HTTPError:
                pass  # No collection is created by non-vector tests or unavailable services.
        monkeypatch.delenv("PGOPTIONS")
        with connect(config) as db:
            db.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
