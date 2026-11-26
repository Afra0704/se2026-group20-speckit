import secrets
from string import ascii_uppercase, digits

from flask import Blueprint, current_app, flash, jsonify, redirect, request, session, url_for

from ..auth import limit_attempts, require_teacher
from ..db import connection, write_transaction, read_view
from ..http import ApiError, payload, string
from ..quiz.results_gateway import snapshot
from .classroom_access import (
    activity_transaction, classroom, owned_classroom, requested_activity, require_no_unfinished,
)
from .classroom_catalog import get_catalog, list_catalogs, get_display_content
from .display_service import save_display
from .classroom_membership import group_for, identity_for, join, recover
from .course_service import get_owned_course
from .state_routes import state_view
from .teacher import store_activity, transition, validate_catalog

rooms = Blueprint("classrooms", __name__)


@rooms.get("/teacher/courses")
def list_courses():
    teacher = require_teacher()
    rows = connection().execute(
        "SELECT id AS course_id, title FROM courses WHERE teacher_id = ? ORDER BY created_at, id",
        (teacher.teacher_id,),
    )
    return {"courses": [dict(row) for row in rows]}


@rooms.post("/teacher/courses")
def create_course():
    title = string(payload(), "title", 128)
    course_id = secrets.token_urlsafe(18)
    with write_transaction() as db:
        try:
            teacher = require_teacher(db)
        except ApiError as error:
            if request.is_json or error.status not in (401, 403):
                raise
            flash("請先以教師帳號登入，再建立課程。", "error")
            return redirect(url_for("teacher.page"), code=303)
        db.execute("INSERT INTO courses(id, teacher_id, title) VALUES (?, ?, ?)",
                   (course_id, teacher.teacher_id, title))
    if not request.is_json:
        flash("課程已建立。")
        return redirect(url_for("teacher.page"), code=303)
    return {"course_id": course_id, "title": title}, 201


@rooms.get("/teacher/courses/<course_id>/catalogs")
def catalogs(course_id):
    teacher = require_teacher()
    return list_catalogs(teacher, get_owned_course(teacher, course_id))


@rooms.get("/teacher/courses/<course_id>/classrooms")
def list_rooms(course_id):
    teacher = require_teacher()
    get_owned_course(teacher, course_id)
    rows = connection().execute(
        "SELECT id AS classroom_id, title, code, state, created_at, closed_at FROM classrooms WHERE course_id = ? ORDER BY created_at DESC",
        (course_id,),
    )
    return {"classrooms": [dict(row) for row in rows]}


@rooms.post("/teacher/courses/<course_id>/classrooms")
def create_room(course_id):
    title = string(payload(), "title", 128)
    classroom_id = secrets.token_urlsafe(18)
    with write_transaction() as db:
        get_owned_course(require_teacher(db), course_id, db=db)
        code = insert_room(db, classroom_id, course_id, title)
    return {"classroom_id": classroom_id, "title": title, "code": code, "state": "OPEN"}, 201


def make_room_code():
    return "".join(secrets.choice(chars) for chars in (ascii_uppercase, ascii_uppercase, digits, digits, digits))


def insert_room(db, classroom_id, course_id, title):
    for _ in range(12):
        code = make_room_code()
        inserted = db.execute(
            """INSERT INTO classrooms(id, course_id, title, code) VALUES (?, ?, ?, ?)
               ON CONFLICT(code) WHERE state='OPEN' DO NOTHING""",
            (classroom_id, course_id, title, code),
        )
        if inserted.rowcount:
            return code
    raise ApiError(503, "CLASSROOM_CODE_UNAVAILABLE")


def require_open(room):
    if room["state"] != "OPEN":
        raise ApiError(409, "CLASSROOM_CLOSED")


