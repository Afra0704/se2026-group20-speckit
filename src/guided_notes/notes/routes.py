"""Teacher-only import UI/API; source coordinates never enter student views."""
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, url_for

from ..auth import require_teacher
from ..db import connection
from ..http import ApiError, payload
from . import course_catalogs as courses, export_service, import_service as service, repository as repo, writeback
from .google_authorization import AuthError, authorize
from .models import ContractError, normalize_lecture_name
from .recognition import RecognitionError
from .sheets_gateway import GatewayError, SheetsGateway, build_google_service, parse_sheets_url

notes = Blueprint("notes", __name__, url_prefix="/teacher/notes",
                  template_folder="templates", static_folder="static", static_url_path="/assets")


def a1_range(area):
    def column(index):
        result = ""
        index += 1
        while index:
            index, remainder = divmod(index - 1, 26)
            result = chr(65 + remainder) + result
        return result
    start = f"{column(area.start_column)}{area.start_row + 1}"
    end = f"{column(area.end_column - 1)}{area.end_row}"
    return start if start == end else f"{start}:{end}"


def taipei_time(value):
    return datetime.fromisoformat(value).astimezone(timezone(timedelta(hours=8), "Asia/Taipei")).strftime("%Y-%m-%d %H:%M")


def gateway(teacher):
    substitute = current_app.config.get("NOTES_GATEWAY")
    if substitute is not None and current_app.testing:
        return substitute
    if current_app.config.get('TEACHER_AUTH_MODE') == 'google':
        from ..google_login.sheets_service import credentials
        return SheetsGateway(build_google_service(credentials(teacher)))
    profile = current_app.config.get("NOTES_GOOGLE_TEACHER_ID")
    if profile is None:
        raise ApiError(503, "GOOGLE_PROFILE_NOT_CONFIGURED")
    if profile != teacher.teacher_id:
        raise ApiError(403, "SOURCE_READ_FORBIDDEN")
    credentials = authorize(current_app.config.get("NOTES_GOOGLE_CLIENT_SECRETS"),
        current_app.config.get("NOTES_GOOGLE_TOKEN"),
        repo_root=Path(__file__).resolve().parents[3])
    return SheetsGateway(build_google_service(credentials))


def api_request():
    return request.is_json or request.accept_mimetypes.best == "application/json"


