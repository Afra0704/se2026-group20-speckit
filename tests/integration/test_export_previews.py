"""Preview real HTTP/provider boundaries without writing any external Sheets."""
import copy

import pytest

from conftest import post
from guided_notes.db import connection
from test_import_routes import confirm, preview, sheets


def ended_activity(app, teacher, *, closed=True):
    catalog = confirm(teacher, preview(teacher)).json
    activity = post(teacher, "/activities", import_id=catalog["import_id"], import_version=1).json
    snapshot = {"contract_version": 1, "activity_id": activity["activity_id"],
                "import_id": catalog["import_id"], "import_version": 1,
                "result_version": "settled-1", "ended": True, "units": []}
    for question in catalog["questions"]:
        snapshot["units"].append({"question_id": question["question_id"], "winner_group_id": "group-A",
            "no_winner": False, "answers": [dict(item_id=item["item_id"], blank_id=item["blank_id"],
                answer_text="  =001\n中文  ") for item in question["items"]]})
    app.config["GET_SETTLED_RESULTS"] = lambda db, aid: {"snapshot": copy.deepcopy(snapshot), "results": []}
    if closed:
        with app.app_context():
            connection().execute("UPDATE activities SET phase='CLOSED' WHERE id=?", (activity["activity_id"],))
    return activity["activity_id"], catalog, snapshot


def create(teacher, activity_id, **extra):
    return post(teacher, "/teacher/notes/export-previews", activity_id=activity_id, **extra)


def test_preview_persists_literal_answers_and_get_never_reads_source(app, teacher, sheets):
    aid, catalog, snapshot = ended_activity(app, teacher)
    response = create(teacher, aid)
    assert response.status_code == 201, response.get_data(as_text=True)
    data = response.json
    assert data["activity_id"] == aid
    assert data["import_id"] == catalog["import_id"]
    assert data["result_version"] == "settled-1"
    assert len(data["items"]) == 3
    assert {i["action"] for i in data["items"]} == {"write"}
    assert all(i["proposed_text"] == "  =001\n中文  " for i in data["items"])
    assert all(i["winner_group_id"] == "group-A" for i in data["items"])
    assert data["counts"]["write"] == 3
    assert "snapshot" not in data and "recognized" not in data
    reads = len(sheets.calls)
    fetched = teacher.get(data["preview_url"], headers={"Accept": "application/json"})
    assert fetched.json == data
    html = teacher.get(data["preview_url"]).get_data(as_text=True)
    assert "尚未寫入 Google Sheets" in html and "G5:H5" in html
    assert len(sheets.calls) == reads
    # A preview alone is insufficient: confirmation also needs an idempotency key.
    assert post(teacher, data["preview_url"] + "/confirm", confirm=True).status_code == 400


def test_unended_and_unsettled_fail_before_google(app, teacher, sheets):
    aid, _, _ = ended_activity(app, teacher, closed=False)
    reads = len(sheets.calls)
    assert create(teacher, aid).json["error"]["code"] == "ACTIVITY_NOT_ENDED"
    with app.app_context():
        connection().execute("UPDATE activities SET phase='CLOSED' WHERE id=?", (aid,))
    app.config["GET_SETTLED_RESULTS"] = None
    response = create(teacher, aid)
    assert response.status_code == 409
    assert response.json["error"]["code"] == "RESULT_NOT_READY"
    assert len(sheets.calls) == reads


@pytest.mark.parametrize("mutation", ["missing", "mixed_winner", "version", "activity", "secret"])
def test_invalid_provider_result_never_reads_google(app, teacher, sheets, mutation):
    aid, _, snapshot = ended_activity(app, teacher)
    if mutation == "missing":
        snapshot["units"][0]["answers"].pop()
    elif mutation == "mixed_winner":
        snapshot["units"][0]["answers"][0]["winner_group_id"] = "group-B"
    elif mutation == "version":
        snapshot["import_version"] = 2
    elif mutation == "activity":
        snapshot["activity_id"] = "different"
    else:
        snapshot["token"] = "must-not-leak"
    reads = len(sheets.calls)
    response = create(teacher, aid)
    assert response.status_code == 422
    assert response.json["error"]["code"] == "RESULT_INVALID"
    assert "must-not-leak" not in response.get_data(as_text=True)
    assert len(sheets.calls) == reads


