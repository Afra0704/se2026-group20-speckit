from catalog_support import course_import_id
from classroom_tab_support import activate_tab, browser_tabs, join_tab
from conftest import post
from guided_notes.auth import require_teacher
from guided_notes.quiz.results_gateway import get_ended_snapshot
from guided_notes.activities.teacher import get_activity_reference
from quiz_support import published_quiz, submit_question


def test_tab_result_authorization_is_bound_to_browser_room_and_closure(
        classroom_app, classroom_teacher, classroom_setup):
    course, room = classroom_setup
    rid = room['classroom_id']
    second = post(classroom_teacher, f"/teacher/courses/{course['course_id']}/classrooms",
                  title='其他課堂').json
    student, _ = browser_tabs(classroom_app)
    headers = activate_tab(student, join_tab(student, room, '1'))
    aid, _ = published_quiz(classroom_app, classroom_teacher, classroom_setup)
    other, _ = published_quiz(classroom_app, classroom_teacher, (course, second))
    result = f"/activities/{aid['activity_id']}/results"
    other_result = f"/activities/{other['activity_id']}/results"

    assert student.get(result, headers=headers).status_code == 200
    assert student.get(result).status_code == 401
    legacy = classroom_app.test_client()
    assert post(legacy, '/classroom-memberships', code=room['code'], group_name='2').status_code == 201
    with legacy.session_transaction() as session:
        legacy_grant = session['classroom_grant']
    with student.session_transaction() as session:
        session['classroom_grant'] = legacy_grant
    for no_token in ({}, {'X-Classroom-Protocol': '1'}):
        missing = student.get(result, headers=no_token)
        assert missing.status_code == 401 and missing.json['error'] == 'CLASSROOM_TAB_REQUIRED'
    assert post(student, '/classroom-memberships', code=room['code'], group_name='2').status_code == 401
    assert student.get(result, headers={'X-Classroom-Tab': 'unknown-test-token'}).status_code == 401
    assert student.get(other_result, headers=headers).status_code == 403
    other_browser, _ = browser_tabs(classroom_app)
    assert other_browser.get(result, headers=headers).status_code == 403

    assert post(classroom_teacher, f'/teacher/classrooms/{rid}/close', confirm=True).status_code == 200
    closed = student.get(f'/classrooms/{rid}/state', headers=headers)
    assert closed.json['classroom_state'] == 'CLOSED'
    assert closed.json.get('activity') is None
    assert student.get(result, headers=headers).status_code == 409
    assert student.get(f'/classrooms/{rid}/results', headers=headers).status_code == 409
    teacher_result = classroom_teacher.get(result, headers={'X-Activity-Role': 'teacher'})
    assert teacher_result.status_code == 200


def test_late_member_can_view_same_room_results_until_room_closes(classroom_app, classroom_teacher, classroom_setup):
    _, room = classroom_setup
    rid = room["classroom_id"]
    paths = f"/teacher/classrooms/{rid}"
    a, b, late, outsider = [classroom_app.test_client() for _ in range(4)]
    for client, group in ((a, "1"), (b, "2")):
        assert post(client, "/classroom-memberships", code=room["code"], group_name=group).status_code == 201
    activity, questions = published_quiz(classroom_app, classroom_teacher, classroom_setup)
    aid = activity["activity_id"]
    assert post(classroom_teacher, f"{paths}/activities/{aid}/start").status_code == 200
    progress = classroom_teacher.get(f"/activities/{aid}/results", headers={"X-Activity-Role": "teacher"})
    assert {row["group_name"] for row in progress.json["results"]} == {"第 1 組", "第 2 組"}
    for client, answer in ((a, "first"), (b, "private second")):
        assert submit_question(client, aid, questions[0], answer=answer).status_code == 201
    assert post(classroom_teacher, f"{paths}/activities/{aid}/finish").status_code == 200
    assert post(late, "/classroom-memberships", code=room["code"], group_name="1").status_code == 201
    result_url, history = f"/activities/{aid}/results", f"/classrooms/{rid}/results"
    assert [row["activity_id"] for row in late.get(history).json["activities"]] == [aid]
    response = late.get(result_url)
    row = response.json["results"][0]
    assert row["own"]["rank"] == 1 and row["winner_name"] == "第 1 組"
    assert "groups" not in row and b"private second" not in response.data
    teacher_row = classroom_teacher.get(result_url, headers={"X-Activity-Role": "teacher"}).json["results"][0]
    assert [entry["group_name"] for entry in teacher_row["groups"]] == ["第 1 組", "第 2 組"]
    assert post(classroom_teacher, paths + "/close", confirm=True).status_code == 200
    assert post(outsider, "/classroom-memberships", code=room["code"], group_name="1").status_code == 403
    assert outsider.get(result_url).status_code == outsider.get(history).status_code == 401
    late.delete_cookie("session")
    assert post(late, f"/classrooms/{rid}/result-access").status_code == 409
    assert late.get(result_url).status_code == 401


