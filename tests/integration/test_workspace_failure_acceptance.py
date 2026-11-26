"""HTTP-level abnormal acceptance with synthetic accounts and throwaway databases."""
import copy
import json
import pytest
from google_support import google_app,google_teacher,post,login
from workspace_support import flow,path,published,Sheets
from guided_notes.db import connection
from guided_notes.notes.sheets_gateway import GatewayError


@pytest.mark.parametrize('url',[None,'','http://docs.google.com/spreadsheets/d/test/edit','https://evil.example/spreadsheets/d/test/edit','https://docs.google.com/spreadsheets/d/test/edit?gid=1#gid=2','https://docs.google.com/spreadsheets/d/test/edit?gid=x'])
def test_bad_link_creates_no_half_flow(google_app,google_teacher,url):
    cid=post(google_teacher,'/teacher/courses',title='連結異常').json['course_id']
    result=post(google_teacher,f'/teacher/workspace/courses/{cid}/imports',source_kind='link',spreadsheet_url=url)
    assert result.status_code==400,result.text
    with google_app.app_context():assert connection().execute('SELECT count(*) FROM workspace_import_flows').fetchone()[0]==0


@pytest.mark.parametrize('code,status',[('SOURCE_READ_FORBIDDEN',403),('SOURCE_NOT_FOUND',404),('SOURCE_READ_UNAVAILABLE',503)])
def test_read_failure_keeps_teacher_and_never_publishes(google_app,google_teacher,flow,code,status):
    def unavailable():raise GatewayError(code,http_status=status)
    google_app.config['NOTES_GATEWAY'].hook=unavailable
    result=post(google_teacher,path(flow,'read'))
    assert result.status_code==status and result.json['error']['code']==code
    assert google_teacher.get('/teacher/session').json['authenticated']
    with google_app.app_context():
        db=connection()
        assert db.execute('SELECT count(*) FROM notes_imports').fetchone()[0]==0
        assert db.execute('SELECT count(*) FROM notes_import_previews').fetchone()[0]==0
    google_app.config['NOTES_GATEWAY'].hook=None
    assert post(google_teacher,path(flow,'retry')).status_code==200


def test_completed_import_cannot_reopen_after_sheets_authorization_lost(google_app,google_teacher,flow):
    catalog,pid=published(google_teacher,flow)
    google_app.config.pop('NOTES_GATEWAY')
    result=post(google_teacher,path(flow,'read'))
    assert result.status_code==409,result.text
    with google_app.app_context():
        row=connection().execute('SELECT status,confirmed_import_id FROM workspace_import_flows WHERE flow_id=?',(flow,)).fetchone()
        assert tuple(row)==('completed',catalog['import_id'])


def test_missing_sheets_authorization_preserves_intent(google_app,google_teacher,flow):
    google_app.config.pop('NOTES_GATEWAY')
    result=post(google_teacher,path(flow,'read'))
    assert result.status_code==202 and result.json['needs_authorization']=='sheets'
    assert result.json['flow_id']==flow
    with google_app.app_context():
        row=connection().execute('SELECT spreadsheet_id,source_kind,course_id FROM workspace_import_flows WHERE flow_id=?',(flow,)).fetchone()
        assert row['spreadsheet_id']=='synthetic' and row['source_kind']=='link' and row['course_id']


def test_cancel_old_page_and_wrong_course_cannot_publish(google_app,google_teacher,flow):
    post(google_teacher,path(flow,'read'))
    pid=post(google_teacher,path(flow,'previews'),choice_revision=1,sheet_id=7,name_mode='source').json['preview_id']
    assert post(google_teacher,path(flow,'cancel')).status_code==200
    assert post(google_teacher,path(flow,'confirm'),confirm=True,preview_id=pid).status_code==409
    assert post(google_teacher,f'/teacher/notes/import-previews/{pid}/confirm',confirm=True).status_code==409
    with google_app.app_context():assert connection().execute('SELECT count(*) FROM notes_catalogs').fetchone()[0]==0


def test_confirm_after_source_changed_requires_new_preview(google_app,google_teacher,flow):
    post(google_teacher,path(flow,'read'))
    pid=post(google_teacher,path(flow,'previews'),choice_revision=1,sheet_id=7,name_mode='source').json['preview_id']
    # A harmless source cell change still invalidates the observed preview fingerprint.
    layout=google_app.config['NOTES_GATEWAY'].layout
    from guided_notes.notes.recognition import recognize
    anchor=recognize(layout).questions[0].items[0].answer_range.anchor
    block=layout['data'][0]
    row_index=anchor[0]-block.get('startRow',0)
    col_index=anchor[1]-block.get('startColumn',0)
    cells=block['rowData'][row_index].setdefault('values',[])
    while len(cells)<=col_index:cells.append({})
    cells[col_index]['userEnteredValue']={'stringValue':'來源外部修改'}
    result=post(google_teacher,path(flow,'confirm'),confirm=True,preview_id=pid)
    assert result.status_code==409 and result.json['error']['code']=='SOURCE_CHANGED',result.text
    current=google_teacher.get(path(flow),headers={'Accept':'application/json'}).json
    assert current['preview_id']!=pid
    assert post(google_teacher,path(flow,'confirm'),confirm=True,preview_id=pid).status_code==409
    assert post(google_teacher,path(flow,'confirm'),confirm=True,preview_id=current['preview_id']).status_code==200