def test_all_four_actions_preserve_typed_values_and_escape_html(app, teacher, sheets):
    aid, _, snapshot = ended_activity(app, teacher)
    # Main question 2 has no winner, so its source must be retained.
    snapshot["units"][1].update(no_winner=True, winner_group_id=None, answers=[])
    snapshot["units"][0]["answers"][0]["answer_text"] = "<script>literal</script>"
    values = sheets.sheet["data"][0]["rowData"]
    values[4]["values"].append({"userEnteredValue": {"formulaValue": "=1+1"}})
    values[5]["values"].append({"userEnteredValue": {"stringValue": "  =001\n中文  "}})
    data = create(teacher, aid).json
    assert [i["action"] for i in data["items"]] == [
        "requires_overwrite_confirmation", "already_matches", "skip"]
    assert data["items"][0]["original_user_value"] == {"formulaValue": "=1+1"}
    assert data["items"][2]["proposed_text"] is None
    html = teacher.get(data["preview_url"]).get_data(as_text=True)
    assert "&lt;script&gt;literal&lt;/script&gt;" in html
    assert "<script>literal</script>" not in html
    assert "公式" in html and "無勝組，略過" in html


def test_source_movement_rebinds_but_semantic_change_rejects(app, teacher, sheets):
    aid, _, _ = ended_activity(app, teacher)
    sheets.sheet = copy.deepcopy(sheets.layouts["moved"])
    moved = create(teacher, aid)
    assert moved.status_code == 201
    assert [(i["answer_range"]["start_row"], i["answer_range"]["start_column"])
            for i in moved.json["items"]] == [(7, 8), (8, 8), (10, 7)]
    sheets.sheet = copy.deepcopy(sheets.layouts["single"])
    bad = create(teacher, aid)
    assert bad.status_code == 409
    assert bad.json["error"]["code"] == "SOURCE_STRUCTURE_CHANGED"


def test_rejects_client_snapshot_targets_and_invalid_identifiers(app, teacher, sheets):
    aid, _, _ = ended_activity(app, teacher)
    reads = len(sheets.calls)
    for extra in ({"snapshot": {}}, {"winner_group_id": "X"}, {"sheet_id": 7}, {"confirm": True}):
        assert create(teacher, aid, **extra).status_code == 400
    for invalid in (None, "", " ", 1, True, [], "a" * 257):
        assert create(teacher, invalid).status_code == 400
    assert len(sheets.calls) == reads


def test_auth_ownership_csrf_and_unknown_activity_do_not_read_google(app, teacher, sheets):
    aid, _, _ = ended_activity(app, teacher)
    data = create(teacher, aid).json
    reads = len(sheets.calls)
    other = app.test_client()
    anon = app.test_client()
    assert create(anon, aid).status_code == 401
    assert post(other, "/teacher/session", username="other", password="test-password").status_code == 204
    assert create(other, aid).status_code == 404
    assert other.get(data["preview_url"]).status_code == 404
    assert teacher.post("/teacher/notes/export-previews", json={"activity_id": aid}).status_code == 403
    assert create(teacher, "unknown").status_code == 404
    assert len(sheets.calls) == reads


def test_expired_teacher_during_source_read_cannot_save(app, teacher, sheets, monkeypatch):
    aid, _, _ = ended_activity(app, teacher)
    original = sheets.read_sheet
    def expire(*args):
        value = original(*args)
        connection().execute("UPDATE grants SET expires=0 WHERE teacher_id=1")
        return value
    monkeypatch.setattr(sheets, "read_sheet", expire)
    assert create(teacher, aid).status_code == 401
    with app.app_context():
        assert connection().execute("SELECT count(*) FROM notes_export_previews").fetchone()[0] == 0


