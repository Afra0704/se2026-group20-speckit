from conftest import post
from guided_notes.db import connection


def test_reuse_keeps_old_membership_and_close_is_idempotent(classroom_app, classroom_teacher, classroom_setup, monkeypatch):
    from guided_notes.activities import classroom_routes
    course, room = classroom_setup
    rid = room['classroom_id']
    student = classroom_app.test_client()
    original = post(student, '/classroom-memberships', code=room['code'].lower(), group_name=' A ')
    assert original.status_code == 201
    path = f'/teacher/classrooms/{rid}/close'
    assert post(classroom_teacher, path, confirm=True).status_code == 200
    closed_state = student.get(f'/classrooms/{rid}/state')
    assert set(closed_state.json) == {'classroom_id', 'classroom_state', 'state_version'}
    assert post(classroom_app.test_client(), '/classroom-memberships', code=room['code'], group_name='B').status_code == 403
    monkeypatch.setattr(classroom_routes, 'make_room_code', lambda: room['code'])
    new = post(classroom_teacher, f"/teacher/courses/{course['course_id']}/classrooms", title='new')
    assert new.status_code == 201 and new.json['classroom_id'] != rid
    with classroom_app.app_context():
        old = tuple(connection().execute('SELECT * FROM classrooms WHERE id=?', (rid,)).fetchone())
    assert post(classroom_teacher, path, confirm=True).status_code == 200
    with classroom_app.app_context():
        assert tuple(connection().execute('SELECT * FROM classrooms WHERE id=?', (rid,)).fetchone()) == old
    assert student.get(f"/classrooms/{new.json['classroom_id']}/state").status_code == 403
    assert student.get(f'/classrooms/{rid}/state').json == closed_state.json
    assert post(student, f'/classrooms/{rid}/result-access').status_code == 409
    joined = post(student, '/classroom-memberships', code=room['code'], group_name='A')
    assert joined.json['classroom_id'] == new.json['classroom_id']
    assert joined.json['group_id'] != original.json['group_id']


def test_input_normalization_and_collision_failure(classroom_app, classroom_teacher, classroom_setup, monkeypatch):
    from guided_notes.activities import classroom_routes
    course, room = classroom_setup
    client = classroom_app.test_client()
    assert post(client, '/classroom-memberships', code=' '+room['code'].lower()+' ', group_name='A').status_code == 201
    for invalid in (' ', 12, 'A'*33):
        assert post(client, '/classroom-memberships', code=invalid, group_name='A').status_code == 400
    assert post(client, '/classroom-memberships', code=room['code'][:2]+' '+room['code'][2:], group_name='A').status_code == 403
    monkeypatch.setattr(classroom_routes, 'make_room_code', lambda: room['code'])
    assert post(classroom_teacher, f"/teacher/courses/{course['course_id']}/classrooms", title='collision').status_code == 503


def test_closed_room_blocks_results_and_teacher_ownership_is_preserved(classroom_app, classroom_teacher, classroom_setup):
    from catalog_support import course_import_id
    course, room = classroom_setup
    rid = room['classroom_id']
    client = classroom_app.test_client()
    post(client, '/classroom-memberships', code=room['code'], group_name='A')
    aid = post(classroom_teacher, f'/teacher/classrooms/{rid}/activities', import_id=course_import_id(course['course_id']), import_version=1).json['activity_id']
    post(classroom_teacher, f'/teacher/classrooms/{rid}/close', confirm=True)
    for url in (f'/classrooms/{rid}/results', f'/activities/{aid}/results'):
        result = client.get(url)
        assert result.status_code == 409 and result.json == {'error': 'CLASSROOM_CLOSED'}
    result = client.get(f'/classrooms/{rid}/state', headers={'X-Activity-Role':'teacher'})
    assert result.status_code == 401
    assert classroom_teacher.get(f'/classrooms/{rid}/state', headers={'X-Activity-Role':'teacher'}).json['activity']['phase'] == 'CLOSED'
