"""Narrow online-only Picker credentials. Never deliver the backend Sheets token."""
import json
import re
import secrets
import time
from uuid import uuid4
from pathlib import Path
from flask import current_app
from ..auth import require_teacher
from ..db import connection, write_transaction
from ..http import ApiError
from ..notes.repository import dumps
from ..workspace import import_flows as flows
from . import crypto, repository
from .provider import load_client, configuration as main_configuration, actual_scopes, LOGIN_SCOPES
from .sheets_service import expiry

DRIVE_FILE='https://www.googleapis.com/auth/drive.file'
SCOPES=set(LOGIN_SCOPES)|{DRIVE_FILE}
SHEETS_MIME='application/vnd.google-apps.spreadsheet'


def configuration():
    try:
        config=load_client(current_app.config.get('GOOGLE_PICKER_CLIENT_SECRETS'),current_app.config['GOOGLE_REDIRECT_URI'],Path(__file__).resolve().parents[3])
        key=current_app.config.get('PICKER_API_KEY')
        app_id=current_app.config.get('PICKER_APP_ID')
        if config['web']['client_id']==main_configuration()['web']['client_id'] or not isinstance(key,str) or len(key)<20 or 'replace' in key.lower() or not isinstance(app_id,str) or not re.fullmatch(r'[0-9]+',app_id):raise ValueError()
        return config
    except (ApiError,ValueError,TypeError):
        raise ApiError(503,'PICKER_NOT_CONFIGURED') from None


def binding(row):
    return {'purpose':'picker',**{k:row[k] for k in ('teacher_id','instance_uuid','issuer','subject','client_id','credential_id','revision','actual_scopes','expires_at')}}


def connect(db,attempt,result):
    teacher=require_teacher(db);identity=repository.identity(teacher.teacher_id,db)
    actual=actual_scopes(result['token'])
    if actual-SCOPES:raise ApiError(503,'PICKER_SCOPE_UNSAFE')
    if actual!=SCOPES:raise ApiError(403,'PICKER_SCOPE_REQUIRED')
    if result['identity']['issuer']!=identity['issuer'] or result['identity']['subject']!=identity['subject']:raise ApiError(409,'GOOGLE_ACCOUNT_MISMATCH')
    if attempt['client_id']!=configuration()['web']['client_id']:raise ApiError(400,'GOOGLE_FLOW_INVALID')
    access=result['token'].get('access_token')
    if not isinstance(access,str) or not access:raise ApiError(400,'GOOGLE_FLOW_INVALID')
    old=db.execute('SELECT revision FROM google_picker_credentials WHERE teacher_id=?',(teacher.teacher_id,)).fetchone()
    now=time.time()
    row=dict(teacher_id=teacher.teacher_id,instance_uuid=repository.instance_id(db),issuer=identity['issuer'],subject=identity['subject'],client_id=attempt['client_id'],credential_id=str(uuid4()),revision=old[0]+1 if old else 1,actual_scopes=dumps(sorted(actual)),expires_at=expiry(result['token']))
    row['secret_blob']=crypto.encrypt({'access_token':access,'scopes':sorted(actual),'expiry':row['expires_at']},binding(row))
    row.update(created_at=now,updated_at=now)
    columns=list(row)
    db.execute('INSERT INTO google_picker_credentials('+','.join(columns)+') VALUES('+','.join('?' for _ in columns)+') ON CONFLICT(teacher_id) DO UPDATE SET '+','.join(k+'=excluded.'+k for k in columns if k!='teacher_id'),tuple(row.values()))


def usable_cache(teacher, *, missing_ok=False, db=None):
    db=db or connection()
    if require_teacher(db)!=teacher:raise ApiError(403,'FORBIDDEN')
    row=db.execute('SELECT * FROM google_picker_credentials WHERE teacher_id=?',(teacher.teacher_id,)).fetchone()
    if row is None or row['expires_at']<=time.time()+60:
        if missing_ok:return None
        raise ApiError(409,'PICKER_REAUTH_REQUIRED')
    owner=repository.identity(teacher.teacher_id,db)
    if row['instance_uuid']!=repository.instance_id(db) or row['issuer']!=owner['issuer'] or row['subject']!=owner['subject'] or row['client_id']!=configuration()['web']['client_id']:raise ApiError(409,'GOOGLE_ACCOUNT_MISMATCH')
    scopes=set(json.loads(row['actual_scopes']))
    if scopes-SCOPES:raise ApiError(503,'PICKER_SCOPE_UNSAFE')
    if scopes!=SCOPES:raise ApiError(403,'PICKER_SCOPE_REQUIRED')
    secret=crypto.decrypt(row['secret_blob'],binding(row))
    if secret.get('scopes')!=sorted(scopes) or secret.get('expiry')!=row['expires_at'] or not isinstance(secret.get('access_token'),str):raise ApiError(503,'GOOGLE_CREDENTIALS_UNAVAILABLE')
    return dict(row),secret


