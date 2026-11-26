from catalog_support import course_import_id
from conftest import post
from guided_notes.auth import require_teacher
from guided_notes.quiz.results_gateway import get_ended_snapshot
from guided_notes.activities.teacher import get_activity_reference


def test_closed_room_only_exposes_its_settled_results(classroom_app, classroom_teacher, classroom_setup):
    course, room = classroom_setup
    cid, rid = course["course_id"], room["classroom_id"]
    path = f"/teacher/classrooms/{rid}"
    student = classroom_app.test_client()
    gid = post(student, "/classroom-memberships", code=room["code"], group_name="A").json["group_id"]
    ids = []
    for _ in range(3):
        activity = post(classroom_teacher, path + "/activities", import_id=course_import_id(cid), import_version=1).json
        ids.append(activity["activity_id"])
        assert post(classroom_teacher, f"{path}/activities/{ids[-1]}/start").status_code == 200
        assert post(classroom_teacher, f"{path}/activities/{ids[-1]}/finish").status_code == 200
    other = post(classroom_teacher, f"/teacher/courses/{cid}/classrooms", title="其他班").json["classroom_id"]
    foreign_id = post(classroom_teacher, f"/teacher/classrooms/{other}/activities",
                      import_id=course_import_id(cid), import_version=1).json["activity_id"]
    assert post(classroom_teacher, path + "/close", confirm=True).status_code == 200
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
    with classroom_teacher:
        classroom_teacher.get(path + "/activities")
        context = require_teacher()
        assert get_ended_snapshot(context, ids[0])["activity_id"] == ids[0]
        assert get_activity_reference(context, ids[0]) == {
            "activity_id": ids[0], "import_id": course_import_id(cid), "import_version": 1, "ended": True,
        }
