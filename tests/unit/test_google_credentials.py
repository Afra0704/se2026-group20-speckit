import json
import time
import pytest
from cryptography.fernet import Fernet
from google_support import google_app,google_teacher,connect,start,complete,login
from guided_notes.auth import TeacherContext
from guided_notes.db import connection
from guided_notes.google_login import crypto,sheets_service
from guided_notes.google_login.provider import SHEETS_SCOPE
from guided_notes.http import ApiError


def expire(app):
    with app.app_context():
        db=connection();row=dict(db.execute('SELECT * FROM google_sheets_credentials WHERE teacher_id=1').fetchone())
        secret=crypto.decrypt(row['secret_blob'],sheets_service.binding(row))
        row['expires_at']=time.time()-1;secret['expires_at']=row['expires_at']
        db.execute('UPDATE google_sheets_credentials SET expires_at=?,secret_blob=? WHERE teacher_id=1',
                   (row['expires_at'],crypto.encrypt(secret,sheets_service.binding(row))))


def row(app):
    with app.app_context():return dict(connection().execute('SELECT * FROM google_sheets_credentials WHERE teacher_id=1').fetchone())


def test_envelope_purpose_owner_and_bad_key(google_app):
    with google_app.app_context():
        secret=crypto.encrypt({'access_token':'sentinel'},{'owner':'A'})
        assert b'sentinel' not in secret
        assert crypto.decrypt(secret,{'owner':'A'})['access_token']=='sentinel'
        with pytest.raises(ApiError):crypto.decrypt(secret,{'owner':'B'})
        with pytest.raises(ApiError):crypto.decrypt(secret[:30]+b'XXXXX'+secret[35:],{'owner':'A'})
        google_app.config['GOOGLE_TOKEN_KEY_FILE']=None
        with pytest.raises(ApiError):crypto.decrypt(secret,{'owner':'A'})


def test_success_refresh_and_missing_refresh_preservation(google_app,google_teacher):
    connect(google_teacher)
    google_app.config['GOOGLE_PROVIDER'].refresh_token=None
    connect(google_teacher)
    expire(google_app);before=row(google_app)
    assert google_teacher.get('/test-google-credentials').json=={'valid':True}
    after=row(google_app)
    assert after['revision']==before['revision']+1 and after['refresh_lease_id'] is None
    assert sum(call[0]=='refresh' for call in google_app.config['GOOGLE_PROVIDER'].calls)==1


@pytest.mark.parametrize('kind',['timeout','late','late_invalid','clock_lease','lease_expired','invalid_grant','wrong_identity','scope'])
def test_refresh_failures_do_not_misclassify(google_app,google_teacher,kind,monkeypatch):
    connect(google_teacher);expire(google_app)
    before=row(google_app)
    def failed(secret,client,budget):
        if kind=='timeout':raise ApiError(503,'GOOGLE_REFRESH_TIMEOUT',retry_after=1)
        if kind=='late':budget.deadline=0
        if kind=='late_invalid':
            budget.deadline=0
            raise ApiError(409,'GOOGLE_REAUTH_REQUIRED')
        if kind=='clock_lease':
            now=time.time()+31
            monkeypatch.setattr(time,'time',lambda:now)
        if kind=='lease_expired':
            connection().execute('UPDATE google_sheets_credentials SET lease_until=0')
        if kind=='invalid_grant':raise ApiError(409,'GOOGLE_REAUTH_REQUIRED')
        result={'access_token':'new','expires_in':3600}
        if kind=='wrong_identity':result['_identity']={'issuer':'https://accounts.google.com','subject':'B'}
        if kind=='scope':result['scope']='openid'
        return result
    google_app.config['GOOGLE_PROVIDER'].refresh_hook=failed
    response=google_teacher.get('/test-google-credentials')
    assert response.status_code in (409,503)
    after=row(google_app)
    assert after['refresh_lease_id'] is None
    if kind in ('invalid_grant','scope'):
        assert after['status']=='reauth_required' and after['secret_blob'] is None
    else:
        assert after['secret_blob']==before['secret_blob'] and after['revision']==before['revision']
    if kind in ('timeout','late','late_invalid','clock_lease','lease_expired'):
        assert response.json['error']=='GOOGLE_REFRESH_TIMEOUT' and response.headers['Retry-After']=='1'
    assert google_teacher.get('/teacher/session').json['authenticated']


