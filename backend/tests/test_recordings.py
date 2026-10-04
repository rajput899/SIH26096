"""Self-created silence is a test fixture, never an authentic historical recording."""

import io
import json
import shutil
import subprocess
import wave

import pytest
from pydantic import ValidationError
from test_archive import metadata

from app.recording_probe import inspect_recording
from app.recordings import Cue


def wav_fixture():
    output = io.BytesIO()
    with wave.open(output, "wb") as recording:
        recording.setnchannels(1)
        recording.setsampwidth(2)
        recording.setframerate(8000)
        recording.writeframes(b"\x00\x00" * 8000)
    return output.getvalue()


def test_recording_probe_uses_actual_duration(tmp_path):
    path = tmp_path / "synthetic-silence.wav"
    original = wav_fixture()
    path.write_bytes(original)
    assert inspect_recording(path, "audio/wav")["duration_seconds"] == 1
    assert path.read_bytes() == original
    path.write_bytes(original[:-100])
    with pytest.raises(ValueError, match="Truncated"):
        inspect_recording(path, "audio/wav")
    for values in [
        dict(start=0, end=0, text="Test"),
        dict(start=2, end=1, text="Test"),
        dict(start=0, end=float("nan"), text="Test"),
    ]:
        with pytest.raises(ValidationError):
            Cue(**values)


@pytest.mark.parametrize("mime,suffix", [("audio/mpeg", ".mp3"), ("video/mp4", ".mp4")])
def test_actual_ffmpeg_test_assets_match_declared_container(tmp_path, mime, suffix):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("FFmpeg/ffprobe required for actual media fixture validation")
    path = tmp_path / ("SYNTHETIC-self-created-silence" + suffix)
    command = ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=8000:cl=mono"]
    if suffix == ".mp4":
        command += [
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=32x32:r=10",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
        ]
    else:
        command += ["-c:a", "libmp3lame"]
    subprocess.run([*command, "-t", "1", str(path)], check=True, capture_output=True, timeout=30)
    result = inspect_recording(path, mime)
    assert 0 < result["duration_seconds"] < 2
    with pytest.raises(ValueError, match="container"):
        inspect_recording(path, "video/mp4" if suffix == ".mp3" else "audio/mpeg")


