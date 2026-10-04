from uuid import uuid4

import pytest
from pydantic import ValidationError

from app import certificate_email
from app.certificate_email import Delivery, configured, send


def test_email_is_optional_and_consent_and_address_are_required(settings):
    settings.smtp_host = ""
    assert not configured(settings)
    for values in [
        dict(email="a@example.test", consent=False),
        dict(email="a@example.test\r\nBcc: b@example.test", consent=True),
        dict(email="not-an-address", consent=True),
    ]:
        with pytest.raises(ValidationError):
            Delivery(**values)


def test_smtp_uses_starttls_and_confirmation_without_real_delivery(settings, monkeypatch):
    calls = []

    class SMTP:
        def __init__(self, *args, **kwargs):
            calls.append("connect")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def starttls(self, **kwargs):
            calls.append("tls")

        def send_message(self, message):
            assert message["To"] == "visitor@example.test"
            assert "certificate-of-completion.html" in message.as_string()
            calls.append("accepted")
            return {}

    monkeypatch.setattr(certificate_email.smtplib, "SMTP", SMTP)
    settings.smtp_host = "smtp.example.test"
    settings.smtp_from = "archive@example.test"
    send(
        settings,
        "visitor@example.test",
        dict(
            id=uuid4(),
            display_name="Test visitor",
            activity="Synthetic activity",
            score=1,
            total=1,
            date="2026-01-01",
        ),
    )
    assert calls == ["connect", "tls", "accepted"]
