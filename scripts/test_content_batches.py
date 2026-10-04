"""Safety checks for the operator wrapper; no database, model or dataset writes."""
import hashlib
import json

import pytest
import resume_content_batches as batches


def checkpoint(tmp_path):
    path = tmp_path / "Volume_01.pdf"
    path.write_bytes(b"synthetic wrapper fixture, not a PDF")
    return {"relative_path": path.name, "checksum": hashlib.sha256(path.read_bytes()).hexdigest(),
            "page_count": 12, "current_text_revision": None, "pending": 12,
            "failed": 0, "extracted": 0}


def test_changed_source_stops_before_import(tmp_path, monkeypatch):
    row = checkpoint(tmp_path)
    (tmp_path / row["relative_path"]).write_bytes(b"changed")
    monkeypatch.setattr(batches, "pending", lambda _: [row])
    monkeypatch.setattr(batches, "run", lambda *_a, **_k: pytest.fail("Importer must not run"))
    with pytest.raises(RuntimeError, match="Existing source changed"):
        batches.resume(tmp_path, 5, 1)


def test_held_failed_and_existing_text_are_never_processed(tmp_path, monkeypatch, capsys):
    row = checkpoint(tmp_path)
    rows = [dict(row, page_count=5001), dict(row, failed=1),
            dict(row, current_text_revision=2)]
    monkeypatch.setattr(batches, "pending", lambda _: rows)
    monkeypatch.setattr(batches, "run", lambda *_a, **_k: pytest.fail("Importer must not run"))
    batches.resume(tmp_path, 5, 1)
    assert json.loads(capsys.readouterr().out)["remaining"] == rows


def test_no_progress_stops_instead_of_repeating(tmp_path, monkeypatch):
    row = checkpoint(tmp_path)
    calls = []
    monkeypatch.setattr(batches, "pending", lambda _: [row])
    monkeypatch.setattr(batches, "run", lambda *_a, **kwargs: calls.append(kwargs))
    with pytest.raises(RuntimeError, match="made no progress"):
        batches.resume(tmp_path, 5, 20)
    assert calls == [{"ocr_pages": 5, "max_pages": 5, "relative_path": row["relative_path"]}]


def test_batch_limit_retains_remaining_checkpoint_work(tmp_path, monkeypatch, capsys):
    row = checkpoint(tmp_path)
    calls = []
    monkeypatch.setattr(batches, "pending", lambda _: [row])

    def process(*_args, **kwargs):
        calls.append(kwargs)
        # DB queries return fresh dictionaries; avoid mutating the before-snapshot.
        nonlocal row
        row = dict(row, pending=row["pending"] - kwargs["ocr_pages"])

    monkeypatch.setattr(batches, "run", process)
    batches.resume(tmp_path, 5, 2)
    result = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert len(calls) == 2 and result["batch_limit_reached"]
    assert result["remaining"][0]["pending"] == 2
