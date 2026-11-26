from pathlib import Path
import json
import time
import pytest
from google_support import google_app,google_teacher,post,complete
from urllib.parse import urlsplit,parse_qs
from guided_notes.db import connection
from guided_notes.google_login.picker_service import SCOPES
from guided_notes.google_login.provider import ISSUER


def configure(app,tmp_path):
    web=json.loads(Path(app.config['GOOGLE_WEB_CLIENT_SECRETS']).read_text())
    web['web']['client_id']='synthetic-picker-client'
    path=tmp_path/'picker.json';path.write_text(json.dumps(web))
    app.config.update(GOOGLE_PICKER_CLIENT_SECRETS=str(path),PICKER_API_KEY='synthetic-restricted-browser-key',PICKER_APP_ID='123456')
    return app.config['GOOGLE_PROVIDER']


def cloud(client):
    cid=post(client,'/teacher/courses',title='Cloud').json['course_id']
    row=post(client,f'/teacher/workspace/courses/{cid}/imports',source_kind='cloud').json
    return row['flow_id']


def url(fid,action):return '/teacher/workspace/imports/'+fid+'/'+action


def auth(client,app,fid):
    response=post(client,url(fid,'authorize'),credential_kind='picker')
    assert response.status_code==200,response.text
    state=parse_qs(urlsplit(response.json['authorization_url']).query)['state'][0]
    return complete(client,state)


def test_narrow_picker_and_original_credentials(google_app,google_teacher,tmp_path):
    fake=configure(google_app,tmp_path);fid=cloud(google_teacher)
    fake.scopes=sorted(SCOPES)
    assert auth(google_teacher,google_app,fid).location.endswith(fid)
    token=post(google_teacher,url(fid,'picker/token'))
    assert token.status_code==200,token.text
    assert 'synthetic-access'==token.json['access_token']
    assert token.headers['Referrer-Policy']=='no-referrer'
    with google_app.app_context():
        row=connection().execute('SELECT * FROM google_picker_credentials').fetchone()
        assert b'synthetic-access' not in row['secret_blob']
        assert connection().execute('SELECT count(*) FROM google_sheets_credentials').fetchone()[0]==0
        assert json.loads(row['actual_scopes'])==sorted(SCOPES)
    page=google_teacher.get('/teacher/workspace/imports/'+fid)
    assert page.status_code==200
    assert page.headers['Referrer-Policy']=='strict-origin-when-cross-origin'
    assert 'synthetic-access' not in page.text
    before=len(fake.calls)
    assert post(google_teacher,url(fid,'authorize'),credential_kind='picker').status_code==200
    assert len(fake.calls)==before


@pytest.mark.parametrize('scopes,subject,code',[(SCOPES|{'https://www.googleapis.com/auth/spreadsheets'},'A','PICKER_SCOPE_UNSAFE'),(SCOPES-{'profile'},'A','PICKER_SCOPE_REQUIRED'),(SCOPES,'B','GOOGLE_ACCOUNT_MISMATCH')])
def test_invalid_picker_preserves_teacher(google_app,google_teacher,tmp_path,scopes,subject,code):
    fake=configure(google_app,tmp_path);fid=cloud(google_teacher)
    fake.scopes=sorted(scopes);fake.subject=subject
    response=auth(google_teacher,google_app,fid)
    assert response.status_code==303
    assert google_teacher.get('/teacher/session').json['teacher']['display_name']=='Teacher A'
    with google_app.app_context():assert connection().execute('SELECT count(*) FROM google_picker_credentials').fetchone()[0]==0


def test_missing_picker_only_blocks_cloud(google_app,google_teacher):
    fid=cloud(google_teacher)
    response=post(google_teacher,url(fid,'authorize'),credential_kind='picker')
    assert response.status_code==503
    assert google_teacher.get('/teacher/workspace').status_code==200


def test_actual_picker_authorization_url_uses_dedicated_profile(google_app,google_teacher,tmp_path):
    from guided_notes.google_login.provider import GoogleProvider
    from flask import session
    fake=configure(google_app,tmp_path);fid=cloud(google_teacher)
    post(google_teacher,url(fid,'authorize'),credential_kind='picker')
    attempt=fake.calls[-1][1]
    with google_teacher.session_transaction() as current:saved=dict(current)
    with google_app.test_request_context('/'):
        session.update(saved)
        query=parse_qs(urlsplit(GoogleProvider().authorization_request(attempt)).query)
    assert query['client_id']==['synthetic-picker-client']
    assert query['include_granted_scopes']==['false']
    assert query['access_type']==['online']
    assert 'prompt' not in query
    assert set(query['scope'][0].split())==SCOPES
    assert query['code_challenge_method']==['S256']


def test_picker_credential_tampering_and_csrf_rejected(google_app,google_teacher,tmp_path):
    fake=configure(google_app,tmp_path);fid=cloud(google_teacher);fake.scopes=sorted(SCOPES)
    auth(google_teacher,google_app,fid)
    assert google_teacher.post(url(fid,'picker/token'),json={}).status_code==403
    with google_app.app_context():connection().execute('UPDATE google_picker_credentials SET revision=revision+1')
    assert post(google_teacher,url(fid,'picker/token')).status_code==503


