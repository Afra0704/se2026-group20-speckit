import copy
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from conftest import post
from guided_notes.db import connection
from guided_notes.http import ApiError
from test_import_routes import URL, confirm, preview, sheets


@pytest.fixture
def courses(app):
    data = {cid: {"course_id": cid, "teacher_id": owner, "title": title} for cid, owner, title in (
        ("course-a", 1, "計算機概論"), ("course-b", 1, "第二門課"), ("private", 2, "他人課程"))}
    def owned(teacher, course_id):
        assert not connection().in_transaction
        row = data.get(course_id)
        if row is None or row["teacher_id"] != teacher.teacher_id:
            raise ApiError(404, "COURSE_NOT_FOUND")
        return copy.deepcopy(row)
    app.config["GET_OWNED_COURSE"] = owned
    return data


def scoped_preview(teacher, course_id="course-a", **extra):
    return post(teacher, "/teacher/notes/import-previews", spreadsheet_url=URL, sheet_id=7,
                course_id=course_id, **extra)


def listing(teacher, course_id="course-a"):
    return teacher.get(f"/teacher/notes/courses/{course_id}/catalogs")


def test_course_import_listing_versions_and_exact_catalog(app, teacher, sheets, courses):
    response = scoped_preview(teacher, name_mode="custom", custom_title="第一週")
    assert response.status_code == 201
    assert response.json["course_id"] == "course-a"
    catalog = confirm(teacher, response.json["preview_id"]).json
    row = listing(teacher).json
    assert row["course_id"] == "course-a" and row["title"] == "計算機概論"
    assert len(row["lectures"]) == 1
    lecture = row["lectures"][0]
    assert lecture["import_id"] == catalog["import_id"]
    assert lecture["versions"][0]["title"] == "第一週"
    assert lecture["versions"][0]["question_count"] == 2
    second = scoped_preview(teacher, name_mode="custom", custom_title="新版")
    newer = confirm(teacher, second.json["preview_id"], existing_import_id=catalog["import_id"])
    assert newer.json["import_version"] == 2
    versions = listing(teacher).json["lectures"][0]["versions"]
    assert [v["import_version"] for v in versions] == [2, 1]
    assert [v["title"] for v in versions] == ["新版", "第一週"]
    exact = f"/teacher/notes/courses/course-a/catalogs/{catalog['import_id']}/versions/1"
    assert teacher.get(exact).json == catalog
    assert "course_id" not in catalog and "source_bindings" not in json.dumps(row)
    assert listing(teacher, "course-b").json["lectures"] == []


def test_provider_absence_blocks_course_only_and_keeps_legacy_working(app, teacher, sheets):
    response = scoped_preview(teacher)
    assert response.status_code == 503
    assert response.json["error"]["code"] == "COURSE_UNAVAILABLE"
    assert sheets.calls == []
    assert listing(teacher).status_code == 503
    assert confirm(teacher, preview(teacher)).status_code == 200


@pytest.mark.parametrize("invalid", [None, "", "  ", 1, True, [], "a" * 129, "bad\nname"])
def test_explicit_invalid_course_never_reads_google(teacher, sheets, courses, invalid):
    assert scoped_preview(teacher, invalid).status_code == 400
    assert sheets.calls == []


def test_cross_teacher_and_unknown_course_rejected_before_google(teacher, sheets, courses):
    for cid in ("private", "unknown"):
        assert scoped_preview(teacher, cid).status_code == 404
        assert listing(teacher, cid).status_code == 404
    assert sheets.calls == []


def test_course_context_survives_source_change_and_confirm_cannot_replace(teacher, sheets, courses):
    response = scoped_preview(teacher)
    pid = response.json["preview_id"]
    tamper = confirm(teacher, pid, course_id="course-b")
    assert tamper.status_code == 400
    sheets.sheet = copy.deepcopy(sheets.layouts["moved"])
    changed = confirm(teacher, pid)
    assert changed.status_code == 409
    next_id = changed.json["error"]["context"]["new_preview_id"]
    html = teacher.get(f"/teacher/notes/import-previews/{next_id}").get_data(as_text=True)
    assert "計算機概論" in html
    assert confirm(teacher, next_id).status_code == 200
    assert len(listing(teacher).json["lectures"]) == 1
    assert listing(teacher, "course-b").json["lectures"] == []


