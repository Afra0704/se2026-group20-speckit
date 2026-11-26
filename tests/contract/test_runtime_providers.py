from types import ModuleType
import sys

from conftest import post
from catalog_support import IMPORT_ID, course_import_id
from quiz_support import submit


def test_old_flag_cannot_enable_fake_catalog(app, teacher, monkeypatch):
    monkeypatch.setenv('GUIDED_NOTES_DEMO_CATALOG', '1')
    app.config.update(GET_CATALOG=None, DEMO_CATALOG=True)
    monkeypatch.setitem(sys.modules, 'guided_notes.notes.import_service', ModuleType('guided_notes.notes.import_service'))
    response = post(teacher, '/activities', import_id=IMPORT_ID, import_version=1)
    assert response.status_code == 503 and response.json['error'] == 'CATALOG_UNAVAILABLE'


def test_missing_display_fails_closed(app, teacher, monkeypatch):
    app.config['GET_DISPLAY_CONTENT'] = None
    name = 'guided_notes.notes.display_service'
    monkeypatch.setitem(sys.modules, name, ModuleType(name))
    response = post(teacher, '/activities', import_id=IMPORT_ID, import_version=1)
    assert response.status_code == 503 and response.json['error'] == 'DISPLAY_CONTENT_UNAVAILABLE'


def test_no_submission_fallback(app, teacher, activity, joined, monkeypatch):
    monkeypatch.setenv('GUIDED_NOTES_DEMO_CATALOG', '1')
    app.config['DEMO_CATALOG'] = True
    aid = activity['activity_id']
    assert post(teacher, f'/activities/{aid}/start').status_code == 200
    assert submit(joined[0], aid).status_code == 201
    app.config['ACCEPT_SUBMISSION'] = None
    response = post(joined[0], f'/activities/{aid}/submissions', question_id='q1',
                    items=[dict(item_id='i1-1', answer_text='test')])
    assert response.status_code == 503 and response.json['error'] == 'QUIZ_UNAVAILABLE'


def test_course_missing_display_provider(classroom_app, classroom_teacher, classroom_setup, monkeypatch):
    course, room = classroom_setup
    classroom_app.config['GET_COURSE_DISPLAY_CONTENT'] = None
    name = 'guided_notes.notes.course_catalogs'
    monkeypatch.setitem(sys.modules, name, ModuleType(name))
    response = post(classroom_teacher, f"/teacher/classrooms/{room['classroom_id']}/activities",
                    import_id=course_import_id(course['course_id']), import_version=1)
    assert response.status_code == 503 and response.json['error'] == 'DISPLAY_CONTENT_UNAVAILABLE'
