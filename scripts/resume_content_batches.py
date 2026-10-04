"""Bounded continuation of existing private PDF checkpoints; never register new files.

Uses the existing importer's advisory lock and immutable-text finalization guards.
Held compilations, failed pages and existing text revisions are not reprocessed.
"""
import argparse
import json
from pathlib import Path

from app.config import Settings
from app.corpus import checksum, run
from app.db import connect


def pending(config):
    with connect(config) as db:
        db.execute("SET TRANSACTION READ ONLY")
        return db.execute("""
            SELECT f.relative_path,f.page_count,f.checksum,i.current_text_revision,
              count(*) FILTER(WHERE p.status='ocr_pending') AS pending,
              count(*) FILTER(WHERE p.status='failed') AS failed,
              count(*) FILTER(WHERE p.status='extracted') AS extracted
            FROM corpus_file f JOIN corpus_page p USING(checksum)
            JOIN archival_item i ON i.id=f.item_id
            GROUP BY f.checksum,i.current_text_revision
            HAVING count(*) FILTER(WHERE p.status<>'extracted')>0
            ORDER BY (f.relative_path LIKE 'Volume_%%') DESC,f.relative_path
        """).fetchall()


def resume(root, batch_pages, max_batches):
    config = Settings()
    for batch in range(1, max_batches + 1):
        rows = pending(config)
        eligible = [r for r in rows if r["page_count"] <= 5000
                    and r["current_text_revision"] is None and not r["failed"]]
        if not eligible:
            print(json.dumps({"finished": True, "remaining": rows}, default=str), flush=True)
            return
        row = eligible[0]
        path = (root / row["relative_path"]).resolve(strict=True)
        if not path.is_relative_to(root) or checksum(path) != row["checksum"]:
            raise RuntimeError(
                "Existing source changed; stop before any registration or processing"
            )
        print(json.dumps({"batch": batch, "file": row["relative_path"],
                          "before_pending": row["pending"], "limit": batch_pages}), flush=True)
        # Exact existing file, original hash checked by the importer. No auto-publication.
        run(config, root, ocr_pages=batch_pages, max_pages=batch_pages,
            relative_path=row["relative_path"])
        after = next((r for r in pending(config) if r["checksum"] == row["checksum"]), None)
        remaining = after["pending"] if after else 0
        print(json.dumps({"batch": batch, "file": row["relative_path"],
                          "after_pending": remaining,
                          "failed": after["failed"] if after else 0}), flush=True)
        if after and (after["failed"] or remaining >= row["pending"]):
            raise RuntimeError(
                "Batch failed or made no progress; checkpoints retained for inspection"
            )
    print(json.dumps({"batch_limit_reached": True, "remaining": pending(config)}, default=str),
          flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--batch-pages", type=int, choices=range(1, 51), default=25)
    parser.add_argument("--max-batches", type=int, choices=range(1, 61), default=1)
    args = parser.parse_args()
    resume(args.root.resolve(strict=True), args.batch_pages, args.max_batches)