def error_response(code, status, context=None):
    code = {"AUTH_REQUIRED": "TEACHER_LOGIN_REQUIRED", "FORBIDDEN": "TEACHER_REQUIRED",
            "INVALID_CSRF": "CSRF_INVALID"}.get(code, code)
    messages = {"SOURCE_CHANGED": "來源已變更，請檢查新的預覽並再次確認。",
        "PREVIEW_STALE": "這份預覽已失效，請重新建立預覽。",
        "SOURCE_READ_FORBIDDEN": "目前帳號無法讀取這份講義，請確認授權與共用設定。",
        "TEACHER_LOGIN_REQUIRED": "請先到教師活動頁登入。",
        "TEACHER_REQUIRED": "此操作需要教師權限。",
        "GOOGLE_PROFILE_NOT_CONFIGURED": "尚未設定這台電腦的講義授權帳號。",
        "GOOGLE_REAUTH_REQUIRED": "Google 授權已失效，請在本機重新執行授權指令。",
        "CSRF_INVALID": "頁面驗證已失效，請重新整理再操作。"}
    messages.update({"ACTIVITY_NOT_ENDED": "活動尚未結束，請先結束活動再建立回填預覽。",
        "RESULT_NOT_READY": "活動已結束，但結果尚未結算完成。請等待結果模組完成結算後再試。",
        "RESULT_INVALID": "結算結果與活動的講義版本或完整小題不符，請與結果模組負責同學核對。",
        "RESULT_VERSION_CHANGED": "建立預覽期間結果已改變，請重新建立預覽。",
        "SOURCE_STRUCTURE_CHANGED": "講義的題目或小題已改變，請重新匯入並核對活動使用的版本。",
        "ACTIVITY_NOT_FOUND": "找不到可存取的活動。請核對活動識別與教師帳號。"})
    messages.update({"COURSE_UNAVAILABLE": "課程管理介面尚未接好，請待 002 完成接線。既有講義匯入仍可使用。",
        "COURSE_NOT_FOUND": "找不到可存取的課程。",
        "COURSE_MISMATCH": "這份講義屬於不同課程，請在原課程更新，或另建講義清單。"})
    messages.update({"SOURCE_BUSY": "這份講義已有回填正在執行或尚待恢復，請查看原作業後再操作。",
        "IDEMPOTENCY_CONFLICT": "這次重送的內容與原確認不同，請回到預覽重新確認。",
        "OVERWRITE_CONFIRMATION_REQUIRED": "請逐項確認所有需要覆寫的答案格。"})
    messages["INVALID_LECTURE_NAME"] = "請選擇名稱方式；自訂講義名稱須為 1–100 個字元，且不能包含換行或控制字元。"
    if current_app.config.get('TEACHER_AUTH_MODE') == 'google':
        from ..google_login.routes import MESSAGES
        messages.update(MESSAGES)
    data = {"code": code, "message": messages.get(code, "操作未完成，請確認來源與設定後重試。"),
            "retryable": code in {"SOURCE_READ_UNAVAILABLE", "GOOGLE_RATE_LIMITED", 'GOOGLE_REFRESH_BUSY', 'GOOGLE_REFRESH_TIMEOUT', 'GOOGLE_CREDENTIALS_REFRESH_REQUIRED'}, "context": context or {}}
    if (request.is_json or request.accept_mimetypes.best == "application/json"
            or (request.method == "GET" and request.accept_mimetypes.best != "text/html")):
        return jsonify(error=data), status
    return render_template("notes/error.html", error=data), status


@notes.errorhandler(ApiError)
def api_error(error):
    response = current_app.make_response(error_response(error.code, error.status, getattr(error, "context", None)))
    if error.retry_after is not None:
        response.headers['Retry-After'] = str(error.retry_after)
    return response


@notes.errorhandler(GatewayError)
@notes.errorhandler(AuthError)
@notes.errorhandler(ContractError)
def domain_error(error):
    return error_response(error.code, error.http_status)


@notes.errorhandler(RecognitionError)
def format_error(error):
    return error_response(error.issues[0].code, 422, {"issues": [{"code": issue.code,
        "message": issue.message,
        "sheet_id": issue.sheet_id, "question_number": issue.question_number,
        "range": asdict(issue.problem_range) if issue.problem_range else None}
        for issue in error.issues]})


def preview_data(row):
    recognized = repo.unpack_recognition(row["recognized"])
    title = row["custom_title"] if row["name_mode"] == "custom" else row["display_title"]
    return {"preview_id": row["preview_id"], "status": row["status"], "title": title,
        "source_title": row["display_title"], "name_mode": row["name_mode"],
        "sheet_id": row["sheet_id"], "course_id": row["course_id"], "question_count": recognized.question_count,
        "answer_item_count": recognized.answer_item_count, "recognized": recognized}


@notes.get("")
def index():
    teacher = require_teacher()
    catalogs = connection().execute("""SELECT c.import_id,c.version,c.confirmed_at,
        s.display_title AS source_title,
        CASE WHEN n.name_mode='custom' THEN n.custom_title ELSE s.display_title END AS display_title
        FROM notes_catalogs c JOIN notes_imports i USING(import_id)
        JOIN notes_sources s USING(source_id) LEFT JOIN notes_catalog_names n ON n.import_id=c.import_id AND n.version=c.version
        WHERE s.teacher_id=? AND NOT EXISTS(SELECT 1 FROM notes_lecture_removals r WHERE r.import_id=i.import_id) ORDER BY c.confirmed_at DESC""",
        (teacher.teacher_id,)).fetchall()
    configured = (current_app.config.get("NOTES_GATEWAY") is not None or (
        current_app.config.get("NOTES_GOOGLE_TEACHER_ID") == teacher.teacher_id
        and bool(current_app.config.get("NOTES_GOOGLE_CLIENT_SECRETS"))
        and bool(current_app.config.get("NOTES_GOOGLE_TOKEN"))))
    if current_app.config.get('TEACHER_AUTH_MODE') == 'google':
        from ..google_login.sheets_service import authorization_status
        configured = authorization_status(teacher)['status'] == 'connected'
    return render_template("notes/import.html", catalogs=catalogs, configured=configured)


