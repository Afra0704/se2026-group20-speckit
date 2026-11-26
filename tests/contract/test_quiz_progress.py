from conftest import post
from quiz_support import submit


def test_live_progress_only_exposes_flags_to_teacher(teacher, activity, joined):
    aid = activity["activity_id"]
    assert post(teacher, f"/activities/{aid}/start").status_code == 200
    assert submit(joined[0], aid).status_code == 201
    url = f"/activities/{aid}/results"
    rows = teacher.get(url).json["results"]
    assert {"question_id": "q1", "group_name": "甲組", "submitted": True} in rows
    assert {"question_id": "q1", "group_name": "乙組", "submitted": False} in rows
    assert all(set(row) == {"question_id", "group_name", "submitted"} for row in rows)
    assert joined[1].get(url).json == {"status": "active", "results": []}
