"""001 lecture associations; course ownership/lifecycle remains owned by 002."""
from importlib import import_module
import json
import re

from flask import current_app

from ..auth import require_teacher
from ..db import connection, write_transaction
from ..http import ApiError
from . import repository as repo


def validate_course_id(course_id):
    if not isinstance(course_id, str) or re.fullmatch(r"[A-Za-z0-9_-]{1,128}", course_id) is None:
        raise ApiError(400, "INVALID_REQUEST")
    return course_id


def get_owned_course(teacher_context, course_id):
    course_id = validate_course_id(course_id)
    if require_teacher() != teacher_context:
        raise ApiError(403, "TEACHER_REQUIRED")
    provider = current_app.config.get("GET_OWNED_COURSE")
    if provider is None:
        try:
            module = import_module("..activities.course_service", __package__)
        except ModuleNotFoundError as error:
            if error.name != "guided_notes.activities.course_service":
                raise
            raise ApiError(503, "COURSE_UNAVAILABLE") from None
        provider = getattr(module, "get_owned_course", None)
    if not callable(provider):
        raise ApiError(503, "COURSE_UNAVAILABLE")
    course = provider(teacher_context, course_id)
    if require_teacher() != teacher_context:
        raise ApiError(403, "TEACHER_REQUIRED")
    if course is None:
        raise ApiError(404, "COURSE_NOT_FOUND")
    if not isinstance(course, dict) or not {"course_id", "teacher_id", "title"} <= course.keys():
        raise ApiError(503, "COURSE_UNAVAILABLE")
    if course["course_id"] != course_id or course["teacher_id"] != teacher_context.teacher_id:
        raise ApiError(404, "COURSE_NOT_FOUND")
    if type(course["teacher_id"]) is not int or not isinstance(course["title"], str) or not course["title"].strip():
        raise ApiError(503, "COURSE_UNAVAILABLE")
    return {key: course[key] for key in ("course_id", "teacher_id", "title")}


def import_course_id(db, import_id):
    row = db.execute("SELECT course_id FROM notes_import_courses WHERE import_id=?", (import_id,)).fetchone()
    return None if row is None else row["course_id"]


def check_import_context(db, teacher_id, import_id, course_id):
    repo.owned_import(db, teacher_id, import_id)
    if import_course_id(db, import_id) != course_id:
        raise ApiError(409, "COURSE_MISMATCH")


def list_course_catalogs(teacher_context, course_id):
    course = get_owned_course(teacher_context, course_id)
    rows = connection().execute("""SELECT c.*,s.display_title AS source_title,
        CASE WHEN n.name_mode='custom' THEN n.custom_title ELSE s.display_title END AS title
        FROM notes_import_courses a JOIN notes_imports i USING(import_id)
        JOIN notes_sources s USING(source_id) JOIN notes_catalogs c USING(import_id)
        LEFT JOIN notes_catalog_names n ON n.import_id=c.import_id AND n.version=c.version
        WHERE a.course_id=? AND s.teacher_id=? AND NOT EXISTS(SELECT 1 FROM notes_lecture_removals r WHERE r.import_id=i.import_id) ORDER BY c.confirmed_at DESC,c.version DESC""",
        (course_id, teacher_context.teacher_id)).fetchall()
    lectures = {}
    for row in rows:
        catalog = json.loads(row["dto"])
        entry = lectures.setdefault(row["import_id"], {"import_id": row["import_id"], "versions": []})
        entry["versions"].append({"import_version": row["version"], "title": row["title"],
            "source_title": row["source_title"], "question_count": catalog["question_count"],
            "answer_item_count": catalog["answer_item_count"], "confirmed_at": row["confirmed_at"]})
    for lecture in lectures.values():
        lecture["versions"].sort(key=lambda version: version["import_version"], reverse=True)
    return {"course_id": course["course_id"], "title": course["title"], "lectures": list(lectures.values())}


def get_course_catalog(teacher_context, course_id, import_id, import_version):
    from .import_service import get_catalog
    get_owned_course(teacher_context, course_id)
    repo.owned_import(connection(), teacher_context.teacher_id, import_id)
    if import_course_id(connection(), import_id) != course_id:
        raise ApiError(404, "CATALOG_NOT_FOUND")
    return get_catalog(teacher_context, import_id, import_version)


def assign_lecture(teacher_context, course_id, import_id):
    get_owned_course(teacher_context, course_id)
    with write_transaction() as db:
        if require_teacher(db) != teacher_context:
            raise ApiError(403, "TEACHER_REQUIRED")
        repo.owned_import(db, teacher_context.teacher_id, import_id)
        from .lecture_lifecycle import require_active_import
        require_active_import(db, teacher_context.teacher_id, import_id)
        assigned = import_course_id(db, import_id)
        if assigned is not None and assigned != course_id:
            raise ApiError(409, "COURSE_MISMATCH")
        db.execute("INSERT INTO notes_import_courses VALUES(?,?,?) ON CONFLICT(import_id) DO NOTHING",
                   (import_id, course_id, repo.now()))
    return {"import_id": import_id, "course_id": course_id}


def get_course_display_content(teacher_context, course_id, import_id, import_version):
    from .display_service import get_display_content
    get_owned_course(teacher_context, course_id)
    repo.owned_import(connection(), teacher_context.teacher_id, import_id)
    if import_course_id(connection(), import_id) != course_id:
        raise ApiError(404, 'CATALOG_NOT_FOUND')
    from .lecture_lifecycle import require_active_import
    require_active_import(connection(), teacher_context.teacher_id, import_id, course_id)
    return get_display_content(teacher_context, import_id, import_version)
