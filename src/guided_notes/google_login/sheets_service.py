"""Per-teacher encrypted credentials with bounded, leased explicit refresh."""
import json
import math
import time
from datetime import datetime, timezone
from uuid import uuid4
from flask import session

from ..auth import digest, require_teacher
from ..db import connection, write_transaction
from ..http import ApiError
from . import crypto, repository
from .provider import Budget, SHEETS_SCOPE, actual_scopes, configuration, provider
from .transport import CredentialSnapshot, CredentialSnapshotExpired


def binding(row):
    return {'purpose':'sheets', **{key: row[key] for key in ('teacher_id','instance_uuid','issuer','subject','client_id','credential_id','revision')}}


def unpack(row, teacher):
    owner = repository.identity(teacher.teacher_id)
    client = configuration()['web']
    if not owner or not owner['active'] or row['teacher_id'] != teacher.teacher_id or row['instance_uuid'] != repository.instance_id() or row['issuer'] != owner['issuer'] or row['subject'] != owner['subject'] or row['client_id'] != client['client_id']:
        raise ApiError(503, 'GOOGLE_CREDENTIALS_UNAVAILABLE')
    secret = crypto.decrypt(row['secret_blob'], binding(row))
    if (not isinstance(secret.get('access_token'), str) or not secret.get('refresh_token')
            or SHEETS_SCOPE not in secret.get('scopes', []) or secret.get('scopes') != json.loads(row['granted_scopes'])
            or secret.get('expires_at') != row['expires_at']):
        raise ApiError(503, 'GOOGLE_CREDENTIALS_UNAVAILABLE')
    return secret


def authorization_status(teacher):
    row = connection().execute('SELECT * FROM google_sheets_credentials WHERE teacher_id=?', (teacher.teacher_id,)).fetchone()
    if not row:
        return {'status':'not_connected'}
    if row['status'] != 'connected':
        return {'status':'reauth_required'}
    try:
        unpack(row, teacher)
    except ApiError:
        return {'status':'unavailable'}
    return {'status':'connected'}


def expiry(token):
    try:
        seconds = float(token.get('expires_in', 0))
        end = float(token.get('expires_at', time.time()+seconds))
        if end <= time.time()+30 or not math.isfinite(end):
            raise ValueError()
        return end
    except (ValueError, TypeError):
        raise ApiError(400, 'GOOGLE_FLOW_INVALID') from None


def connect(db, attempt, result):
    teacher = require_teacher(db)
    owner = repository.identity(teacher.teacher_id, db)
    if result['identity']['subject'] != owner['subject'] or result['identity']['issuer'] != owner['issuer']:
        raise ApiError(409, 'GOOGLE_ACCOUNT_MISMATCH')
    token = result['token']
    scopes = sorted(actual_scopes(token))
    if SHEETS_SCOPE not in scopes:
        raise ApiError(403, 'SHEETS_SCOPE_REQUIRED')
    old = db.execute('SELECT * FROM google_sheets_credentials WHERE teacher_id=?', (teacher.teacher_id,)).fetchone()
    refresh = token.get('refresh_token')
    if not refresh and old and old['status'] == 'connected':
        refresh = unpack(old, teacher)['refresh_token']
    if not isinstance(refresh, str) or not refresh:
        raise ApiError(409, 'SHEETS_REAUTH_REQUIRED')
    if not isinstance(token.get('access_token'), str) or not token['access_token']:
        raise ApiError(400, 'GOOGLE_FLOW_INVALID')
    row = dict(teacher_id=teacher.teacher_id, instance_uuid=repository.instance_id(db), issuer=owner['issuer'],
        subject=owner['subject'], client_id=attempt['client_id'], credential_id=str(uuid4()), revision=old['revision']+1 if old else 1,
        status='connected', granted_scopes=json.dumps(scopes), expires_at=expiry(token))
    secret = {'access_token':token['access_token'], 'refresh_token':refresh, 'scopes':scopes,'expires_at':row['expires_at']}
    row['secret_blob'] = crypto.encrypt(secret, binding(row))
    columns = list(row)
    db.execute(f"INSERT INTO google_sheets_credentials({','.join(columns)}) VALUES({','.join('?' for _ in columns)}) ON CONFLICT(teacher_id) DO UPDATE SET " + ','.join(f'{key}=excluded.{key}' for key in columns if key != 'teacher_id') + ',refresh_lease_id=NULL,lease_until=NULL,updated_at=CURRENT_TIMESTAMP', tuple(row.values()))


def _guard(teacher, grant_hash=None):
    if require_teacher() != teacher or (grant_hash is not None and digest(session.get('teacher_grant','')) != grant_hash):
        raise ApiError(403, 'FORBIDDEN')


