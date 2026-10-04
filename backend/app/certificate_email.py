"""Opt-in certificate delivery. Addresses are never persisted or logged."""

import hashlib
import re
import smtplib
import ssl
from email.message import EmailMessage
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db import connect
from app.learning import certificate_html, completed

router = APIRouter(prefix="/archive")


class Delivery(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    email: str = Field(min_length=3, max_length=254)
    consent: Literal[True]

    @field_validator("email")
    @classmethod
    def address(cls, value):
        if not re.fullmatch(
            r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+", value
        ):
            raise ValueError("Enter one valid email address")
        return value


def configured(config):
    return bool(config.smtp_host and config.smtp_from)


def send(config, address, data):
    message = EmailMessage()
    message["Subject"] = "Your archive completion certificate"
    message["From"] = config.smtp_from
    message["To"] = address
    url = str(config.certificate_public_url).rstrip("/") + "/certificate/" + str(data["id"])
    message.set_content("You requested this completion certificate. Verify it at " + url)
    message.add_attachment(
        certificate_html(data).encode("utf-8"),
        maintype="text",
        subtype="html",
        filename="certificate-of-completion.html",
    )
    with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=15) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        if config.smtp_user:
            smtp.login(config.smtp_user, config.smtp_password.get_secret_value())
        if smtp.send_message(message):
            raise RuntimeError("SMTP did not accept the recipient")


@router.get("/certificate-email/status")
def email_status(request: Request):
    return {
        "configured": configured(request.app.state.config),
        "message": "Delivery requires consent and uses the address only for this certificate.",
    }


@router.post("/attempts/{token}/certificate-email")
def deliver(token: UUID, data: Delivery, request: Request):
    config = request.app.state.config
    if not configured(config):
        raise HTTPException(503, "Email is not configured. Certificate download remains available.")
    failed = False
    with connect(config) as db:
        # Secret attempt token, not the public verification ID, authorizes delivery.
        attempt = completed(db, token)
        cert = db.execute(
            "SELECT * FROM certificate WHERE attempt_id=%s FOR UPDATE", (token,)
        ).fetchone()
        if not cert:
            raise HTTPException(409, "Create the completion certificate first")
        db.execute("SELECT pg_advisory_xact_lock(260967)")
        prior = db.execute(
            "SELECT * FROM certificate_delivery WHERE certificate_id=%s", (cert["id"],)
        ).fetchone()
        if prior and (prior["status"] == "accepted" or prior["attempts"] >= 3):
            raise HTTPException(409, "Delivery already accepted or retry limit reached")
        count = db.execute(
            "SELECT coalesce(sum(attempts),0) AS n FROM certificate_delivery "
            "WHERE updated_at>now()-interval '1 hour'"
        ).fetchone()["n"]
        if count >= 10:
            raise HTTPException(429, "Email limit reached. Use the download instead.")
        fingerprint = hashlib.sha256((str(cert["id"]) + data.email).encode()).hexdigest()
        db.execute(
            "INSERT INTO certificate_delivery(certificate_id,consent_at,recipient_hash,status) "
            "VALUES(%s,now(),%s,'sending') ON CONFLICT(certificate_id) DO UPDATE SET "
            "status='sending',attempts=certificate_delivery.attempts+1,updated_at=now(),"
            "consent_at=now(),recipient_hash=excluded.recipient_hash",
            (cert["id"], fingerprint),
        )
        content = dict(
            id=cert["id"],
            display_name=cert["display_name"],
            activity=attempt["title"],
            score=attempt["result"]["score"],
            total=attempt["result"]["total"],
            date=attempt["completed_at"],
        )
        try:
            send(config, data.email, content)
        except Exception:
            # SMTP errors may contain credentials or recipient addresses. Never expose them.
            failed = True
        db.execute(
            "UPDATE certificate_delivery SET status=%s,updated_at=now() WHERE certificate_id=%s",
            ("failed" if failed else "accepted", cert["id"]),
        )
    if failed:
        raise HTTPException(
            503, "Email service did not confirm acceptance. Download or retry later."
        )
    return {
        "status": "accepted",
        "message": "The email service accepted your certificate. Inbox delivery is not guaranteed.",
    }
