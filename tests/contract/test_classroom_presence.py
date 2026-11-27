from google_support import google_app, google_teacher, login, post
from guided_notes.activities import classroom_presence


def test_online_counts_use_live_browser_identities(google_app, google_teacher, monkeypatch):
    clock = [100]
    monkeypatch.setattr(classroom_presence, 'now', lambda: clock[0])
    course_id = post(google_teacher, '/teacher/courses', title='Presence').json['course_id']
    room = post(google_teacher, f'/teacher/courses/{course_id}/classrooms', title='One').json
    other = post(google_teacher, f'/teacher/courses/{course_id}/classrooms', title='Two').json
    rid = room['classroom_id']
    path = f'/classrooms/{rid}/presence'
    groups = f"/teacher/workspace/courses/{course_id}/classrooms/{rid}/groups"
    first = google_app.test_client()
    second = google_app.test_client()

    def join(student):
        assert post(student, '/classroom-memberships', code=room['code'], group_name='1').status_code == 201

    outsider = login(google_app.test_client(), google_app, 'B')
    assert outsider.get(groups, headers={'Accept': 'application/json'}).status_code == 404

    def online():
        return google_teacher.get(groups).json['groups'][0]['online_count']

    join(first)
    assert post(first, path, page_id='a').status_code == 204
    join(first)
    assert post(first, path, page_id='b').status_code == 204
    assert online() == 1
    join(second)
    assert post(second, path, page_id='a').status_code == 204
    assert online() == 2
    assert post(first, f"/classrooms/{other['classroom_id']}/presence", page_id='a').status_code == 403
    assert post(first, path, page_id='b', group_id=999).status_code == 400
    assert first.get(groups).status_code in (401, 403, 303)

    clock[0] = 103
    assert post(first, path, page_id='b').status_code == 204
    assert post(second, path, page_id='a').status_code == 204
    clock[0] = 106
    assert online() == 2
    assert post(first, f"/classrooms/{other['classroom_id']}/presence", page_id='a').status_code == 403
    clock[0] = 107
    assert online() == 0
    assert post(first, path, page_id='b').status_code == 204
    assert online() == 1

    assert post(google_teacher, f'/teacher/classrooms/{rid}/close', confirm=True).status_code == 200
    assert post(first, path, page_id='b').status_code == 409
    assert google_teacher.get(groups).json['classroom_state'] == 'CLOSED'
    assert online() is None


def test_page_departure_is_immediate_deduplicated_and_ignores_late_heartbeat(google_app, google_teacher):
    course = post(google_teacher, '/teacher/courses', title='Departures').json['course_id']
    room = post(google_teacher, f'/teacher/courses/{course}/classrooms', title='One').json
    rid = room['classroom_id']
    path = f'/classrooms/{rid}/presence'
    groups = f'/teacher/workspace/courses/{course}/classrooms/{rid}/groups'
    student = google_app.test_client()
    stranger = google_app.test_client()
    for client in (student, stranger):
        assert post(client, '/classroom-memberships', code=room['code'], group_name='1').status_code == 201

    def online():
        return google_teacher.get(groups).json['groups'][0]['online_count']

    assert post(student, path, page_id='first').status_code == 204
    assert post(student, path, page_id='second').status_code == 204
    assert online() == 1
    assert post(stranger, path + '/leave', page_id='first').status_code == 204
    assert online() == 1, 'another browser cannot remove this browser page'
    assert post(student, path + '/leave', page_id='first').status_code == 204
    assert online() == 1, 'the second page is still online'
    assert post(student, path + '/leave', page_id='second').status_code == 204
    assert online() == 0, 'no need to advance the timeout clock'
    assert post(student, path, page_id='second').status_code == 204
    assert online() == 0, 'a late heartbeat cannot resurrect a departed page'
    assert post(student, path + '/leave', page_id='second').status_code == 204
    assert post(student, path, page_id='restored-page').status_code == 204
    assert online() == 1
    assert post(student, path + '/leave', page_id='restored-page', group_id=999).status_code == 400
    assert student.post(path + '/leave', json={'page_id': 'restored-page'}).status_code == 403
    other = post(google_teacher, f'/teacher/courses/{course}/classrooms', title='Other').json['classroom_id']
    assert post(student, f'/classrooms/{other}/presence/leave', page_id='restored-page').status_code == 403


def test_form_beacons_require_csrf_and_preserve_same_browser_other_pages(google_app, google_teacher):
    course = post(google_teacher, '/teacher/courses', title='Beacon').json['course_id']
    room = post(google_teacher, f'/teacher/courses/{course}/classrooms', title='One').json
    rid = room['classroom_id']
    student = google_app.test_client()
    assert post(student, '/classroom-memberships', code=room['code'], group_name='1').status_code == 201
    csrf = student.get('/csrf').json['csrf']
    path = f'/classrooms/{rid}/presence'

    def online():
        return google_teacher.get(f'/teacher/workspace/courses/{course}/classrooms/{rid}/groups').json['groups'][0]['online_count']

    for page in ('a', 'b'):
        assert student.post(path, data={'page_id': page, 'csrf_token': csrf}).status_code == 204
    assert online() == 1
    assert student.post(path + '/leave', data={'page_id': 'a', 'csrf_token': 'wrong'}).status_code == 403
    assert student.post(path + '/leave', data={'page_id': 'a', 'csrf_token': csrf}).status_code == 204
    assert online() == 1
    assert student.post(path + '/leave', data={'page_id': 'b', 'csrf_token': csrf}).status_code == 204
    assert online() == 0
    assert student.post(path, data={'page_id': 'b', 'csrf_token': csrf}).status_code == 204
    assert online() == 0, 'a delayed form heartbeat also cannot restore the departed page'