def test_open_room_results_remain_private_and_closing_blocks_student(classroom_app, classroom_teacher, classroom_setup):
    course, room = classroom_setup
    cid, rid = course["course_id"], room["classroom_id"]
    path = f"/teacher/classrooms/{rid}"
    student = classroom_app.test_client()
    gid = post(student, "/classroom-memberships", code=room["code"], group_name="1").json["group_id"]
    ids = []
    for _ in range(3):
        activity = post(classroom_teacher, path + "/activities", import_id=course_import_id(cid), import_version=1).json
        ids.append(activity["activity_id"])
        assert post(classroom_teacher, f"{path}/activities/{ids[-1]}/start").status_code == 200
        assert post(classroom_teacher, f"{path}/activities/{ids[-1]}/finish").status_code == 200
    other = post(classroom_teacher, f"/teacher/courses/{cid}/classrooms", title="其他班").json["classroom_id"]
    foreign_id = post(classroom_teacher, f"/teacher/classrooms/{other}/activities",
                      import_id=course_import_id(cid), import_version=1).json["activity_id"]
    classroom_app.config["GET_SETTLED_RESULTS"] = lambda db, activity_id: (
        {"snapshot": {"activity_id": activity_id, "result_version": 1},
         "results": [{"question_id": "fixture-q1", "winner_name": "A", "winner_answer": "答案",
                      "groups": [{"group_id": gid, "group_name": "A", "answer": "答案", "rank": 1},
                                 {"group_id": -1, "group_name": "B", "answer": "隱藏", "rank": 2}]}]}
        if activity_id in ids[:2] else None
    )
    assert classroom_app.test_client().post(f"/classrooms/{rid}/result-access").status_code == 403
    student.delete_cookie("session")
    assert post(student, f"/classrooms/{rid}/result-access").status_code == 204
    assert [item["activity_id"] for item in student.get(f"/classrooms/{rid}/results").json["activities"]] == ids[:2]
    assert student.get(f"/activities/{foreign_id}/results").status_code == 403
    assert student.get(f"/activities/{ids[2]}/results").json == {"status": "pending"}
    result = student.get(f"/activities/{ids[0]}/results").json["results"][0]
    assert result["own"] == {"answer": "答案", "rank": 1}
    assert "groups" not in result
    assert post(classroom_teacher, path + "/close", confirm=True).status_code == 200
    for url in (f"/classrooms/{rid}/results", f"/activities/{ids[0]}/results"):
        assert student.get(url).status_code == 409
    assert post(student, f"/classrooms/{rid}/result-access").status_code == 409
    with classroom_teacher:
        classroom_teacher.get(path + "/activities")
        context = require_teacher()
        assert get_ended_snapshot(context, ids[0])["activity_id"] == ids[0]
        assert get_activity_reference(context, ids[0]) == {
            "activity_id": ids[0], "import_id": course_import_id(cid), "import_version": 1, "ended": True,
        }
