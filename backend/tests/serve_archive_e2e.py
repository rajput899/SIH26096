"""Isolated browser fixture server; run with python -m tests.serve_archive_e2e.

Never serves against the production schema or archive volume. Stop with SIGINT to clean up.
"""

import json
import os
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

import httpx
import uvicorn
from psycopg import sql

from app.config import Settings
from app.db import connect, migrate
from app.staff import hash_password


def main():
    # Automated browser checks must never incur cloud inference or send real mail.
    os.environ["AI_PROVIDER"] = "ollama"
    os.environ["GEMINI_API_KEY"] = ""
    os.environ["SMTP_HOST"] = ""
    if os.getenv("RUN_AI_ACCEPTANCE") != "1":
        os.environ["OLLAMA_GENERATION_MODEL"] = ""
        os.environ["OLLAMA_EMBEDDING_MODEL"] = ""
    config = Settings()
    schema = "test_browser_" + uuid4().hex
    with connect(config) as db:
        db.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    auth_path = Path("/tmp/archive-e2e-auth.json")
    try:
        os.environ["PGOPTIONS"] = f"-c search_path={schema}"
        os.environ["RESEARCH_COLLECTION"] = schema
        with tempfile.TemporaryDirectory(prefix="archive-browser-") as root:
            os.environ["ARCHIVE_ROOT"] = root
            migrate(config)
            login, password = "synthetic-browser-admin", secrets.token_hex(24)
            with connect(config) as db:
                db.execute(
                    "INSERT INTO staff_user(id,login,password_hash,role) VALUES (%s,%s,%s,%s)",
                    (uuid4(), login, hash_password(password), "admin"),
                )
            auth_path.write_text(
                json.dumps(
                    {
                        "login": login,
                        "password": password,
                        "schema": schema,
                        "storage_root": root,
                        "pid": os.getpid(),
                    }
                )
            )
            auth_path.chmod(0o600)
            worker = None
            if os.getenv("PROCESSING_E2E") == "1":
                # Uses the same isolated schema and storage inherited through the environment.
                worker = subprocess.Popen([sys.executable, "-m", "app.worker"])
            try:
                uvicorn.run("app.main:app", host="0.0.0.0", port=8011, access_log=False)
            finally:
                if worker is not None:
                    worker.terminate()
                    worker.wait(timeout=15)
    finally:
        try:
            httpx.delete(
                f"{str(config.qdrant_url).rstrip('/')}/collections/{schema}",
                timeout=5,
                trust_env=False,
            ).raise_for_status()
        except httpx.HTTPError:
            pass
        auth_path.unlink(missing_ok=True)
        os.environ.pop("PGOPTIONS", None)
        with connect(config) as db:
            db.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    main()
