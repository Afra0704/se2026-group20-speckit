from conftest import post
from quiz_support import submit


def test_formal_submit_validates_uuid_and_items(teacher, activity, joined):
    aid = activity["activity_id"]
    assert submit(joined[0], aid).status_code == 409
    assert post(teacher, f"/activities/{aid}/start").status_code == 200
    assert submit(teacher, aid).status_code == 403
    for options in ({"key": "invalid"}, {"answer": "   "}, {"items": []},
                    {"items": [{"item_id": "other", "answer_text": "wrong"}]}):
        assert submit(joined[0], aid, **options).status_code == 400
    assert submit(joined[0], aid).json == {"status": "accepted"}
