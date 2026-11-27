"""Formal classroom export fixtures; temporary DB and recorded Sheets only."""
from conftest import post
from test_classroom_notes_integration import prepare_real_course
import pytest


@pytest.fixture
def result_teacher(classroom_app):
    from guided_notes.workspace.routes import workspace
    from guided_notes.workspace.repository import initialize
    with classroom_app.app_context():
        initialize()
    classroom_app.register_blueprint(workspace)
    @classroom_app.context_processor
    def test_identity():
        return {'google_session': {'teacher': {'display_name': '測試教師'}}, 'sheets_reconnect_required': lambda code: False}
    client = classroom_app.test_client()
    assert post(client, '/teacher/session', username='teacher', password='test-password').status_code == 204
    return client


def export_room(app, teacher, *, number='42', no_winner=False):
    cid, catalog, room = prepare_real_course(app, teacher)
    student = app.test_client()
    group = post(student, '/classroom-memberships', code=room['code'], group_name=number).json
    path = f"/teacher/classrooms/{room['classroom_id']}/activities"
    aid = post(teacher, path, title='同名活動', import_id=catalog['import_id'], import_version=1).json['activity_id']
    assert post(teacher, f'{path}/{aid}/finish').status_code == 200
    snapshot = {'contract_version': 1, 'activity_id': aid, 'import_id': catalog['import_id'],
                'import_version': 1, 'result_version': aid, 'ended': True, 'units': [
                    {'question_id': q['question_id'], 'winner_group_id': None if no_winner else str(group['group_id']),
                     'no_winner': no_winner, 'answers': [] if no_winner else [
                         {'item_id': i['item_id'], 'blank_id': i['blank_id'], 'answer_text': f'答案 {number}'}
                         for i in q['items']]} for q in catalog['questions']]}
    snapshots = app.config.setdefault('RESULT_WRITEBACK_SNAPSHOTS', {})
    snapshots[aid] = snapshot
    app.config['GET_SETTLED_RESULTS'] = lambda db, value: {'snapshot': snapshots[value], 'results': []} if value in snapshots else None
    return cid, room, aid, group, snapshot
