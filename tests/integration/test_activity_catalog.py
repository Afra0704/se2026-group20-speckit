from conftest import post


def test_catalog_version_is_pinned(teacher, activity):
    original = f"/activities/{activity['activity_id']}/state"
    assert post(teacher, "/activities", import_id="missing", import_version=1).status_code == 400
    next_activity = post(teacher, "/activities", import_id="demo", import_version=2).json
    questions = teacher.get(original).json["questions"]
    assert [q["display_number"] for q in questions] == ["1.1", "1.2", "1.3"]
    assert len(questions[1]["items"]) == 2
    assert teacher.get(f"/activities/{next_activity['activity_id']}/state").json["questions"][0]["display_number"] == "2.1"
