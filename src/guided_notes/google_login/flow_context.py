"""Trusted OAuth dispatch sidecar; client choice never comes from callback parameters."""
import time
from flask import current_app
from ..db import connection
from ..auth import require_teacher
from ..http import ApiError
from ..workspace import import_flows as flows


def enabled(db):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='google_oauth_attempt_context'").fetchone() is not None


def context(attempt, db=None):
    db=db or connection()
    if not enabled(db):return None
    row=db.execute('SELECT * FROM google_oauth_attempt_context WHERE attempt_id=?',(attempt['attempt_id'],)).fetchone()
    linked=db.execute('SELECT flow_id FROM workspace_import_flows WHERE oauth_attempt_id=?',(attempt['attempt_id'],)).fetchone()
    if linked and not row:raise ApiError(409,'FLOW_INVALIDATED')
    if row:
        flow=flows.load(db,row['flow_id'])
        expected='awaiting_picker_auth' if row['credential_kind']=='picker' else 'awaiting_sheets_auth'
        if flow['oauth_attempt_id']!=attempt['attempt_id'] or flow['status']!=expected:raise ApiError(409,'FLOW_INVALIDATED')
        return dict(row)
    return None


def client_for(attempt):
    from .provider import configuration
    ctx=context(attempt)
    if ctx and ctx['credential_kind']=='picker':
        from .picker_service import configuration as picker_configuration
        return picker_configuration()
    return configuration()


def attach(db, attempt, fid, kind):
    flow=flows.load(db,fid)
    if flow['status'] in flows.TERMINAL or flow['status']=='reading':raise ApiError(409,'FLOW_STEP_CONFLICT')
    db.execute('INSERT INTO google_oauth_attempt_context VALUES(?,?,?,?)',(attempt['attempt_id'],fid,kind,time.time()))
    db.execute('UPDATE workspace_import_flows SET oauth_attempt_id=?,status=?,revision=revision+1 WHERE flow_id=?',(attempt['attempt_id'],'awaiting_picker_auth' if kind=='picker' else 'awaiting_sheets_auth',fid))


def authorize(fid, kind):
    flow=flows.get(fid)
    if kind not in ('picker','sheets'):raise ApiError(400,'INVALID_REQUEST')
    if kind=='picker':
        from .picker_service import usable_cache, configuration
        if flow['source_kind']!='cloud' or flow['status'] not in ('source_pending','awaiting_picker_auth','picking'):raise ApiError(409,'FLOW_STEP_CONFLICT')
        configuration()
        from ..db import write_transaction
        if usable_cache(require_teacher(),missing_ok=True):
            with write_transaction() as db:
                flows.load(db,fid)
                db.execute("UPDATE workspace_import_flows SET status='picking',revision=revision+1 WHERE flow_id=?",(fid,))
            return flows.safe(flows.get(fid))
    else:
        if flow['status']!='awaiting_sheets_auth':raise ApiError(409,'FLOW_STEP_CONFLICT')
        from .sheets_service import authorization_status
        if authorization_status(require_teacher())['status']=='connected':return flows.safe(flow)
    from .service import start
    return {'authorization_required':True,'authorization_url':start('sheets',flow_id=fid,credential_kind=kind)}


def finish(db,attempt,result):
    ctx=context(attempt,db)
    if not ctx:return False
    if ctx['credential_kind']=='picker':
        from .picker_service import connect
        connect(db,attempt,result)
        status='picking'
    else:
        from .sheets_service import connect
        connect(db,attempt,result)
        # Resume only a prior explicit source read, never a GET side effect.
        status='source_pending'
    db.execute('UPDATE workspace_import_flows SET status=?,revision=revision+1 WHERE flow_id=?',(status,ctx['flow_id']))
    return True
