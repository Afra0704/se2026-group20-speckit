from conftest import post
from guided_notes.db import connection
import time
from uuid import uuid4

from classroom_tab_support import browser_tabs, join_tab


def test_tab_access_handoff_is_once_but_retry_returns_same_document(
        classroom_app, classroom_setup):
    _, room = classroom_setup
    first, duplicate = browser_tabs(classroom_app)
    stranger, _ = browser_tabs(classroom_app)
    path = f"/classrooms/{room['classroom_id']}/tab-access"
    joined = join_tab(first, room, '1').json

    def activate(client, index, **fields):
        return post(client, path, resume_id=index, page_id=uuid4().hex,
                    request_id=uuid4().hex, **fields)

    assert activate(stranger, joined['resume_id']).status_code == 403
    original_page = uuid4().hex
    original = post(first, path, resume_id=joined['resume_id'], page_id=original_page,
                    request_id=uuid4().hex).json
    handoff = uuid4().hex
    assert post(first, path.replace('/tab-access', '/presence/leave'),
                page_id=original_page, page_token=original['page_token'], handoff_id=handoff).status_code == 204
    copied = activate(duplicate, original['resume_id'])
    assert copied.status_code == 200 and not copied.json['continued_operation_scope']
    fields = dict(resume_id=original['resume_id'], page_id=uuid4().hex,
                  request_id=uuid4().hex, handoff_id=handoff)
    reloaded = post(first, path, **fields)
    assert reloaded.status_code == 200 and reloaded.json['continued_operation_scope']
    assert post(first, path, **fields).json == reloaded.json
    changed = dict(fields, page_id=uuid4().hex)
    assert post(first, path, **changed).json['error'] == 'CLASSROOM_TAB_REQUEST_CONFLICT'
    assert not activate(duplicate, original['resume_id'], handoff_id=handoff).json['continued_operation_scope']


def test_tab_revoke_is_idempotent_and_keeps_duplicate(classroom_app, classroom_setup):
    _, room = classroom_setup
    student, duplicate = browser_tabs(classroom_app)
    path = f"/classrooms/{room['classroom_id']}"
    joined = join_tab(student, room, '1').json

    def access(client, index):
        return post(client, path+'/tab-access', resume_id=index, page_id=uuid4().hex,
                    request_id=uuid4().hex)

    original = access(student, joined['resume_id']).json
    copied = access(duplicate, original['resume_id']).json
    headers = {'X-Classroom-Tab': original['page_token'],
               'X-CSRF-Token': student.get('/csrf').json['csrf']}
    request = {'request_id': uuid4().hex}
    for _ in range(2):
        assert student.post(path+'/tab-access/revoke', json=request, headers=headers).status_code == 204
    assert student.get(path+'/state', headers=headers).status_code == 401
    assert access(student, original['resume_id']).status_code == 401
    assert duplicate.get(path+'/state', headers={'X-Classroom-Tab': copied['page_token']}).status_code == 200


def test_expired_tab_index_cannot_restore(classroom_app, classroom_setup):
    _, room = classroom_setup
    student, _ = browser_tabs(classroom_app)
    join = join_tab(student, room, '1').json
    with classroom_app.app_context():
        connection().execute('UPDATE classroom_tab_grants SET resume_expires_at=0')
    path = f"/classrooms/{room['classroom_id']}/tab-access"
    response = post(student, path, resume_id=join['resume_id'], page_id=uuid4().hex,
                    request_id=uuid4().hex)
    assert response.status_code == 401
    assert response.json['error'] == 'CLASSROOM_REJOIN_REQUIRED'


