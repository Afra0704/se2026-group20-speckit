from catalog_support import course_import_id
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import sqlite3

import pytest

from conftest import post
from guided_notes.db import connection, write_transaction


def activity_path(setup):
    course, room = setup
    return f"/teacher/classrooms/{room['classroom_id']}/activities", course['course_id'], room


def create(client, path, cid, **extra):
    return post(client, path, import_id=course_import_id(cid), import_version=1, **extra)


def test_create_publishes_safe_preview_to_two_groups(classroom_app, classroom_teacher, classroom_setup):
    path, cid, room = activity_path(classroom_setup)
    students = [classroom_app.test_client() for _ in range(2)]
    for client, name in zip(students, ('甲', '乙')):
        assert post(client, '/classroom-memberships', code=room['code'], group_name=name).status_code == 201
    response = create(classroom_teacher, path, cid, title='<img src=x onerror=alert(1)>')
    assert response.status_code == 201
    aid = response.json['activity_id']
    for client in students:
        state = client.get(f"/classrooms/{room['classroom_id']}/state").json
        assert state['current_activity_id'] == aid
        assert state['state_version'] == 1
        view = state['activity']
        assert view['phase'] == 'PREPARING'
        assert view['title'] == '<img src=x onerror=alert(1)>'
        assert [len(q['items']) for q in view['questions']] == [1, 2, 1]
        assert all(set(item) == {'item_id', 'subitem_label', 'prompt_text'} for q in view['questions'] for item in q['items'])
        assert set(view) == {'activity_id', 'phase', 'phase_version', 'role', 'questions', 'group_id', 'group_name', 'title',
                             'display_contract_version', 'question_text_status'}
        assert client.get(f"/classrooms/{room['classroom_id']}/state").json == state
    with classroom_app.app_context():
        assert connection().execute('SELECT started_at FROM classroom_activities WHERE activity_id=?', (aid,)).fetchone()[0] is None


@pytest.mark.parametrize('live', [False, True])
def test_unfinished_blocks_create_without_residue(classroom_app, classroom_teacher, classroom_setup, live):
    path, cid, room = activity_path(classroom_setup)
    aid = create(classroom_teacher, path, cid).json['activity_id']
    if live:
        assert post(classroom_teacher, f'{path}/{aid}/start').status_code == 200
    before = classroom_teacher.get(f"/classrooms/{room['classroom_id']}/state", headers={'X-Activity-Role': 'teacher'}).json
    refused = create(classroom_teacher, path, cid)
    assert refused.status_code == 409
    assert refused.json['error'] == 'ACTIVITY_IN_PROGRESS'
    with classroom_app.app_context():
        assert connection().execute('SELECT count(*) FROM activities').fetchone()[0] == 1
    assert classroom_teacher.get(f"/classrooms/{room['classroom_id']}/state", headers={'X-Activity-Role': 'teacher'}).json == before


def test_prepare_finish_then_new_activity_and_reinit(classroom_app, classroom_teacher, classroom_setup):
    path, cid, room = activity_path(classroom_setup)
    first = create(classroom_teacher, path, cid).json['activity_id']
    result = post(classroom_teacher, f'{path}/{first}/finish')
    assert result.status_code == 200
    assert result.json['phase_version'] == 1
    assert post(classroom_teacher, f'{path}/{first}/finish').status_code == 409
    second = create(classroom_teacher, path, cid).json['activity_id']
    assert post(classroom_teacher, f'{path}/{first}/start').status_code == 409
    assert post(classroom_teacher, f'{path}/{first}/finish').status_code == 409
    assert post(classroom_teacher, f'{path}/{second}/start').status_code == 200
    assert classroom_app.test_cli_runner().invoke(args=['init-db']).exit_code == 0
    with classroom_app.app_context():
        row = connection().execute('SELECT * FROM classroom_activities WHERE activity_id=?', (first,)).fetchone()
        assert row['started_at'] is None and row['closed_at'] is not None
        assert connection().execute('SELECT count(*) FROM classroom_activities').fetchone()[0] == 2
        assert connection().execute('SELECT current_activity_id, state_version FROM classrooms').fetchone()[:] == (second, 4)


def test_concurrent_creation_single_winner(classroom_app, classroom_teacher, classroom_setup):
    path, cid, _ = activity_path(classroom_setup)
    other = classroom_app.test_client()
    assert post(other, '/teacher/session', username='teacher', password='test-password').status_code == 204
    barrier = Barrier(2)
    def submit(client):
        barrier.wait(timeout=5)
        return create(client, path, cid).status_code
    with ThreadPoolExecutor(2) as pool:
        responses = list(pool.map(submit, (classroom_teacher, other)))
    assert sorted(responses) == [201, 409]
    with classroom_app.app_context():
        assert connection().execute('SELECT count(*) FROM activities').fetchone()[0] == 1


