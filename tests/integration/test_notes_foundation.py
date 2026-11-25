from conftest import post
from guided_notes import create_app
from guided_notes.db import connection


def test_notes_requires_teacher_and_csrf(app, teacher, joined):
    anonymous = app.test_client()
    assert anonymous.get("/teacher/notes").status_code == 401
    browser = anonymous.get("/teacher/notes", headers={"Accept": "text/html"})
    assert browser.status_code == 401
    assert "教師活動管理" in browser.get_data(as_text=True)
    assert joined[0].get("/teacher/notes").status_code == 403
    response = teacher.post("/teacher/notes/import-previews", json={})
    assert response.status_code == 403
    assert response.json["error"]["code"] == "CSRF_INVALID"
    assert "token" not in response.get_data(as_text=True).lower()


def test_schema_and_init_db_preserve_existing_data(app):
    with app.app_context():
        db = connection()
        before = db.execute("SELECT count(*) FROM teachers").fetchone()[0]
        assert db.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert 0 < db.execute("PRAGMA busy_timeout").fetchone()[0] <= 1000
    runner = app.test_cli_runner()
    assert runner.invoke(args=["init-db"]).exit_code == 0
    assert runner.invoke(args=["init-db"]).exit_code == 0
    with app.app_context():
        assert connection().execute("SELECT count(*) FROM teachers").fetchone()[0] == before
        assert connection().execute("SELECT count(*) FROM notes_catalogs").fetchone()[0] == 0


def test_google_profile_does_not_share_teacher_credentials(app, teacher):
    app.config.update(NOTES_GOOGLE_TEACHER_ID=2, NOTES_GATEWAY=None)
    response = post(teacher, "/teacher/notes/worksheets",
        spreadsheet_url="https://docs.google.com/spreadsheets/d/synthetic/edit#gid=7")
    assert response.status_code == 403
    assert response.json["error"]["code"] == "SOURCE_READ_FORBIDDEN"


def test_notes_does_not_store_google_settings_in_session_or_errors(app, teacher):
    app.config.update(NOTES_GOOGLE_TEACHER_ID=None, NOTES_GOOGLE_TOKEN="private-token-path")
    response = post(teacher, "/teacher/notes/worksheets",
        spreadsheet_url="https://docs.google.com/spreadsheets/d/synthetic/edit#gid=7")
    assert response.status_code == 503
    assert "private-token-path" not in response.get_data(as_text=True)
    with teacher.session_transaction() as state:
        assert set(state) == {"csrf", "teacher_grant"}
