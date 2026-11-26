import copy
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest

from conftest import post
from guided_notes.db import connection
from guided_notes.notes.sheets_gateway import GatewayError


URL = "https://docs.google.com/spreadsheets/d/synthetic/edit?gid=7#gid=7"


class MutableSheets:
    def __init__(self):
        path = Path(__file__).parents[1] / "fixtures/sheets_layouts.json"
        self.layouts = json.loads(path.read_text(encoding="utf-8"))
        self.sheet = copy.deepcopy(self.layouts["mixed"])
        self.calls = []
        self.error = None
        self.barrier = None

    def list_worksheets(self, spreadsheet_id):
        assert not connection().in_transaction
        self.calls.append("list")
        if self.error:
            raise self.error
        return [{"sheet_id": 7, "title": "合成學習單"}]

    def read_sheet(self, spreadsheet_id, sheet_id):
        assert not connection().in_transaction
        self.calls.append("read")
        if self.error:
            raise self.error
        assert sheet_id == 7
        if self.barrier:
            self.barrier.wait(timeout=5)
        return copy.deepcopy(self.sheet)

    def write_unit(self, *args, **kwargs):
        raise AssertionError("Import must never write to Sheets")


@pytest.fixture
def sheets(app):
    gateway = MutableSheets()
    app.config.update(NOTES_GATEWAY=gateway, GET_CATALOG=None)
    return gateway


def preview(teacher):
    response = post(teacher, "/teacher/notes/import-previews", spreadsheet_url=URL, sheet_id=7)
    assert response.status_code == 201, response.get_data(as_text=True)
    return response.json["preview_id"]


def confirm(teacher, preview_id, **extra):
    return post(teacher, f"/teacher/notes/import-previews/{preview_id}/confirm", confirm=True, **extra)


def test_teacher_import_confirm_catalog_and_activity_are_connected(app, teacher, sheets):
    assert teacher.get("/teacher/notes").status_code == 200
    listed = post(teacher, "/teacher/notes/worksheets", spreadsheet_url=URL)
    assert listed.status_code == 200
    assert listed.json["worksheets"] == [{"sheet_id": 7, "title": "合成學習單"}]
    pid = preview(teacher)
    page = teacher.get(f"/teacher/notes/import-previews/{pid}")
    assert page.status_code == 200
    assert "合成學習單" in page.get_data(as_text=True)
    saved = confirm(teacher, pid)
    assert saved.status_code == 200
    catalog = saved.json
    assert (catalog["question_count"], catalog["answer_item_count"]) == (2, 3)
    assert "answer_range" not in json.dumps(catalog)
    saved_page = teacher.get(f"/teacher/notes/catalogs/{catalog['import_id']}/versions/1")
    assert saved_page.status_code == 200
    assert "使用這份講義建立活動" in saved_page.get_data(as_text=True)
    assert "台北時間" in teacher.get("/teacher/notes").get_data(as_text=True)
    created = post(teacher, "/activities", import_id=catalog["import_id"], import_version=1)
    assert created.status_code == 201
    state = teacher.get(f"/activities/{created.json['activity_id']}/state").json
    assert [len(q["items"]) for q in state["questions"]] == [2, 1]
    with app.app_context():
        assert connection().execute("SELECT count(*) FROM notes_catalogs").fetchone()[0] == 1
        assert connection().execute("SELECT count(*) FROM notes_blanks").fetchone()[0] == 3


def test_repeated_confirmation_returns_same_version_without_read(app, teacher, sheets):
    pid = preview(teacher)
    first = confirm(teacher, pid)
    reads = len(sheets.calls)
    second = confirm(teacher, pid)
    assert first.json == second.json
    assert len(sheets.calls) == reads


def test_parallel_confirmation_publishes_one_catalog(app, teacher, sheets):
    pid = preview(teacher)
    clients = [app.test_client(), app.test_client()]
    with teacher.session_transaction() as state:
        session_state = dict(state)
    for client in clients:
        with client.session_transaction() as state:
            state.update(session_state)
    sheets.barrier = Barrier(2)
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda c: confirm(c, pid), clients))
    assert [response.status_code for response in results] == [200, 200]
    assert results[0].json == results[1].json
    with app.app_context():
        assert connection().execute("SELECT count(*) FROM notes_catalogs").fetchone()[0] == 1


def test_source_change_invalidates_old_preview_and_requires_new_confirmation(teacher, sheets):
    pid = preview(teacher)
    sheets.sheet = copy.deepcopy(sheets.layouts["moved"])
    stale = confirm(teacher, pid)
    assert stale.status_code == 409
    assert stale.json["error"]["code"] == "SOURCE_CHANGED"
    next_id = stale.json["error"]["context"]["new_preview_id"]
    assert confirm(teacher, pid).status_code == 409
    assert confirm(teacher, next_id).status_code == 200


def test_new_version_never_replaces_an_activity_catalog(app, teacher, sheets):
    first = confirm(teacher, preview(teacher)).json
    created = post(teacher, "/activities", import_id=first["import_id"], import_version=1).json
    sheets.sheet = copy.deepcopy(sheets.layouts["single"])
    second = confirm(teacher, preview(teacher), existing_import_id=first["import_id"]).json
    assert second["import_version"] == 2
    assert second["question_count"] == 1
    old = teacher.get(f"/teacher/notes/catalogs/{first['import_id']}/versions/1", headers={"Accept": "application/json"})
    assert old.json == first
    state = teacher.get(f"/activities/{created['activity_id']}/state").json
    assert len(state["questions"]) == 2
    assert confirm(teacher, preview(teacher), existing_import_id="missing").status_code == 404


