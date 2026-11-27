"""Formal 003 providers under the confirmed 009 classroom lifecycle."""
import sqlite3
from uuid import uuid4
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

from conftest import post
from guided_notes.db import connection
from quiz_support import published_quiz, submit_question
from google_support import google_app, google_teacher, connect


@pytest.mark.parametrize('first', ['submission','close'])
def test_formal_acceptance_and_classroom_close_share_the_write_boundary(classroom_app, classroom_teacher, classroom_setup, monkeypatch, first):
    from guided_notes.quiz import submission_gateway
    from guided_notes.activities import classroom_routes
    activity, questions = published_quiz(classroom_app, classroom_teacher, classroom_setup)
    aid, rid = activity['activity_id'], classroom_setup[1]['classroom_id']
    student = classroom_app.test_client()
    post(student, '/classroom-memberships', code=classroom_setup[1]['code'], group_name='1')
    post(classroom_teacher, f'/teacher/classrooms/{rid}/activities/{aid}/start')
    entered, release = Event(), Event()
    if first == 'submission':
        transaction = submission_gateway.write_transaction
        @contextmanager
        def held_transaction():
            with transaction() as db:
                yield db
                entered.set()
                assert release.wait(3)
        monkeypatch.setattr(submission_gateway, 'write_transaction', held_transaction)
    else:
        transition = classroom_routes.transition
        def held_transition(*args):
            result = transition(*args)
            entered.set()
            assert release.wait(3)
            return result
        monkeypatch.setattr(classroom_routes, 'transition', held_transition)
    send = lambda:submit_question(student, aid, questions[0])
    close = lambda:post(classroom_teacher, f'/teacher/classrooms/{rid}/close', confirm=True)
    with ThreadPoolExecutor(2) as pool:
        leading = pool.submit(send if first=='submission' else close)
        assert entered.wait(3)
        following = pool.submit(close if first=='submission' else send)
        release.set()
        results = [leading.result(),following.result()]
    accepted, closed = results if first=='submission' else results[::-1]
    assert accepted.status_code == (201 if first=='submission' else 409)
    assert closed.status_code == 200
    with classroom_app.app_context():
        assert connection().execute('SELECT count(*) FROM quiz_submissions WHERE activity_id=?',(aid,)).fetchone()[0] == (1 if first=='submission' else 0)


def pending_quiz(app, teacher, setup, monkeypatch):
    from guided_notes.quiz import settlement
    _, room = setup
    activity, questions = published_quiz(app, teacher, setup)
    aid, rid = activity['activity_id'], room['classroom_id']
    student = app.test_client()
    post(student, '/classroom-memberships', code=room['code'], group_name='1')
    post(teacher, f'/teacher/classrooms/{rid}/activities/{aid}/start')
    assert submit_question(student, aid, questions[0]).status_code == 201
    with monkeypatch.context() as patch:
        def fail(*args):
            raise RuntimeError('controlled temporary settlement failure')
        patch.setattr(settlement, 'publish', fail)
        assert post(teacher, f'/teacher/classrooms/{rid}/activities/{aid}/finish').status_code == 200
    return student, aid, rid, questions


@pytest.mark.parametrize('route', ['activity', 'room'])
def test_pending_retry_writes_before_final_authorized_read(classroom_app, classroom_teacher, classroom_setup, monkeypatch, route):
    from guided_notes.quiz import settlement, results_gateway
    student, aid, rid, _ = pending_quiz(classroom_app, classroom_teacher, classroom_setup, monkeypatch)
    retry = settlement.try_pending
    observed = []
    def outside_read(requested):
        assert not connection().in_transaction
        observed.append(requested)
        retry(requested)
    monkeypatch.setattr(settlement, 'try_pending', outside_read)
    monkeypatch.setattr(results_gateway, 'try_pending', outside_read)
    url = f'/activities/{aid}/results' if route == 'activity' else f'/classrooms/{rid}/results'
    response = student.get(url)
    assert response.status_code == 200
    assert observed == [aid]
    if route == 'activity':
        assert response.json['status'] == 'settled'
        assert response.json['results'][0]['own']['rank'] == 1
    else:
        assert response.json['activities'][0]['status'] == 'settled'


