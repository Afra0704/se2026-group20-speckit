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


def test_blank_errors_identify_only_authorized_expected_items(teacher, activity, joined):
    aid = activity["activity_id"]
    assert post(teacher, f"/activities/{aid}/start").status_code == 200
    for options in ({"answer": "\u0085\u001c"}, {"items": []}):
        response = submit(joined[0], aid, **options)
        assert response.status_code == 400
        assert response.json["error"] == "INVALID_ITEMS"
        assert response.json["invalid_item_ids"] == ["i1-1"]
    foreign = submit(joined[0], aid, items=[{"item_id": "other", "answer_text": " "}])
    assert foreign.json == {"error": "INVALID_ITEMS"}
    assert submit(joined[0], aid, answer="\ufeff").status_code == 201
