import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Event

from conftest import post
from guided_notes.activities import teacher_routes
from guided_notes.db import connection
from guided_notes.http import ApiError


def fixture_storage(app):
    with app.app_context():
        connection().execute("CREATE TABLE accepted (answer TEXT NOT NULL)")


def test_cutoff_both_orders(app, teacher, activity, joined):
    student = joined[0]
    url = f"/activities/{activity['activity_id']}"
    body = dict(question_id="q1", items=[{"item_id": "i1-1", "answer_text": "  answer\n"}])
    fixture_storage(app)
    assert post(student, url + "/submissions", **body).status_code == 409
    assert post(teacher, url + "/start").status_code == 200
    inside, release = Event(), Event()

    def accept(db, context, answers):
        db.execute("INSERT INTO accepted VALUES (?)", (answers["i1-1"],))
        inside.set()
        assert release.wait(2)

    app.config["ACCEPT_SUBMISSION"] = accept
    blank = dict(question_id="q1", items=[{"item_id": "i1-1", "answer_text": " \n\t"}])
    assert post(student, url + "/submissions", **blank).status_code == 400
    with ThreadPoolExecutor(2) as pool:
        submission = pool.submit(post, student, url + "/submissions", **body)
        assert inside.wait(2)
        closing = pool.submit(post, teacher, url + "/close")
        release.set()
        assert submission.result().status_code == 201
        assert closing.result().status_code == 200
    assert post(student, url + "/submissions", **body).status_code == 409
    assert post(app.test_client(), "/activity-memberships", code=activity["code"], group_name="late").status_code == 409
    with sqlite3.connect(app.config["DATABASE"]) as db:
        assert db.execute("SELECT answer FROM accepted").fetchall() == [("  answer\n",)]


def test_rejected_submission_rolls_back(app, teacher, activity, joined):
    url = f"/activities/{activity['activity_id']}"
    fixture_storage(app)
    post(teacher, url + "/start")

    def accept(db, context, answers):
        db.execute("INSERT INTO accepted VALUES ('partial')")
        raise ApiError(409, "REJECTED")

    app.config["ACCEPT_SUBMISSION"] = accept
    body = dict(question_id="q1", items=[{"item_id": "i1-1", "answer_text": "answer"}])
    assert post(joined[0], url + "/submissions", **body).status_code == 409
    with app.app_context():
        assert connection().execute("SELECT count(*) FROM accepted").fetchone()[0] == 0


def test_join_cannot_slip_past_closing_transaction(app, teacher, activity, monkeypatch):
    url = f"/activities/{activity['activity_id']}"
    assert post(teacher, url + "/start").status_code == 200
    original = teacher_routes.transition
    updated, release = Event(), Event()

    def hold_close(*args):
        result = original(*args)
        updated.set()
        assert release.wait(2)
        return result

    monkeypatch.setattr(teacher_routes, "transition", hold_close)
    outsider = app.test_client()
    with ThreadPoolExecutor(2) as pool:
        closing = pool.submit(post, teacher, url + "/close")
        assert updated.wait(2)
        joining = pool.submit(post, outsider, "/activity-memberships", code=activity["code"], group_name="late")
        release.set()
        assert closing.result().status_code == 200
        assert joining.result().status_code == 409
    with app.app_context():
        assert connection().execute("SELECT count(*) FROM memberships").fetchone()[0] == 0
