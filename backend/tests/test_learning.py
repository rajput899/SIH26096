"""Rights-cleared synthetic learning fixtures; no historical material or live AI calls."""

from uuid import uuid4

import pytest
from pydantic import ValidationError
from test_research import publish_fixture

from app.learning import (
    CertificateName,
    Content,
    Submission,
    certificate_html,
    grade,
    public_questions,
)


def activity(item=None):
    return dict(
        kind="quiz",
        title="SYNTHETIC reading-room test",
        topic="Test fixture",
        description="Synthetic local test activity, not historical archival content.",
        sources=[
            dict(
                item_id=str(item or uuid4()),
                revision=2,
                quote="Synthetic reading rooms have blue chairs.",
            )
        ],
        questions=[
            dict(
                prompt="What color are the synthetic chairs?",
                options=["Blue", "Green"],
                correct=0,
                explanation="The synthetic source says blue chairs.",
                source_index=0,
            )
        ],
    )


def test_quiz_keys_stay_server_side_and_scores_are_validated():
    body = Content(**activity()).model_dump(mode="json")
    public = public_questions(body)
    assert set(public[0]) == {"prompt", "options"}
    assert grade(body, [0])["score"] == 1
    assert grade(body, [1])["score"] == 0
    for answers in [[], [2], [-1], [True], [0, 0]]:
        with pytest.raises(ValueError):
            grade(body, answers)
    for payload in [{"answers": [0], "score": 100}, {"answers": [True]}, {"answers": [0.0]}]:
        with pytest.raises(ValidationError):
            Submission(**payload)


def test_quiz_requires_traceable_evidence_and_valid_options():
    body = activity()
    body["sources"][0]["revision"] = None
    with pytest.raises(ValidationError):
        Content(**body)
    body = activity()
    body["questions"][0]["correct"] = 3
    with pytest.raises(ValidationError):
        Content(**body)
    with pytest.raises(ValidationError):
        Content(
            kind="timeline",
            title="Test event",
            description="Synthetic test only",
            date_label="1900-02-31",
            sources=activity()["sources"],
        )


def test_certificate_escapes_fields_and_rejects_markup_names():
    with pytest.raises(ValidationError):
        CertificateName(display_name="<script>alert()</script>")
    output = certificate_html(
        dict(
            display_name="<img src=x>",
            activity="A & B",
            score=1,
            total=1,
            date="2026-01-01",
            id=uuid4(),
        )
    )
    assert "<img" not in output and "&lt;img" in output and "A &amp; B" in output
    assert "not academic credit" in output


@pytest.mark.integration
def test_learning_quiz_certificate_and_source_withdrawal(archive, monkeypatch):
    client, config, _, curator = archive
    item, source_base, _ = publish_fixture(archive)
    payload = activity(item)
    assert client.post("/archive/staff/learning", json=payload).status_code == 401
    draft = client.post("/archive/staff/learning", json=payload, auth=curator)
    assert draft.status_code == 201, draft.text
    id_ = draft.json()["id"]
    base = f"/archive/staff/learning/{id_}/transition"
    assert client.get("/archive/learning?kind=quiz").json() == []
    assert client.post(base, json={"action": "publish"}, auth=curator).status_code == 409
    assert client.post(base, json={"action": "verify"}, auth=curator).status_code == 422
    assert (
        client.post(
            base, json={"action": "verify", "evidence_reviewed": True}, auth=curator
        ).status_code
        == 200
    )
    assert client.get("/archive/learning?kind=quiz").json() == []
    assert client.post(base, json={"action": "publish"}, auth=curator).status_code == 200
    public = client.get("/archive/learning?kind=quiz").json()
    assert len(public) == 1 and "questions" not in public[0]
    attempt = client.post(f"/archive/learning/{id_}/attempts").json()
    assert "correct" not in attempt["questions"][0]
    token = attempt["attempt_id"]
    attempt_base = f"/archive/attempts/{token}"
    assert client.post(attempt_base + "/certificate", json={}).status_code == 409
    assert (
        client.post(attempt_base + "/submit", json={"answers": [0], "score": 999}).status_code
        == 422
    )
    response = client.post(attempt_base + "/submit", json={"answers": [0]})
    assert response.status_code == 200, response.text
    assert response.json()["score"] == 1
    assert client.post(attempt_base + "/submit", json={"answers": [0]}).json() == response.json()
    assert client.post(attempt_base + "/submit", json={"answers": [1]}).status_code == 409
    cert = client.post(attempt_base + "/certificate", json={"display_name": "Test visitor"})
    assert cert.status_code == 200, cert.text
    cert_id = cert.json()["id"]
    assert client.post(attempt_base + "/certificate", json={}).json()["id"] == cert_id
    assert client.get(f"/archive/certificates/{cert_id}").json()["status"] == "valid"
    assert client.get(f"/archive/certificates/{cert_id}/download").status_code == 200
    from app import certificate_email

    config.smtp_host = "smtp.example.test"
    config.smtp_from = "archive@example.test"
    payload = {"email": "visitor@example.test", "consent": True}
    assert (
        client.post(
            attempt_base + "/certificate-email",
            json={"email": "visitor@example.test", "consent": False},
        ).status_code
        == 422
    )

    def fail(*args):
        raise RuntimeError("Synthetic SMTP failure containing private address")

    monkeypatch.setattr(certificate_email, "send", fail)
    failed = client.post(attempt_base + "/certificate-email", json=payload)
    assert failed.status_code == 503 and "private address" not in failed.text
    monkeypatch.setattr(certificate_email, "send", lambda *args: None)
    assert (
        client.post(attempt_base + "/certificate-email", json=payload).json()["status"]
        == "accepted"
    )
    assert client.post(attempt_base + "/certificate-email", json=payload).status_code == 409
    # Exercise durable per-certificate and global delivery limits with mocked SMTP only.
    monkeypatch.setattr(certificate_email, "send", fail)

    def another_certificate():
        attempt_id = client.post(f"/archive/learning/{id_}/attempts").json()["attempt_id"]
        path = f"/archive/attempts/{attempt_id}"
        assert client.post(path + "/submit", json={"answers": [0]}).status_code == 200
        assert client.post(path + "/certificate", json={}).status_code == 200
        return path + "/certificate-email"

    retry_path = another_certificate()
    for _ in range(3):
        assert client.post(retry_path, json=payload).status_code == 503
    assert client.post(retry_path, json=payload).status_code == 409
    for _ in range(5):
        assert client.post(another_certificate(), json=payload).status_code == 503
    assert client.post(another_certificate(), json=payload).status_code == 429
    assert client.get("/archive/leaderboard").json() == []
    alias = client.post(attempt_base + "/leaderboard").json()["alias"]
    assert client.post(attempt_base + "/leaderboard").json()["alias"] == alias
    assert len(client.get("/archive/leaderboard").json()) == 1
    assert (
        client.post(
            source_base + "/transition", json={"action": "withdraw"}, auth=curator
        ).status_code
        == 200
    )
    assert client.get("/archive/learning?kind=quiz").json() == []
    assert client.get("/archive/leaderboard").json() == []
    assert client.get(f"/archive/certificates/{cert_id}").status_code == 409
    assert client.post(f"/archive/learning/{id_}/attempts").status_code == 409
