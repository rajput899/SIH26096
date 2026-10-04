"""Read-only archive snapshot for the language regression; excludes credentials."""
import json

from psycopg import sql

from app.config import Settings
from app.db import connect
from app.research_index import ELIGIBLE

tables = [
    "archival_item", "asset", "source", "text_revision", "text_segment", "passage",
    "corpus_file", "corpus_page", "dataset_release", "dataset_member", "schema_migration",
]
with connect(Settings()) as db:
    db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
    snapshots = {}
    for table in tables:
        snapshots[table] = db.execute(sql.SQL(
            "SELECT count(*) AS count, md5(string_agg(h, ',' ORDER BY h)) AS fingerprint "
            "FROM (SELECT md5(row_to_json(t)::text) AS h FROM {} t) rows"
        ).format(sql.Identifier(table))).fetchone()
    eligible = db.execute(
        "SELECT i.id,i.current_text_revision FROM archival_item i JOIN text_revision r "
        "ON r.item_id=i.id AND r.revision=i.current_text_revision WHERE " + ELIGIBLE
        + " ORDER BY i.id"
    ).fetchall()
    publication = db.execute(
        "SELECT review_status,access_level,count(*) FROM archival_item "
        "GROUP BY review_status,access_level ORDER BY review_status,access_level"
    ).fetchall()
print(json.dumps({"tables": snapshots, "eligible": eligible, "publication": publication},
                 default=str, indent=2))
