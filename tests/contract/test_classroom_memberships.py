from catalog_support import course_import_id
from classroom_tab_support import activate_tab, browser_tabs, join_tab
from conftest import post
import pytest


@pytest.mark.parametrize('name', [None, 3, '', ' ', 'A'*81])
def test_join_rejects_invalid_raw_group_names(classroom_app, classroom_setup, name):
    _, room = classroom_setup
    client = classroom_app.test_client()
    response = post(client, '/classroom-memberships', code=room['code'], group_name=name)
    assert response.status_code == 400
    assert not response.headers.getlist('Set-Cookie')


def test_classroom_join_isolated_and_switch_preserves_group(classroom_app, classroom_teacher, classroom_setup):
    course, room = classroom_setup
    cid, rid = course["course_id"], room["classroom_id"]
    second = post(classroom_teacher, f"/teacher/courses/{cid}/classrooms", title="下午班").json
    a, b, other = [classroom_app.test_client() for _ in range(3)]
    assert post(a, "/classroom-memberships", code=room["code"], group_name=" ").status_code == 400
    a_join = post(a, "/classroom-memberships", code=room["code"], group_name=" 1 ").json
    assert post(b, "/classroom-memberships", code=room["code"], group_name="1").json["group_id"] == a_join["group_id"]
    assert post(b, "/classroom-memberships", code=room["code"], group_name="2").json["group_id"] != a_join["group_id"]
    assert post(other, "/classroom-memberships", code=second["code"], group_name="1").json["group_id"] != a_join["group_id"]
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


def test_numeric_join_rejects_invalid_group_without_replacing_grant(classroom_app, classroom_setup):
    _, room = classroom_setup
    student = classroom_app.test_client()
    endpoint = '/classroom-memberships'
    assert post(student, endpoint, code=room['code'], group_name=' 42 ').status_code == 201
    with student.session_transaction() as session:
        grant = session['classroom_grant']
    for value in ('0', '01', '１', '1000', '1.0', '1e2', '', '  ', 42):
        reply = post(student, endpoint, code=room['code'], group_name=value)
        assert reply.status_code == 400
        assert reply.json['error'] == 'INVALID_GROUP_NUMBER'
    with student.session_transaction() as session:
        assert session['classroom_grant'] == grant
    state = student.get(f"/classrooms/{room['classroom_id']}/state")
    assert state.json['group_name'] == '第 42 組'


def test_tabs_keep_separate_classrooms_in_one_browser(classroom_app, classroom_teacher, classroom_setup):
    course, room = classroom_setup
    second_room = post(classroom_teacher, f"/teacher/courses/{course['course_id']}/classrooms",
                       title='下午班').json
    browser, _ = browser_tabs(classroom_app)
    a = activate_tab(browser, join_tab(browser, room, '1'))
    b = activate_tab(browser, join_tab(browser, second_room, '2'))
    for room_data, expected_name, headers in (
        (second_room, '第 2 組', b), (room, '第 1 組', a),
    ):
        state = browser.get(f"/classrooms/{room_data['classroom_id']}/state", headers=headers)
        assert state.status_code == 200
        assert state.json['group_name'] == expected_name
    same_group = activate_tab(browser, join_tab(browser, room, '1'))
    assert same_group != a
    state_url = f"/classrooms/{room['classroom_id']}/state"
    assert browser.get(state_url, headers=a).status_code == 200
    assert browser.get(state_url, headers=same_group).status_code == 200

    from guided_notes.activities.classroom_presence import roster
    from guided_notes.db import connection

    with classroom_app.app_context():
        groups = list(roster(connection(), {'id': room['classroom_id'], 'state': 'OPEN'}))
    assert len(groups) == 1
    assert groups[0]['online_count'] == 1


def test_invalid_tab_join_does_not_replace_current_authorization(classroom_app, classroom_setup):
    _, room = classroom_setup
    student, _ = browser_tabs(classroom_app)
    headers = activate_tab(student, join_tab(student, room, '1'))
    invalid = join_tab(student, room, '01')
    assert invalid.status_code == 400
    assert invalid.json['error'] == 'INVALID_GROUP_NUMBER'
    assert student.get(f"/classrooms/{room['classroom_id']}/state", headers=headers).status_code == 200