def test_document_renewal_transfers_online_reservation_and_operation_scope(classroom_app, classroom_setup):
    _, room = classroom_setup
    student, _ = browser_tabs(classroom_app)
    path = f"/classrooms/{room['classroom_id']}"
    joined = join_tab(student, room, '1').json
    previous_page = uuid4().hex
    previous = post(student, path+'/tab-access', resume_id=joined['resume_id'],
                    page_id=previous_page, request_id=uuid4().hex).json
    headers = {'X-Classroom-Tab': previous['page_token'],
               'X-CSRF-Token': student.get('/csrf').json['csrf']}
    page = uuid4().hex
    renewed = student.post(path+'/tab-access', headers=headers, json={
        'resume_id': previous['resume_id'], 'page_id': page, 'request_id': uuid4().hex,
    })
    assert renewed.status_code == 200 and renewed.json['continued_operation_scope']
    assert student.post(path+'/presence', headers=headers, json={'page_id': previous_page}).status_code == 204
    with classroom_app.app_context():
        pages = connection().execute('SELECT page_id FROM classroom_presence WHERE classroom_id=?',
                                     (room['classroom_id'],)).fetchall()
    assert [row['page_id'] for row in pages] == [page]


def test_recovery_requires_csrf_and_obeys_rate_limit(classroom_app, classroom_setup):
    _, room = classroom_setup
    student = classroom_app.test_client()
    post(student, '/classroom-memberships', code=room['code'], group_name='1')
    path = f"/classrooms/{room['classroom_id']}/result-access"
    assert student.post(path, json={}).status_code == 403
    classroom_app.config['TESTING'] = False
    with classroom_app.app_context():
        connection().execute('INSERT INTO attempts VALUES (?,?,?)', ('classroom-recover:127.0.0.1', 100, int(time.time())+60))
    blocked = post(student, path)
    assert blocked.status_code == 429
    assert not blocked.headers.getlist('Set-Cookie')


def test_recover_open_only_and_reject_spoofed_group(classroom_app, classroom_teacher, classroom_setup):
    _, room = classroom_setup
    rid = room['classroom_id']
    student = classroom_app.test_client()
    post(student, '/classroom-memberships', code=room['code'], group_name='1')
    student.delete_cookie('session')
    assert post(student, f'/classrooms/{rid}/result-access', group_id=999).status_code == 400
    assert post(student, f'/classrooms/{rid}/result-access').status_code == 204
    assert student.get(f'/classrooms/{rid}/state').json['group_name'] == '第 1 組'
    post(classroom_teacher, f'/teacher/classrooms/{rid}/close', confirm=True)
    with classroom_app.app_context():
        count = connection().execute('SELECT count(*) FROM classroom_grants').fetchone()[0]
    closed = post(student, f'/classrooms/{rid}/result-access')
    assert closed.status_code == 409
    assert not closed.headers.getlist('Set-Cookie')
    with classroom_app.app_context():
        assert connection().execute('SELECT count(*) FROM classroom_grants').fetchone()[0] == count


def test_proof_cannot_recover_another_room(classroom_app, classroom_teacher, classroom_setup):
    course, room = classroom_setup
    student = classroom_app.test_client()
    post(student, '/classroom-memberships', code=room['code'], group_name='1')
    other = post(classroom_teacher, f"/teacher/courses/{course['course_id']}/classrooms", title='other').json
    assert post(student, f"/classrooms/{other['classroom_id']}/result-access").status_code == 403


def test_expired_proof_and_failed_join_do_not_replace_current_scope(classroom_app, classroom_teacher, classroom_setup):
    _, room = classroom_setup
    student = classroom_app.test_client()
    rid = room['classroom_id']
    response = post(student, '/classroom-memberships', code=room['code'], group_name='1')
    cookie = next(value for value in response.headers.getlist('Set-Cookie') if value.startswith('classroom_proof='))
    assert 'HttpOnly' in cookie and 'SameSite=Lax' in cookie
    assert f'Path=/classrooms/{rid}/result-access' in cookie
    assert post(student, '/classroom-memberships', code='ZZ-INVALID', group_name='2').status_code == 403
    assert student.get(f'/classrooms/{rid}/state').json['group_name'] == '第 1 組'
    with classroom_app.app_context():
        connection().execute('UPDATE classroom_memberships SET expires=0')
    assert post(student, f'/classrooms/{rid}/result-access').status_code == 403
