from conftest import post
from guided_notes.db import connection
import time


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
