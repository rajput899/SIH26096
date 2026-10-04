"""Synthetic local processing fixtures: never archival holdings or historical evidence."""

import hashlib
import io
import json

import pytest
from test_archive import metadata

from app.db import connect
from app.extraction import extract
from app.worker import claim, finish, heartbeat, run_once


def scanned_fixture():
    from PIL import Image, ImageDraw, ImageFont

    pages = []
    for number, word in [(1, "ALPHA"), (2, "BETA")]:
        page = Image.new("RGB", (1240, 1754), "white")
        draw = ImageDraw.Draw(page)
        font = ImageFont.load_default(size=42)
        for line, text in enumerate(
            [
                "SYNTHETIC LOCAL TEST FIXTURE",
                f"PAGE {number} - {word}",
                "Created for OCR verification only.",
                "This is not historical archival material.",
                "The original file must remain unchanged.",
            ]
        ):
            draw.text((80, 100 + line * 85), text, font=font, fill="black")
        pages.append(page)
    output = io.BytesIO()
    pages[0].save(output, format="PDF", save_all=True, append_images=pages[1:], resolution=150)
    return output.getvalue()


def upload_pdf(client, admin, content=None):
    content = scanned_fixture() if content is None else content
    data = metadata(access_level="public")
    data["original_filename"] = "SYNTHETIC-processing-two-pages.pdf"
    response = client.post(
        "/archive/staff/documents",
        params={"metadata": json.dumps(data)},
        content=content,
        headers={"Content-Type": "application/pdf"},
        auth=admin,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"], content


def test_real_rapidocr_scanned_pdf_and_integrity(tmp_path):
    path = tmp_path / "synthetic.pdf"
    path.write_bytes(scanned_fixture())
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    result = extract(path, "application/pdf", checksum)
    assert [page["page_number"] for page in result["pages"]] == [1, 2]
    assert all(page["extraction_method"] == "rapidocr" for page in result["pages"])
    assert "ALPHA" in result["pages"][0]["text"]
    assert "BETA" in result["pages"][1]["text"]
    assert result["provenance"]["model_sha256"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == checksum
    with pytest.raises(ValueError, match="checksum"):
        extract(path, "application/pdf", "0" * 64)


@pytest.mark.integration
def test_real_worker_pages_review_versions_and_publication(archive):
    client, config, admin, curator = archive
    item, original = upload_pdf(client, admin)
    base = f"/archive/staff/documents/{item}"
    assert client.post(base + "/processing", json={}).status_code == 401
    job = client.post(base + "/processing", json={}, auth=curator)
    assert job.status_code == 202
    assert client.post(base + "/processing", json={}, auth=curator).json()["id"] == job.json()["id"]
    assert (
        client.post(
            base + "/transition", json={"action": "verify", "metadata_reviewed": True}, auth=curator
        ).status_code
        == 200
    )
    assert (
        client.post(base + "/transition", json={"action": "publish"}, auth=curator).status_code
        == 409
    )
    assert run_once(config)
    status = client.get(base + "/processing", auth=curator).json()
    assert status["status"] == "succeeded", status
    assert not run_once(config)
    record = client.get(base + "/text", auth=curator).json()
    assert record["snapshot"]["status"] == "extracted"
    assert [s["page_number"] for s in record["segments"]] == [1, 2]
    assert "ALPHA" in record["segments"][0]["text"]
    assert "BETA" in record["segments"][1]["text"]
    assert (
        client.post(
            base + "/text/verify", json={"revision": 1, "original_compared": True}, auth=curator
        ).status_code
        == 409
    )
    pages = [{"sequence": s["sequence"], "text": s["text"]} for s in record["segments"]]
    pages[0]["text"] += "\nSYNTHETIC CURATOR CORRECTION"
    review = {"base_revision": 1, "pages": pages, "note": "Synthetic curator correction test"}
    corrected = client.post(base + "/text/revisions", json=review, auth=curator)
    assert corrected.status_code == 201, corrected.text
    assert client.post(base + "/text/revisions", json=review, auth=curator).status_code == 409
    assert (
        client.get(base + "/text?revision=1", auth=curator).json()["segments"] == record["segments"]
    )
    assert (
        client.post(
            base + "/text/verify", json={"revision": 1, "original_compared": True}, auth=curator
        ).status_code
        == 409
    )
    assert (
        client.post(
            base + "/text/verify", json={"revision": 2, "original_compared": True}, auth=curator
        ).status_code
        == 200
    )
    assert client.get("/archive/documents").json() == []
    for action in ["verify", "publish"]:
        assert (
            client.post(
                base + "/transition",
                json={"action": action, "metadata_reviewed": True},
                auth=curator,
            ).status_code
            == 200
        )
    assert client.get("/archive/documents").json()[0]["id"] == item
    # A further correction preserves verified history but revokes publication immediately.
    assert (
        client.post(
            base + "/text/revisions", json={**review, "base_revision": 2}, auth=curator
        ).status_code
        == 201
    )
    assert client.get("/archive/documents").json() == []
    assert (
        client.get(base + "/text?revision=2", auth=curator).json()["snapshot"]["status"]
        == "verified"
    )
    assert client.get(base + "/original", auth=admin).content == original
    with connect(config) as db:
        segments = db.execute(
            "SELECT revision,page_number FROM text_segment WHERE item_id=%s "
            "ORDER BY revision,sequence",
            (item,),
        ).fetchall()
        assert [(s["revision"], s["page_number"]) for s in segments] == [
            (1, 1),
            (1, 2),
            (2, 1),
            (2, 2),
            (3, 1),
            (3, 2),
        ]
        assert (
            db.execute(
                "SELECT current_text_revision FROM archival_item WHERE id=%s", (item,)
            ).fetchone()["current_text_revision"]
            == 3
        )


@pytest.mark.integration
def test_failure_retry_and_crash_claim_fencing(archive):
    client, config, admin, curator = archive
    item, _ = upload_pdf(client, admin, b"%PDF-invalid synthetic fixture")
    base = f"/archive/staff/documents/{item}"
    client.post(base + "/processing", json={}, auth=curator)
    first = claim(config)
    assert first and claim(config) is None
    with connect(config) as db:
        db.execute(
            "UPDATE processing_job SET heartbeat_at=now()-interval '2 minutes' WHERE id=%s",
            (first["id"],),
        )
    second = claim(config)
    assert second["id"] == first["id"] and second["claim_token"] != first["claim_token"]
    assert not heartbeat(config, first)
    assert not finish(config, first, {"pages": [], "provenance": {}})
    with connect(config) as db:
        db.execute(
            "UPDATE processing_job SET heartbeat_at=now()-interval '2 minutes' WHERE id=%s",
            (second["id"],),
        )
    assert run_once(config)  # Actual invalid-PDF processing fails on its third claim.
    failed = client.get(base + "/processing", auth=curator).json()
    assert failed["status"] == "failed" and failed["attempts"] == 3
    assert client.post(base + "/processing/retry", auth=curator).status_code == 409
    assert client.get(base + "/text", auth=curator).json()["segments"] == []


@pytest.mark.integration
def test_failure_retry_and_page_validation(archive):
    client, config, admin, curator = archive
    item, _ = upload_pdf(client, admin, b"%PDF-invalid synthetic fixture")
    base = f"/archive/staff/documents/{item}"
    client.post(base + "/processing", json={}, auth=curator)
    assert run_once(config)
    assert client.get(base + "/processing", auth=curator).json()["status"] == "failed"
    assert client.post(base + "/processing/retry", auth=curator).status_code == 202
    assert client.get(base + "/processing", auth=curator).json()["attempts"] == 1
    assert (
        client.post(
            base + "/text/revisions",
            json={"base_revision": 1, "pages": [{"sequence": 1, "text": "test"}], "note": "test"},
            auth=curator,
        ).status_code
        == 409
    )


def test_plain_text_has_no_invented_page_number(tmp_path):
    path = tmp_path / "synthetic.txt"
    path.write_text("SYNTHETIC plain text fixture", encoding="utf-8")
    result = extract(path, "text/plain", hashlib.sha256(path.read_bytes()).hexdigest())
    assert result["pages"][0]["page_number"] is None
    assert result["pages"][0]["extraction_method"] == "plain_text"


def test_embedded_pdf_text_extraction(tmp_path):
    # Minimal ASCII PDF authored solely for a parser test, not archival material.
    stream = b"BT /F1 20 Tf 50 700 Td (SYNTHETIC EMBEDDED TEXT FIXTURE) Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    data = b"%PDF-1.4\n"
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data += f"{number} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(data)
    data += b"xref\n0 6\n0000000000 65535 f \n"
    data += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])
    data += f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    path = tmp_path / "synthetic-embedded.pdf"
    path.write_bytes(data)
    result = extract(path, "application/pdf", hashlib.sha256(data).hexdigest())
    assert result["pages"][0]["text"] == "SYNTHETIC EMBEDDED TEXT FIXTURE"
    assert result["pages"][0]["page_number"] == 1
    assert result["pages"][0]["extraction_method"] == "pdf_text"
