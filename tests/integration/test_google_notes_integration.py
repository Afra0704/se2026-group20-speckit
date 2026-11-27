import copy
import json
from pathlib import Path

import pytest
from google_support import google_app,google_teacher,login,post,connect
from guided_notes.db import connection
from quiz_support import submit

URL='https://docs.google.com/spreadsheets/d/synthetic/edit#gid=7'


@pytest.mark.parametrize('layout_name,omit_last',[('single',False),('mixed',False),('moved',False),('mixed',True)])
def test_google_mode_import_to_student_frozen_full_text(google_app,google_teacher,monkeypatch,layout_name,omit_last):
    from guided_notes.notes import routes
    # Exercise the credential service even though external Sheets is synthetic.
    connect(google_teacher)
    layouts=json.loads((Path(__file__).parents[1]/'fixtures/sheets_layouts.json').read_text(encoding='utf-8'))
    from writeback_support import WritableSheets
    from test_export_routes import confirm_export
    fake=WritableSheets();fake.sheet=copy.deepcopy(layouts[layout_name]);snapshots=[]
    def gateway(snapshot):
        assert snapshot.valid and not hasattr(snapshot,'refresh_token');snapshots.append(snapshot);return object()
    monkeypatch.setattr(routes,'build_google_service',gateway)
    monkeypatch.setattr(routes,'SheetsGateway',lambda service:fake)
    monkeypatch.setattr(routes,'authorize',lambda *a,**k:pytest.fail('Desktop fallback forbidden'))
    google_app.config.update(NOTES_GOOGLE_TOKEN='poison-token',NOTES_GOOGLE_TEACHER_ID=1)
    course=post(google_teacher,'/teacher/courses',title='A course').json
    course_id=course['course_id']
    room=post(google_teacher,f'/teacher/courses/{course_id}/classrooms',title='A room').json
    response=post(google_teacher,'/teacher/notes/worksheets',spreadsheet_url=URL,course_id=course_id)
    assert response.status_code==200,response.json
    preview=post(google_teacher,'/teacher/notes/import-previews',spreadsheet_url=URL,sheet_id=7,course_id=course_id)
    assert preview.status_code==201,preview.json
    preview_url=preview.json['preview_url']
    catalog=post(google_teacher,preview_url+'/confirm',confirm=True).json
    activity=post(google_teacher,f"/teacher/classrooms/{room['classroom_id']}/activities",import_id=catalog['import_id'],import_version=1,title='Lecture')
    assert activity.status_code==201,activity.json
    student=google_app.test_client()
    joined=post(student,'/classroom-memberships',code=room['code'],group_name='1')
    assert joined.status_code==201,joined.json
    state=student.get(f"/classrooms/{room['classroom_id']}/state").json['activity']
    assert state['phase']=='PREPARING' and state['question_text_status']=='complete'
    assert all(item['prompt_text'] for question in state['questions'] for item in question['items'])
    assert all('answer_range' not in item for question in state['questions'] for item in question['items'])
    assert snapshots and fake.calls
    b=login(google_app.test_client(),google_app,'B')
    assert b.get(f'/teacher/courses/{course_id}/catalogs').status_code in (403,404)
    assert b.get(preview_url,headers={'Accept':'application/json'}).status_code in (403,404)
    aid=activity.json['activity_id']
    activity_path=f"/teacher/classrooms/{room['classroom_id']}/activities/{aid}"
    assert post(b,activity_path+'/start').status_code in (403,404)
    assert post(google_teacher,activity_path+'/start').status_code==200
    answered=catalog['questions'][:-1] if omit_last else catalog['questions']
    for question in answered:
        response=submit(student,aid,question_id=question['question_id'],items=[
            {'item_id':item['item_id'],'answer_text':'  =001\n文字  '} for item in question['items']])
        assert response.status_code==201,response.json
    assert post(google_teacher,activity_path+'/finish').status_code==200
    with google_app.app_context():
        from guided_notes.notes.models import validate_snapshot
        from guided_notes.quiz.settlement import settled
        validate_snapshot(settled(connection(), aid)['snapshot'], catalog, activity_id=aid)
    export=post(google_teacher,'/teacher/notes/export-previews',activity_id=aid)
    assert export.status_code==201,export.json
    if layout_name=='mixed' and not omit_last:fake.fail_at=2
    overwrite=[item['item_id'] for item in export.json['items'] if item['action']=='requires_overwrite_confirmation']
    report=confirm_export(google_teacher,export.json['preview_id'],overwrite=overwrite).json
    if layout_name=='mixed' and not omit_last:
        assert report['counts']['verified']==2 and report['counts']['failed']==1
        recovery=post(google_teacher,f"/teacher/notes/operations/{report['operation_id']}/recovery-preview")
        assert recovery.status_code==201,recovery.json
        report=confirm_export(google_teacher,recovery.json['preview_id'],key='recover').json
        assert [len(batch) for batch in fake.writes]==[2,1,1]
    assert 'status' in report,report
    winners={str(joined.json['group_id'])}
    if omit_last:
        winners.add(None)
        assert report['counts']['skipped']==len(catalog['questions'][-1]['items'])
        assert sum(map(len,fake.writes))==sum(len(question['items']) for question in answered)
    assert report['status']=='completed' and {unit['winner_group_id'] for unit in report['units']}==winners
    assert all(write.text=='  =001\n文字  ' for batch in fake.writes for write in batch)
    assert b.get(f"/teacher/notes/operations/{report['operation_id']}").status_code==404
    # Logout in the same browser must preserve a real classroom membership.
    login(student,google_app,'A')
    assert post(student,'/teacher/session/logout').status_code==204
    assert student.get(f"/classrooms/{room['classroom_id']}/state").status_code==200


def test_no_profile_fallback_even_reused_teacher_number(google_app,google_teacher,monkeypatch):
    from guided_notes.notes import routes
    google_app.config.update(NOTES_GOOGLE_TOKEN='poison-token',NOTES_GOOGLE_CLIENT_SECRETS='poison-client',NOTES_GOOGLE_TEACHER_ID=1)
    monkeypatch.setattr(routes,'authorize',lambda *a,**k:pytest.fail('Desktop fallback forbidden'))
    response=post(google_teacher,'/teacher/notes/worksheets',spreadsheet_url=URL)
    assert response.status_code==409 and response.json['error']['code']=='SHEETS_CONNECT_REQUIRED'
