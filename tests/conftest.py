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
