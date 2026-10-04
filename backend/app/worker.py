"""Single PostgreSQL worker, with fenced claims and recoverable crashed jobs."""

import argparse
import json
import logging
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from uuid import uuid4

from app.config import Settings
from app.db import connect, migrate
from app.processing import insert_segment

logger = logging.getLogger(__name__)


def claim(config):
    with connect(config) as db:
        db.execute("""UPDATE processing_job SET status=CASE WHEN attempts<3 THEN 'queued'
            ELSE 'failed' END, claim_token=NULL, error='Worker lease expired', updated_at=now()
            WHERE status='running' AND heartbeat_at < now() - interval '90 seconds'""")
        job = db.execute("""SELECT * FROM processing_job WHERE status='queued' AND attempts<3
            ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1""").fetchone()
        if not job:
            return None
        return db.execute(
            """UPDATE processing_job SET status='running', attempts=attempts+1,
            claim_token=%s, claimed_at=now(), heartbeat_at=now(), error=NULL, updated_at=now()
            WHERE id=%s RETURNING *""",
            (uuid4(), job["id"]),
        ).fetchone()


def heartbeat(config, job):
    with connect(config) as db:
        return (
            db.execute(
                """UPDATE processing_job SET heartbeat_at=now()
            WHERE id=%s AND claim_token=%s AND status='running' RETURNING id""",
                (job["id"], job["claim_token"]),
            ).fetchone()
            is not None
        )


def finish(config, job, result):
    with connect(config) as db:
        # Same lock order as HTTP review/retry: item, then job.
        item = db.execute(
            "SELECT * FROM archival_item WHERE id=%s FOR UPDATE", (job["item_id"],)
        ).fetchone()
        active = db.execute(
            """SELECT * FROM processing_job WHERE id=%s AND claim_token=%s
            AND status='running' FOR UPDATE""",
            (job["id"], job["claim_token"]),
        ).fetchone()
        if not active:
            return False
        if item["current_text_revision"] is not None:
            raise ValueError("Text already exists; refusing to overwrite a revision")
        db.execute(
            """INSERT INTO text_revision
            (item_id,revision,job_id,status,created_by,provenance)
            VALUES (%s,1,%s,'extracted',%s,%s)""",
            (job["item_id"], job["id"], job["requested_by"], json.dumps(result["provenance"])),
        )
        for page in result["pages"]:
            insert_segment(db, job["item_id"], job["asset_id"], 1, page)
        db.execute(
            "UPDATE archival_item SET current_text_revision=1, updated_at=now() WHERE id=%s",
            (job["item_id"],),
        )
        db.execute(
            """UPDATE processing_job SET status='succeeded', output_reference=1,
            heartbeat_at=now(), updated_at=now() WHERE id=%s""",
            (job["id"],),
        )
        return True


def fail(config, job, message):
    with connect(config) as db:
        db.execute(
            """UPDATE processing_job SET status='failed', error=%s, updated_at=now()
            WHERE id=%s AND claim_token=%s AND status='running'""",
            (message, job["id"], job["claim_token"]),
        )


def run_once(config):
    job = claim(config)
    if not job:
        return False
    try:
        with connect(config) as db:
            asset = db.execute("SELECT * FROM asset WHERE id=%s", (job["asset_id"],)).fetchone()
        with tempfile.TemporaryDirectory(prefix="archive-processing-") as directory:
            parameters, output = Path(directory) / "input.json", Path(directory) / "output.json"
            parameters.write_text(
                json.dumps(
                    {
                        "path": str(Path(config.archive_root) / asset["storage_key"]),
                        "mime": asset["mime_type"],
                        "checksum": asset["checksum"],
                        "mode": job["mode"],
                    }
                ),
                encoding="utf-8",
            )
            # Separate process provides a hard timeout even if a native PDF/OCR call hangs.
            with subprocess.Popen(
                [sys.executable, "-m", "app.extraction", str(parameters), str(output)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            ) as process:
                started = time.monotonic()
                try:
                    while process.poll() is None:
                        if time.monotonic() - started > config.processing_timeout_seconds:
                            raise TimeoutError("Processing timeout")
                        if not heartbeat(config, job):
                            raise ValueError("Worker lease lost")
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            pass
                    if process.returncode != 0:
                        raise ValueError(
                            "Extraction failed: check format, integrity, limits and OCR runtime"
                        )
                    finish(config, job, json.loads(output.read_text(encoding="utf-8")))
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.wait()
    except Exception as exc:
        # Never persist arbitrary exception text containing source text, credentials or paths.
        message = (
            "Processing timed out"
            if isinstance(exc, TimeoutError)
            else "Extraction failed; check original integrity, format, limits and runtime"
        )
        fail(config, job, message)
        logger.warning("Processing job %s failed (%s)", job["id"], type(exc).__name__)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    config = Settings()
    migrate(config)
    if args.once:
        run_once(config)
        return
    while True:
        try:
            if not run_once(config):
                from app.research_index import index_once

                if not index_once(config):
                    time.sleep(2)
        except Exception:
            logger.exception("Worker database unavailable; retrying")
            time.sleep(5)


if __name__ == "__main__":
    main()