def test_cloud_selection_uses_backend_metadata_and_preserves_sheets(google_app,google_teacher,tmp_path):
    from workspace_support import Sheets
    fake=configure(google_app,tmp_path);fid=cloud(google_teacher);fake.scopes=sorted(SCOPES)
    auth(google_teacher,google_app,fid)
    google_app.config.update(NOTES_GATEWAY=Sheets(),PICKER_METADATA=lambda file_id:{'id':file_id,'mimeType':'application/vnd.google-apps.spreadsheet','trashed':False,'capabilities':{'canEdit':False}})
    ticket=post(google_teacher,url(fid,'picker/token')).json['ticket_id']
    selected=post(google_teacher,url(fid,'picker/selection'),file_id='chosen',ticket_id=ticket)
    assert selected.status_code==200,selected.text
    assert selected.json['status']=='worksheets_ready'
    # Identical successful selection is idempotent; another file cannot reuse it.
    assert post(google_teacher,url(fid,'picker/selection'),file_id='chosen',ticket_id=ticket).status_code==200
    assert post(google_teacher,url(fid,'picker/selection'),file_id='other',ticket_id=ticket).status_code==409


def test_sidecar_cleanup_set_null_without_auto_resuming(google_app,google_teacher,tmp_path):
    from google_support import start
    fake=configure(google_app,tmp_path);fid=cloud(google_teacher)
    post(google_teacher,url(fid,'authorize'),credential_kind='picker')
    with google_app.app_context():
        db=connection();attempt=db.execute('SELECT oauth_attempt_id FROM workspace_import_flows WHERE flow_id=?',(fid,)).fetchone()[0]
        db.execute("UPDATE google_oauth_attempts SET expires_at=0,status='failed',secret_blob=NULL WHERE attempt_id=?",(attempt,))
    assert start(google_teacher,'sheets')
    with google_app.app_context():
        db=connection()
        assert db.execute('SELECT oauth_attempt_id FROM workspace_import_flows WHERE flow_id=?',(fid,)).fetchone()[0] is None
        assert db.execute('SELECT count(*) FROM google_oauth_attempt_context WHERE attempt_id=?',(attempt,)).fetchone()[0]==0
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
    before=len(fake.calls)
    assert google_teacher.get('/teacher/workspace/imports/'+fid).status_code==200
    assert len(fake.calls)==before


def test_picker_connect_does_not_rewrite_main_sheets_ciphertext(google_app,google_teacher,tmp_path):
    from google_support import connect
    connect(google_teacher)
    with google_app.app_context():before=bytes(connection().execute('SELECT secret_blob FROM google_sheets_credentials').fetchone()[0])
    fake=configure(google_app,tmp_path);fid=cloud(google_teacher);fake.scopes=sorted(SCOPES)
    auth(google_teacher,google_app,fid)
    with google_app.app_context():assert bytes(connection().execute('SELECT secret_blob FROM google_sheets_credentials').fetchone()[0])==before


@pytest.mark.parametrize('mime,trashed,code', [('text/plain',False,'SOURCE_NOT_GOOGLE_SHEETS'),('application/vnd.google-apps.spreadsheet',True,'SOURCE_TRASHED')])
def test_picker_source_metadata_not_trusted(google_app,google_teacher,tmp_path,mime,trashed,code):
    fake=configure(google_app,tmp_path);fid=cloud(google_teacher);fake.scopes=sorted(SCOPES)
    auth(google_teacher,google_app,fid)
    google_app.config['PICKER_METADATA']=lambda file_id:{'id':file_id,'mimeType':mime,'trashed':trashed}
    ticket=post(google_teacher,url(fid,'picker/token')).json['ticket_id']
    response=post(google_teacher,url(fid,'picker/selection'),file_id='chosen',ticket_id=ticket)
    assert response.status_code==400 and response.json['error']['code']==code
    with google_app.app_context():assert connection().execute('SELECT source_verified_at FROM workspace_import_flows WHERE flow_id=?',(fid,)).fetchone()[0] is None


def test_picker_expiring_cache_is_not_delivered(google_app,google_teacher,tmp_path):
    fake=configure(google_app,tmp_path);fid=cloud(google_teacher);fake.scopes=sorted(SCOPES)
    auth(google_teacher,google_app,fid)
    with google_app.app_context():connection().execute('UPDATE google_picker_credentials SET expires_at=?',(time.time()+59,))
    response=post(google_teacher,url(fid,'picker/token'))
    assert response.status_code==409 and response.json['error']['code']=='PICKER_REAUTH_REQUIRED'


def test_picker_reconnect_fences_selection_late_result(google_app,google_teacher,tmp_path):
    from guided_notes.google_login import picker_service
    from guided_notes.db import write_transaction
    fake=configure(google_app,tmp_path);fid=cloud(google_teacher);fake.scopes=sorted(SCOPES)
    auth(google_teacher,google_app,fid)
    ticket=post(google_teacher,url(fid,'picker/token')).json['ticket_id']
    def metadata(file_id):
        with write_transaction() as db:
            picker_service.connect(db,{'client_id':'synthetic-picker-client'}, {'identity':{'issuer':ISSUER,'subject':'A'},'token':{'access_token':'synthetic-new-generation','scope':sorted(SCOPES),'expires_in':3600}})
        return {'id':file_id,'mimeType':'application/vnd.google-apps.spreadsheet','trashed':False}
    google_app.config['PICKER_METADATA']=metadata
    response=post(google_teacher,url(fid,'picker/selection'),file_id='chosen',ticket_id=ticket)
    assert response.status_code==409
    with google_app.app_context():assert connection().execute('SELECT source_verified_at FROM workspace_import_flows WHERE flow_id=?',(fid,)).fetchone()[0] is None
