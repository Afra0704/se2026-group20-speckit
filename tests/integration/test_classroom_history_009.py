"""Student closure cannot fake a result or start a source write."""
from test_classroom_notes_integration import prepare_real_course
from conftest import post


def test_unknown_export_history_survives_upgrade_close_and_cross_teacher_reuse(classroom_app, classroom_teacher, monkeypatch):
    from guided_notes import create_app
    from guided_notes.activities import classroom_routes
    from classroom_009_support import rows, downgrade_classrooms
    from test_export_routes import confirm_export
    cid, catalog, room = prepare_real_course(classroom_app, classroom_teacher)
    rid = room['classroom_id']
    students = [classroom_app.test_client() for _ in range(2)]
    groups = [post(s, '/classroom-memberships', code=room['code'], group_name=name).json for s, name in zip(students, ('A', 'B'))]
    aid = post(classroom_teacher, f'/teacher/classrooms/{rid}/activities', import_id=catalog['import_id'], import_version=1).json['activity_id']
    post(classroom_teacher, f'/teacher/classrooms/{rid}/activities/{aid}/finish')
    snapshot = {'contract_version':1,'activity_id':aid,'import_id':catalog['import_id'],'import_version':1,
                'result_version':'009-controlled','ended':True,'units':[
                    {'question_id':q['question_id'],'winner_group_id':str(groups[0]['group_id']),'no_winner':False,
                     'answers':[{'item_id':i['item_id'],'blank_id':i['blank_id'],'answer_text':'saved'} for i in q['items']]}
                    for q in catalog['questions']]}
    classroom_app.config['GET_SETTLED_RESULTS'] = lambda db, requested: {'snapshot':snapshot,'results':[]} if requested==aid else None
    preview = post(classroom_teacher, '/teacher/notes/export-previews', activity_id=aid).json
    gateway = classroom_app.config['NOTES_GATEWAY']
    gateway.write_hook = lambda: setattr(gateway, 'readback_error', True)
    report = confirm_export(classroom_teacher, preview['preview_id']).json
    assert report['status'] == 'needs_attention' and report['counts']['unknown'] == 2
    target = classroom_app.config['DATABASE']
    before = rows(target)
    downgrade_classrooms(target)
    create_app(dict(classroom_app.config))
    assert rows(target) == before
    assert post(classroom_teacher, f'/teacher/classrooms/{rid}/close', confirm=True).status_code == 200
    other = classroom_app.test_client()
    post(other, '/teacher/session', username='other', password='test-password')
    new_course = post(other, '/teacher/courses', title='other').json['course_id']
    monkeypatch.setattr(classroom_routes, 'make_room_code', lambda: room['code'])
    new = post(other, f'/teacher/courses/{new_course}/classrooms', title='new')
    assert new.status_code == 201
    assert classroom_teacher.get(f"/teacher/notes/operations/{report['operation_id']}", headers={'Accept':'application/json'}).json == report
    assert len(gateway.writes) == 1
    for student in students:
        assert student.get(f'/activities/{aid}/results').status_code == 409
        assert student.get(f"/classrooms/{new.json['classroom_id']}/state").status_code == 403


def test_pending_history_is_preserved_without_automatic_writeback(classroom_app, classroom_teacher):
    _, catalog, room = prepare_real_course(classroom_app, classroom_teacher)
    rid = room['classroom_id']
    student = classroom_app.test_client()
    post(student, '/classroom-memberships', code=room['code'], group_name='A')
    aid = post(classroom_teacher, f'/teacher/classrooms/{rid}/activities', import_id=catalog['import_id'], import_version=1).json['activity_id']
    post(classroom_teacher, f'/teacher/classrooms/{rid}/close', confirm=True)
    assert classroom_teacher.get(f'/teacher/classrooms/{rid}/activities').json['activities'][0]['activity_id'] == aid
    pending = post(classroom_teacher, '/teacher/notes/export-previews', activity_id=aid)
    assert pending.status_code == 409 and pending.json['error']['code'] == 'RESULT_NOT_READY'
    assert classroom_app.config['NOTES_GATEWAY'].writes == []
    student.delete_cookie('session')
    assert post(student, f'/classrooms/{rid}/result-access').status_code == 409
