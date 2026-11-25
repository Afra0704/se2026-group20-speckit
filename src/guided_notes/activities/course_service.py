"""The authoritative course ownership adapter used by 001."""

from flask import current_app

from ..auth import require_teacher
from ..db import connection
from ..http import ApiError


def get_owned_course(teacher_context, course_id, *, db=None):
    db = db if db is not None else connection()
    if require_teacher(db) != teacher_context:
        raise ApiError(403, "TEACHER_REQUIRED")
    if not current_app.config["CLASSROOM_MODE"]:
        raise ApiError(503, "COURSE_UNAVAILABLE")
    row = db.execute(
        "SELECT id AS course_id, teacher_id, title FROM courses WHERE id = ? AND teacher_id = ?",
        (course_id, teacher_context.teacher_id),
    ).fetchone()
    if row is None:
        raise ApiError(404, "COURSE_NOT_FOUND")
    return dict(row)