def test_cross_course_catalog_and_update_are_rejected(app, teacher, sheets, courses):
    catalog = confirm(teacher, scoped_preview(teacher).json["preview_id"]).json
    wrong = f"/teacher/notes/courses/course-b/catalogs/{catalog['import_id']}/versions/1"
    assert teacher.get(wrong).status_code == 404
    reads = len(sheets.calls)
    b = scoped_preview(teacher, "course-b").json["preview_id"]
    assert confirm(teacher, b, existing_import_id=catalog["import_id"]).status_code == 409
    assert len(sheets.calls) == reads + 1  # preview read only, no confirm read
    unscoped = preview(teacher)
    assert confirm(teacher, unscoped, existing_import_id=catalog["import_id"]).status_code == 409


def test_explicit_legacy_assignment_is_idempotent_and_never_rewrites_catalog(app, teacher, sheets, courses):
    catalog = confirm(teacher, preview(teacher)).json
    old_activity = post(teacher, "/activities", import_id=catalog["import_id"], import_version=1).json
    old_state = teacher.get(f"/activities/{old_activity['activity_id']}/state").json
    assert listing(teacher).json["lectures"] == []
    path = "/teacher/notes/courses/course-a/lectures"
    first = post(teacher, path, import_id=catalog["import_id"])
    again = post(teacher, path, import_id=catalog["import_id"])
    assert first.status_code == again.status_code == 200
    assert first.json == again.json
    assert post(teacher, "/teacher/notes/courses/course-b/lectures", import_id=catalog["import_id"]).status_code == 409
    exact = f"/teacher/notes/catalogs/{catalog['import_id']}/versions/1"
    assert teacher.get(exact, headers={"Accept": "application/json"}).json == catalog
    assert teacher.get(f"/activities/{old_activity['activity_id']}/state").json == old_state
    with app.app_context():
        assert connection().execute("SELECT count(*) FROM notes_import_courses").fetchone()[0] == 1
    assert "data-activity-form" not in teacher.get(exact).get_data(as_text=True)


def test_confirm_rechecks_course_permission_before_google(app, teacher, sheets, courses):
    pid = scoped_preview(teacher).json["preview_id"]
    courses["course-a"]["teacher_id"] = 2
    reads = len(sheets.calls)
    assert confirm(teacher, pid).status_code == 404
    assert len(sheets.calls) == reads
    with app.app_context():
        assert connection().execute("SELECT count(*) FROM notes_catalogs").fetchone()[0] == 0


def test_course_permission_changed_during_source_read_does_not_save(app, teacher, sheets, courses, monkeypatch):
    original = sheets.read_sheet
    def revoke(*args):
        result = original(*args)
        courses["course-a"]["teacher_id"] = 2
        return result
    monkeypatch.setattr(sheets, "read_sheet", revoke)
    assert scoped_preview(teacher).status_code == 404
    with app.app_context():
        assert connection().execute("SELECT count(*) FROM notes_import_previews").fetchone()[0] == 0


def test_course_html_flow_escapes_names_and_preserves_hidden_context(teacher, sheets, courses):
    courses["course-a"]["title"] = "<script>課程</script>"
    page = teacher.get("/teacher/notes/courses/course-a").get_data(as_text=True)
    assert "&lt;script&gt;課程&lt;/script&gt;" in page and "<script>課程</script>" not in page
    token = teacher.get("/csrf").json["csrf"]
    listed = teacher.post("/teacher/notes/worksheets", data={"csrf_token": token,
        "course_id": "course-a", "spreadsheet_url": URL})
    assert 'name="course_id" value="course-a"' in listed.get_data(as_text=True)
    result = teacher.post("/teacher/notes/import-previews", data={"csrf_token": token,
        "course_id": "course-a", "spreadsheet_url": URL, "sheet_id": "7"})
    assert result.status_code == 303
    saved = teacher.post(result.location + "/confirm", data={"csrf_token": token, "confirm": "true"})
    assert saved.status_code == 303
    assert "返回課程講義" in teacher.get(saved.location).get_data(as_text=True)


