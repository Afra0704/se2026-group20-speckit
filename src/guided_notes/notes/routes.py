"""Teacher-only import UI/API; source coordinates never enter student views."""
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, url_for

from ..auth import require_teacher
from ..db import connection
from ..http import ApiError, payload
from . import import_service as service, repository as repo
from .google_authorization import AuthError, authorize
from .models import ContractError
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
    if substitute is not None:
        return substitute
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
    data = {"code": code, "message": messages.get(code, "操作未完成，請確認來源與設定後重試。"),
            "retryable": code in {"SOURCE_READ_UNAVAILABLE", "GOOGLE_RATE_LIMITED"}, "context": context or {}}
    if (request.is_json or request.accept_mimetypes.best == "application/json"
            or (request.method == "GET" and request.accept_mimetypes.best != "text/html")):
        return jsonify(error=data), status
    return render_template("notes/error.html", error=data), status


@notes.errorhandler(ApiError)
def api_error(error):
    return error_response(error.code, error.status)


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
    return {"preview_id": row["preview_id"], "status": row["status"], "title": row["display_title"],
        "sheet_id": row["sheet_id"], "question_count": recognized.question_count,
        "answer_item_count": recognized.answer_item_count, "recognized": recognized}


@notes.get("")
def index():
    teacher = require_teacher()
    catalogs = connection().execute("""SELECT c.import_id,c.version,c.confirmed_at,s.display_title
        FROM notes_catalogs c JOIN notes_imports i USING(import_id)
        JOIN notes_sources s USING(source_id) WHERE s.teacher_id=? ORDER BY c.confirmed_at DESC""",
        (teacher.teacher_id,)).fetchall()
    configured = (current_app.config.get("NOTES_GATEWAY") is not None or (
        current_app.config.get("NOTES_GOOGLE_TEACHER_ID") == teacher.teacher_id
        and bool(current_app.config.get("NOTES_GOOGLE_CLIENT_SECRETS"))
        and bool(current_app.config.get("NOTES_GOOGLE_TOKEN"))))
    return render_template("notes/import.html", catalogs=catalogs, configured=configured)


@notes.post("/worksheets")
def worksheets():
    teacher = require_teacher()
    url = payload().get("spreadsheet_url")
    spreadsheet_id, gid = parse_sheets_url(url)
    sheets = gateway(teacher).list_worksheets(spreadsheet_id)
    if api_request():
        return jsonify(worksheets=sheets, suggested_sheet_id=gid)
    return render_template("notes/worksheets.html", worksheets=sheets, spreadsheet_url=url, gid=gid)


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
    pid = service.create_preview(teacher, gateway(teacher), spreadsheet_id, sheet_id)
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
    imports = connection().execute("""SELECT i.import_id,max(c.version) AS version FROM notes_imports i
        JOIN notes_catalogs c USING(import_id) WHERE i.source_id=? GROUP BY i.import_id""", (row["source_id"],)).fetchall()
    return render_template("notes/import_preview.html", preview=preview_data(row), imports=imports,
        confirmed_import_id=row["confirmed_import_id"], confirmed_version=row["confirmed_version"])


@notes.post("/import-previews/<preview_id>/confirm")
def confirm_preview(preview_id):
    teacher = require_teacher()
    data = payload()
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
    return redirect(url_for("notes.view_catalog", import_id=catalog["import_id"], version=catalog["import_version"]), code=303)


@notes.get("/catalogs/<import_id>/versions/<int:version>")
def view_catalog(import_id, version):
    teacher = require_teacher()
    catalog = service.get_catalog(teacher, import_id, version)
    if api_request():
        return jsonify(catalog)
    row = repo.catalog_row(connection(), teacher.teacher_id, import_id, version)
    source = repo.owned_import(connection(), teacher.teacher_id, import_id)
    return render_template("notes/catalog.html", catalog=catalog, title=source["display_title"],
                           recognized=repo.unpack_recognition(row["recognized"]))
