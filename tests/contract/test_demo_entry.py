from conftest import post
from guided_notes.db import connection


def test_demo_teacher_can_be_created_and_run_activity(app):
    app.config.update(GET_CATALOG=None, DEMO_CATALOG=True)
    runner = app.test_cli_runner()
    created = runner.invoke(args=["init-teacher", "demo-teacher", "--password", "test-password"])
    assert created.exit_code == 0, created.output
    teacher = app.test_client()
    assert teacher.get("/teacher").status_code == 200
    assert post(teacher, "/teacher/session", username="demo-teacher", password="test-password").status_code == 204
    activity = post(teacher, "/activities", import_id="demo", import_version=1).json
    student = app.test_client()
    assert student.get("/").status_code == 200
    assert post(student, "/activity-memberships", code=activity["code"], group_name="A").status_code == 201
    assert post(teacher, f"/activities/{activity['activity_id']}/start").status_code == 200
    url = f"/activities/{activity['activity_id']}/submissions"
    answer = {"question_id": "demo-q1", "items": [{"item_id": "demo-item-1-1", "answer_text": "測試答案"}]}
    assert post(student, url, **answer).status_code == 201
    assert post(teacher, f"/activities/{activity['activity_id']}/close").status_code == 200
    assert post(student, url, **answer).status_code == 409
    with app.app_context():
        assert connection().execute("SELECT count(*) FROM demo_submissions").fetchone()[0] == 1
