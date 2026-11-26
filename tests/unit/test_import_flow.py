import time
import pytest
from google_support import google_app,google_teacher,post
from workspace_support import flow,Sheets,path
from guided_notes.db import connection
from guided_notes.notes.sheets_gateway import GatewayError


def test_failed_read_retries_original_input(google_app,google_teacher,flow):
    sheet=google_app.config['NOTES_GATEWAY']
    def error():raise GatewayError('SOURCE_READ_UNAVAILABLE')
    sheet.hook=error
    assert post(google_teacher,path(flow,'read')).status_code==503
    assert google_teacher.get(path(flow),headers={'Accept':'application/json'}).json['retryable']
    sheet.hook=None
    assert post(google_teacher,path(flow,'retry')).status_code==200
    assert google_teacher.get(path(flow),headers={'Accept':'application/json'}).json['status']=='worksheets_ready'


def test_old_preview_cannot_publish_after_revision(google_app,google_teacher,flow):
    post(google_teacher,path(flow,'read'))
    preview=post(google_teacher,path(flow,'previews'),choice_revision=1,sheet_id=7,name_mode='source').json
    state=google_teacher.get(path(flow),headers={'Accept':'application/json'}).json
    assert post(google_teacher,path(flow,'revise'),expected_revision=state['revision']-1).status_code==409
    assert post(google_teacher,path(flow,'revise'),expected_revision=state['revision']).status_code==200
    assert post(google_teacher,path(flow,'confirm'),confirm=True,preview_id=preview['preview_id']).status_code==409
    assert post(google_teacher,path(flow,'previews'),choice_revision=1,sheet_id=7,name_mode='source').status_code==409


def test_cancel_commits_preview_invalidation(google_app,google_teacher,flow):
    post(google_teacher,path(flow,'read'))
    pid=post(google_teacher,path(flow,'previews'),choice_revision=1,sheet_id=7,name_mode='source').json['preview_id']
    assert post(google_teacher,path(flow,'cancel')).status_code==200
    with google_app.app_context():assert connection().execute('SELECT status FROM notes_import_previews WHERE preview_id=?',(pid,)).fetchone()[0]=='invalidated'
    assert post(google_teacher,f'/teacher/notes/import-previews/{pid}/confirm',confirm=True).status_code==409
