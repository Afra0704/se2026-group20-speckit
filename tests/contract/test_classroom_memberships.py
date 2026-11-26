from catalog_support import course_import_id
from conftest import post


def test_classroom_join_isolated_and_switch_preserves_group(classroom_app, classroom_teacher, classroom_setup):
    course, room = classroom_setup
    cid, rid = course["course_id"], room["classroom_id"]
    second = post(classroom_teacher, f"/teacher/courses/{cid}/classrooms", title="下午班").json
    a, b, other = [classroom_app.test_client() for _ in range(3)]
    assert post(a, "/classroom-memberships", code=room["code"], group_name=" ").status_code == 400
    a_join = post(a, "/classroom-memberships", code=room["code"], group_name=" A ").json
    assert post(b, "/classroom-memberships", code=room["code"], group_name="A").json["group_id"] == a_join["group_id"]
    assert post(b, "/classroom-memberships", code=room["code"], group_name="B").json["group_id"] != a_join["group_id"]
    assert post(other, "/classroom-memberships", code=second["code"], group_name="A").json["group_id"] != a_join["group_id"]
    state = f"/classrooms/{rid}/state"
    assert a.get(state).json["current_activity_id"] is None
    assert other.get(state).status_code == 403
    assert classroom_app.test_client().get(state).status_code == 401
    path = f"/teacher/classrooms/{rid}/activities"
    for index, version in enumerate((1, 2)):
        activity_id = post(classroom_teacher, path, import_id=course_import_id(cid), import_version=version).json["activity_id"]
        assert post(classroom_teacher, f"{path}/{activity_id}/start").status_code == 200
        for client in (a, b):
            current = client.get(state).json
            assert current["current_activity_id"] == activity_id
            assert current["state_version"] == 3 * index + 2
        assert a.get(state).json["activity"]["group_id"] == a_join["group_id"]
        assert post(classroom_teacher, f"{path}/{activity_id}/finish").status_code == 200