@pytest.mark.parametrize('live', [False, True])
def test_submission_boundaries_and_close(classroom_app, classroom_teacher, classroom_setup, live):
    path, cid, room = activity_path(classroom_setup)
    aid = create(classroom_teacher, path, cid).json['activity_id']
    student = classroom_app.test_client()
    post(student, '/classroom-memberships', code=room['code'], group_name='甲')
    accepted = []
    classroom_app.config['ACCEPT_SUBMISSION'] = lambda db, context, answers: accepted.append(context['activity_id'])
    body = {'question_id': 'fixture-q1', 'items': [{'item_id': 'fixture-item-1-1', 'answer_text': ' answer '}]}
    assert post(student, f'/activities/{aid}/submissions', **body).status_code == 409
    assert accepted == []
    if live:
        assert post(classroom_teacher, f'{path}/{aid}/start').status_code == 200
        assert post(student, f'/activities/{aid}/submissions', **body).status_code == 201
    assert post(classroom_teacher, f"/teacher/classrooms/{room['classroom_id']}/close", confirm=True).status_code == 200
    assert post(student, f'/activities/{aid}/submissions', **body).status_code in (401, 403, 409)
    assert post(classroom_teacher, f'{path}/{aid}/start').status_code == 409
    assert classroom_teacher.get(path).json['activities'][0]['phase'] == 'CLOSED'
    assert len(accepted) == int(live)


def test_authorization_and_csrf(classroom_app, classroom_teacher, classroom_setup):
    path, cid, room = activity_path(classroom_setup)
    aid = create(classroom_teacher, path, cid).json['activity_id']
    stranger = classroom_app.test_client()
    post(stranger, '/teacher/session', username='other', password='test-password')
    student = classroom_app.test_client()
    post(student, '/classroom-memberships', code=room['code'], group_name='甲')
    for suffix in (f'/activities/{aid}/start', f'/activities/{aid}/finish', '/close'):
        endpoint = f"/teacher/classrooms/{room['classroom_id']}{suffix}"
        assert post(stranger, endpoint, confirm=True).status_code in (403, 404)
        assert post(student, endpoint, confirm=True).status_code in (401, 403)
        assert classroom_teacher.post(endpoint, json={'confirm': True}).status_code == 403


def test_database_guards_and_transaction_rollback(classroom_app, classroom_teacher, classroom_setup):
    path, cid, room = activity_path(classroom_setup)
    aid = create(classroom_teacher, path, cid).json['activity_id']
    with classroom_app.app_context():
        with pytest.raises(sqlite3.IntegrityError):
            with write_transaction() as db:
                db.execute("INSERT INTO activities(id,teacher_id,code,import_id,import_version) VALUES ('extra',1,'EXTRA','x',1)")
                db.execute('INSERT INTO classroom_activities VALUES (?,?,?,CURRENT_TIMESTAMP,NULL,NULL)', ('extra', room['classroom_id'], 'extra'))
        assert connection().execute("SELECT 1 FROM activities WHERE id='extra'").fetchone() is None
    assert post(classroom_teacher, f'{path}/{aid}/finish').status_code == 200
    with classroom_app.app_context():
        with pytest.raises(sqlite3.IntegrityError):
            connection().execute("UPDATE activities SET phase='PREPARING' WHERE id=?", (aid,))


def test_catalog_failure_preserves_state(classroom_app, classroom_teacher, classroom_setup):
    from guided_notes.http import ApiError
    path, cid, room = activity_path(classroom_setup)
    before = classroom_teacher.get(f"/classrooms/{room['classroom_id']}/state", headers={'X-Activity-Role': 'teacher'}).json
    def fail(*args):
        raise ApiError(503, 'CATALOG_UNAVAILABLE')
    classroom_app.config['GET_COURSE_CATALOG'] = fail
    assert create(classroom_teacher, path, cid).status_code == 503
    assert classroom_teacher.get(path).json == {'activities': []}
    assert classroom_teacher.get(f"/classrooms/{room['classroom_id']}/state", headers={'X-Activity-Role': 'teacher'}).json == before


def test_create_failure_inside_transaction_rolls_back(classroom_app, classroom_teacher, classroom_setup, monkeypatch):
    from guided_notes.activities import classroom_routes
    from guided_notes.http import ApiError
    path, cid, room = activity_path(classroom_setup)
    original = classroom_routes.store_activity
    def fail_after_insert(*args):
        original(*args)
        raise ApiError(503, 'CATALOG_UNAVAILABLE')
    monkeypatch.setattr(classroom_routes, 'store_activity', fail_after_insert)
    assert create(classroom_teacher, path, cid).status_code == 503
    with classroom_app.app_context():
        db = connection()
        for table in ('activities', 'questions', 'classroom_activities'):
            assert db.execute(f'SELECT count(*) FROM {table}').fetchone()[0] == 0
        assert db.execute('SELECT current_activity_id,state_version FROM classrooms').fetchone()[:] == (None, 0)


def test_other_room_and_noncurrent_operations(classroom_app, classroom_teacher, classroom_setup):
    path, cid, room = activity_path(classroom_setup)
    first = create(classroom_teacher, path, cid).json['activity_id']
    other_room = post(classroom_teacher, f'/teacher/courses/{cid}/classrooms', title='Other').json
    other_path = f"/teacher/classrooms/{other_room['classroom_id']}/activities"
    other = create(classroom_teacher, other_path, cid)
    assert other.status_code == 201
    for action in ('start', 'finish'):
        assert post(classroom_teacher, f"{path}/{other.json['activity_id']}/{action}").status_code == 403
    assert post(classroom_teacher, f'{path}/{first}/finish').status_code == 200
    create(classroom_teacher, path, cid)
    before = classroom_teacher.get(f"/classrooms/{room['classroom_id']}/state", headers={'X-Activity-Role':'teacher'}).json
    for action in ('start', 'finish'):
        assert post(classroom_teacher, f'{path}/{first}/{action}').status_code == 409
    assert classroom_teacher.get(f"/classrooms/{room['classroom_id']}/state", headers={'X-Activity-Role':'teacher'}).json == before
