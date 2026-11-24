from flask import Blueprint, render_template, session
from werkzeug.security import check_password_hash

from ..auth import csrf_token, issue_grant, limit_attempts, require_teacher
from ..db import connection, write_transaction
from ..http import ApiError, payload, string
from .teacher import fixed_questions, store_activity, transition

teacher = Blueprint("teacher", __name__)


@teacher.get("/teacher")
def page():
    return render_template("activities/teacher.html", csrf=csrf_token())


@teacher.post("/teacher/session")
def login():
    data = payload()
    username, password = string(data, "username", 128), string(data, "password", 1024, strip=False)
    limit_attempts("teacher")
    row = connection().execute("SELECT * FROM teachers WHERE username = ? AND active = 1", (username,)).fetchone()
    if row is None or not check_password_hash(row["password_hash"], password):
        raise ApiError(401, "INVALID_LOGIN")
    with write_transaction() as db:
        token = issue_grant(db, teacher_id=row["id"])
    session["teacher_grant"] = token
    return "", 204


@teacher.post("/activities")
def create():
    data = payload()
    teacher_context = require_teacher()
    import_id = string(data, "import_id")
    version = data.get("import_version")
    if type(version) is not int or not 0 < version <= 2**63 - 1:
        raise ApiError(400, "INVALID_REQUEST")
    questions = fixed_questions(teacher_context, import_id, version)
    with write_transaction() as db:
        result = store_activity(db, require_teacher(db), import_id, version, questions)
    return result, 201


@teacher.post("/activities/<activity_id>/start")
def start(activity_id):
    with write_transaction() as db:
        result = transition(db, activity_id, require_teacher(db), "PREPARING", "LIVE")
    return result


@teacher.post("/activities/<activity_id>/close")
def close(activity_id):
    with write_transaction() as db:
        result = transition(db, activity_id, require_teacher(db), "LIVE", "CLOSED")
    return result
