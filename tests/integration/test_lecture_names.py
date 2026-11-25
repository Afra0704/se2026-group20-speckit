import copy
import json

from conftest import post
from guided_notes.db import connection
from test_import_routes import URL, MutableSheets, sheets


def named_preview(teacher, **naming):
    response = post(teacher, "/teacher/notes/import-previews", spreadsheet_url=URL, sheet_id=7, **naming)
    assert response.status_code == 201
    return response.json


def confirm(teacher, pid, **extra):
    return post(teacher, f"/teacher/notes/import-previews/{pid}/confirm", confirm=True, **extra)


def test_default_uses_source_name_and_custom_name_is_local_metadata(app, teacher, sheets):
    original = copy.deepcopy(sheets.sheet)
    inherited = named_preview(teacher)
    assert inherited["title"] == inherited["source_title"] == "合成學習單"
    custom = named_preview(teacher, name_mode="custom", custom_title="  第一章複習  ")
    assert custom["title"] == "第一章複習"
    assert custom["source_title"] == "合成學習單"
    page = teacher.get(custom["preview_url"]).get_data(as_text=True)
    assert "第一章複習" in page and "合成學習單" in page
    catalog = confirm(teacher, custom["preview_id"]).json
    saved = teacher.get(f"/teacher/notes/catalogs/{catalog['import_id']}/versions/1").get_data(as_text=True)
    assert "第一章複習" in saved and "合成學習單" in saved
    assert "第一章複習" in teacher.get("/teacher/notes").get_data(as_text=True)
    assert "custom_title" not in catalog and "name_mode" not in catalog
    assert sheets.sheet == original
    with app.app_context():
        assert connection().execute("SELECT display_title FROM notes_sources").fetchone()[0] == "合成學習單"


def test_invalid_name_rejected_before_google_read(teacher, sheets):
    for value in ("", " \t ", "a" * 101, "第一行\n第二行", None, [], 123):
        response = post(teacher, "/teacher/notes/import-previews", spreadsheet_url=URL, sheet_id=7,
                        name_mode="custom", custom_title=value)
        assert response.status_code == 400
        assert response.json["error"]["code"] == "INVALID_LECTURE_NAME"
    assert not sheets.calls
    assert post(teacher, "/teacher/notes/import-previews", spreadsheet_url=URL,
                sheet_id=7, name_mode="unknown").status_code == 400


def test_custom_name_survives_source_changes_and_refresh(teacher, sheets):
    preview = named_preview(teacher, name_mode="custom", custom_title="複習講義")
    sheets.sheet = copy.deepcopy(sheets.layouts["moved"])
    sheets.sheet["properties"]["title"] = "改過的分頁"
    stale = confirm(teacher, preview["preview_id"])
    assert stale.status_code == 409
    new_pid = stale.json["error"]["context"]["new_preview_id"]
    page = teacher.get(f"/teacher/notes/import-previews/{new_pid}").get_data(as_text=True)
    assert "複習講義" in page and "改過的分頁" in page
    catalog = confirm(teacher, new_pid).json
    for _ in range(2):
        assert "複習講義" in teacher.get(f"/teacher/notes/catalogs/{catalog['import_id']}/versions/1").get_data(as_text=True)


def test_names_are_version_specific_and_cannot_be_changed_on_confirm(teacher, sheets):
    first = named_preview(teacher, name_mode="custom", custom_title="第一版名稱")
    assert confirm(teacher, first["preview_id"], custom_title="偷改名稱").status_code == 400
    old = confirm(teacher, first["preview_id"]).json
    second = named_preview(teacher, name_mode="custom", custom_title="第二版名稱")
    new = confirm(teacher, second["preview_id"], existing_import_id=old["import_id"]).json
    assert new["import_version"] == 2
    for version, title in ((1,"第一版名稱"),(2,"第二版名稱")):
        html = teacher.get(f"/teacher/notes/catalogs/{old['import_id']}/versions/{version}").get_data(as_text=True)
        assert title in html
    assert confirm(teacher, second["preview_id"], existing_import_id=old["import_id"]).json == new


def test_custom_name_is_escaped_and_source_mode_ignores_unused_name(teacher, sheets):
    value = '<script>alert("name")</script>'
    preview = named_preview(teacher, name_mode="custom", custom_title=value)
    html = teacher.get(preview["preview_url"]).get_data(as_text=True)
    assert value not in html and "&lt;script&gt;" in html
    inherited = named_preview(teacher, name_mode="source", custom_title="忽略這個欄位")
    assert inherited["title"] == "合成學習單"


