from catalog_support import course_import_id
from concurrent.futures import ThreadPoolExecutor
from threading import Event

from conftest import post


def test_close_waits_for_committed_submission(classroom_app, classroom_teacher, classroom_setup):
    course, room = classroom_setup
    rid = room["classroom_id"]
    path = f"/teacher/classrooms/{rid}"
    activity_id = post(classroom_teacher, path + "/activities", import_id=course_import_id(course["course_id"]),
                       import_version=1).json["activity_id"]
    student = classroom_app.test_client()
    assert post(student, "/classroom-memberships", code=room["code"], group_name="A").status_code == 201
    assert post(classroom_teacher, f"{path}/activities/{activity_id}/start").status_code == 200
    assert post(classroom_teacher, path + "/close", confirm=False).status_code == 400
    assert student.get(f"/classrooms/{rid}/state").json["activity"]["phase"] == "LIVE"
    body = {"question_id": "fixture-q1", "items": [{"item_id": "fixture-item-1-1", "answer_text": " A "}]}
    entered, release = Event(), Event()

    def accept(db, context, answers):
        entered.set()
        assert context["activity_id"] == activity_id
        assert answers["fixture-item-1-1"] == " A "
        assert release.wait(2)

    classroom_app.config["ACCEPT_SUBMISSION"] = accept
    with ThreadPoolExecutor(2) as pool:
        pending = pool.submit(post, student, f"/activities/{activity_id}/submissions", **body)
        assert entered.wait(2)
        closing = pool.submit(post, classroom_teacher, path + "/close", confirm=True)
        release.set()
        assert pending.result().status_code == 201
        assert closing.result().status_code == 200
    state = student.get(f"/classrooms/{rid}/state").json
    assert state["classroom_state"] == "CLOSED"
    assert set(state) == {"classroom_id", "classroom_state", "state_version"}
    assert post(student, f"/activities/{activity_id}/submissions", **body).status_code == 409
    assert post(student, "/classroom-memberships", code=room["code"], group_name="B").status_code == 403
    assert post(classroom_teacher, f"{path}/activities/{activity_id}/start").status_code == 409
    assert classroom_teacher.get(path + "/activities").json["activities"][0]["closed_at"]