@pytest.mark.integration
def test_recording_original_range_transcript_review_and_withdrawal(archive, monkeypatch):
    from app import research
    from app.db import connect
    from app.research import Question, retrieve
    from app.research_index import index_once

    client, config, admin, curator = archive
    config.ollama_embedding_model = ""
    original = wav_fixture()
    upload = client.post(
        "/archive/staff/documents",
        auth=admin,
        content=original,
        headers={"Content-Type": "audio/wav"},
        params={
            "metadata": json.dumps(
                metadata(
                    access_level="public",
                    material_type="speech",
                )
            )
        },
    )
    assert upload.status_code == 201, upload.text
    id_ = upload.json()["id"]
    staff = f"/archive/staff/documents/{id_}"
    public = f"/archive/documents/{id_}"
    assert client.get(public + "/playback").status_code == 404
    assert client.post(staff + "/processing", json={}, auth=curator).status_code == 415
    cues = [{"start": 0, "end": 1, "text": "[Synthetic silent recording; local test fixture]"}]
    question = Question(question="Synthetic silent recording", material_type="speech")
    assert client.post(staff + "/recording", json={"cues": cues}, auth=curator).status_code == 200
    assert client.post(staff + "/recording", json={"cues": cues}, auth=curator).status_code == 409
    assert (
        client.post(
            staff + "/transition",
            json={"action": "verify", "metadata_reviewed": True},
            auth=curator,
        ).status_code
        == 200
    )
    assert (
        client.post(staff + "/transition", json={"action": "publish"}, auth=curator).status_code
        == 409
    )
    assert (
        client.post(
            staff + "/recording/verify",
            json={"revision": 1, "compared_with_recording": True},
            auth=curator,
        ).status_code
        == 200
    )
    assert client.get(public + "/playback").status_code == 404
    assert retrieve(config, question)[0] == []
    assert (
        client.post(staff + "/transition", json={"action": "publish"}, auth=curator).status_code
        == 200
    )
    assert client.get(public + "/playback").content == original
    partial = client.get(public + "/playback", headers={"Range": "bytes=0-9"})
    assert partial.status_code == 206 and partial.content == original[:10]
    assert client.get(public + "/recording").json()["transcript"] == cues
    assert index_once(config)
    passages, _ = retrieve(config, question)
    assert len(passages) == 1
    assert passages[0]["start_seconds"] == 0 and passages[0]["end_seconds"] == 1
    assert passages[0]["page_number"] is None

    def grounded(*args):
        return {
            "paragraphs": [
                {
                    "text": "This is a synthetic recording fixture.",
                    "evidence": [{"passage_id": str(passages[0]["id"]), "quote": cues[0]["text"]}],
                }
            ]
        }

    monkeypatch.setattr(research, "generate_grounded", grounded)
    answer = client.post("/archive/research/ask", json=question.model_dump()).json()
    assert answer["status"] == "answered"
    assert answer["sources"][0]["start_seconds"] == 0
    reader = client.get(f"/archive/catalog/{id_}?revision=1").json()
    assert reader["pages"][0]["end_seconds"] == 1
    # Document editing cannot bypass timestamped transcript review.
    assert (
        client.post(
            staff + "/text/revisions",
            auth=curator,
            json={
                "base_revision": 1,
                "pages": [{"sequence": 1, "text": "Replacement"}],
                "note": "Test",
            },
        ).status_code
        == 415
    )
    assert (
        client.post(
            staff + "/recording", json={"base_revision": 1, "cues": cues}, auth=curator
        ).status_code
        == 200
    )
    assert client.get(public + "/playback").status_code == 404
    assert client.get(public + "/recording").status_code == 404
    assert retrieve(config, question)[0] == []
    with connect(config) as db:
        assert (
            db.execute(
                "SELECT status FROM generated_artifact WHERE id=%s", (answer["artifact_id"],)
            ).fetchone()["status"]
            == "invalidated"
        )
        assert (
            db.execute(
                "SELECT count(*) AS n FROM recording_revision WHERE item_id=%s", (id_,)
            ).fetchone()["n"]
            == 2
        )
    assert client.get(f"/archive/catalog/{id_}?revision=1").status_code == 404
    assert client.get(staff + "/original", auth=curator).content == original


@pytest.mark.integration
def test_private_playback_grant_is_scoped_expiring_and_revocable(archive):
    from uuid import UUID, uuid4

    from app.db import connect
    from app.recordings import playback_cookie

    client, config, admin, _ = archive
    original = wav_fixture()
    r = client.post(
        "/archive/staff/documents",
        auth=admin,
        content=original,
        headers={"Content-Type": "audio/wav"},
        params={"metadata": json.dumps(metadata(material_type="audio"))},
    )
    assert r.status_code == 201
    id_ = r.json()["id"]
    base = f"/archive/staff/documents/{id_}"
    assert client.post(base + "/playback-session").status_code == 401
    assert client.get(base + "/playback").status_code == 401
    grant = client.post(base + "/playback-session", auth=admin)
    cookie = grant.cookies.get(playback_cookie(UUID(id_)))
    assert cookie and "HttpOnly" in grant.headers["set-cookie"]
    headers = {"Cookie": f"{playback_cookie(UUID(id_))}={cookie}", "Range": "bytes=0-15"}
    played = client.get(base + "/playback", headers=headers)
    assert played.status_code == 206 and played.content == original[:16]
    assert client.get(f"/archive/documents/{id_}/playback").status_code == 404
    assert (
        client.get(f"/archive/staff/documents/{uuid4()}/playback", headers=headers).status_code
        == 401
    )
    assert client.post(base + "/playback-stop", auth=admin).status_code == 200
    assert client.get(base + "/playback", headers=headers).status_code == 401
    renewed = client.post(base + "/playback-session", auth=admin)
    renewed_cookie = renewed.cookies.get(playback_cookie(UUID(id_)))
    headers["Cookie"] = f"{playback_cookie(UUID(id_))}={renewed_cookie}"
    assert client.get(base + "/playback", headers=headers).status_code == 206
    with connect(config) as db:
        db.execute("UPDATE staff_playback_session SET expires_at=now()-interval '1 second'")
    assert client.get(base + "/playback", headers=headers).status_code == 401
