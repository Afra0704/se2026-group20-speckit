"""One-use browser-bound attempts and atomic teacher grant replacement."""
import secrets
import time
from uuid import uuid4

from flask import current_app, session

from ..auth import digest, issue_grant, require_teacher
from ..db import connection, write_transaction
from ..http import ApiError
from . import crypto, repository
from .provider import configuration, provider


def browser(db, create=False):
    raw = session.get('auth_browser')
    row = db.execute('SELECT * FROM auth_browsers WHERE binding_hash=?', (digest(raw),)).fetchone() if raw else None
    if row and row['expires_at'] > time.time():
        return row
    if not create:
        raise ApiError(400, 'GOOGLE_FLOW_INVALID')
    raw = secrets.token_urlsafe(32)
    session['auth_browser'] = raw
    key = digest(raw)
    now = time.time()
    db.execute('INSERT INTO auth_browsers(binding_hash,created_at,expires_at) VALUES(?,?,?)',
               (key, now, now + current_app.config['AUTH_SECONDS'] + 600))
    return db.execute('SELECT * FROM auth_browsers WHERE binding_hash=?', (key,)).fetchone()


def binding(attempt):
    return {key: attempt[key] for key in ('attempt_id','purpose','instance_uuid','browser_hash','browser_epoch','client_id')}


def start(purpose='login', *, flow_id=None, credential_kind=None):
    if flow_id is not None:
        from .flow_context import attach
        from .picker_service import configuration as picker_configuration
    web = (picker_configuration() if flow_id is not None and credential_kind == 'picker' else configuration())['web']
    expected = require_teacher().teacher_id if purpose == 'sheets' else None
    state = secrets.token_urlsafe(32)
    with write_transaction() as db:
        now = time.time()
        db.execute("UPDATE google_oauth_attempts SET status='expired',secret_blob=NULL WHERE expires_at<=? AND status IN ('pending','processing')", (now,))
        db.execute("DELETE FROM google_oauth_attempts WHERE expires_at<? AND status NOT IN ('pending','processing')", (now-86400,))
        owner = browser(db, True)
        if purpose == 'sheets' and require_teacher(db).teacher_id != expected:
            raise ApiError(409, 'GOOGLE_FLOW_SUPERSEDED')
        db.execute("UPDATE google_oauth_attempts SET status='superseded',secret_blob=NULL WHERE browser_hash=? AND status IN ('pending','processing')", (owner['binding_hash'],))
        db.execute('UPDATE auth_browsers SET epoch=epoch+1 WHERE binding_hash=?', (owner['binding_hash'],))
        attempt = dict(attempt_id=str(uuid4()), state_hash=digest(state), browser_hash=owner['binding_hash'],
            browser_epoch=owner['epoch']+1, purpose=purpose, expected_teacher_id=expected,
            expected_grant_hash=owner['teacher_grant_hash'], client_id=web['client_id'],
            redirect_uri=current_app.config['GOOGLE_REDIRECT_URI'], instance_uuid=repository.instance_id(db),
            created_at=time.time(), expires_at=time.time()+300)
        secret = {'nonce':secrets.token_urlsafe(32), 'verifier':secrets.token_urlsafe(64)}
        attempt['secret_blob'] = crypto.encrypt(secret, binding(attempt))
        columns = list(attempt)
        db.execute(f"INSERT INTO google_oauth_attempts({','.join(columns)},status) VALUES({','.join('?' for _ in columns)},'pending')", tuple(attempt.values()))
        if flow_id is not None:
            attach(db, attempt, flow_id, credential_kind)
    attempt.update(state=state, secrets=secret)
    return provider().authorization_request(attempt)


def claim(state):
    if not isinstance(state, str) or not state or len(state)>128:
        raise ApiError(400, 'GOOGLE_FLOW_INVALID')
    with write_transaction() as db:
        owner = browser(db)
        row = db.execute('SELECT * FROM google_oauth_attempts WHERE state_hash=?', (digest(state),)).fetchone()
        if not row or row['browser_hash'] != owner['binding_hash']:
            raise ApiError(400, 'GOOGLE_FLOW_INVALID')
        attempt = dict(row)
        validate_current(db, attempt, owner, pending=True)
        claim_id = secrets.token_urlsafe(32)
        db.execute("UPDATE google_oauth_attempts SET status='processing',claim_id=? WHERE attempt_id=? AND status='pending'", (claim_id, row['attempt_id']))
    attempt.update(claim_id=claim_id, status='processing', state=state)
    attempt['secrets'] = crypto.decrypt(row['secret_blob'], binding(attempt))
    return attempt


