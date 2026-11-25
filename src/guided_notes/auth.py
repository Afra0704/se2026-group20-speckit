from dataclasses import dataclass
from hashlib import sha256
import secrets
import time

from flask import current_app, request, session

from .db import connection, write_transaction
from .http import ApiError


@dataclass(frozen=True)
class TeacherContext:
    teacher_id: int


def digest(token):
    return sha256(token.encode()).hexdigest()


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


def check_csrf():
    expected = session.get("csrf")
    supplied = (request.headers.get("X-CSRFToken") or request.headers.get("X-CSRF-Token")
                or request.form.get("csrf_token", ""))
    if not expected or not secrets.compare_digest(expected.encode(), supplied.encode()):
        raise ApiError(403, "INVALID_CSRF")


def issue_grant(db, *, teacher_id=None, membership_id=None, read_only=False):
    grant = secrets.token_urlsafe(32)
    db.execute(
        "INSERT INTO grants VALUES (?, ?, ?, ?, ?)",
        (digest(grant), teacher_id, membership_id, int(time.time()) + current_app.config["AUTH_SECONDS"], read_only),
    )
    return grant


def grant(db, role=None):
    role = role or request.headers.get("X-Activity-Role")
    if role not in (None, "teacher", "student"):
        raise ApiError(400, "INVALID_REQUEST")
    if role is None:
        token = session.get("student_grant") or session.get("teacher_grant")
    else:
        token = session.get(f"{role}_grant")
    token = token or session.get("grant")
    if not token:
        if role and (session.get("teacher_grant") or session.get("student_grant")):
            raise ApiError(403, "FORBIDDEN")
        raise ApiError(401, "AUTH_REQUIRED")
    row = db.execute(
        "SELECT * FROM grants WHERE token = ? AND expires > ?", (digest(token), int(time.time()))
    ).fetchone()
    if row is None:
        raise ApiError(401, "AUTH_REQUIRED")
    if (role == "teacher" and row["teacher_id"] is None
            or role == "student" and row["membership_id"] is None):
        raise ApiError(403, "FORBIDDEN")
    return row


def require_teacher(db=None):
    db = db if db is not None else connection()
    identity = grant(db, "teacher")
    teacher = db.execute("SELECT id FROM teachers WHERE id = ? AND active = 1", (identity["teacher_id"],)).fetchone()
    if teacher is None:
        raise ApiError(403, "FORBIDDEN")
    return TeacherContext(teacher["id"])


def limit_attempts(action):
    if current_app.testing:
        return
    now = int(time.time())
    scope = f"{action}:{request.remote_addr}"
    with write_transaction() as db:
        db.execute("DELETE FROM attempts WHERE expires <= ?", (now,))
        row = db.execute("SELECT count FROM attempts WHERE scope = ?", (scope,)).fetchone()
        if row and row["count"] >= 20:
            raise ApiError(429, "TOO_MANY_ATTEMPTS")
        db.execute(
            "INSERT INTO attempts VALUES (?, 1, ?) ON CONFLICT(scope) DO UPDATE SET count = count + 1",
            (scope, now + 60),
        )


def check_teacher_login_limit():
    if current_app.testing:
        return
    now = int(time.time())
    row = connection().execute(
        "SELECT count, expires FROM attempts WHERE scope = ? AND expires > ?",
        (teacher_login_scope(), now),
    ).fetchone()
    if row and row["count"] >= 20:
        raise ApiError(429, "TOO_MANY_ATTEMPTS", retry_after=row["expires"] - now)


def record_teacher_login_failure():
    if current_app.testing:
        return
    now = int(time.time())
    with write_transaction() as db:
        db.execute(
            """INSERT INTO attempts VALUES (?, 1, ?)
               ON CONFLICT(scope) DO UPDATE SET
               count = CASE WHEN expires <= ? THEN 1 ELSE count + 1 END,
               expires = CASE WHEN expires <= ? THEN excluded.expires ELSE expires END""",
            (teacher_login_scope(), now + 60, now, now),
        )


def teacher_login_scope():
    return f"teacher-login-failures:{request.remote_addr}"