def test_other_teacher_cannot_read_or_confirm_preview_or_catalog(app, teacher, sheets):
    pid = preview(teacher)
    catalog = confirm(teacher, pid).json
    other = app.test_client()
    assert post(other, "/teacher/session", username="other", password="test-password").status_code == 204
    reads = len(sheets.calls)
    assert other.get(f"/teacher/notes/import-previews/{pid}").status_code == 404
    assert confirm(other, pid).status_code == 404
    assert other.get(f"/teacher/notes/catalogs/{catalog['import_id']}/versions/1").status_code == 404
    assert post(other, "/activities", import_id=catalog["import_id"], import_version=1).status_code == 404
    assert len(sheets.calls) == reads


def test_invalid_url_format_and_google_permissions_are_safe(teacher, sheets):
    assert post(teacher, "/teacher/notes/worksheets", spreadsheet_url="https://evil.invalid/").status_code == 400
    assert not sheets.calls
    sheets.error = GatewayError("SOURCE_READ_FORBIDDEN", http_status=403)
    denied = post(teacher, "/teacher/notes/worksheets", spreadsheet_url=URL)
    assert denied.status_code == 403
    assert denied.json["error"]["code"] == "SOURCE_READ_FORBIDDEN"
    sheets.error = None
    sheets.sheet = copy.deepcopy(sheets.layouts["missing_header"])
    bad = post(teacher, "/teacher/notes/import-previews", spreadsheet_url=URL, sheet_id=7)
    assert bad.status_code == 422
    assert bad.json["error"]["code"] == "HEADER_MISSING"


def test_preview_escapes_source_text(teacher, sheets):
    sheets.sheet["data"][0]["rowData"][4]["values"][2]["userEnteredValue"] = {"stringValue": "<script>alert(1)</script>"}
    pid = preview(teacher)
    html = teacher.get(f"/teacher/notes/import-previews/{pid}").get_data(as_text=True)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_html_forms_keep_csrf_and_confirm_by_redirect(teacher, sheets):
    token = teacher.get("/csrf").json["csrf"]
    listed = teacher.post("/teacher/notes/worksheets", data={"csrf_token": token, "spreadsheet_url": URL})
    assert listed.status_code == 200
    assert 'name="sheet_id"' in listed.get_data(as_text=True)
    response = teacher.post("/teacher/notes/import-previews",
        data={"csrf_token": token, "spreadsheet_url": URL, "sheet_id": "7"})
    assert response.status_code == 303
    preview_url = response.location
    preview_page = teacher.get(preview_url).get_data(as_text=True)
    assert "G5:H5" in preview_page
    saved = teacher.post(preview_url + "/confirm", data={"csrf_token": token, "confirm": "true"})
    assert saved.status_code == 303
    assert teacher.get(saved.location).status_code == 200


def test_parallel_reimports_allocate_distinct_versions(app, teacher, sheets):
    first = confirm(teacher, preview(teacher)).json
    ids = [preview(teacher), preview(teacher)]
    clients = [app.test_client(), app.test_client()]
    with teacher.session_transaction() as state:
        original = dict(state)
    for client in clients:
        with client.session_transaction() as state:
            state.update(original)
    sheets.barrier = Barrier(2)
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda pair: confirm(pair[0], pair[1], existing_import_id=first["import_id"]),
                                zip(clients, ids)))
    assert sorted(result.json["import_version"] for result in results) == [2, 3]


def test_permission_expiry_during_source_read_does_not_publish(app, teacher, sheets, monkeypatch):
    pid = preview(teacher)
    read = sheets.read_sheet
    def expire(*args):
        value = read(*args)
        connection().execute("UPDATE grants SET expires=0 WHERE teacher_id=1")
        return value
    monkeypatch.setattr(sheets, "read_sheet", expire)
    assert confirm(teacher, pid).status_code == 401
    with app.app_context():
        assert connection().execute("SELECT count(*) FROM notes_catalogs").fetchone()[0] == 0


def test_confirm_requires_explicit_confirmation_and_consistent_target(teacher, sheets):
    pid = preview(teacher)
    assert post(teacher, f"/teacher/notes/import-previews/{pid}/confirm").status_code == 400
    assert confirm(teacher, pid).status_code == 200
    assert confirm(teacher, pid, existing_import_id="changed-target").status_code == 409


def test_renamed_worksheet_keeps_numeric_identity_and_updates_title(teacher, sheets):
    pid = preview(teacher)
    sheets.sheet["properties"]["title"] = "更新名稱"
    catalog = confirm(teacher, pid).json
    assert catalog["import_version"] == 1
    page = teacher.get(f"/teacher/notes/catalogs/{catalog['import_id']}/versions/1")
    assert "更新名稱" in page.get_data(as_text=True)


def test_published_catalog_survives_app_restart_and_is_immutable(app, teacher, sheets):
    import sqlite3
    from guided_notes import create_app
    catalog = confirm(teacher, preview(teacher)).json
    restarted = create_app({"TESTING": True, "TEACHER_AUTH_MODE": "test_password", "SECRET_KEY": app.secret_key,
                            "DATABASE": app.config["DATABASE"], "NOTES_GATEWAY": sheets})
    client = restarted.test_client()
    assert post(client, "/teacher/session", username="teacher", password="test-password").status_code == 204
    response = client.get(f"/teacher/notes/catalogs/{catalog['import_id']}/versions/1",
                          headers={"Accept": "application/json"})
    assert response.json == catalog
    with restarted.app_context():
        with pytest.raises(sqlite3.IntegrityError):
            connection().execute("UPDATE notes_catalogs SET dto='{}'")
        assert connection().execute("SELECT count(*) FROM teachers").fetchone()[0] == 2
