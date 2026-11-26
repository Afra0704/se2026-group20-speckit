import pytest
from google_support import google_app, google_teacher, post, start, complete, connect
from guided_notes.db import connection


def test_separate_connect_and_same_account(google_app,google_teacher):
    assert google_teacher.get('/teacher/google/sheets/status').json=={'status':'not_connected'}
    google_app.config['GOOGLE_PROVIDER'].subject='B'
    assert 'GOOGLE_ACCOUNT_MISMATCH' in complete(google_teacher,start(google_teacher,'sheets')).location
    assert google_teacher.get('/teacher/session').json['teacher']['display_name']=='Teacher A'
    google_app.config['GOOGLE_PROVIDER'].subject='A';connect(google_teacher)
    assert google_teacher.get('/teacher/google/sheets/status').json=={'status':'connected'}
    with google_app.app_context():
        row=connection().execute('SELECT * FROM google_sheets_credentials').fetchone()
        assert b'synthetic-access' not in row['secret_blob'] and b'synthetic-refresh' not in row['secret_blob']


@pytest.mark.parametrize('problem,code',[('scope','SHEETS_SCOPE_REQUIRED'),('refresh','SHEETS_REAUTH_REQUIRED')])
def test_missing_grants_fail_closed(google_app,google_teacher,problem,code):
    fake=google_app.config['GOOGLE_PROVIDER']
    if problem=='scope': fake.scopes=['openid','email','profile']
    else: fake.refresh_token=None
    assert code in complete(google_teacher,start(google_teacher,'sheets')).location
    assert google_teacher.get('/teacher/google/sheets/status').json['status']=='not_connected'


def test_cancel_and_bad_scope_preserve_connection(google_app,google_teacher):
    connect(google_teacher)
    fake=google_app.config['GOOGLE_PROVIDER'];fake.scopes=[]
    assert 'SHEETS_SCOPE_REQUIRED' in complete(google_teacher,start(google_teacher,'sheets')).location
    assert google_teacher.get('/teacher/google/sheets/status').json['status']=='connected'


def test_connect_requires_csrf_and_teacher(google_app,google_teacher):
    assert google_teacher.post('/teacher/google/sheets/connect').status_code==403
    anonymous=google_app.test_client()
    assert post(anonymous,'/teacher/google/sheets/connect').status_code==401
    assert anonymous.get('/teacher/google/sheets/status').status_code==401