@notes.post("/worksheets")
def worksheets():
    teacher = require_teacher()
    data = payload()
    course = courses.get_owned_course(teacher, data.get("course_id")) if "course_id" in data else None
    url = data.get("spreadsheet_url")
    spreadsheet_id, gid = parse_sheets_url(url)
    sheets = gateway(teacher).list_worksheets(spreadsheet_id)
    if api_request():
        if course:
            return jsonify(worksheets=sheets, suggested_sheet_id=gid, course_id=course["course_id"])
        return jsonify(worksheets=sheets, suggested_sheet_id=gid)
    return render_template("notes/worksheets.html", worksheets=sheets, spreadsheet_url=url, gid=gid, course=course)


@notes.post("/import-previews")
def create_preview():
    teacher = require_teacher()
    data = payload()
    spreadsheet_id, _ = parse_sheets_url(data.get("spreadsheet_url"))
    sheet_id = data.get("sheet_id")
    if not request.is_json:
        try:
            sheet_id = int(sheet_id)
        except (ValueError, TypeError):
            raise ApiError(400, "INVALID_REQUEST") from None
    if type(sheet_id) is not int or not 0 <= sheet_id <= 2**63 - 1:
        raise ApiError(400, "INVALID_REQUEST")
    name_mode, custom_title = normalize_lecture_name(data.get("name_mode", "source"), data.get("custom_title"))
    course = courses.get_owned_course(teacher, data.get("course_id")) if "course_id" in data else None
    pid = service.create_preview(teacher, gateway(teacher), spreadsheet_id, sheet_id, name_mode, custom_title,
                                 course["course_id"] if course else None)
    if api_request():
        row = repo.owned_preview(connection(), teacher.teacher_id, pid)
        data = preview_data(row)
        data.pop("recognized")
        data["preview_url"] = url_for("notes.view_preview", preview_id=pid)
        return jsonify(data), 201
    return redirect(url_for("notes.view_preview", preview_id=pid), code=303)


@notes.get("/import-previews/<preview_id>")
def view_preview(preview_id):
    teacher = require_teacher()
    row = repo.owned_preview(connection(), teacher.teacher_id, preview_id)
    if not api_request() and current_app.config["TEACHER_AUTH_MODE"] == "google" and current_app.config["CLASSROOM_MODE"]:
        from ..workspace.import_flows import preview_context
        context = preview_context(connection(), preview_id)
        if context:
            return redirect(url_for("workspace.import_page", flow_id=context["flow_id"]), code=303)
    course = courses.get_owned_course(teacher, row["course_id"]) if row["course_id"] is not None else None
    imports = connection().execute("""SELECT i.import_id,c.version,
        CASE WHEN n.name_mode='custom' THEN n.custom_title ELSE s.display_title END AS display_title
        FROM notes_imports i JOIN notes_sources s USING(source_id)
        JOIN notes_catalogs c ON c.import_id=i.import_id
        LEFT JOIN notes_catalog_names n ON n.import_id=c.import_id AND n.version=c.version
        LEFT JOIN notes_import_courses ic ON ic.import_id=i.import_id
        WHERE i.source_id=? AND ic.course_id IS ? AND NOT EXISTS(SELECT 1 FROM notes_lecture_removals r WHERE r.import_id=i.import_id) AND c.version=(SELECT max(version) FROM notes_catalogs WHERE import_id=i.import_id)
        ORDER BY c.confirmed_at DESC""", (row["source_id"], row["course_id"])).fetchall()
    return render_template("notes/import_preview.html", preview=preview_data(row), imports=imports,
        confirmed_import_id=row["confirmed_import_id"], confirmed_version=row["confirmed_version"], course=course)