def validate_current(db, attempt, owner=None, pending=False):
    owner = owner or browser(db)
    if attempt['expires_at'] <= time.time():
        raise ApiError(410, 'GOOGLE_FLOW_EXPIRED')
    if owner['epoch'] != attempt['browser_epoch'] or owner['teacher_grant_hash'] != attempt['expected_grant_hash']:
        raise ApiError(409, 'GOOGLE_FLOW_SUPERSEDED')
    from .flow_context import client_for
    if attempt['instance_uuid'] != repository.instance_id(db) or attempt['client_id'] != client_for(attempt)['web']['client_id'] or attempt['redirect_uri'] != current_app.config['GOOGLE_REDIRECT_URI']:
        raise ApiError(400, 'GOOGLE_FLOW_INVALID')
    current = db.execute('SELECT status,claim_id FROM google_oauth_attempts WHERE attempt_id=?', (attempt['attempt_id'],)).fetchone()
    if not current or current['status'] != ('pending' if pending else 'processing') or (not pending and current['claim_id'] != attempt['claim_id']):
        raise ApiError(409, 'GOOGLE_FLOW_SUPERSEDED')
    old = db.execute('SELECT teacher_id FROM grants WHERE token=?', (attempt['expected_grant_hash'],)).fetchone()
    if old and not db.execute('SELECT 1 FROM teachers WHERE id=? AND active=1', (old['teacher_id'],)).fetchone():
        raise ApiError(403, 'TEACHER_DISABLED')
    if attempt['purpose'] == 'sheets' and require_teacher(db).teacher_id != attempt['expected_teacher_id']:
        raise ApiError(409, 'GOOGLE_FLOW_SUPERSEDED')


def finish(attempt, result):
    identity = result['identity']
    with write_transaction() as db:
        validate_current(db, attempt)
        if attempt['purpose'] == 'sheets':
            from .sheets_service import connect
            from .flow_context import finish as finish_flow
            if not finish_flow(db, attempt, result):
                connect(db, attempt, result)
            token = None
        else:
            row = db.execute('SELECT i.teacher_id,t.active FROM google_identities i JOIN teachers t ON t.id=i.teacher_id WHERE issuer=? AND subject=?', (identity['issuer'],identity['subject'])).fetchone()
            if row and not row['active']:
                raise ApiError(403, 'TEACHER_DISABLED')
            if row:
                teacher_id = row['teacher_id']
                db.execute('UPDATE google_identities SET display_name=?,email=?,email_verified=?,updated_at=CURRENT_TIMESTAMP WHERE teacher_id=?', (identity['display_name'],identity['email'],int(identity['email_verified']),teacher_id))
            else:
                teacher_id = db.execute('INSERT INTO teachers(username,password_hash,active) VALUES(NULL,NULL,1)').lastrowid
                db.execute('INSERT INTO google_identities(teacher_id,issuer,subject,display_name,email,email_verified) VALUES(?,?,?,?,?,?)', (teacher_id,identity['issuer'],identity['subject'],identity['display_name'],identity['email'],int(identity['email_verified'])))
            token = issue_grant(db, teacher_id=teacher_id)
            if attempt['expected_grant_hash']:
                db.execute('DELETE FROM grants WHERE token=?', (attempt['expected_grant_hash'],))
            db.execute('UPDATE auth_browsers SET teacher_grant_hash=?,epoch=epoch+1,expires_at=? WHERE binding_hash=?', (digest(token),time.time()+current_app.config['AUTH_SECONDS']+600,attempt['browser_hash']))
        db.execute("UPDATE google_oauth_attempts SET status='succeeded',secret_blob=NULL,consumed_at=? WHERE attempt_id=?", (time.time(),attempt['attempt_id']))
    if token:
        session['teacher_grant'] = token
        alias = session.get('grant')
        if alias:
            row = connection().execute('SELECT teacher_id FROM grants WHERE token=?',(digest(alias),)).fetchone()
            if row and row['teacher_id'] is not None:
                session.pop('grant', None)


def fail(attempt):
    if attempt:
        with write_transaction() as db:
            db.execute("UPDATE google_oauth_attempts SET status='failed',secret_blob=NULL,consumed_at=? WHERE attempt_id=? AND claim_id=? AND status='processing'", (time.time(),attempt['attempt_id'],attempt['claim_id']))


def logout():
    with write_transaction() as db:
        try:
            owner = browser(db)
        except ApiError:
            owner = None
        if owner:
            db.execute("UPDATE google_oauth_attempts SET status='superseded',secret_blob=NULL WHERE browser_hash=? AND status IN ('pending','processing')", (owner['binding_hash'],))
            if owner['teacher_grant_hash']:
                db.execute('DELETE FROM grants WHERE token=?', (owner['teacher_grant_hash'],))
            db.execute('UPDATE auth_browsers SET epoch=epoch+1,teacher_grant_hash=NULL WHERE binding_hash=?', (owner['binding_hash'],))
    session.pop('teacher_grant', None)
    # A legacy alias may belong to a student. Preserve it unless it was a teacher.
    alias = session.get('grant')
    if alias:
        row = connection().execute('SELECT teacher_id FROM grants WHERE token=?', (digest(alias),)).fetchone()
        if row is not None and row['teacher_id'] is not None:
            session.pop('grant', None)