@pytest.mark.parametrize('route', ['activity', 'room'])
def test_close_between_retry_and_final_read_is_reauthorized(classroom_app, classroom_teacher, classroom_setup, monkeypatch, route):
    from guided_notes.quiz import settlement, results_gateway
    student, aid, rid, _ = pending_quiz(classroom_app, classroom_teacher, classroom_setup, monkeypatch)
    original = settlement.try_pending
    closed = False
    def close_after_retry(requested):
        nonlocal closed
        assert not connection().in_transaction
        original(requested)
        if not closed:
            closed = True
            assert post(classroom_teacher, f'/teacher/classrooms/{rid}/close', confirm=True).status_code == 200
    monkeypatch.setattr(settlement, 'try_pending', close_after_retry)
    monkeypatch.setattr(results_gateway, 'try_pending', close_after_retry)
    url = f'/activities/{aid}/results' if route == 'activity' else f'/classrooms/{rid}/results'
    response = student.get(url)
    assert response.status_code == 409 and response.json == {'error':'CLASSROOM_CLOSED'}


def test_formal_settlement_and_sequence_survive_legacy_upgrade_and_reuse(classroom_app, classroom_teacher, classroom_setup, monkeypatch):
    from guided_notes import create_app
    from guided_notes.activities import classroom_routes
    from classroom_009_support import downgrade_classrooms, rows
    _, room = classroom_setup
    activity, questions = published_quiz(classroom_app, classroom_teacher, classroom_setup)
    aid, rid = activity['activity_id'], room['classroom_id']
    a, b = classroom_app.test_client(), classroom_app.test_client()
    for client, name in ((a,'1'),(b,'2')):
        post(client, '/classroom-memberships', code=room['code'], group_name=name)
    post(classroom_teacher, f'/teacher/classrooms/{rid}/activities/{aid}/start')
    key = str(uuid4())
    assert submit_question(a, aid, questions[0], key=key, answer='first').status_code == 201
    assert submit_question(b, aid, questions[0], answer='second').status_code == 201
    assert submit_question(a, aid, questions[0], key=key, answer='first').status_code == 201
    post(classroom_teacher, f'/teacher/classrooms/{rid}/close', confirm=True)
    teacher_result = classroom_teacher.get(f'/activities/{aid}/results', headers={'X-Activity-Role':'teacher'}).json
    assert teacher_result['results'][0]['winner_name'] == '第 1 組'
    assert [g['rank'] for g in teacher_result['results'][0]['groups']] == [1,2]
    target = classroom_app.config['DATABASE']
    # The published_quiz fixture seeds the catalog directly; complete the normal
    # 001 name backfill before measuring the 009 migration's preservation.
    create_app(dict(classroom_app.config))
    before = rows(target)
    with sqlite3.connect(target) as db:
        sequence = db.execute('SELECT * FROM sqlite_sequence').fetchall()
    downgrade_classrooms(target)
    for _ in range(2):
        create_app(dict(classroom_app.config))
    assert rows(target) == before
    with sqlite3.connect(target) as db:
        assert db.execute('SELECT * FROM sqlite_sequence').fetchall() == sequence
        assert db.execute('PRAGMA foreign_key_check').fetchall() == []
    monkeypatch.setattr(classroom_routes, 'make_room_code', lambda:room['code'])
    new = post(classroom_teacher, f"/teacher/courses/{classroom_setup[0]['course_id']}/classrooms", title='new').json
    assert new['classroom_id'] != rid
    assert post(classroom_teacher, f'/teacher/classrooms/{rid}/close', confirm=True).status_code == 200
    assert classroom_teacher.get(f'/activities/{aid}/results', headers={'X-Activity-Role':'teacher'}).json == teacher_result
    assert a.get(f'/activities/{aid}/results').status_code == 409
    assert submit_question(a, aid, questions[0], key=key, answer='first').status_code == 409
    assert post(a, f'/classrooms/{rid}/result-access').status_code == 409
    assert a.get(f"/classrooms/{new['classroom_id']}/state").status_code == 403