@notes.post("/import-previews/<preview_id>/confirm")
def confirm_preview(preview_id):
    teacher = require_teacher()
    data = payload()
    if "name_mode" in data or "custom_title" in data or "course_id" in data:
        raise ApiError(400, "INVALID_REQUEST")
    if (request.is_json and data.get("confirm") is not True) or (
            not request.is_json and data.get("confirm") != "true"):
        raise ApiError(400, "INVALID_REQUEST")
    import_id = data.get("existing_import_id") or None
    if import_id is not None and (not isinstance(import_id, str) or len(import_id) > 128):
        raise ApiError(400, "INVALID_REQUEST")
    catalog, new_preview_id = service.confirm_preview(teacher, preview_id, lambda: gateway(teacher), import_id)
    if new_preview_id:
        return error_response("SOURCE_CHANGED", 409, {"new_preview_id": new_preview_id,
            "preview_url": url_for("notes.view_preview", preview_id=new_preview_id)})
    if api_request():
        return jsonify(catalog)
    if current_app.config["TEACHER_AUTH_MODE"] == "google" and current_app.config["CLASSROOM_MODE"]:
        from ..workspace.import_flows import preview_context
        context = preview_context(connection(), preview_id)
        if context:
            row = repo.owned_preview(connection(), teacher.teacher_id, preview_id)
            return redirect(url_for("workspace.lectures", course_id=row["course_id"]), code=303)
    return redirect(url_for("notes.view_catalog", import_id=catalog["import_id"], version=catalog["import_version"]), code=303)


@notes.get("/catalogs/<import_id>/versions/<int:version>")
def view_catalog(import_id, version):
    teacher = require_teacher()
    catalog = service.get_catalog(teacher, import_id, version)
    course_id = courses.import_course_id(connection(), import_id)
    course = courses.get_owned_course(teacher, course_id) if course_id is not None else None
    if api_request():
        return jsonify(catalog)
    row = repo.catalog_row(connection(), teacher.teacher_id, import_id, version)
    source = repo.owned_import(connection(), teacher.teacher_id, import_id)
    title = row["custom_title"] if row["name_mode"] == "custom" else source["display_title"]
    from .display_service import get_display_content
    try:
        display = get_display_content(teacher, import_id, version)
    except ApiError as error:
        if error.code != 'QUESTION_TEXT_UNAVAILABLE':
            raise
        display = None
    return render_template("notes/catalog.html", catalog=catalog, title=title, course=course,
                           display=display,
                           source_title=source["display_title"],
                           source_url=f"https://docs.google.com/spreadsheets/d/{source['spreadsheet_id']}/edit#gid={source['sheet_id']}",
                           recognized=repo.unpack_recognition(row["recognized"]) if display else None)


@notes.get("/courses/<course_id>")
def course_page(course_id):
    teacher = require_teacher()
    if current_app.config["TEACHER_AUTH_MODE"] == "google" and current_app.config["CLASSROOM_MODE"] and not api_request():
        courses.get_owned_course(teacher, course_id)
        return redirect(url_for("workspace.lectures", course_id=course_id), code=303)
    data = courses.list_course_catalogs(teacher, course_id)
    unassigned = connection().execute("""SELECT i.import_id,
        CASE WHEN n.name_mode='custom' THEN n.custom_title ELSE s.display_title END AS title
        FROM notes_imports i JOIN notes_sources s USING(source_id)
        JOIN notes_catalogs c ON c.import_id=i.import_id
        LEFT JOIN notes_catalog_names n ON n.import_id=c.import_id AND n.version=c.version
        LEFT JOIN notes_import_courses ic ON ic.import_id=i.import_id
        WHERE s.teacher_id=? AND ic.import_id IS NULL AND NOT EXISTS(SELECT 1 FROM notes_lecture_removals r WHERE r.import_id=i.import_id)
        AND c.version=(SELECT max(version) FROM notes_catalogs WHERE import_id=i.import_id)
        ORDER BY c.confirmed_at DESC""", (teacher.teacher_id,)).fetchall()
    return render_template("notes/course.html", course=data, unassigned=unassigned)