@rooms.get("/teacher/classrooms/<classroom_id>/activities")
def history(classroom_id):
    db = connection()
    owned_classroom(db, require_teacher(db), classroom_id)
    rows = db.execute(
        """SELECT a.id AS activity_id, a.phase, a.import_id, a.import_version,
           ca.title, ca.created_at, ca.started_at, ca.closed_at
           FROM classroom_activities ca JOIN activities a ON a.id = ca.activity_id
           WHERE ca.classroom_id = ? ORDER BY ca.created_at, ca.rowid""",
        (classroom_id,),
    )
    return {"activities": [dict(row) for row in rows]}


@rooms.post("/teacher/classrooms/<classroom_id>/activities")
def create_activity(classroom_id):
    data = payload()
    import_id, version = string(data, "import_id"), data.get("import_version")
    if type(version) is not int or not 0 < version <= 2**63 - 1:
        raise ApiError(400, "INVALID_REQUEST")
    teacher = require_teacher()
    room = owned_classroom(connection(), teacher, classroom_id)
    require_open(room)
    course = get_owned_course(teacher, room["course_id"])
    questions = validate_catalog(get_catalog(teacher, course["course_id"], import_id, version), import_id, version)
    display = get_display_content(teacher, course['course_id'], import_id, version, questions)
    from ..notes.lecture_lifecycle import require_active_import
    require_active_import(connection(), teacher.teacher_id, import_id, course['course_id'])
    title = data.get("title", "")
    if not isinstance(title, str) or len(title) > 128:
        raise ApiError(400, "INVALID_REQUEST")
    title = title.strip()
    if not title:
        options = list_catalogs(teacher, course)["lectures"]
        title = next((v["title"] for i in options if i["import_id"] == import_id
                      for v in i["versions"] if v["import_version"] == version), None)
        if title is None:
            raise ApiError(404, "CATALOG_NOT_FOUND")
    with activity_transaction() as db:
        current_teacher = require_teacher(db)
        require_open(owned_classroom(db, current_teacher, classroom_id))
        require_no_unfinished(db, classroom_id)
        from ..notes.lecture_lifecycle import require_available_for_activity
        require_available_for_activity(current_teacher, course["course_id"], import_id, version, db)
        result = store_activity(db, current_teacher, import_id, version, questions)
        save_display(db, result['activity_id'], display)
        db.execute("INSERT INTO classroom_activities(activity_id, classroom_id, title) VALUES (?, ?, ?)",
                   (result["activity_id"], classroom_id, title))
        db.execute("UPDATE classrooms SET current_activity_id=?, state_version=state_version+1 WHERE id=?",
                   (result["activity_id"], classroom_id))
    return {"activity_id": result["activity_id"], "title": title, "phase": result["phase"]}, 201


@rooms.post("/teacher/classrooms/<classroom_id>/activities/<activity_id>/<any(start, finish):action>")
def change_activity(classroom_id, activity_id, action):
    with activity_transaction() as db:
        teacher = require_teacher(db)
        room = owned_classroom(db, teacher, classroom_id)
        require_open(room)
        activity = requested_activity(db, activity_id)
        if activity["classroom_id"] != classroom_id:
            raise ApiError(403, "FORBIDDEN")
        if room["current_activity_id"] != activity_id:
            raise ApiError(409, "INVALID_PHASE")
        if action == "start":
            require_no_unfinished(db, classroom_id, excluding=activity_id)
            result = transition(db, activity_id, teacher, "PREPARING", "LIVE")
            db.execute("UPDATE classroom_activities SET started_at = CURRENT_TIMESTAMP WHERE activity_id = ?", (activity_id,))
        else:
            if activity["phase"] not in ("PREPARING", "LIVE"):
                raise ApiError(409, "INVALID_PHASE")
            result = transition(db, activity_id, teacher, activity["phase"], "CLOSED")
            db.execute("UPDATE classroom_activities SET closed_at = CURRENT_TIMESTAMP WHERE activity_id = ?", (activity_id,))
        db.execute("UPDATE classrooms SET current_activity_id = ?, state_version = state_version + 1 WHERE id = ?",
                   (activity_id, classroom_id))
    return result


