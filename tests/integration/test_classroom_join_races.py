from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
import pytest

from conftest import post
from classroom_tab_support import activate_tab, browser_tabs, join_tab
from guided_notes.db import connection


def test_close_writer_first_prevents_waiting_join_from_using_old_mapping(classroom_app, classroom_teacher, classroom_setup, monkeypatch):
    from guided_notes.activities import classroom_routes
    _, room = classroom_setup
    entered, release = Event(), Event()
    original = classroom_routes.owned_classroom
    def held(*args):
        result = original(*args)
        entered.set()
        assert release.wait(3)
        return result
    monkeypatch.setattr(classroom_routes, 'owned_classroom', held)
    student = classroom_app.test_client()
    with ThreadPoolExecutor(2) as pool:
        closing = pool.submit(post, classroom_teacher, f"/teacher/classrooms/{room['classroom_id']}/close", confirm=True)
        assert entered.wait(3)
        joining = pool.submit(post, student, '/classroom-memberships', code=room['code'], group_name='1')
        release.set()
        assert closing.result().status_code == 200
        result = joining.result()
        assert result.status_code == 403 and result.json['error'] == 'JOIN_DENIED'
        assert not result.headers.getlist('Set-Cookie')


def test_join_resolves_one_target_before_close_can_commit(classroom_app, classroom_teacher, classroom_setup, monkeypatch):
    from guided_notes.activities import classroom_routes
    course, room = classroom_setup
    entered, release = Event(), Event()
    original = classroom_routes.join
    def held(db, code, name):
        result = original(db, code, name)
        entered.set()
        assert release.wait(3)
        return result
    monkeypatch.setattr(classroom_routes, 'join', held)
    student = classroom_app.test_client()
    with ThreadPoolExecutor(2) as pool:
        joining = pool.submit(post, student, '/classroom-memberships', code=room['code'], group_name='1')
        assert entered.wait(3)
        closing = pool.submit(post, classroom_teacher, f"/teacher/classrooms/{room['classroom_id']}/close", confirm=True)
        release.set()
        result = joining.result()
        assert result.status_code == 201 and result.json['classroom_id'] == room['classroom_id']
        assert closing.result().status_code == 200
    assert student.get(f"/classrooms/{room['classroom_id']}/state").json['classroom_state'] == 'CLOSED'


def test_failure_during_close_rolls_back_activity_and_code(classroom_app, classroom_teacher, classroom_setup, monkeypatch):
    from catalog_support import course_import_id
    from guided_notes.activities import classroom_routes
    course, room = classroom_setup
    aid = post(classroom_teacher, f"/teacher/classrooms/{room['classroom_id']}/activities", import_id=course_import_id(course['course_id']), import_version=1).json['activity_id']
    original = classroom_routes.transition
    def fail(*args):
        original(*args)
        raise RuntimeError('injected close failure')
    monkeypatch.setattr(classroom_routes, 'transition', fail)
    with pytest.raises(RuntimeError, match='injected close failure'):
        post(classroom_teacher, f"/teacher/classrooms/{room['classroom_id']}/close", confirm=True)
    with classroom_app.app_context():
        assert connection().execute('SELECT state FROM classrooms WHERE id=?', (room['classroom_id'],)).fetchone()[0] == 'OPEN'
        assert connection().execute('SELECT phase FROM activities WHERE id=?', (aid,)).fetchone()[0] == 'PREPARING'
    assert post(classroom_app.test_client(), '/classroom-memberships', code=room['code'], group_name='2').status_code == 201


def test_parallel_tab_joins_choose_only_one_group_before_heartbeat(classroom_app, classroom_setup):
    _, room = classroom_setup
    first, second = browser_tabs(classroom_app)
    ready = Barrier(2)

    def join(client, group):
        ready.wait(timeout=5)
        return join_tab(client, room, group)

    with ThreadPoolExecutor(2) as pool:
        a = pool.submit(join, first, '1')
        b = pool.submit(join, second, '2')
        responses = [a.result(timeout=10), b.result(timeout=10)]
    assert sorted(response.status_code for response in responses) == [201, 409]
    denied = next(response for response in responses if response.status_code == 409)
    assert denied.json['error'] == 'CLASSROOM_GROUP_IN_USE'


def test_expired_last_page_allows_group_change_and_invalidates_old_generation(
        classroom_app, classroom_setup, monkeypatch):
    from guided_notes.activities import classroom_presence

    _, room = classroom_setup
    first, second = browser_tabs(classroom_app)
    clock = [classroom_presence.now()]
    monkeypatch.setattr(classroom_presence, 'now', lambda: clock[0])
    headers = activate_tab(first, join_tab(first, room, '1'))
    assert join_tab(second, room, '2').status_code == 409
    clock[0] += classroom_presence.PRESENCE_TTL_SECONDS + 1
    activate_tab(second, join_tab(second, room, '2'))
    clock[0] += classroom_presence.PRESENCE_TTL_SECONDS + 1
    state = first.get(f"/classrooms/{room['classroom_id']}/state", headers=headers)
    assert state.status_code in (401, 403)