@notes.get("/courses/<course_id>/catalogs")
def course_catalog_list(course_id):
    return jsonify(courses.list_course_catalogs(require_teacher(), course_id))


@notes.get("/courses/<course_id>/catalogs/<import_id>/versions/<int:version>")
def course_catalog_version(course_id, import_id, version):
    return jsonify(courses.get_course_catalog(require_teacher(), course_id, import_id, version))


@notes.post("/courses/<course_id>/lectures")
def assign_course_lecture(course_id):
    teacher = require_teacher()
    data = payload()
    import_id = data.get("import_id")
    allowed = {"import_id"} if request.is_json else {"import_id", "csrf_token"}
    if (set(data) - allowed or not isinstance(import_id, str) or not import_id.strip() or len(import_id) > 128):
        raise ApiError(400, "INVALID_REQUEST")
    result = courses.assign_lecture(teacher, course_id, import_id)
    if api_request():
        return jsonify(result)
    return redirect(url_for("notes.course_page", course_id=course_id), code=303)


def export_preview_data(row, preview):
    winners = {unit["question_id"]: unit["winner_group_id"] for unit in preview.snapshot["units"]}
    questions = {q["question_id"]: q for q in preview.bundle.catalog["questions"]}
    items = [{"question_id": item.question_id, "display_number": questions[item.question_id]["display_number"],
        "item_id": item.item_id, "blank_id": item.blank_id, "subitem_label": item.binding.subitem_label,
        "winner_group_id": winners[item.question_id], "answer_range": asdict(item.binding.answer_range),
        "original_user_value": item.original_user_value, "proposed_text": item.proposed_text,
        "action": item.action} for item in preview.items]
    return {"preview_id": row["preview_id"], "status": row["status"], "activity_id": row["activity_id"],
        "origin_operation_id": row["origin_operation_id"],
        "import_id": row["import_id"], "import_version": row["import_version"],
        "result_version": row["result_version"], "created_at": row["created_at"],
        "title": row["custom_title"] if row["name_mode"] == "custom" else row["display_title"],
        "source_title": row["display_title"], "sheet_id": row["sheet_id"],
        "question_count": preview.bundle.catalog["question_count"], "answer_item_count": len(items),
        "items": items, "counts": {action: sum(i["action"] == action for i in items) for action in (
            "write", "already_matches", "skip", "requires_overwrite_confirmation")},
        "preview_url": url_for("notes.view_export_preview", preview_id=row["preview_id"])}


@notes.get("/export-previews")
def export_form():
    teacher = require_teacher()
    previews = connection().execute("""SELECT p.preview_id,p.activity_id,p.created_at
        FROM notes_export_previews p JOIN notes_sources s USING(source_id)
        WHERE s.teacher_id=? ORDER BY p.created_at DESC""", (teacher.teacher_id,)).fetchall()
    return render_template("notes/export_form.html", previews=previews)


@notes.post("/export-previews")
def create_export_preview():
    teacher = require_teacher()
    data = payload()
    allowed = {"activity_id"} if request.is_json else {"activity_id", "csrf_token"}
    aid = data.get("activity_id")
    if (set(data) - allowed or not isinstance(aid, str) or not aid.strip()
            or len(aid) > 256 or any(ord(c) < 32 or ord(c) == 127 for c in aid)):
        raise ApiError(400, "INVALID_REQUEST")
    pid = export_service.create_saved_preview(teacher, aid, lambda: gateway(teacher))
    if api_request():
        row, preview = export_service.get_saved_preview(teacher, pid)
        return jsonify(export_preview_data(row, preview)), 201
    return redirect(url_for("notes.view_export_preview", preview_id=pid), code=303)


