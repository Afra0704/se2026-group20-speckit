import pytest

from conftest import post
from guided_notes.auth import TeacherContext
from guided_notes.http import ApiError
from guided_notes.quiz.results_gateway import get_ended_snapshot


def test_results_are_scoped_and_not_published_early(app, teacher, activity, joined):
    app.config["GET_SETTLED_RESULTS"] = None
    a, b = joined
    url = f"/activities/{activity['activity_id']}"
    a_id, b_id = [client.get(url + "/state").json["group_id"] for client in joined]
    assert post(teacher, url + "/start").status_code == 200
    app.config["GET_PROGRESS"] = lambda db, activity_id: [
        {"group_name": "乙組", "question_id": "q1", "submitted": True, "answer": "private"}
    ]
    assert teacher.get(url + "/results").json["results"][0]["submitted"]
    assert a.get(url + "/results").json["results"] == []
    assert b.get(url + "/results").json["results"] == []
    assert b"private" not in a.get("/").data
    assert post(teacher, url + "/close").status_code == 200
    assert a.get(url + "/results").json == {"status": "pending"}
    app.config["GET_SETTLED_RESULTS"] = lambda db, activity_id: {"results": [{
        "question_id": "q1", "winner_name": "甲組", "winner_answer": "winning",
        "groups": [
            {"group_id": a_id, "group_name": "甲組", "answer": "winning", "rank": 1},
            {"group_id": b_id, "group_name": "乙組", "answer": "private", "rank": 2},
        ],
    }]}
    assert "private" not in a.get(url + "/results").get_data(as_text=True)
    assert b.get(url + "/results").json["results"][0]["own"] == {"answer": "private", "rank": 2}
    assert len(teacher.get(url + "/results").json["results"][0]["groups"]) == 2


def test_ended_snapshot_requires_settlement_and_management(app, teacher, activity):
    app.config["GET_SETTLED_RESULTS"] = None
    activity_id = activity["activity_id"]
    url = f"/activities/{activity_id}"
    with teacher:
        teacher.get(url + "/state")
        with pytest.raises(ApiError) as not_ended:
            get_ended_snapshot(TeacherContext(1), activity_id)
        assert (not_ended.value.status, not_ended.value.code) == (409, "ACTIVITY_NOT_ENDED")
    post(teacher, url + "/start")
    post(teacher, url + "/close")
    with teacher:
        teacher.get(url + "/state")
        with pytest.raises(ApiError) as not_ready:
            get_ended_snapshot(TeacherContext(1), activity_id)
        assert (not_ready.value.status, not_ready.value.code) == (409, "RESULT_NOT_READY")
    app.config["GET_SETTLED_RESULTS"] = lambda db, key: {
        "snapshot": {"activity_id": key, "result_version": 1, "ended": True}
    }
    with teacher:
        teacher.get(url + "/state")
        assert get_ended_snapshot(TeacherContext(1), activity_id)["result_version"] == 1
        with pytest.raises(ApiError) as denied:
            get_ended_snapshot(TeacherContext(2), activity_id)
        assert denied.value.status == 403
