from catalog_support import course_import_id
from conftest import post
from concurrent.futures import ThreadPoolExecutor
from threading import Event


def test_accept_first_keeps_original_scope_while_close_waits(classroom_app, classroom_teacher, classroom_setup):
    from guided_notes.db import connection
    course, room = classroom_setup
    rid = room['classroom_id']
    student = classroom_app.test_client()
    joined = post(student, '/classroom-memberships', code=room['code'], group_name='A').json
    aid = post(classroom_teacher, f'/teacher/classrooms/{rid}/activities', import_id=course_import_id(course['course_id']), import_version=1).json['activity_id']
    post(classroom_teacher, f'/teacher/classrooms/{rid}/activities/{aid}/start')
    entered, release = Event(), Event()
    with classroom_app.app_context():
        connection().execute('CREATE TABLE accepted_009(activity_id TEXT, group_id INTEGER, answer TEXT)')
    def accept(db, context, answers):
        assert db.in_transaction
        db.execute('INSERT INTO accepted_009 VALUES (?,?,?)', (aid, joined['group_id'], next(iter(answers.values()))))
        entered.set()
        assert release.wait(3)
    classroom_app.config['ACCEPT_SUBMISSION'] = accept
    with ThreadPoolExecutor(2) as pool:
        submitting = pool.submit(post, student, f'/activities/{aid}/submissions', question_id='fixture-q1', items=[{'item_id':'fixture-item-1-1','answer_text':'saved'}])
        assert entered.wait(3)
        closing = pool.submit(post, classroom_teacher, f'/teacher/classrooms/{rid}/close', confirm=True)
        release.set()
        assert submitting.result().status_code == 201
        assert closing.result().status_code == 200
    with classroom_app.app_context():
        assert [tuple(r) for r in connection().execute('SELECT * FROM accepted_009')] == [(aid, joined['group_id'], 'saved')]


def test_close_first_rejects_new_submission_and_new_result_read(classroom_app, classroom_teacher, classroom_setup):
    course, room = classroom_setup
    rid = room['classroom_id']
    student = classroom_app.test_client()
    post(student, '/classroom-memberships', code=room['code'], group_name='A')
    aid = post(classroom_teacher, f'/teacher/classrooms/{rid}/activities', import_id=course_import_id(course['course_id']), import_version=1).json['activity_id']
    post(classroom_teacher, f'/teacher/classrooms/{rid}/activities/{aid}/start')
    accepted = []
    classroom_app.config['ACCEPT_SUBMISSION'] = lambda db, context, answers: accepted.append(context)
    post(classroom_teacher, f'/teacher/classrooms/{rid}/close', confirm=True)
    response = post(student, f'/activities/{aid}/submissions', question_id='fixture-q1', items=[{'item_id':'fixture-item-1-1','answer_text':'A'}])
    assert response.status_code == 409 and not accepted
    assert student.get(f'/activities/{aid}/results').status_code == 409


def test_authorized_result_snapshot_precedes_close_and_new_read_is_rejected(classroom_app, classroom_teacher, classroom_setup):
    course, room = classroom_setup
    rid = room['classroom_id']
    student = classroom_app.test_client()
    post(student, '/classroom-memberships', code=room['code'], group_name='A')
    aid = post(classroom_teacher, f'/teacher/classrooms/{rid}/activities', import_id=course_import_id(course['course_id']), import_version=1).json['activity_id']
    post(classroom_teacher, f'/teacher/classrooms/{rid}/activities/{aid}/finish')
    entered, release = Event(), Event()
    def settled(db, requested):
        assert db.in_transaction and requested == aid
        entered.set()
        assert release.wait(3)
        return {'snapshot':{},'results':[]}
    classroom_app.config['GET_SETTLED_RESULTS'] = settled
    with ThreadPoolExecutor(2) as pool:
        reading = pool.submit(student.get, f'/activities/{aid}/results')
        assert entered.wait(3)
        closing = pool.submit(post, classroom_teacher, f'/teacher/classrooms/{rid}/close', confirm=True)
        release.set()
        assert reading.result().json == {'status':'settled','results':[]}
        assert closing.result().status_code == 200
    assert student.get(f'/activities/{aid}/results').status_code == 409
