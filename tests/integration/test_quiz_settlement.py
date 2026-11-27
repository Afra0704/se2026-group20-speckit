import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest

from conftest import post
from guided_notes.db import connection
from quiz_support import published_quiz, submit_question


def test_legacy_preparing_activity_can_close_without_winners(app, teacher):
    activity, questions = published_quiz(app, teacher)
    url = f"/activities/{activity['activity_id']}"
    other = app.test_client()
    assert post(other, "/teacher/session", username="other", password="test-password").status_code == 204
    assert post(other, url + "/close").status_code == 403

    response = post(teacher, url + "/close")
    assert response.status_code == 200
    assert response.json["phase"] == "CLOSED"
    result = teacher.get(url + "/results").json
    assert result["status"] == "settled"
    assert [row["question_id"] for row in result["results"]] == [q["question_id"] for q in questions]
    assert all(row["no_winner"] and row["winner_items"] == [] for row in result["results"])
    for action in ("close", "start"):
        assert post(teacher, f"{url}/{action}").status_code == 409
    assert teacher.get(url + "/results").json == result


@pytest.mark.parametrize("replace", [False, True])
def test_effective_order_and_immutable_results(app, teacher, replace):
    activity, questions = published_quiz(app, teacher)
    aid = activity["activity_id"]
    url = f"/activities/{aid}"
    a, b = app.test_client(), app.test_client()
    for client, group in ((a, "甲組"), (b, "乙組")):
        assert post(client, "/activity-memberships", code=activity["code"], group_name=group).status_code == 201
    key = str(uuid4())
    post(teacher, url + "/start")
    assert submit_question(a, aid, questions[0], key=key).status_code == 201
    assert submit_question(b, aid, questions[0], answer="B").status_code == 201
    assert submit_question(a, aid, questions[0], key=None if replace else key).status_code == 201
    assert post(teacher, url + "/close").status_code == 200
    result = teacher.get(url + "/results").json
    assert result["status"] == "settled"
    assert result["results"][0]["winner_name"] == ("乙組" if replace else "甲組")
    assert [g["rank"] for g in result["results"][0]["groups"]] == [1, 2]
    assert any(row["no_winner"] for row in result["results"])
    assert submit_question(a, aid, questions[0], key=key).status_code == 201
    assert submit_question(a, aid, questions[0]).status_code == 409
    with app.app_context():
        version = connection().execute("SELECT result_version FROM quiz_settlements WHERE activity_id=?",
                                       (aid,)).fetchone()[0]
    assert teacher.get(url + "/results").json == result
    with app.app_context():
        assert connection().execute("SELECT result_version FROM quiz_settlements WHERE activity_id=?",
                                    (aid,)).fetchone()[0] == version


def test_close_commits_despite_publish_failure_and_restart_recovers(app, teacher, monkeypatch):
    from guided_notes import create_app
    from guided_notes.quiz import settlement

    activity, questions = published_quiz(app, teacher)
    aid = activity["activity_id"]
    student = app.test_client()
    assert post(student, "/activity-memberships", code=activity["code"], group_name="A").status_code == 201
    url = f"/activities/{aid}"
    post(teacher, url + "/start")
    assert submit_question(student, aid, questions[0]).status_code == 201
    publish = settlement.publish

    def interrupt(*args):
        publish(*args)
        raise RuntimeError("interrupted before commit")

    with monkeypatch.context() as patched:
        patched.setattr(settlement, "publish", interrupt)
        assert post(teacher, url + "/close").status_code == 200
        assert student.get(url + "/results").json == {"status": "pending"}
        with app.app_context():
            row = connection().execute("SELECT * FROM quiz_settlements WHERE activity_id=?", (aid,)).fetchone()
            assert row["result_version"] is None and row["snapshot"] is None
    restarted = create_app({"TESTING": True, "TEACHER_AUTH_MODE": "test_password",
                            "SECRET_KEY": "test-only", "DATABASE": app.config["DATABASE"]})
    with restarted.app_context():
        row = connection().execute("SELECT * FROM quiz_settlements WHERE activity_id=?", (aid,)).fetchone()
        assert row["result_version"] and row["snapshot"]


def test_parallel_groups_settle_once_when_the_classroom_closes(classroom_app, classroom_teacher, classroom_setup):
    _, room = classroom_setup
    activity, questions = published_quiz(classroom_app, classroom_teacher, classroom_setup)
    aid, rid = activity["activity_id"], room["classroom_id"]
    students = [classroom_app.test_client(), classroom_app.test_client()]
    for client, group in zip(students, ("1", "2")):
        assert post(client, "/classroom-memberships", code=room["code"], group_name=group).status_code == 201
    base = f"/teacher/classrooms/{rid}"
    assert post(classroom_teacher, f"{base}/activities/{aid}/start").status_code == 200
    together = Barrier(2, timeout=5)

    def send(client, answer):
        together.wait()
        return submit_question(client, aid, questions[0], answer=answer)

    with ThreadPoolExecutor(2) as pool:
        first, second = [pool.submit(send, client, answer) for client, answer in zip(students, ("A", "B"))]
        assert first.result().status_code == second.result().status_code == 201
    assert post(classroom_teacher, f"{base}/close", confirm=True).status_code == 200
    with classroom_app.app_context():
        received = connection().execute(
            "SELECT answers FROM quiz_submissions WHERE activity_id=? ORDER BY accept_seq", (aid,),
        ).fetchall()
        winner = next(iter(json.loads(received[0]["answers"]).values()))
    result = classroom_teacher.get(f"/activities/{aid}/results", headers={"X-Activity-Role": "teacher"}).json
    assert result["results"][0]["winner_name"] == ("第 1 組" if winner == "A" else "第 2 組")
    assert [g["rank"] for g in result["results"][0]["groups"]] == [1, 2]
    assert submit_question(students[0], aid, questions[0]).status_code == 409