def test_google_upgrade_failure_preserves_formal_quiz_and_encrypted_identity(google_app, google_teacher, monkeypatch):
    from guided_notes import create_app
    from guided_notes.google_login import repository
    from classroom_009_support import downgrade_classrooms, rows
    connect(google_teacher)
    course = post(google_teacher, '/teacher/courses', title='formal preservation').json
    room = post(google_teacher, f"/teacher/courses/{course['course_id']}/classrooms", title='saved').json
    activity, questions = published_quiz(google_app, google_teacher, (course,room))
    student = google_app.test_client()
    post(student, '/classroom-memberships', code=room['code'], group_name='1')
    aid, rid = activity['activity_id'], room['classroom_id']
    post(google_teacher, f'/teacher/classrooms/{rid}/activities/{aid}/start')
    assert submit_question(student, aid, questions[0]).status_code == 201
    post(google_teacher, f'/teacher/classrooms/{rid}/close', confirm=True)
    create_app(dict(google_app.config))
    target = google_app.config['DATABASE']
    before = rows(target)
    assert all(before[name] for name in ('auth_instance','google_identities','google_sheets_credentials','quiz_submissions','quiz_settlements'))
    with sqlite3.connect(target) as db:
        sequence = db.execute('SELECT * FROM sqlite_sequence').fetchall()
    downgrade_classrooms(target)
    with monkeypatch.context() as patch:
        original = repository.initialize
        def fail(db):
            original(db)
            raise RuntimeError('controlled Google bootstrap failure')
        patch.setattr(repository, 'initialize', fail)
        with pytest.raises(RuntimeError, match='Google bootstrap failure'):
            create_app(dict(google_app.config))
    assert rows(target) == before
    with sqlite3.connect(target) as db:
        assert not db.execute("SELECT 1 FROM sqlite_master WHERE name='classroom_schema_versions'").fetchone()
        assert db.execute('SELECT * FROM sqlite_sequence').fetchall() == sequence
    for _ in range(2):
        create_app(dict(google_app.config))
    assert rows(target) == before


def test_formal_closed_classroom_keeps_teacher_snapshot_and_unknown_writeback(classroom_app, classroom_teacher, monkeypatch):
    from test_classroom_notes_integration import prepare_real_course
    from test_export_routes import confirm_export
    from guided_notes.activities import classroom_routes
    cid, catalog, room = prepare_real_course(classroom_app, classroom_teacher)
    rid = room['classroom_id']
    activity = post(classroom_teacher, f'/teacher/classrooms/{rid}/activities', import_id=catalog['import_id'], import_version=1).json
    aid = activity['activity_id']
    a, b = classroom_app.test_client(), classroom_app.test_client()
    for client, name in ((a,'1'),(b,'2')):
        post(client, '/classroom-memberships', code=room['code'], group_name=name)
    post(classroom_teacher, f'/teacher/classrooms/{rid}/activities/{aid}/start')
    for question in catalog['questions']:
        assert submit_question(a, aid, question, answer='first').status_code == 201
        assert submit_question(b, aid, question, answer='second').status_code == 201
    assert post(classroom_teacher, f'/teacher/classrooms/{rid}/close', confirm=True).status_code == 200
    result = classroom_teacher.get(f'/activities/{aid}/results', headers={'X-Activity-Role':'teacher'}).json
    assert result['status'] == 'settled'
    assert all(row['winner_name']=='第 1 組' for row in result['results'])
    preview = post(classroom_teacher, '/teacher/notes/export-previews', activity_id=aid)
    assert preview.status_code == 201
    gateway = classroom_app.config['NOTES_GATEWAY']
    assert not gateway.writes
    gateway.write_hook = lambda:setattr(gateway, 'readback_error', True)
    report = confirm_export(classroom_teacher, preview.json['preview_id']).json
    assert report['status'] == 'needs_attention' and report['counts']['unknown'] > 0
    monkeypatch.setattr(classroom_routes, 'make_room_code', lambda:room['code'])
    new_room = post(classroom_teacher, f'/teacher/courses/{cid}/classrooms', title='new').json
    assert post(classroom_teacher, f'/teacher/classrooms/{rid}/close', confirm=True).status_code == 200
    assert len(gateway.writes) == 1
    assert classroom_teacher.get(f'/activities/{aid}/results', headers={'X-Activity-Role':'teacher'}).json == result
    assert classroom_teacher.get(f"/teacher/notes/operations/{report['operation_id']}", headers={'Accept':'application/json'}).json == report
    for client in (a,b):
        assert client.get(f'/activities/{aid}/results').status_code == 409
        assert post(client, f'/classrooms/{rid}/result-access').status_code == 409
    post(a, '/classroom-memberships', code=new_room['code'], group_name='1')
    assert a.get(f'/activities/{aid}/results').status_code == 403