@notes.get("/export-previews/<preview_id>")
def view_export_preview(preview_id):
    teacher = require_teacher()
    row, preview = export_service.get_saved_preview(teacher, preview_id)
    data = export_preview_data(row, preview)
    if api_request():
        return jsonify(data)
    operation = connection().execute("SELECT operation_id FROM notes_write_operations WHERE preview_id=?", (preview_id,)).fetchone()
    return render_template("notes/export_preview.html", preview=data, items=preview.items, idempotency_key=str(uuid4()),
                           operation_id=operation[0] if operation else None)


@notes.post("/export-previews/<preview_id>/confirm")
def confirm_export_preview(preview_id):
    teacher = require_teacher()
    data = payload()
    allowed = {"confirm", "overwrite_item_ids"}
    if not request.is_json:
        allowed |= {"csrf_token", "idempotency_key"}
    confirm_value = data.get("confirm")
    if set(data) - allowed or (request.is_json and confirm_value is not True) or (
            not request.is_json and confirm_value != "true"):
        raise ApiError(400, "INVALID_REQUEST")
    key = request.headers.get("Idempotency-Key") if request.is_json else data.get("idempotency_key")
    overwrite = data.get("overwrite_item_ids", []) if request.is_json else data.getlist("overwrite_item_ids")
    if (not isinstance(key, str) or not 1 <= len(key) <= 128 or any(ord(c) < 33 or ord(c) > 126 for c in key)
            or not isinstance(overwrite, list) or any(not isinstance(i, str) for i in overwrite)
            or len(set(overwrite)) != len(overwrite)):
        raise ApiError(400, "INVALID_REQUEST")
    report = writeback.confirm(teacher, preview_id, key, overwrite, lambda: gateway(teacher))
    if api_request():
        return jsonify(report), 202 if report["status"] in {"writing", "queued"} else 200
    return redirect(url_for("notes.operation_report", operation_id=report["operation_id"]), code=303)


@notes.get("/operations/<operation_id>")
def operation_report(operation_id):
    teacher = require_teacher()
    report = writeback.get_report(teacher, operation_id)
    if api_request():
        return jsonify(report)
    row = repo.owned_operation(connection(), teacher.teacher_id, operation_id)
    preview_row, preview = export_service.get_saved_preview(teacher, row["preview_id"])
    data = export_preview_data(preview_row, preview)
    return render_template("notes/report.html", report=report, preview=data,
                           labels={item["item_id"]: item for item in data["items"]})


@notes.post("/operations/<operation_id>/recovery-preview")
def recover_export(operation_id):
    teacher = require_teacher()
    data = payload()
    if set(data) - (set() if request.is_json else {"csrf_token"}):
        raise ApiError(400, "INVALID_REQUEST")
    pid = writeback.recovery_preview(teacher, operation_id, lambda: gateway(teacher))
    if api_request():
        row, preview = export_service.get_saved_preview(teacher, pid)
        return jsonify(export_preview_data(row, preview)), 201
    return redirect(url_for("notes.view_export_preview", preview_id=pid), code=303)


@notes.post('/courses/<course_id>/lectures/<import_id>/remove')
def remove_lecture(course_id,import_id):
    from .lecture_lifecycle import remove
    data=dict(payload());data.pop('csrf_token',None)
    if set(data)!={'confirm'} or (data['confirm'] is not True if request.is_json else data['confirm']!='true'):
        raise ApiError(400,'INVALID_REQUEST')
    result=remove(require_teacher(),course_id,import_id)
    if api_request():return jsonify(result)
    return redirect(url_for('workspace.lectures',course_id=course_id),code=303)