def test_busy_and_corrupt_binding_fail_closed(google_app,google_teacher):
    connect(google_teacher);expire(google_app)
    with google_app.app_context():connection().execute('UPDATE google_sheets_credentials SET refresh_lease_id=?,lease_until=?',('other',time.time()+30))
    response=google_teacher.get('/test-google-credentials')
    assert response.json['error']=='GOOGLE_REFRESH_BUSY' and response.headers['Retry-After']=='1'
    with google_app.app_context():connection().execute("UPDATE google_sheets_credentials SET client_id='wrong'")
    assert google_teacher.get('/teacher/google/sheets/status').json['status']=='unavailable'


def test_old_refresh_cannot_overwrite_reconnect(google_app,google_teacher):
    connect(google_teacher);expire(google_app)
    before=row(google_app)
    def replaced(secret,client,budget):
        connection().execute("UPDATE google_sheets_credentials SET credential_id='replacement',revision=revision+1,refresh_lease_id=NULL,lease_until=NULL")
        raise ApiError(409,'GOOGLE_REAUTH_REQUIRED')
    google_app.config['GOOGLE_PROVIDER'].refresh_hook=replaced
    assert google_teacher.get('/test-google-credentials').status_code==503
    after=row(google_app)
    assert after['credential_id']=='replacement' and after['status']=='connected' and after['secret_blob']==before['secret_blob']


def test_real_reconnect_wins_over_late_refresh(google_app,google_teacher):
    connect(google_teacher);expire(google_app)
    before=row(google_app)
    other=google_app.test_client();other.set_cookie('session',google_teacher.get_cookie('session').value)
    def reconnected(secret,client,budget):
        connect(other)
        return {'access_token':'stale-result','expires_in':3600}
    google_app.config['GOOGLE_PROVIDER'].refresh_hook=reconnected
    response=google_teacher.get('/test-google-credentials')
    assert response.status_code==503 and response.json['error']=='GOOGLE_REFRESH_BUSY'
    after=row(google_app)
    assert after['credential_id']!=before['credential_id'] and after['refresh_lease_id'] is None
    assert google_teacher.get('/teacher/google/sheets/status').json['status']=='connected'


@pytest.mark.parametrize('change',['key','instance','subject','revision'])
def test_moved_or_modified_ciphertext_is_not_usable(google_app,google_teacher,tmp_path,change):
    connect(google_teacher)
    with google_app.app_context():
        if change=='key':
            key=tmp_path/'wrong-key';key.write_bytes(Fernet.generate_key());google_app.config['GOOGLE_TOKEN_KEY_FILE']=str(key)
        elif change=='instance':connection().execute("UPDATE auth_instance SET instance_uuid='new-database'")
        elif change=='subject':connection().execute("UPDATE google_sheets_credentials SET subject='B'")
        else:connection().execute('UPDATE google_sheets_credentials SET revision=revision+1')
    assert google_teacher.get('/teacher/google/sheets/status').json['status']=='unavailable'
    assert google_teacher.get('/test-google-credentials').status_code==503


def test_copied_ciphertext_into_new_db_with_same_teacher_number(google_app,google_teacher,tmp_path):
    from guided_notes import create_app
    connect(google_teacher);old=row(google_app)
    second=create_app({**google_app.config,'DATABASE':str(tmp_path/'second-instance.sqlite3')})
    b=login(second.test_client(),second)
    with second.app_context():
        columns=list(old)
        connection().execute('INSERT INTO google_sheets_credentials('+','.join(columns)+') VALUES('+','.join('?' for _ in columns)+')',tuple(old.values()))
    assert b.get('/teacher/google/sheets/status').json['status']=='unavailable'


def test_notes_retry_envelope_retains_retry_after(google_app,google_teacher):
    from google_support import post
    connect(google_teacher);expire(google_app)
    def timeout(*args):raise ApiError(503,'GOOGLE_REFRESH_TIMEOUT',retry_after=1)
    google_app.config['GOOGLE_PROVIDER'].refresh_hook=timeout
    response=post(google_teacher,'/teacher/notes/worksheets',spreadsheet_url='https://docs.google.com/spreadsheets/d/synthetic/edit')
    assert response.status_code==503 and response.headers['Retry-After']=='1'
    assert response.json['error']['code']=='GOOGLE_REFRESH_TIMEOUT' and response.json['error']['retryable']
