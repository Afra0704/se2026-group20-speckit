import pytest
from werkzeug.security import generate_password_hash

from guided_notes import create_app
from guided_notes.db import connection


@pytest.fixture
def app(tmp_path):
    def catalog(teacher, import_id, import_version):
        if teacher.teacher_id != 1 or import_id != "demo" or import_version not in (1, 2):
            return None
        return {"questions": [
            {"question_id": f"q{i}", "display_number": f"{import_version}.{i}", "kind": "question_set" if i == 2 else "single",
             "items": [{"item_id": f"i{i}-{j}", "blank_id": f"b{i}-{j}", "subitem_label": str(j)}
                       for j in range(1, 3 if i == 2 else 2)]}
            for i in range(1, 4)
        ]}

    app = create_app({"TESTING": True, "SECRET_KEY": "test-only", "DATABASE": str(tmp_path / "test.sqlite3"),
                      "GET_CATALOG": catalog})
    with app.app_context():
        connection().executemany(
            "INSERT INTO teachers(username, password_hash) VALUES (?, ?)",
            [(name, generate_password_hash("test-password")) for name in ("teacher", "other")],
        )
    return app


def post(client, path, **body):
    csrf = client.get("/csrf").json["csrf"]
    return client.post(path, json=body, headers={"X-CSRF-Token": csrf})


@pytest.fixture
def teacher(app):
    client = app.test_client()
    assert post(client, "/teacher/session", username="teacher", password="test-password").status_code == 204
    return client


@pytest.fixture
def activity(teacher):
    response = post(teacher, "/activities", import_id="demo", import_version=1)
    assert response.status_code == 201
    return response.json


@pytest.fixture
def joined(app, activity):
    clients = [app.test_client(), app.test_client()]
    for client, name in zip(clients, ("甲組", "乙組")):
        assert post(client, "/activity-memberships", code=activity["code"], group_name=name).status_code == 201
    return clients


@pytest.fixture
def classroom_app(tmp_path):
    from guided_notes.activities.demo_catalog import get_demo_catalog

    def catalogs(teacher, course_id):
        return {"course_id": course_id, "lectures": [
            {"import_id": course_id, "versions": [{"import_version": 1, "title": "第一週講義"},
                                                  {"import_version": 2, "title": "第二週講義"}]},
            {"import_id": f"{course_id}-second", "versions": [{"import_version": 1, "title": "另一份講義"}]},
        ]}

    def catalog(teacher, course_id, import_id, version):
        if import_id not in (course_id, f"{course_id}-second"):
            from guided_notes.http import ApiError
            raise ApiError(404, "CATALOG_NOT_FOUND")
        return get_demo_catalog(teacher, "demo", version) | {"import_id": import_id}

    app = create_app({"TESTING": True, "SECRET_KEY": "test-only", "CLASSROOM_MODE": True,
                      "DATABASE": str(tmp_path / "classroom.sqlite3"), "LIST_COURSE_CATALOGS": catalogs,
                      "GET_COURSE_CATALOG": catalog})
    with app.app_context():
        connection().executemany(
            "INSERT INTO teachers(username, password_hash) VALUES (?, ?)",
            [(name, generate_password_hash("test-password")) for name in ("teacher", "other")],
        )
    return app


@pytest.fixture
def classroom_teacher(classroom_app):
    client = classroom_app.test_client()
    assert post(client, "/teacher/session", username="teacher", password="test-password").status_code == 204
    return client


@pytest.fixture
def classroom_setup(classroom_teacher):
    course = post(classroom_teacher, "/teacher/courses", title="計算機概論").json
    path = f"/teacher/courses/{course['course_id']}/classrooms"
    room = post(classroom_teacher, path, title="上午班").json
    return course, room


@pytest.fixture
def writable(app):
    """Recorded Sheets failure substitute; settled results are injected per test."""
    from writeback_support import WritableSheets
    gateway = WritableSheets()
    app.config.update(NOTES_GATEWAY=gateway, GET_CATALOG=None)
    return gateway
