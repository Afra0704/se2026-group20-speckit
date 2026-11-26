from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from conftest import post
from guided_notes.db import connection


def test_two_creators_compete_for_only_one_effective_code(classroom_app, classroom_teacher, classroom_setup, monkeypatch):
    from guided_notes.activities import classroom_routes
    course, room = classroom_setup
    post(classroom_teacher, f"/teacher/classrooms/{room['classroom_id']}/close", confirm=True)
    clients = [classroom_app.test_client() for _ in range(2)]
    for client in clients:
        post(client, '/teacher/session', username='teacher', password='test-password')
    monkeypatch.setattr(classroom_routes, 'make_room_code', lambda: room['code'])
    barrier = Barrier(2)
    def create(client):
        barrier.wait(timeout=3)
        return post(client, f"/teacher/courses/{course['course_id']}/classrooms", title='race').status_code
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(create, clients))
    assert sorted(results) == [201, 503]
    assert post(classroom_teacher, f"/teacher/classrooms/{room['classroom_id']}/close", confirm=True).status_code == 200
    with classroom_app.app_context():
        assert connection().execute("SELECT count(*) FROM classrooms WHERE code=? AND state='OPEN'", (room['code'],)).fetchone()[0] == 1


def test_old_close_retry_and_new_allocation_do_not_release_new_owner(classroom_app, classroom_teacher, classroom_setup, monkeypatch):
    from guided_notes.activities import classroom_routes
    course, room = classroom_setup
    path = f"/teacher/classrooms/{room['classroom_id']}/close"
    assert post(classroom_teacher, path, confirm=True).status_code == 200
    second = classroom_app.test_client()
    post(second, '/teacher/session', username='teacher', password='test-password')
    monkeypatch.setattr(classroom_routes, 'make_room_code', lambda: room['code'])
    barrier = Barrier(2)
    def retry():
        barrier.wait(timeout=3)
        return post(classroom_teacher, path, confirm=True)
    def create():
        barrier.wait(timeout=3)
        return post(second, f"/teacher/courses/{course['course_id']}/classrooms", title='new')
    with ThreadPoolExecutor(2) as pool:
        retried, created = pool.submit(retry), pool.submit(create)
        assert retried.result().status_code == 200
        result = created.result()
        assert result.status_code == 201
    with classroom_app.app_context():
        assert connection().execute("SELECT id FROM classrooms WHERE code=? AND state='OPEN'", (room['code'],)).fetchone()[0] == result.json['classroom_id']
