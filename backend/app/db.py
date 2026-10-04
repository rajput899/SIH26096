from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from app.config import Settings


def connect(config: Settings):
    return psycopg.connect(
        host=config.postgres_host,
        port=config.postgres_port,
        dbname=config.postgres_db,
        user=config.postgres_user,
        password=config.postgres_password.get_secret_value(),
        row_factory=dict_row,
        connect_timeout=5,
    )


def migrate(config: Settings):
    with connect(config) as db:
        db.execute("SELECT pg_advisory_xact_lock(26096)")
        db.execute("CREATE TABLE IF NOT EXISTS schema_migration (version text PRIMARY KEY)")
        for path in sorted((Path(__file__).parent / "migrations").glob("*.sql")):
            if not db.execute(
                "SELECT 1 FROM schema_migration WHERE version=%s", (path.name,)
            ).fetchone():
                db.execute(path.read_text())
                db.execute("INSERT INTO schema_migration VALUES (%s)", (path.name,))