@pytest.mark.parametrize("change_version", [False, True])
def test_result_change_during_source_read_cannot_save(app, teacher, sheets, monkeypatch, change_version):
    aid, _, snapshot = ended_activity(app, teacher)
    original = sheets.read_sheet
    def change(*args):
        value = original(*args)
        if change_version:
            snapshot["result_version"] = "settled-2"
        else:
            snapshot["units"][0]["answers"][0]["answer_text"] = "changed-without-version-bump"
        return value
    monkeypatch.setattr(sheets, "read_sheet", change)
    bad = create(teacher, aid)
    assert bad.status_code == 409
    assert bad.json["error"]["code"] == "RESULT_VERSION_CHANGED"
    with app.app_context():
        assert connection().execute("SELECT count(*) FROM notes_export_previews").fetchone()[0] == 0


def test_preview_survives_restart_and_html_form_redirects(app, teacher, sheets):
    from guided_notes import create_app
    aid, _, _ = ended_activity(app, teacher)
    token = teacher.get("/csrf").json["csrf"]
    form = teacher.get("/teacher/notes/export-previews").get_data(as_text=True)
    assert 'name="activity_id"' in form
    response = teacher.post("/teacher/notes/export-previews", data={"csrf_token": token, "activity_id": aid})
    assert response.status_code == 303
    reads = len(sheets.calls)
    restarted = create_app({"TESTING": True, "SECRET_KEY": app.secret_key, "DATABASE": app.config["DATABASE"]})
    client = restarted.test_client()
    assert post(client, "/teacher/session", username="teacher", password="test-password").status_code == 204
    data = client.get(response.location, headers={"Accept": "application/json"})
    assert data.status_code == 200
    assert data.json["items"][0]["proposed_text"] == "  =001\n中文  "
    assert len(sheets.calls) == reads


def test_student_cannot_access_teacher_preview(app, teacher, sheets):
    aid, _, _ = ended_activity(app, teacher, closed=False)
    student = app.test_client()
    with app.app_context():
        code = connection().execute("SELECT code FROM activities WHERE id=?", (aid,)).fetchone()[0]
    assert post(student, "/activity-memberships", code=code, group_name="甲組").status_code == 201
    with app.app_context():
        connection().execute("UPDATE activities SET phase='CLOSED' WHERE id=?", (aid,))
    data = create(teacher, aid).json
    reads = len(sheets.calls)
    assert create(student, aid).status_code == 403
    assert student.get(data["preview_url"]).status_code == 403
    assert len(sheets.calls) == reads


def test_google_read_failure_is_safe_and_does_not_save(app, teacher, sheets):
    from guided_notes.notes.sheets_gateway import GatewayError
    aid, _, _ = ended_activity(app, teacher)
    sheets.error = GatewayError("SOURCE_READ_FORBIDDEN", http_status=403)
    response = create(teacher, aid)
    assert response.status_code == 403
    assert response.json["error"]["code"] == "SOURCE_READ_FORBIDDEN"
    with app.app_context():
        assert connection().execute("SELECT count(*) FROM notes_export_previews").fetchone()[0] == 0


def test_single_question_and_all_no_winner(app, teacher, sheets):
    sheets.sheet = copy.deepcopy(sheets.layouts["single"])
    aid, _, snapshot = ended_activity(app, teacher)
    snapshot["units"][0].update(winner_group_id=None, no_winner=True, answers=[])
    data = create(teacher, aid).json
    assert data["question_count"] == 1 and data["answer_item_count"] == 1
    assert data["items"][0]["action"] == "skip"
    assert data["counts"]["skip"] == 1
