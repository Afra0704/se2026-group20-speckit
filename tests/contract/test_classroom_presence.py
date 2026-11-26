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
        assert post(student, '/classroom-memberships', code=room['code'], group_name='A').status_code == 201

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

    clock[0] = 119
    assert post(first, path, page_id='b').status_code == 204
    assert post(second, path, page_id='a').status_code == 204
    clock[0] = 126
    assert online() == 2
    assert post(first, f"/classrooms/{other['classroom_id']}/presence", page_id='a').status_code == 403
    clock[0] = 145
    assert online() == 0
    assert post(first, path, page_id='b').status_code == 204
    assert online() == 1

    assert post(google_teacher, f'/teacher/classrooms/{rid}/close', confirm=True).status_code == 200
    assert post(first, path, page_id='b').status_code == 409
    assert google_teacher.get(groups).json['classroom_state'] == 'CLOSED'
    assert online() is None
