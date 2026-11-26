from guided_notes.db import connection
from google_support import google_app, google_teacher, connect, post
from quiz_support import published_quiz


def test_quiz_schema_reinitializes_without_fabricating_history(app, activity):
    activity_id = activity["activity_id"]
    with app.app_context():
        db = connection()
        db.execute("UPDATE activities SET phase='CLOSED' WHERE id=?", (activity_id,))
        assert app.test_cli_runner().invoke(args=["init-db"]).exit_code == 0
        assert db.execute("SELECT phase FROM activities WHERE id=?", (activity_id,)).fetchone()[0] == "CLOSED"
        assert db.execute("SELECT count(*) FROM quiz_settlements").fetchone()[0] == 0
        assert not db.execute("PRAGMA foreign_key_check").fetchall()


def test_quiz_schema_reinit_preserves_google_and_classroom_records(google_app, google_teacher):
    connect(google_teacher)
    course = post(google_teacher, "/teacher/courses", title="Quiz").json
    room = post(google_teacher, f"/teacher/courses/{course['course_id']}/classrooms", title="Room").json
    published_quiz(google_app, google_teacher, (course, room))
    with google_app.app_context():
        db = connection()
        tables = ("auth_instance", "google_identities", "google_sheets_credentials", "courses", "classrooms",
                  "notes_catalogs", "classroom_activities")

        def rows():
            return [db.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall() for table in tables]

        original = rows()
        assert all(original)
        assert google_app.test_cli_runner().invoke(args=["init-db"]).exit_code == 0
        assert original == rows()
        assert not db.execute("PRAGMA foreign_key_check").fetchall()