def test_multiple_worksheets_are_listed_but_imported_separately(app, teacher, sheets, monkeypatch):
    reads = []
    def read(spreadsheet_id, sheet_id):
        assert not connection().in_transaction
        reads.append(sheet_id)
        sheet = copy.deepcopy(sheets.layouts["mixed" if sheet_id == 7 else "single"])
        sheet["properties"].update(sheetId=sheet_id, title="第一章" if sheet_id == 7 else "第二章")
        for merge in sheet["merges"]:
            merge["sheetId"] = sheet_id
        return sheet
    monkeypatch.setattr(sheets, "list_worksheets", lambda _: [{"sheet_id":7,"title":"第一章"},{"sheet_id":9,"title":"第二章"}])
    monkeypatch.setattr(sheets, "read_sheet", read)
    assert len(post(teacher, "/teacher/notes/worksheets", spreadsheet_url=URL).json["worksheets"]) == 2
    catalogs = []
    for sheet_id in (7,9):
        preview = post(teacher, "/teacher/notes/import-previews", spreadsheet_url=URL, sheet_id=sheet_id).json
        catalogs.append(confirm(teacher, preview["preview_id"]).json)
    assert reads == [7,7,9,9]
    assert [c["question_count"] for c in catalogs] == [2,1]
    assert catalogs[0]["import_id"] != catalogs[1]["import_id"]
    with app.app_context():
        assert connection().execute("SELECT count(*) FROM notes_sources").fetchone()[0] == 2


def test_existing_versions_and_ready_previews_upgrade_without_data_loss(app, teacher, sheets):
    from guided_notes import create_app
    pid = named_preview(teacher)["preview_id"]
    catalog = confirm(teacher, pid).json
    pending = named_preview(teacher)["preview_id"]
    with app.app_context():
        db = connection()
        # Simulate a database from before naming tables existed.
        db.execute("DROP TABLE notes_catalog_names")
        db.execute("DROP TABLE notes_preview_names")
    upgraded = create_app({"TESTING":True,"SECRET_KEY":app.secret_key,"DATABASE":app.config["DATABASE"],"NOTES_GATEWAY":sheets})
    client = upgraded.test_client()
    assert post(client,"/teacher/session",username="teacher",password="test-password").status_code == 204
    assert client.get(f"/teacher/notes/catalogs/{catalog['import_id']}/versions/1", headers={"Accept":"application/json"}).json == catalog
    assert "合成學習單" in client.get(f"/teacher/notes/import-previews/{pending}").get_data(as_text=True)
    assert confirm(client,pending).status_code == 200


def test_restart_preserves_custom_names_and_new_version_cannot_target_another_sheet(app, teacher, sheets):
    from guided_notes import create_app
    named = named_preview(teacher,name_mode="custom",custom_title="重啟後的講義")
    catalog = confirm(teacher,named["preview_id"]).json
    restarted = create_app({"TESTING":True,"SECRET_KEY":app.secret_key,"DATABASE":app.config["DATABASE"],"NOTES_GATEWAY":sheets})
    client = restarted.test_client()
    assert post(client,"/teacher/session",username="teacher",password="test-password").status_code == 204
    assert "重啟後的講義" in client.get(f"/teacher/notes/catalogs/{catalog['import_id']}/versions/1").get_data(as_text=True)
    # The same label on a different spreadsheet must not override source identity.
    other = post(client,"/teacher/notes/import-previews",
                 spreadsheet_url=URL.replace("synthetic/", "different/"),sheet_id=7,
                 name_mode="custom",custom_title="重啟後的講義").json
    assert confirm(client,other["preview_id"],existing_import_id=catalog["import_id"]).status_code == 409


def test_html_naming_form_and_custom_choice_without_javascript(teacher,sheets):
    token = teacher.get("/csrf").json["csrf"]
    page = teacher.post("/teacher/notes/worksheets",data={"csrf_token":token,"spreadsheet_url":URL})
    html = page.get_data(as_text=True)
    assert 'value="source" checked' in html and 'value="custom"' in html
    assert "一次匯入一個分頁" in html
    response = teacher.post("/teacher/notes/import-previews",data={"csrf_token":token,
        "spreadsheet_url":URL,"sheet_id":"7","name_mode":"custom","custom_title":"無 JavaScript 也可輸入"})
    assert response.status_code == 303
    assert "無 JavaScript 也可輸入" in teacher.get(response.location).get_data(as_text=True)