def test_course_csrf_other_teacher_and_no_google_on_assignment(app, teacher, sheets, courses):
    catalog = confirm(teacher, preview(teacher)).json
    reads = len(sheets.calls)
    other = app.test_client()
    assert post(other, "/teacher/session", username="other", password="test-password").status_code == 204
    assert listing(other).status_code == 404
    assert post(other, "/teacher/notes/courses/private/lectures", import_id=catalog["import_id"]).status_code == 404
    assert teacher.post("/teacher/notes/courses/course-a/lectures", json={"import_id": catalog["import_id"]}).status_code == 403
    assert len(sheets.calls) == reads


def test_restart_keeps_assignment_and_old_unassigned_data(app, teacher, sheets, courses):
    from guided_notes import create_app
    first = confirm(teacher, scoped_preview(teacher).json["preview_id"]).json
    old = confirm(teacher, preview(teacher)).json
    config = {"TESTING": True, "SECRET_KEY": app.secret_key, "DATABASE": app.config["DATABASE"],
              "GET_OWNED_COURSE": app.config["GET_OWNED_COURSE"], "NOTES_GATEWAY": sheets}
    restarted = create_app(config)
    client = restarted.test_client()
    post(client, "/teacher/session", username="teacher", password="test-password")
    assert [x["import_id"] for x in listing(client).json["lectures"]] == [first["import_id"]]
    with restarted.app_context():
        assert connection().execute("SELECT count(*) FROM notes_imports").fetchone()[0] == 2
        assert connection().execute("SELECT count(*) FROM notes_import_courses").fetchone()[0] == 1
    assert client.get(f"/teacher/notes/catalogs/{old['import_id']}/versions/1",
                      headers={"Accept": "application/json"}).json == old


@pytest.mark.parametrize("bad", [False, {}, {"course_id": "course-a"},
    {"course_id": "course-a", "teacher_id": 1, "title": ""}])
def test_malformed_provider_fails_closed(app, teacher, sheets, bad):
    app.config["GET_OWNED_COURSE"] = lambda *args: bad
    assert scoped_preview(teacher).status_code == 503
    assert sheets.calls == []


def test_provider_wrong_owner_and_extra_fields_are_not_trusted(app, teacher, sheets, courses):
    app.config["GET_OWNED_COURSE"] = lambda *args: {"course_id": "course-a", "teacher_id": 2, "title": "他人"}
    assert scoped_preview(teacher).status_code == 404
    app.config["GET_OWNED_COURSE"] = lambda *args: {"course_id": "course-a", "teacher_id": 1,
        "title": "課程", "token": "must-not-leak"}
    assert "must-not-leak" not in listing(teacher).get_data(as_text=True)


def test_parallel_legacy_assignment_cannot_move_between_courses(app, teacher, sheets, courses):
    catalog = confirm(teacher, preview(teacher)).json
    clients = [app.test_client(), app.test_client()]
    with teacher.session_transaction() as state:
        saved = dict(state)
    for client in clients:
        with client.session_transaction() as state:
            state.update(saved)
    def assign(args):
        client, cid = args
        return post(client, f"/teacher/notes/courses/{cid}/lectures", import_id=catalog["import_id"])
    with ThreadPoolExecutor(2) as pool:
        responses = list(pool.map(assign, zip(clients, ("course-a", "course-b"))))
    assert sorted(r.status_code for r in responses) == [200, 409]
    with app.app_context():
        assert connection().execute("SELECT count(*) FROM notes_import_courses").fetchone()[0] == 1


def test_parallel_course_confirmation_publishes_one_assignment(app, teacher, sheets, courses):
    pid = scoped_preview(teacher).json["preview_id"]
    clients = [app.test_client(), app.test_client()]
    with teacher.session_transaction() as state:
        saved = dict(state)
    for client in clients:
        with client.session_transaction() as state:
            state.update(saved)
    sheets.barrier = Barrier(2)
    with ThreadPoolExecutor(2) as pool:
        responses = list(pool.map(lambda client: confirm(client, pid), clients))
    assert [r.status_code for r in responses] == [200, 200]
    assert responses[0].json == responses[1].json
    with app.app_context():
        assert connection().execute("SELECT count(*) FROM notes_import_courses").fetchone()[0] == 1