def token(fid):
    flows.get(fid);configuration()
    with write_transaction() as db:
        row=flows.load(db,fid)
        if row['source_kind']!='cloud' or row['status']!='picking':raise ApiError(409,'FLOW_STEP_CONFLICT')
        cache,secret=usable_cache(require_teacher(db),db=db)
        ticket=secrets.token_urlsafe(24);now=time.time();end=min(now+300,row['expires_at'],cache['expires_at']-30)
        db.execute('INSERT INTO workspace_picker_tickets VALUES(?,?,?,?,?,NULL,?)',(ticket,fid,cache['credential_id'],cache['revision'],end,now))
    return {'ticket_id':ticket,'access_token':secret['access_token'],'expires_in':max(0,int(cache['expires_at']-now)),'ticket_expires_in':max(0,int(end-now)),'api_key':current_app.config['PICKER_API_KEY'],'app_id':current_app.config['PICKER_APP_ID']}


def metadata(secret,file_id):
    if current_app.testing and current_app.config.get('PICKER_METADATA'):
        return current_app.config['PICKER_METADATA'](file_id)
    # Dedicated non-refreshable credentials; official Drive client, fixed endpoint.
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from google_auth_httplib2 import AuthorizedHttp
    import httplib2
    from googleapiclient.errors import HttpError
    http=AuthorizedHttp(Credentials(secret['access_token']),http=httplib2.Http(timeout=10),max_refresh_attempts=0)
    try:
        service=build('drive','v3',http=http,cache_discovery=False,static_discovery=True)
        return service.files().get(fileId=file_id,fields='id,name,mimeType,trashed,capabilities(canEdit)').execute(num_retries=0)
    except HttpError as error:
        raise ApiError(403 if error.resp.status in (401,403,404) else 503,'SOURCE_READ_FORBIDDEN' if error.resp.status in (401,403,404) else 'SOURCE_READ_UNAVAILABLE') from None
    except (OSError,httplib2.HttpLib2Error):
        raise ApiError(503,'SOURCE_READ_UNAVAILABLE',retry_after=1) from None
    finally:
        http.close()


def select(fid,body,*,retry=False):
    if set(body)!={'file_id','ticket_id'} or not isinstance(body['file_id'],str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,256}',body['file_id']) or not isinstance(body['ticket_id'],str):raise ApiError(400,'INVALID_REQUEST')
    def validate_ticket(db,row,mark=False):
        ticket=db.execute('SELECT * FROM workspace_picker_tickets WHERE ticket_id=? AND flow_id=?',(body['ticket_id'],fid)).fetchone()
        cache,secret=usable_cache(require_teacher(db),db=db)
        if not ticket or ticket['expires_at']<=time.time() or ticket['credential_id']!=cache['credential_id'] or ticket['credential_revision']!=cache['revision']:raise ApiError(409,'FLOW_STEP_CONFLICT')
        if mark and ticket['used_at'] is not None and not retry:raise ApiError(409,'FLOW_STEP_CONFLICT')
        if mark:db.execute('UPDATE workspace_picker_tickets SET used_at=? WHERE ticket_id=?',(time.time(),body['ticket_id']))
        return cache,secret
    row,cid,done=flows.claim(fid,'selection',body,retry=retry,preclaim=lambda db,row:validate_ticket(db,row,True))
    if cid is None:return flows.safe(row),200
    try:
        cache,secret=validate_ticket(connection(),row)
        info=metadata(secret,body['file_id'])
        if info.get('id')!=body['file_id'] or info.get('mimeType')!=SHEETS_MIME:raise ApiError(400,'SOURCE_NOT_GOOGLE_SHEETS')
        if info.get('trashed'):raise ApiError(400,'SOURCE_TRASHED')
        with write_transaction() as db:
            current=flows.validate_claim(db,fid,cid,row['revision'])
            validate_ticket(db,current)
            flows.finish(db,current,'selection',{'file_id':body['file_id']},'source_pending',spreadsheet_id=body['file_id'],source_verified_at=flows.clock())
    except Exception as exc:
        flows.fail(row,cid,exc);raise
    return flows.read(fid)