def credentials(teacher):
    _guard(teacher)
    expected_grant = digest(session['teacher_grant'])
    row = connection().execute('SELECT * FROM google_sheets_credentials WHERE teacher_id=?', (teacher.teacher_id,)).fetchone()
    if not row:
        raise ApiError(409, 'SHEETS_CONNECT_REQUIRED')
    if row['status'] != 'connected':
        raise ApiError(409, 'SHEETS_REAUTH_REQUIRED')
    secret = unpack(row, teacher)
    if row['expires_at'] <= time.time()+60:
        secret = refresh(teacher)
    _guard(teacher, expected_grant)
    def snapshot_guard():
        try:
            _guard(teacher, expected_grant)
        except ApiError:
            raise CredentialSnapshotExpired() from None
    return CredentialSnapshot(secret['access_token'], datetime.fromtimestamp(secret['expires_at'], timezone.utc),
                              secret['scopes'], guard=snapshot_guard)


def refresh(teacher):
    with write_transaction() as db:
        _guard(teacher)
        expected_grant = digest(session['teacher_grant'])
        row = dict(db.execute('SELECT * FROM google_sheets_credentials WHERE teacher_id=?', (teacher.teacher_id,)).fetchone())
        if row['status'] != 'connected':
            raise ApiError(409, 'SHEETS_REAUTH_REQUIRED')
        secret = unpack(row, teacher)
        if row['expires_at'] > time.time()+60:
            return secret
        if row['lease_until'] and row['lease_until'] > time.time():
            raise ApiError(503, 'GOOGLE_REFRESH_BUSY', retry_after=1)
        lease = str(uuid4())
        lease_until = time.time()+30
        db.execute('UPDATE google_sheets_credentials SET refresh_lease_id=?,lease_until=? WHERE teacher_id=?', (lease,lease_until,teacher.teacher_id))
    budget = Budget(20)
    where = 'teacher_id=? AND credential_id=? AND revision=? AND refresh_lease_id=?'
    args = (teacher.teacher_id,row['credential_id'],row['revision'],lease)
    try:
        value = provider().refresh(secret, configuration()['web'], budget)
        budget.check()
        if value.get('_identity') and (value['_identity']['subject'] != row['subject'] or value['_identity']['issuer'] != row['issuer']):
            raise ApiError(503, 'GOOGLE_CREDENTIALS_UNAVAILABLE')
        scopes = sorted(actual_scopes(value)) if 'scope' in value else secret['scopes']
        if SHEETS_SCOPE not in scopes:
            raise ApiError(409, 'GOOGLE_REAUTH_REQUIRED')
        updated = {'access_token':value['access_token'], 'refresh_token':value.get('refresh_token') or secret['refresh_token'],
                   'scopes':scopes,'expires_at':expiry(value)}
        with write_transaction() as db:
            budget.check()
            _guard(teacher, expected_grant)
            if time.time() >= lease_until:
                raise ApiError(503, 'GOOGLE_REFRESH_TIMEOUT', retry_after=1)
            live = db.execute('SELECT * FROM google_sheets_credentials WHERE '+where, args).fetchone()
            if not live:
                raise ApiError(503, 'GOOGLE_REFRESH_BUSY', retry_after=1)
            if live['lease_until'] is None or live['lease_until'] <= time.time():
                raise ApiError(503, 'GOOGLE_REFRESH_TIMEOUT', retry_after=1)
            unpack(live, teacher)
            new = {**row,'revision':row['revision']+1}
            blob = crypto.encrypt(updated, binding(new))
            budget.check()
            db.execute('UPDATE google_sheets_credentials SET secret_blob=?,revision=revision+1,expires_at=?,granted_scopes=?,refresh_lease_id=NULL,lease_until=NULL,updated_at=CURRENT_TIMESTAMP WHERE '+where,
                       (blob,updated['expires_at'],json.dumps(scopes),*args))
        return updated
    except ApiError as error:
        # A late invalid_grant must not poison either this generation or a reconnect.
        timely = time.monotonic() < budget.deadline and time.time() < lease_until
        replaced = False
        with write_transaction() as db:
            live = db.execute('SELECT lease_until FROM google_sheets_credentials WHERE '+where,args).fetchone()
            replaced = live is None
            if live and (live['lease_until'] is None or live['lease_until'] <= time.time()):
                timely = False
            if error.code == 'GOOGLE_REAUTH_REQUIRED' and timely:
                try:
                    _guard(teacher, expected_grant)
                except ApiError:
                    pass
                else:
                    db.execute("UPDATE google_sheets_credentials SET status='reauth_required',secret_blob=NULL,revision=revision+1,refresh_lease_id=NULL,lease_until=NULL WHERE "+where,args)
            db.execute('UPDATE google_sheets_credentials SET refresh_lease_id=NULL,lease_until=NULL WHERE '+where,args)
        if not timely:
            raise ApiError(503, 'GOOGLE_REFRESH_TIMEOUT', retry_after=1) from None
        if replaced:
            raise ApiError(503, 'GOOGLE_REFRESH_BUSY', retry_after=1) from None
        if error.code == 'GOOGLE_REAUTH_REQUIRED':
            raise ApiError(409, 'SHEETS_REAUTH_REQUIRED') from None
        raise
    except Exception:
        with write_transaction() as db:
            db.execute('UPDATE google_sheets_credentials SET refresh_lease_id=NULL,lease_until=NULL WHERE '+where,args)
        raise ApiError(503, 'GOOGLE_UNAVAILABLE') from None
