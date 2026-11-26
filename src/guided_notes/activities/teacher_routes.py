from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from ..auth import check_teacher_login_limit, csrf_token, issue_grant, record_teacher_login_failure, require_teacher
from ..db import connection, write_transaction
from ..http import ApiError, payload, string
from .teacher import fixed_questions, store_activity, transition
from .display_service import get_display_content, save_display

teacher = Blueprint("teacher", __name__)


@teacher.get("/teacher")
def page():
    if current_app.config['TEACHER_AUTH_MODE'] == 'google':
        try:
            require_teacher()
        except ApiError as error:
            if error.status in (401,403):
                return redirect('/teacher/login',code=303)
            raise
    if not current_app.config["CLASSROOM_MODE"]:
        return render_template("activities/teacher.html", csrf=csrf_token())
    if current_app.config["TEACHER_AUTH_MODE"] == "google":
        return render_template("workspace/welcome.html", csrf=csrf_token())
    courses = []
    logged_in = False
    try:
        context = require_teacher()
    except ApiError as error:
        if error.status not in (401, 403):
            raise
    else:
        logged_in = True
        courses = connection().execute(
            "SELECT id AS course_id, title FROM courses WHERE teacher_id = ? ORDER BY created_at, id",
            (context.teacher_id,),
        ).fetchall()
    return render_template("activities/classroom.html", csrf=csrf_token(), role="teacher",
                           initial_courses=courses, teacher_logged_in=logged_in)


@teacher.post("/teacher/session")
def login():
    if current_app.config['TEACHER_AUTH_MODE'] == 'google':
        raise ApiError(410,'PASSWORD_LOGIN_DISABLED')
    data = payload()
    browser_form = current_app.config["CLASSROOM_MODE"] and not request.is_json
    username, password = string(data, "username", 128), string(data, "password", 1024, strip=False)
    try:
        check_teacher_login_limit()
    except ApiError as error:
        if not browser_form or error.status != 429:
            raise
        flash(f"密碼輸錯次數過多，請等 {error.retry_after} 秒再試。", "error")
        return redirect(url_for("teacher.page"), code=303)
    row = connection().execute("SELECT * FROM teachers WHERE username = ? AND active = 1", (username,)).fetchone()
    if row is None or not check_password_hash(row["password_hash"], password):
        record_teacher_login_failure()
        if browser_form:
            flash("帳號或密碼不正確。", "error")
            return redirect(url_for("teacher.page"), code=303)
        raise ApiError(401, "INVALID_LOGIN")
    with write_transaction() as db:
        token = issue_grant(db, teacher_id=row["id"])
    session["teacher_grant"] = token
    if browser_form:
        flash("已登入。")
        return redirect(url_for("teacher.page"), code=303)
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
    display = get_display_content(teacher_context, import_id, version, questions)
    with write_transaction() as db:
        current_teacher = require_teacher(db)
        if current_teacher != teacher_context:
            raise ApiError(403, 'FORBIDDEN')
        from ..notes.lecture_lifecycle import require_available_for_activity
        require_available_for_activity(current_teacher, None, import_id, version, db)
        result = store_activity(db, current_teacher, import_id, version, questions)
        save_display(db, result['activity_id'], display)
    return result, 201


@teacher.post("/activities/<activity_id>/start")
def start(activity_id):
    with write_transaction() as db:
        result = transition(db, activity_id, require_teacher(db), "PREPARING", "LIVE")
    return result


@teacher.post("/activities/<activity_id>/close")
def close(activity_id):
    with write_transaction() as db:
        result = transition(db, activity_id, require_teacher(db), ("PREPARING", "LIVE"), "CLOSED")
    from ..quiz.settlement import try_pending
    try_pending(activity_id)
    return result