@rooms.post("/teacher/classrooms/<classroom_id>/close")
def close(classroom_id):
    if payload().get("confirm") is not True:
        raise ApiError(400, "CONFIRM_REQUIRED")
    with activity_transaction() as db:
        teacher = require_teacher(db)
        room = owned_classroom(db, teacher, classroom_id)
        if room['state'] == 'CLOSED':
            return {'classroom_state': 'CLOSED'}
        unfinished = db.execute(
            """SELECT a.id, a.phase FROM classroom_activities c JOIN activities a ON a.id=c.activity_id
               WHERE c.classroom_id=? AND a.phase IN ('PREPARING','LIVE')""", (classroom_id,)
        ).fetchall()
        for activity in unfinished:
            transition(db, activity["id"], teacher, activity["phase"], "CLOSED")
            db.execute("UPDATE classroom_activities SET closed_at = CURRENT_TIMESTAMP WHERE activity_id = ?",
                       (activity["id"],))
        db.execute("""UPDATE classrooms SET state = 'CLOSED', closed_at = CURRENT_TIMESTAMP,
                      state_version = state_version + 1 WHERE id = ?""", (classroom_id,))
    return {"classroom_state": "CLOSED"}


@rooms.post("/classroom-memberships")
def enroll():
    data = payload()
    code, group_name = string(data, "code", 32).upper(), string(data, "group_name", 80)
    limit_attempts("classroom-join")
    with write_transaction() as db:
        classroom_id, group_id, proof, token = join(db, code, group_name)
    session["classroom_grant"] = token
    response = jsonify(classroom_id=classroom_id, group_id=group_id)
    response.set_cookie("classroom_proof", proof, httponly=True, samesite="Lax",
                        secure=current_app.config["SESSION_COOKIE_SECURE"],
                        max_age=current_app.config["RECOVERY_SECONDS"],
                        path=f"/classrooms/{classroom_id}/result-access")
    return response, 201


@rooms.get("/classrooms/<classroom_id>/state")
def state(classroom_id):
    db = connection()
    db.execute("BEGIN")
    try:
        role = request.headers.get("X-Activity-Role", "student")
        if role == "teacher":
            room, group = owned_classroom(db, require_teacher(db), classroom_id), None
        else:
            group = identity_for(db, classroom_id)
            room = classroom(db, classroom_id)
            if room['state'] == 'CLOSED':
                return dict(classroom_id=room['id'], classroom_state='CLOSED', state_version=room['state_version'])
        activity_id = room["current_activity_id"]
        activity = requested_activity(db, activity_id) if activity_id else None
        view = state_view(db, activity, group) if activity is not None else None
        if view is not None:
            view["title"] = activity["title"]
        return {
            "classroom_id": room["id"], "classroom_state": room["state"], "state_version": room["state_version"],
            "current_activity_id": activity_id, "group_name": group["name"] if group else None,
            "activity": view,
        }
    finally:
        db.execute("ROLLBACK")


@rooms.post("/classrooms/<classroom_id>/result-access")
def result_access(classroom_id):
    data = payload()
    if 'group_id' in data or 'group_name' in data:
        raise ApiError(400, 'INVALID_REQUEST')
    limit_attempts("classroom-recover")
    with write_transaction() as db:
        token = recover(db, classroom_id, request.cookies.get("classroom_proof"))
    session["classroom_grant"] = token
    return "", 204


@rooms.get("/classrooms/<classroom_id>/results")
@read_view
def settled_activities(classroom_id):
    db = connection()
    group_for(db, classroom_id)
    rows = db.execute(
        """SELECT a.id AS activity_id, c.title FROM classroom_activities c
           JOIN activities a ON a.id = c.activity_id
           WHERE c.classroom_id = ? AND a.phase = 'CLOSED' ORDER BY c.rowid""", (classroom_id,)
    ).fetchall()
    return {"activities": [dict(row) for row in rows if snapshot(db, row["activity_id"]) is not None]}
