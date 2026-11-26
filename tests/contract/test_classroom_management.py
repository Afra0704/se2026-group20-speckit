from catalog_support import course_import_id
import re
import time

from conftest import post
from guided_notes.db import connection


def test_classroom_teacher_ownership_and_reuse(classroom_app, classroom_teacher, classroom_setup):
    course, room = classroom_setup
    cid, rid = course["course_id"], room["classroom_id"]
    afternoon = post(classroom_teacher, f"/teacher/courses/{cid}/classrooms", title="下午班").json
    assert room["code"] != afternoon["code"]
    assert re.fullmatch(r"[A-Z]{2}[0-9]{3}", room["code"])
    assert len(classroom_teacher.get(f"/teacher/courses/{cid}/catalogs").json["lectures"]) == 2
    path = f"/teacher/classrooms/{rid}/activities"
    first = post(classroom_teacher, path, import_id=course_import_id(cid), import_version=1).json
    assert post(classroom_teacher, path, import_id=course_import_id(cid), import_version=1).status_code == 409
    assert post(classroom_teacher, f"{path}/{first['activity_id']}/finish").status_code == 200
    second = post(classroom_teacher, path, import_id=course_import_id(cid), import_version=1).json
    assert first["activity_id"] != second["activity_id"]
    assert first["title"] == second["title"] == "第一週講義"
    assert post(classroom_teacher, f"/teacher/classrooms/{afternoon['classroom_id']}/activities",
                import_id=course_import_id(cid), import_version=1).status_code == 201
    other = classroom_app.test_client()
    post(other, "/teacher/session", username="other", password="test-password")
    assert other.get(f"/teacher/courses/{cid}/catalogs").status_code == 404
    assert other.get(path).status_code == 404
    assert other.get(f"/classrooms/{rid}/state", headers={"X-Activity-Role": "teacher"}).status_code == 404


def test_classroom_code_collision_retries(classroom_teacher, classroom_setup, monkeypatch):
    from guided_notes.activities import classroom_routes

    course, room = classroom_setup
    replacement = "AB123" if room["code"] != "AB123" else "CD456"
    codes = iter((room["code"], replacement))
    monkeypatch.setattr(classroom_routes, "make_room_code", lambda: next(codes))
    created = post(classroom_teacher, f"/teacher/courses/{course['course_id']}/classrooms", title="下午班")
    assert created.status_code == 201
    assert created.json["code"] == replacement


def test_teacher_can_initialize_four_character_password(classroom_app):
    runner = classroom_app.test_cli_runner()
    assert runner.invoke(args=["init-teacher", "four", "--password", "123"]).exit_code != 0
    created = runner.invoke(args=["init-teacher", "four", "--password", "1234"])
    assert created.exit_code == 0, created.output
    assert post(classroom_app.test_client(), "/teacher/session", username="four", password="1234").status_code == 204


def test_both_classroom_pages_load_shared_styles(classroom_app):
    client = classroom_app.test_client()
    for path in ("/teacher", "/"):
        response = client.get(path)
        assert response.status_code == 200
        assert b"/static/classroom.css" in response.data
    assert client.get("/static/classroom.css").status_code == 200


def test_teacher_native_forms_show_login_and_creation_feedback(classroom_app):
    client = classroom_app.test_client()
    page = client.get("/teacher")
    assert b'method="post" action="/teacher/session"' in page.data
    token = client.get("/csrf").json["csrf"]
    refused = client.post("/teacher/session", data={"csrf_token": token, "username": "teacher",
                                                   "password": "wrong"}, follow_redirects=True)
    assert "帳號或密碼不正確" in refused.get_data(as_text=True)
    logged_in = client.post("/teacher/session", data={"csrf_token": token, "username": "teacher",
                                                    "password": "test-password"}, follow_redirects=True)
    assert "已登入" in logged_in.get_data(as_text=True)
    created = client.post("/teacher/courses", data={"csrf_token": token, "title": "測試課程"},
                          follow_redirects=True)
    assert "課程已建立" in created.get_data(as_text=True)
    assert "測試課程" in created.get_data(as_text=True)


def test_login_limit_counts_failures_and_returns_wait_time(classroom_app):
    classroom_app.config["TESTING"] = False
    scope = "teacher-login-failures:127.0.0.1"
    with classroom_app.app_context():
        connection().execute("INSERT INTO attempts VALUES (?, ?, ?)", (scope, 19, int(time.time()) + 60))
    client = classroom_app.test_client()
    path = "/teacher/session"
    assert post(client, path, username="teacher", password="test-password").status_code == 204
    assert post(client, path, username="teacher", password="wrong").status_code == 401
    blocked = post(client, path, username="teacher", password="test-password")
    assert blocked.status_code == 429
    assert 0 < blocked.json["retry_after"] <= 60
    assert blocked.headers["Retry-After"] == str(blocked.json["retry_after"])
    token = client.get("/csrf").json["csrf"]
    page = client.post(path, data={"csrf_token": token, "username": "teacher", "password": "test-password"},
                       follow_redirects=True)
    assert "請等" in page.get_data(as_text=True)
    assert "秒再試" in page.get_data(as_text=True)
    with classroom_app.app_context():
        connection().execute("UPDATE attempts SET expires = 0 WHERE scope = ?", (scope,))
    assert post(client, path, username="teacher", password="test-password").status_code == 204
