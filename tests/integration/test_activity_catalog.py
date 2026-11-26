import sys
from types import ModuleType

from conftest import post


def test_catalog_version_is_pinned(teacher, activity):
    original = f"/activities/{activity['activity_id']}/state"
    assert post(teacher, "/activities", import_id="missing", import_version=1).status_code == 400
    next_activity = post(teacher, "/activities", import_id="11111111-1111-4111-8111-111111111111", import_version=2).json
    questions = teacher.get(original).json["questions"]
    assert [q["display_number"] for q in questions] == ["1.1", "1.2", "1.3"]
    assert len(questions[1]["items"]) == 2
    assert teacher.get(f"/activities/{next_activity['activity_id']}/state").json["questions"][0]["display_number"] == "2.1"


def test_catalog_module_without_provider_is_unavailable(app, teacher, monkeypatch):
    app.config.update(GET_CATALOG=None, DEMO_CATALOG=False)
    name = "guided_notes.notes.import_service"
    monkeypatch.setitem(sys.modules, name, ModuleType(name))
    response = post(teacher, "/activities", import_id="11111111-1111-4111-8111-111111111111", import_version=1)
    assert response.status_code == 503
    assert response.json == {"error": "CATALOG_UNAVAILABLE"}
