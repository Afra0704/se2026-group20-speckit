from catalog_support import course_import_id
from concurrent.futures import ThreadPoolExecutor

from conftest import post


def test_concurrent_start_and_stale_submission(classroom_app, classroom_teacher, classroom_setup):
    course, room = classroom_setup
    path = f"/teacher/classrooms/{room['classroom_id']}/activities"
    first = post(classroom_teacher, path, import_id=course_import_id(course["course_id"]), import_version=1).json["activity_id"]
    second_teacher = classroom_app.test_client()
    post(second_teacher, "/teacher/session", username="teacher", password="test-password")
    with ThreadPoolExecutor(2) as pool:
        responses = [pool.submit(post, client, f"{path}/{id}/start")
                     for client, id in zip((classroom_teacher, second_teacher), (first, first))]
        statuses = [response.result().status_code for response in responses]
    assert sorted(statuses) == [200, 409]
    winner = first
    student = classroom_app.test_client()
    assert post(student, "/classroom-memberships", code=room["code"], group_name="A").status_code == 201
    accepted = []
    classroom_app.config["ACCEPT_SUBMISSION"] = lambda db, context, answers: accepted.append(context["activity_id"])
    body = {"question_id": "fixture-q1", "items": [{"item_id": "fixture-item-1-1", "answer_text": "答"}]}
    assert post(student, f"/activities/{winner}/submissions", **body).status_code == 201
    assert post(classroom_teacher, f"{path}/{winner}/finish").status_code == 200
    waiting = post(classroom_teacher, path, import_id=course_import_id(course["course_id"]), import_version=2).json["activity_id"]
    assert post(classroom_teacher, f"{path}/{waiting}/start").status_code == 200
    assert post(student, f"/activities/{winner}/submissions", **body).status_code == 409
    assert post(student, f"/activities/{waiting}/submissions", **body).status_code == 201
    assert accepted == [winner, waiting]
