import pytest
from werkzeug.security import generate_password_hash

from guided_notes import create_app
from guided_notes.db import connection
from catalog_support import IMPORT_ID, course_import_id, catalog as test_catalog, display, seed_published


@pytest.fixture
def app(tmp_path):
    def catalog(teacher, import_id, import_version):
        if teacher.teacher_id != 1 or import_id != IMPORT_ID or import_version not in (1, 2):
            return None
        value = test_catalog(import_id, import_version, legacy=True)
        seed_published(teacher.teacher_id, value)
        return value

    def display_provider(teacher, import_id, version):
        if import_id == IMPORT_ID:
            return display(catalog(teacher, import_id, version))
        from guided_notes.notes.display_service import get_display_content
        return get_display_content(teacher, import_id, version)

    app = create_app({"TESTING": True, "TEACHER_AUTH_MODE": "test_password", "SECRET_KEY": "test-only", "DATABASE": str(tmp_path / "test.sqlite3"),
                      "GET_CATALOG": catalog, "GET_DISPLAY_CONTENT": display_provider})
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
    response = post(teacher, "/activities", import_id=IMPORT_ID, import_version=1)
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
    def catalogs(teacher, course_id):
        return {"course_id": course_id, "lectures": [
            {"import_id": course_import_id(course_id), "versions": [{"import_version": 1, "title": "第一週講義"},
                                                  {"import_version": 2, "title": "第二週講義"}]},
            {"import_id": course_import_id(course_id, 'second'), "versions": [{"import_version": 1, "title": "另一份講義"}]},
        ]}

    def catalog(teacher, course_id, import_id, version):
        if import_id not in (course_import_id(course_id), course_import_id(course_id, 'second')):
            from guided_notes.http import ApiError
            raise ApiError(404, "CATALOG_NOT_FOUND")
        value = test_catalog(import_id, version)
        seed_published(teacher.teacher_id, value, course_id)
        return value

    def display_provider(teacher, course_id, import_id, version):
        if import_id in (course_import_id(course_id), course_import_id(course_id, 'second')):
            return display(catalog(teacher, course_id, import_id, version))
        from guided_notes.notes.course_catalogs import get_course_display_content
        return get_course_display_content(teacher, course_id, import_id, version)

    app = create_app({"TESTING": True, "TEACHER_AUTH_MODE": "test_password", "SECRET_KEY": "test-only", "CLASSROOM_MODE": True,
                      "DATABASE": str(tmp_path / "classroom.sqlite3"), "LIST_COURSE_CATALOGS": catalogs,
                      "GET_COURSE_CATALOG": catalog, "GET_COURSE_DISPLAY_CONTENT": display_provider})
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
