import json
import sqlite3
from copy import deepcopy

import pytest

from conftest import post
from guided_notes.db import connection
from test_classroom_notes_integration import prepare_real_course
from test_import_routes import MutableSheets, URL


def create_real(app, teacher):
    cid, catalog, room = prepare_real_course(app, teacher)
    path = f"/teacher/classrooms/{room['classroom_id']}/activities"
    result = post(teacher, path, import_id=catalog['import_id'], import_version=1)
    assert result.status_code == 201, result.json
    return catalog, room, path, result.json['activity_id']


def test_full_text_snapshot_scope_and_core_unchanged(classroom_app, classroom_teacher):
    catalog, room, path, aid = create_real(classroom_app, classroom_teacher)
    state_path = f"/classrooms/{room['classroom_id']}/state"
    assert classroom_app.test_client().get(state_path).status_code == 401
    clients = [classroom_app.test_client(), classroom_app.test_client()]
    for client, name in zip(clients, ('甲', '乙')):
        assert post(client, '/classroom-memberships', code=room['code'], group_name=name).status_code == 201
    gateway = classroom_app.config['NOTES_GATEWAY']
    before = len(gateway.calls)
    states = [c.get(state_path).json['activity'] for c in clients]
    assert states[0]['questions'] == states[1]['questions']
    assert states[0]['question_text_status'] == 'complete'
    assert [len(q['items']) for q in states[0]['questions']] == [2, 1]
    with classroom_app.app_context():
        db = connection()
        recognized = json.loads(db.execute('SELECT recognized FROM notes_catalogs WHERE import_id=?', (catalog['import_id'],)).fetchone()[0])
        for q, source in zip(states[0]['questions'], recognized['questions'], strict=True):
            for item, original in zip(q['items'], source['items'], strict=True):
                assert set(item) == {'item_id', 'subitem_label', 'prompt_text'}
                assert item['prompt_text'] == original['prompt_text']
        assert all('prompt_text' not in row[0] for row in db.execute('SELECT content FROM questions WHERE activity_id=?', (aid,)))
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE activity_displays SET dto='{}' WHERE activity_id=?", (aid,))
        with pytest.raises(sqlite3.IntegrityError):
            db.execute('DELETE FROM activity_displays WHERE activity_id=?', (aid,))
    # Refresh and source edits cannot mutate the activity snapshot or call Sheets.
    gateway.sheet = deepcopy(gateway.sheet)
    assert clients[0].get(state_path).json['activity']['questions'] == states[0]['questions']
    assert len(gateway.calls) == before
    assert post(classroom_teacher, f'{path}/{aid}/start').status_code == 200
    received = []
    classroom_app.config['ACCEPT_SUBMISSION'] = lambda db, context, answers: received.append((context, answers))
    question = catalog['questions'][0]
    assert post(clients[0], f'/activities/{aid}/submissions', question_id=question['question_id'],
                items=[dict(item_id=i['item_id'], answer_text=' 原字串 ') for i in question['items']]).status_code == 201
    assert set(received[0][1]) == {i['item_id'] for i in question['items']}
    assert 'prompt_text' not in json.dumps(received[0][0])
    assert post(classroom_teacher, f'{path}/{aid}/finish').status_code == 200
    assert clients[1].get(state_path).json['activity']['phase'] == 'CLOSED'
    assert classroom_app.test_cli_runner().invoke(args=['init-db']).exit_code == 0
    assert clients[0].get(state_path).json['activity']['questions'] == states[0]['questions']


def test_old_activity_unavailable_and_corrupt_snapshot_rejected(app, teacher, activity):
    aid = activity['activity_id']
    with app.app_context():
        db = connection()
        db.execute('DROP TRIGGER activity_displays_no_delete')
        db.execute('DELETE FROM activity_displays WHERE activity_id=?', (aid,))
    state = teacher.get(f'/activities/{aid}/state').json
    assert state['question_text_status'] == 'unavailable'
    assert all(i['prompt_text'] is None for q in state['questions'] for i in q['items'])
    with app.app_context():
        connection().execute('INSERT INTO activity_displays(activity_id,dto) VALUES(?,?)', (aid, '{}'))
    response = teacher.get(f'/activities/{aid}/state')
    assert response.status_code == 409 and response.json['error'] == 'DISPLAY_CONTENT_MISMATCH'


