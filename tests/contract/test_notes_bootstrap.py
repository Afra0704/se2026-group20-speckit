from flask import Blueprint, render_template_string
from werkzeug.security import generate_password_hash

from conftest import post
from guided_notes import create_app
from guided_notes.auth import require_teacher
from guided_notes.db import connection, write_transaction


def test_notes_blueprint_shares_teacher_db_and_csrf(tmp_path):
    notes = Blueprint("notes_fixture", __name__)

    @notes.route("/notes-fixture", methods=("GET", "POST"))
    def route():
        teacher = require_teacher()
        assert connection().execute("PRAGMA foreign_keys").fetchone()[0] == 1
        return {"teacher_id": teacher.teacher_id}

    @notes.get("/notes-form")
    def form():
        return render_template_string("{{ csrf_token() }}")

    app = create_app({
        "TESTING": True, "SECRET_KEY": "test-only", "DATABASE": str(tmp_path / "notes.sqlite3"),
        "NOTES_BLUEPRINT": notes,
    })
    with app.app_context(), write_transaction() as db:
        db.execute("INSERT INTO teachers(username, password_hash) VALUES (?, ?)",
                   ("teacher", generate_password_hash("test-password")))
    client = app.test_client()
    assert client.get("/notes-fixture").status_code == 401
    assert post(client, "/teacher/session", username="teacher", password="test-password").status_code == 204
    token = client.get("/notes-form").get_data(as_text=True)
    assert client.post("/notes-fixture", json={}, headers={"X-CSRFToken": token}).json == {"teacher_id": 1}
    assert client.post("/notes-fixture", data={"csrf_token": token}).status_code == 200
    assert client.post("/notes-fixture", data={"csrf_token": "wrong"}).status_code == 403
