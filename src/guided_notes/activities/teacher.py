from importlib import import_module
import json
import secrets

from flask import current_app

from ..http import ApiError


def fixed_questions(teacher, import_id, import_version):
    provider = current_app.config.get("GET_CATALOG")
    if provider is None:
        try:
            service = import_module("..notes.import_service", __package__)
        except ModuleNotFoundError as error:
            if error.name not in {"guided_notes.notes", "guided_notes.notes.import_service"}:
                raise
            raise ApiError(503, "CATALOG_UNAVAILABLE") from error
        provider = getattr(service, "get_catalog", None)
    if not callable(provider):
        raise ApiError(503, "CATALOG_UNAVAILABLE")
    return validate_catalog(provider(teacher, import_id, import_version), import_id, import_version)


def validate_catalog(catalog, import_id, import_version):
    questions = catalog.get("questions") if isinstance(catalog, dict) else None
    if not questions or not isinstance(questions, list):
        raise ApiError(400, "INVALID_CATALOG")
    if catalog.get("import_id", import_id) != import_id or catalog.get("import_version", import_version) != import_version:
        raise ApiError(400, "INVALID_CATALOG")
    fixed = []
    seen_questions, seen_items, seen_blanks = set(), set(), set()
    for question in questions:
        if not isinstance(question, dict):
            raise ApiError(400, "INVALID_CATALOG")
        question_id = question.get("question_id")
        display = question.get("display_number")
        kind = question.get("kind")
        items = question.get("items")
        if (not valid_identifier(question_id) or question_id in seen_questions
                or not valid_identifier(display) or kind not in ("single", "question_set")
                or not isinstance(items, list) or (kind == "single" and len(items) != 1)
                or (kind == "question_set" and len(items) < 2)):
            raise ApiError(400, "INVALID_CATALOG")
        seen_questions.add(question_id)
        safe_items = []
        for item in items:
            if not isinstance(item, dict):
                raise ApiError(400, "INVALID_CATALOG")
            item_id, blank_id = item.get("item_id"), item.get("blank_id")
            label = item.get("subitem_label")
            if (not valid_identifier(item_id) or item_id in seen_items or not valid_identifier(blank_id)
                    or blank_id in seen_blanks or (label is not None and not isinstance(label, str))):
                raise ApiError(400, "INVALID_CATALOG")
            seen_items.add(item_id)
            seen_blanks.add(blank_id)
            safe_items.append(dict(item_id=item_id, blank_id=blank_id, subitem_label=label))
        fixed.append(dict(question_id=question_id, display_number=display, kind=kind, items=safe_items))
    return fixed


def valid_identifier(value):
    return isinstance(value, str) and bool(value.strip())



def store_activity(db, teacher, import_id, version, questions):
    activity_id = secrets.token_urlsafe(18)
    code = secrets.token_hex(5).upper()
    db.execute(
        "INSERT INTO activities(id, teacher_id, code, import_id, import_version) VALUES (?, ?, ?, ?, ?)",
        (activity_id, teacher.teacher_id, code, import_id, version),
    )
    db.executemany(
        "INSERT INTO questions VALUES (?, ?, ?, ?)",
        [(activity_id, q["question_id"], i, json.dumps(q)) for i, q in enumerate(questions)],
    )
    return dict(activity_id=activity_id, code=code, phase="PREPARING", phase_version=0)


def transition(db, activity_id, teacher, before, after):
    row = db.execute("SELECT * FROM activities WHERE id = ?", (activity_id,)).fetchone()
    if row is None or row["teacher_id"] != teacher.teacher_id:
        raise ApiError(403, "FORBIDDEN")
    allowed_phases = (before,) if isinstance(before, str) else before
    if row["phase"] not in allowed_phases:
        raise ApiError(409, "INVALID_PHASE")
    version = row["phase_version"] + 1
    db.execute("UPDATE activities SET phase = ?, phase_version = ? WHERE id = ?", (after, version, activity_id))
    if after == "CLOSED":
        from ..quiz.settlement import queue
        queue(db, activity_id)
    return dict(activity_id=activity_id, phase=after, phase_version=version)


def get_activity_reference(teacher_context, activity_id):
    from ..auth import require_teacher
    from ..db import connection
    from .classroom_access import owned_classroom, requested_activity

    db = connection()
    if teacher_context != require_teacher(db):
        raise ApiError(403, "FORBIDDEN")
    if current_app.config["CLASSROOM_MODE"]:
        row = requested_activity(db, activity_id)
        owned_classroom(db, teacher_context, row["classroom_id"])
    else:
        row = db.execute("SELECT * FROM activities WHERE id = ? AND teacher_id = ?",
                         (activity_id, teacher_context.teacher_id)).fetchone()
        if row is None:
            raise ApiError(404, "ACTIVITY_NOT_FOUND")
    return {"activity_id": row["id"], "import_id": row["import_id"],
            "import_version": row["import_version"], "ended": row["phase"] == "CLOSED"}