@pytest.mark.parametrize('failure', ['mismatch', 'unavailable', 'save'])
def test_atomic_create_failure(classroom_app, classroom_teacher, classroom_setup, monkeypatch, failure):
    from catalog_support import course_import_id
    course, room = classroom_setup
    if failure == 'mismatch':
        classroom_app.config['GET_COURSE_DISPLAY_CONTENT'] = lambda *args: {}
    elif failure == 'unavailable':
        classroom_app.config['GET_COURSE_DISPLAY_CONTENT'] = False
    else:
        from guided_notes.activities import classroom_routes
        def fail(*args):
            from guided_notes.http import ApiError
            raise ApiError(503, 'DISPLAY_CONTENT_UNAVAILABLE')
        monkeypatch.setattr(classroom_routes, 'save_display', fail)
    response = post(classroom_teacher, f"/teacher/classrooms/{room['classroom_id']}/activities",
                    import_id=course_import_id(course['course_id']), import_version=1)
    assert response.status_code == (409 if failure == 'mismatch' else 503)
    with classroom_app.app_context():
        db = connection()
        assert db.execute('SELECT count(*) FROM activities').fetchone()[0] == 0
        assert db.execute('SELECT count(*) FROM questions').fetchone()[0] == 0
        assert db.execute('SELECT count(*) FROM activity_displays').fetchone()[0] == 0
        row = db.execute('SELECT current_activity_id,state_version FROM classrooms').fetchone()
        assert tuple(row) == (None, 0)


def publish(teacher, **extra):
    preview = post(teacher, '/teacher/notes/import-previews', spreadsheet_url=URL, sheet_id=7).json
    response = post(teacher, f"/teacher/notes/import-previews/{preview['preview_id']}/confirm", confirm=True, **extra)
    assert response.status_code == 200, response.json
    return response.json


@pytest.mark.parametrize('layout', ['single', 'mixed', 'moved'])
def test_real_recognition_legacy_text_and_safe_saved_page(app, teacher, layout):
    gateway = MutableSheets()
    gateway.sheet = deepcopy(gateway.layouts[layout])
    app.config.update(GET_CATALOG=None, GET_DISPLAY_CONTENT=None, NOTES_GATEWAY=gateway)
    catalog = publish(teacher)
    created = post(teacher, '/activities', import_id=catalog['import_id'], import_version=1)
    assert created.status_code == 201
    aid = created.json['activity_id']
    state = teacher.get(f'/activities/{aid}/state').json
    assert state['question_text_status'] == 'complete'
    assert len(state['questions']) == catalog['question_count']
    assert sum(len(q['items']) for q in state['questions']) == catalog['answer_item_count']
    page = teacher.get(f"/teacher/notes/catalogs/{catalog['import_id']}/versions/1").get_data(as_text=True)
    assert all(i['prompt_text'] in page for q in state['questions'] for i in q['items'])
    assert teacher.get(f"/teacher/notes/catalogs/{catalog['import_id']}/versions/1", headers={'Accept':'application/json'}).json == catalog
    # Refreshing state is entirely independent of the mutable notes item table.
    with app.app_context():
        connection().execute("UPDATE notes_answer_items SET prompt_text='不得顯示這段'")
    reads = len(gateway.calls)
    assert teacher.get(f'/activities/{aid}/state').json['questions'] == state['questions']
    assert len(gateway.calls) == reads


def test_source_new_version_does_not_replace_existing_text(app, teacher):
    gateway = MutableSheets()
    app.config.update(GET_CATALOG=None, GET_DISPLAY_CONTENT=None, NOTES_GATEWAY=gateway)
    catalog = publish(teacher)
    aid = post(teacher, '/activities', import_id=catalog['import_id'], import_version=1).json['activity_id']
    original = teacher.get(f'/activities/{aid}/state').json['questions']
    old_prompt = original[0]['items'][0]['prompt_text']
    new_prompt = '  中文\n<script>alert(1)</script> Ω🙂 ' + '長英文abc' * 200
    # Replace a synthetic prompt in the Sheets response, keeping its structure.
    gateway.sheet = json.loads(json.dumps(gateway.sheet, ensure_ascii=False).replace(
        json.dumps(old_prompt, ensure_ascii=False), json.dumps(new_prompt, ensure_ascii=False)))
    next_catalog = publish(teacher, existing_import_id=catalog['import_id'])
    assert next_catalog['import_version'] == 2
    next_id = post(teacher, '/activities', import_id=catalog['import_id'], import_version=2).json['activity_id']
    assert teacher.get(f'/activities/{aid}/state').json['questions'] == original
    updated = teacher.get(f'/activities/{next_id}/state').json['questions']
    assert updated[0]['items'][0]['prompt_text'] == new_prompt
    page = teacher.get(f"/teacher/notes/catalogs/{catalog['import_id']}/versions/2").get_data(as_text=True)
    assert '&lt;script&gt;' in page and '<script>alert(1)</script>' not in page
    assert post(teacher, '/activities', import_id=catalog['import_id'], import_version=99).status_code == 404


