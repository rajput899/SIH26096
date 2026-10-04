"""Curator-reviewed learning material and server-validated, pseudonymous quiz completion."""

import html
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from psycopg.types.json import Jsonb
from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

from app.archive import staff
from app.db import connect

router = APIRouter(prefix="/archive")
Staff = Annotated[dict, Depends(staff)]


class Source(BaseModel):
    item_id: UUID
    revision: int | None = Field(default=None, ge=1)
    quote: str = Field(default="", max_length=1200)


class QuizQuestion(BaseModel):
    prompt: str = Field(min_length=5, max_length=1000)
    options: list[str] = Field(min_length=2, max_length=4)
    correct: int = Field(ge=0, le=3)
    explanation: str = Field(min_length=8, max_length=1500)
    source_index: int = Field(ge=0)

    @model_validator(mode="after")
    def valid_options(self):
        if (
            self.correct >= len(self.options)
            or len(set(self.options)) != len(self.options)
            or any(not option.strip() or len(option) > 300 for option in self.options)
        ):
            raise ValueError("Use distinct nonempty options and a valid answer index")
        return self


class Content(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    kind: Literal["timeline", "story", "quiz"]
    title: str = Field(min_length=3, max_length=200)
    topic: str = Field(default="", max_length=80)
    description: str = Field(min_length=8, max_length=12000)
    date_label: str = Field(default="", max_length=10, pattern=r"^$|^\d{4}(-\d{2}(-\d{2})?)?$")
    sources: list[Source] = Field(min_length=1, max_length=10)
    questions: list[QuizQuestion] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def shape(self):
        from datetime import date

        if self.kind == "timeline" and not self.date_label:
            raise ValueError("Supply a source-supported year, month or date")
        if self.date_label:
            date.fromisoformat(
                self.date_label + {4: "-01-01", 7: "-01", 10: ""}[len(self.date_label)]
            )
        if len({s.item_id for s in self.sources}) != len(self.sources):
            raise ValueError("Duplicate source records")
        if self.kind == "quiz":
            if not self.questions or any(
                q.source_index >= len(self.sources) for q in self.questions
            ):
                raise ValueError("Quiz questions require valid source references")
            if any(s.revision is None or len(s.quote.strip()) < 8 for s in self.sources):
                raise ValueError("Quiz sources need verified text revision and exact quote")
        elif self.questions:
            raise ValueError("Only quizzes have answer keys")
        return self


def evidence(db, content_id, lock=False):
    sources = db.execute(
        "SELECT e.*,i.title,i.review_status,i.access_level,i.current_text_revision "
        "FROM curated_evidence e JOIN archival_item i ON i.id=e.item_id WHERE e.content_id=%s "
        "ORDER BY i.id" + (" FOR SHARE OF i" if lock else ""),
        (content_id,),
    ).fetchall()
    if not sources:
        raise HTTPException(409, "At least one archival source is required")
    for s in sources:
        if s["review_status"] != "published" or s["access_level"] != "public":
            raise HTTPException(409, "A supporting source is no longer public")
        if s["revision"] is not None:
            text = db.execute(
                "SELECT 1 FROM text_revision WHERE item_id=%s AND revision=%s "
                "AND status='verified'",
                (s["item_id"], s["revision"]),
            ).fetchone()
            if not text or s["revision"] != s["current_text_revision"]:
                raise HTTPException(409, "A supporting text revision has changed")
            if (
                s["quote"]
                and not db.execute(
                    "SELECT 1 FROM text_segment WHERE item_id=%s "
                    "AND revision=%s AND strpos(text,%s)>0",
                    (s["item_id"], s["revision"], s["quote"]),
                ).fetchone()
            ):
                raise HTTPException(409, "Supporting quote does not match verified text")
    return [
        {
            "item_id": s["item_id"],
            "title": s["title"],
            "revision": s["revision"],
            "quote": s["quote"],
        }
        for s in sources
    ]


def curated_audit(db, user, action, id_):
    db.execute(
        "INSERT INTO audit_event(id,actor_id,action,target_type,target_id,change_summary) "
        "VALUES(%s,%s,%s,'curated_content',%s,%s)",
        (uuid4(), user["id"], action, id_, action),
    )


@router.post("/staff/learning", status_code=201)
def create_content(data: Content, request: Request, user: Staff):
    id_ = uuid4()
    with connect(request.app.state.config) as db:
        # Drafts may use staff records. Verification and publication check public eligibility.
        for source in data.sources:
            if not db.execute(
                "SELECT id FROM archival_item WHERE id=%s", (source.item_id,)
            ).fetchone():
                raise HTTPException(422, "Unknown source record")
            if (
                source.revision is not None
                and not db.execute(
                    "SELECT 1 FROM text_revision WHERE item_id=%s AND revision=%s",
                    (source.item_id, source.revision),
                ).fetchone()
            ):
                raise HTTPException(422, "Unknown source text revision")
        db.execute(
            "INSERT INTO curated_content(id,kind,title,topic,body,created_by) "
            "VALUES(%s,%s,%s,%s,%s,%s)",
            (
                id_,
                data.kind,
                data.title,
                data.topic,
                Jsonb(data.model_dump(mode="json")),
                user["id"],
            ),
        )
        for source in data.sources:
            db.execute(
                "INSERT INTO curated_evidence VALUES(%s,%s,%s,%s)",
                (id_, source.item_id, source.revision, source.quote),
            )
        curated_audit(db, user, "learning_draft_created", id_)
    return {"id": id_, "status": "draft"}


@router.get("/staff/learning")
def staff_content(request: Request, user: Staff):
    with connect(request.app.state.config) as db:
        return db.execute(
            "SELECT * FROM curated_content ORDER BY created_at DESC LIMIT 200"
        ).fetchall()


class Review(BaseModel):
    action: Literal["verify", "publish", "withdraw"]
    evidence_reviewed: bool = False


@router.post("/staff/learning/{id_}/transition")
def transition(id_: UUID, data: Review, request: Request, user: Staff):
    with connect(request.app.state.config) as db:
        row = db.execute("SELECT * FROM curated_content WHERE id=%s FOR UPDATE", (id_,)).fetchone()
        if not row:
            raise HTTPException(404, "Learning material not found")
        allowed = {
            "verify": ["draft", "withdrawn"],
            "publish": ["verified"],
            "withdraw": ["verified", "published"],
        }
        if row["status"] not in allowed[data.action]:
            raise HTTPException(409, "Invalid learning publication transition")
        if data.action != "withdraw":
            evidence(db, id_, lock=True)
        if data.action == "verify":
            if not data.evidence_reviewed:
                raise HTTPException(422, "Review all claims, answer keys and supporting sources")
            db.execute(
                "UPDATE curated_content SET verified_by=%s,verified_at=now() WHERE id=%s",
                (user["id"], id_),
            )
        state = {"verify": "verified", "publish": "published", "withdraw": "withdrawn"}[data.action]
        db.execute("UPDATE curated_content SET status=%s WHERE id=%s", (state, id_))
        curated_audit(db, user, "learning_" + state, id_)
    return {"status": state}


def public_content(db, id_, kind=None, lock=False):
    row = db.execute(
        "SELECT * FROM curated_content WHERE id=%s AND status='published'"
        + (" FOR SHARE" if lock else ""),
        (id_,),
    ).fetchone()
    if not row or (kind and row["kind"] != kind):
        raise HTTPException(404, "Learning material is not published")
    row["evidence"] = evidence(db, id_, lock=lock)
    return row


@router.get("/learning")
def public_list(request: Request, kind: Literal["timeline", "story", "quiz"]):
    with connect(request.app.state.config) as db:
        rows = db.execute(
            "SELECT id FROM curated_content WHERE kind=%s AND status='published' "
            "ORDER BY created_at DESC LIMIT 200",
            (kind,),
        ).fetchall()
        output = []
        for row in rows:
            try:
                entry = public_content(db, row["id"])
            except HTTPException:
                continue  # Withdrawn evidence removes the derivative immediately.
            output.append(
                {
                    "id": entry["id"],
                    "kind": kind,
                    "title": entry["title"],
                    "topic": entry["topic"],
                    "description": entry["body"]["description"],
                    "date_label": entry["body"]["date_label"],
                    "evidence": entry["evidence"],
                    "question_count": len(entry["body"].get("questions", [])),
                }
            )
        return sorted(output, key=lambda e: e["date_label"]) if kind == "timeline" else output


def public_questions(body):
    return [{"prompt": q["prompt"], "options": q["options"]} for q in body["questions"]]


def grade(body, answers):
    questions = body["questions"]
    if len(answers) != len(questions):
        raise ValueError("Answer every question")
    for answer, question in zip(answers, questions, strict=True):
        if isinstance(answer, bool) or answer < 0 or answer >= len(question["options"]):
            raise ValueError("Invalid option")
    return {
        "score": sum(a == q["correct"] for a, q in zip(answers, questions, strict=True)),
        "total": len(questions),
        "feedback": [
            {
                "prompt": q["prompt"],
                "correct_option": q["options"][q["correct"]],
                "explanation": q["explanation"],
                "source": body["sources"][q["source_index"]],
            }
            for q in questions
        ],
    }


@router.post("/learning/{id_}/attempts", status_code=201)
def start_attempt(id_: UUID, request: Request):
    with connect(request.app.state.config) as db:
        row = public_content(db, id_, "quiz", lock=True)
        # Single-kiosk global creation limit; no persistent IP/person tracking.
        db.execute("SELECT pg_advisory_xact_lock(260966)")
        count = db.execute(
            "SELECT count(*) AS n FROM quiz_attempt WHERE started_at>now()-interval '1 minute'"
        ).fetchone()["n"]
        if count >= 30:
            raise HTTPException(429, "Please wait before starting another quiz")
        token = uuid4()
        db.execute(
            "INSERT INTO quiz_attempt(id,content_id,revision) VALUES(%s,%s,%s)",
            (token, id_, row["revision"]),
        )
        return {
            "attempt_id": token,
            "title": row["title"],
            "questions": public_questions(row["body"]),
        }


class Submission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answers: list[StrictInt] = Field(min_length=1, max_length=10, strict=True)


@router.post("/attempts/{token}/submit")
def submit(token: UUID, data: Submission, request: Request):
    with connect(request.app.state.config) as db:
        attempt = db.execute(
            "SELECT * FROM quiz_attempt WHERE id=%s FOR UPDATE", (token,)
        ).fetchone()
        if not attempt:
            raise HTTPException(404, "Attempt not found")
        row = public_content(db, attempt["content_id"], "quiz", lock=True)
        if row["revision"] != attempt["revision"]:
            raise HTTPException(409, "Quiz changed. Start again.")
        if attempt["result"]:
            if attempt["answers"] != data.answers:
                raise HTTPException(409, "This attempt was already submitted")
            return attempt["result"]
        try:
            result = grade(row["body"], data.answers)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None
        db.execute(
            "UPDATE quiz_attempt SET answers=%s,result=%s,completed_at=now() WHERE id=%s",
            (Jsonb(data.answers), Jsonb(result), token),
        )
        return result


def completed(db, token):
    row = db.execute(
        "SELECT a.*,c.title FROM quiz_attempt a JOIN curated_content c "
        "ON c.id=a.content_id WHERE a.id=%s",
        (token,),
    ).fetchone()
    if not row or not row["result"]:
        raise HTTPException(409, "Complete and submit an approved quiz first")
    current = public_content(db, row["content_id"], "quiz", lock=True)
    if current["revision"] != row["revision"]:
        raise HTTPException(409, "Completion refers to an outdated quiz")
    return row


class CertificateName(BaseModel):
    display_name: str = Field(default="Archive visitor", min_length=2, max_length=60)

    @model_validator(mode="after")
    def safe_name(self):
        name = self.display_name.strip()
        if not name or not all(c.isalpha() or c in " .'-" for c in name):
            raise ValueError("Use a name or pseudonym, without links or control characters")
        self.display_name = name
        return self


@router.post("/attempts/{token}/certificate")
def issue(token: UUID, data: CertificateName, request: Request):
    with connect(request.app.state.config) as db:
        completed(db, token)
        certificate_id = uuid4()
        row = db.execute(
            "INSERT INTO certificate(id,attempt_id,display_name) VALUES(%s,%s,%s) "
            "ON CONFLICT(attempt_id) DO UPDATE SET attempt_id=excluded.attempt_id "
            "RETURNING id",
            (certificate_id, token, data.display_name),
        ).fetchone()
        return {"id": row["id"], "verification_url": f"/certificate/{row['id']}"}


@router.get("/certificates/{id_}")
def verify_certificate(id_: UUID, request: Request):
    with connect(request.app.state.config) as db:
        certificate = db.execute("SELECT * FROM certificate WHERE id=%s", (id_,)).fetchone()
        if not certificate:
            raise HTTPException(404, "Certificate not found")
        attempt = completed(db, certificate["attempt_id"])
        return {
            "id": id_,
            "display_name": certificate["display_name"],
            "activity": attempt["title"],
            "date": attempt["completed_at"],
            "score": attempt["result"]["score"],
            "total": attempt["result"]["total"],
            "status": "valid",
            "wording": "Certificate of Completion",
        }


def certificate_html(data):
    def esc(value):
        return html.escape(str(value), quote=True)

    return (
        '<!doctype html><html lang="en"><meta charset="utf-8"><title>Certificate of Completion'
        "</title><style>body{font:20px Georgia;color:#182c42;padding:5%;text-align:center}"
        "main{border:3px double #9d773a;padding:4rem}h1{font-size:42px}"
        "@media print{@page{size:A4 landscape;margin:15mm}button{display:none}}</style><main>"
        "<p>Dr. B. R. Ambedkar Digital Heritage Archive</p><h1>Certificate of Completion</h1>"
        "<p>Presented to</p><h2>"
        + esc(data["display_name"])
        + "</h2><p>For completing "
        + esc(data["activity"])
        + "</p><p>Score: "
        + esc(data["score"])
        + " / "
        + esc(data["total"])
        + "</p><p>Completed: "
        + esc(data["date"])
        + "</p><p>Verification ID: "
        + esc(data["id"])
        + "</p><p>Verify this ID at the archive kiosk’s /certificate/"
        + esc(data["id"])
        + " page.</p><small>This confirms completion of an archive learning "
        "activity. It is not academic credit, government accreditation or official endorsement."
        "</small></main></html>"
    )


@router.get("/certificates/{id_}/download")
def download_certificate(id_: UUID, request: Request):
    return HTMLResponse(
        certificate_html(verify_certificate(id_, request)),
        headers={
            "Content-Disposition": 'attachment; filename="certificate-of-completion.html"',
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'",
        },
    )


@router.post("/attempts/{token}/leaderboard")
def join_leaderboard(token: UUID, request: Request):
    with connect(request.app.state.config) as db:
        completed(db, token)
        # Generated pseudonyms prevent profanity, personal data and HTML/URL submissions.
        alias = "Reader-" + uuid4().hex[:8]
        row = db.execute(
            "INSERT INTO leaderboard_entry(attempt_id,alias) VALUES(%s,%s) "
            "ON CONFLICT(attempt_id) DO UPDATE SET attempt_id=excluded.attempt_id "
            "RETURNING alias",
            (token, alias),
        ).fetchone()
        return row


@router.get("/leaderboard")
def leaderboard(request: Request):
    with connect(request.app.state.config) as db:
        rows = db.execute(
            "SELECT a.content_id,a.result,l.alias,l.created_at FROM leaderboard_entry l "
            "JOIN quiz_attempt a ON a.id=l.attempt_id ORDER BY "
            "(a.result->>'score')::numeric/(a.result->>'total')::numeric DESC,"
            "l.created_at LIMIT 100"
        ).fetchall()
        output = []
        for row in rows:
            try:
                content = public_content(db, row["content_id"])
            except HTTPException:
                continue
            output.append(
                {
                    "alias": row["alias"],
                    "activity": content["title"],
                    "score": row["result"]["score"],
                    "total": row["result"]["total"],
                }
            )
        return output