@pytest.mark.parametrize('absent', [False, True])
def test_missing_frozen_text_requires_reimport_and_no_activity(app, teacher, absent):
    gateway = MutableSheets()
    app.config.update(GET_CATALOG=None, GET_DISPLAY_CONTENT=None, NOTES_GATEWAY=gateway)
    catalog = publish(teacher)
    with app.app_context():
        db = connection()
        frozen = json.loads(db.execute('SELECT recognized FROM notes_catalogs').fetchone()[0])
        frozen['questions'][0]['items'][0]['prompt_text'] = ''
        if absent:
            del frozen['questions'][0]['items'][0]['prompt_text']
        # Simulate an old incomplete development fixture, never mutate production snapshots.
        db.execute('DROP TRIGGER notes_catalogs_no_update')
        db.execute('UPDATE notes_catalogs SET recognized=?', (json.dumps(frozen),))
    response = post(teacher, '/activities', import_id=catalog['import_id'], import_version=1)
    assert response.status_code == 409 and response.json['error'] == 'QUESTION_TEXT_UNAVAILABLE'
    page = teacher.get(f"/teacher/notes/catalogs/{catalog['import_id']}/versions/1").get_data(as_text=True)
    assert '重新匯入' in page
    with app.app_context():
        assert connection().execute('SELECT count(*) FROM activities').fetchone()[0] == 0


def test_legacy_provider_cannot_revoke_teacher_then_create(app, teacher):
    from catalog_support import IMPORT_ID
    original = app.config['GET_DISPLAY_CONTENT']
    def revoke(context, import_id, version):
        value = original(context, import_id, version)
        connection().execute('UPDATE teachers SET active=0 WHERE id=1')
        return value
    app.config['GET_DISPLAY_CONTENT'] = revoke
    assert post(teacher, '/activities', import_id=IMPORT_ID, import_version=1).status_code in (401, 403)
    with app.app_context():
        assert connection().execute('SELECT count(*) FROM activities').fetchone()[0] == 0


def test_duplicate_snapshot_rejected(app, teacher, activity):
    with app.app_context():
        db = connection()
        with pytest.raises(sqlite3.IntegrityError):
            db.execute('INSERT INTO activity_displays(activity_id,dto) SELECT activity_id,dto FROM activity_displays')
        assert db.execute('SELECT count(*) FROM activity_displays').fetchone()[0] == 1


def test_blank_prompt_is_rejected_before_publication(app, teacher):
    from guided_notes.notes.recognition import recognize
    gateway = MutableSheets()
    first = recognize(gateway.sheet).questions[0].items[0].prompt_text
    gateway.sheet = json.loads(json.dumps(gateway.sheet, ensure_ascii=False).replace(
        json.dumps(first, ensure_ascii=False), json.dumps(' \r\n ', ensure_ascii=False)))
    app.config.update(GET_CATALOG=None, GET_DISPLAY_CONTENT=None, NOTES_GATEWAY=gateway)
    response = post(teacher, '/teacher/notes/import-previews', spreadsheet_url=URL, sheet_id=7)
    assert response.status_code == 422
    assert 'ANSWER_AMBIGUOUS' in response.get_data(as_text=True)
    with app.app_context():
        assert connection().execute('SELECT count(*) FROM notes_catalogs').fetchone()[0] == 0


def test_source_answer_never_becomes_student_text(app, teacher):
    from guided_notes.notes.recognition import recognize
    gateway = MutableSheets()
    item = recognize(gateway.sheet).questions[0].items[0]
    r, c = item.answer_range.anchor
    values = gateway.sheet['data'][0]['rowData'][r]['values']
    values.extend({} for _ in range(c + 1 - len(values)))
    values[c]['userEnteredValue'] = {'stringValue':'PRIVATE-ANSWER-SENTINEL'}
    app.config.update(GET_CATALOG=None, GET_DISPLAY_CONTENT=None, NOTES_GATEWAY=gateway)
    catalog = publish(teacher)
    activity = post(teacher, '/activities', import_id=catalog['import_id'], import_version=1).json
    student = app.test_client()
    assert post(student, '/activity-memberships', code=activity['code'], group_name='甲').status_code == 201
    response = student.get(f"/activities/{activity['activity_id']}/state")
    assert response.status_code == 200
    assert 'PRIVATE-ANSWER-SENTINEL' not in response.get_data(as_text=True)
    assert 'answer_range' not in response.get_data(as_text=True)
