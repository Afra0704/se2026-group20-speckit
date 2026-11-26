"""Server-owned import intent; claims fence late network results and preview edits."""
import hashlib
import json
import secrets
import time
from flask import current_app, session
from ..auth import digest, require_teacher
from ..db import connection, write_transaction
from ..http import ApiError
from ..google_login import repository as identities
from ..notes.repository import dumps
from ..notes.sheets_gateway import parse_sheets_url
from .repository import invalidate

TERMINAL = {'completed','cancelled','expired','invalidated'}


def clock():
    custom = current_app.config.get('WORKSPACE_CLOCK') if current_app.testing else None
    return custom() if custom else time.time()


def load(db, flow_id):
    teacher = require_teacher(db)
    row = db.execute('SELECT * FROM workspace_import_flows WHERE flow_id=? AND teacher_id=?', (flow_id,teacher.teacher_id)).fetchone()
    if not row:
        raise ApiError(404,'FLOW_NOT_FOUND')
    if row['status']=='expired' or row['expires_at']<=clock():
        raise ApiError(410,'FLOW_EXPIRED')
    if row['status'] in ('invalidated','cancelled') or row['instance_uuid']!=identities.instance_id(db) or row['browser_hash']!=digest(session.get('auth_browser','')) or row['expected_grant_hash']!=digest(session.get('teacher_grant','')):
        raise ApiError(409,'FLOW_INVALIDATED')
    course=db.execute('SELECT 1 FROM courses WHERE id=? AND teacher_id=?',(row['course_id'],teacher.teacher_id)).fetchone()
    if not course:raise ApiError(404,'COURSE_NOT_FOUND')
    return dict(row)


def get(flow_id):
    error=None
    with write_transaction() as db:
        try:row=load(db,flow_id)
        except ApiError as exc:
            error=exc
            # Never mutate another teacher's flow, even after a grant change.
            owner=db.execute('SELECT teacher_id FROM workspace_import_flows WHERE flow_id=?',(flow_id,)).fetchone()
            raw=session.get('teacher_grant','')
            grant=db.execute('SELECT teacher_id FROM grants WHERE token=?',(digest(raw),)).fetchone()
            if owner and grant and owner[0]==grant[0] and exc.code in ('FLOW_EXPIRED','FLOW_INVALIDATED'):
                invalidate(db,flow_id,'expired' if exc.code=='FLOW_EXPIRED' else 'invalidated',clock())
    if error:raise error
    return row


def safe(row):
    fields=('flow_id','course_id','source_kind','status','revision','choice_revision','claim_until','error_code')
    result={k:row[k] for k in fields}
    result['worksheets']=json.loads(row['worksheets_json'] or '[]')
    result['source_selected']=bool(row['source_verified_at'])
    result['suggested_sheet_id']=row['suggested_sheet_id']
    result['retryable']=row['status']=='failed' or (row['status']=='reading' and row['claim_until']<=clock())
    result['needs_authorization']='picker' if row['status']=='awaiting_picker_auth' else 'sheets' if row['status']=='awaiting_sheets_auth' else None
    result['preview_id']=row['current_preview_id']
    if row['current_preview_id']:result['preview_url']='/teacher/notes/import-previews/'+row['current_preview_id']
    return result


def create(course_id, source_kind, url=None):
    if source_kind not in ('cloud','link') or (source_kind=='cloud' and url is not None):raise ApiError(400,'INVALID_REQUEST')
    sid,gid=parse_sheets_url(url) if source_kind=='link' else (None,None)
    from ..activities.course_service import get_owned_course
    with write_transaction() as db:
        teacher=require_teacher(db);get_owned_course(teacher,course_id,db=db)
        fid=secrets.token_urlsafe(24);now=clock()
        db.execute("""INSERT INTO workspace_import_flows(flow_id,teacher_id,course_id,instance_uuid,browser_hash,expected_grant_hash,source_kind,spreadsheet_url,spreadsheet_id,suggested_sheet_id,status,created_at,expires_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,'source_pending',?,?,?)""",(fid,teacher.teacher_id,course_id,identities.instance_id(db),digest(session['auth_browser']),digest(session['teacher_grant']),source_kind,'https://docs.google.com/spreadsheets/d/'+sid+'/edit' if sid else None,sid,gid,now,now+1800,now))
    cleanup()
    return get(fid)


def cleanup():
    with write_transaction() as db:
        rows=db.execute("SELECT flow_id,status,expires_at,expected_grant_hash FROM workspace_import_flows WHERE status NOT IN ('completed','cancelled','expired','invalidated') ORDER BY created_at LIMIT 100").fetchall()
        for row in rows:
            active=db.execute('SELECT 1 FROM grants g JOIN teachers t ON t.id=g.teacher_id WHERE g.token=? AND g.expires>? AND t.active=1',(row['expected_grant_hash'],time.time())).fetchone()
            if row['expires_at']<=clock() or not active:
                invalidate(db,row['flow_id'],'expired' if row['expires_at']<=clock() else 'invalidated',clock())
        for row in db.execute("SELECT flow_id FROM workspace_import_flows WHERE status IN ('completed','cancelled','expired','invalidated') AND updated_at<? LIMIT 100",(clock()-86400,)).fetchall():
            # Clear ready previews before removing their safety mapping.
            db.execute("UPDATE notes_import_previews SET status='invalidated' WHERE status='ready' AND preview_id IN (SELECT preview_id FROM workspace_preview_flows WHERE flow_id=?)",(row[0],))
            db.execute('DELETE FROM workspace_import_flows WHERE flow_id=?',(row[0],))


def request_key(body):
    raw=dumps(body)
    return hashlib.sha256(raw.encode()).hexdigest()


def claim(fid, action, body, *, retry=False, preclaim=None):
    get(fid)
    with write_transaction() as db:
        row=load(db,fid);state=json.loads(row['request_state_json']);old=state.get(action)
        if row['status']=='reading' and row['claim_until']>clock():raise ApiError(409,'FLOW_BUSY',retry_after=1)
        if action=='preview' and body.get('choice_revision')!=row['choice_revision']:raise ApiError(409,'FLOW_STEP_CONFLICT')
        if old and old['input']!=body:raise ApiError(409,'FLOW_STEP_CONFLICT')
        if row['status'] in TERMINAL:raise ApiError(409,'FLOW_STEP_CONFLICT')
        if old and old.get('result') is not None:return row,None,old['result']
        if row['status'] in ('reading','failed') and not retry:raise ApiError(409,'FLOW_STEP_CONFLICT')
        allowed={'read':('source_pending','picking','awaiting_sheets_auth'), 'preview':('worksheets_ready',), 'selection':('picking',)}
        if not retry and row['status'] not in allowed[action]:raise ApiError(409,'FLOW_STEP_CONFLICT')
        state[action]={'input':body,'fingerprint':request_key(body),'result':None}
        cid=secrets.token_urlsafe(24)
        if preclaim is not None:preclaim(db,row)
        db.execute("UPDATE workspace_import_flows SET status='reading',claim_id=?,claim_action=?,claim_until=?,retry_action=?,revision=revision+1,request_state_json=?,error_code=NULL,updated_at=? WHERE flow_id=?",(cid,action,clock()+120,action,dumps(state),clock(),fid))
        return load(db,fid),cid,None


def validate_claim(db, fid, cid, revision):
    row=load(db,fid)
    if row['status']!='reading' or row['claim_id']!=cid or row['revision']!=revision or row['claim_until']<=clock():raise ApiError(409,'FLOW_STEP_CONFLICT')
    return row


def finish(db,row,action,result,status,**fields):
    state=json.loads(row['request_state_json']);state[action]['result']=result
    fields.update(status=status,request_state_json=dumps(state),claim_id=None,claim_action=None,claim_until=None,retry_action=None,error_code=None,updated_at=clock())
    db.execute('UPDATE workspace_import_flows SET '+','.join(k+'=?' for k in fields)+',revision=revision+1 WHERE flow_id=?',(*fields.values(),row['flow_id']))


def fail(row,cid,error):
    with write_transaction() as db:
        db.execute("UPDATE workspace_import_flows SET status='failed',claim_id=NULL,claim_action=NULL,claim_until=NULL,error_code=?,revision=revision+1,updated_at=? WHERE flow_id=? AND status='reading' AND claim_id=? AND revision=?",(getattr(error,'code','SOURCE_READ_UNAVAILABLE'),clock(),row['flow_id'],cid,row['revision']))


def read(fid, *, retry=False):
    initial=get(fid)
    if initial['status'] in TERMINAL:
        raise ApiError(409,'FLOW_STEP_CONFLICT')
    if not initial['spreadsheet_id'] or (initial['source_kind']=='cloud' and not initial['source_verified_at']):raise ApiError(409,'FLOW_STEP_CONFLICT')
    prior=json.loads(initial['request_state_json']).get('read')
    if prior and prior.get('result') is not None:
        return safe(initial),200
    from ..notes.routes import gateway
    from ..google_login.sheets_service import authorization_status
    teacher=require_teacher()
    if not (current_app.testing and current_app.config.get('NOTES_GATEWAY')) and authorization_status(teacher)['status']!='connected':
        with write_transaction() as db:
            current=load(db,fid)
            if current['status'] in TERMINAL or current['revision']!=initial['revision']:
                raise ApiError(409,'FLOW_STEP_CONFLICT')
            db.execute("UPDATE workspace_import_flows SET status='awaiting_sheets_auth',claim_id=NULL,claim_action=NULL,claim_until=NULL,revision=revision+1 WHERE flow_id=?",(fid,))
        return safe(get(fid)),202
    body={'spreadsheet_id':initial['spreadsheet_id']}
    row,cid,done=claim(fid,'read',body,retry=retry)
    if cid is None:return safe(row),200
    try:
        sheets=gateway(teacher).list_worksheets(row['spreadsheet_id'])
        with write_transaction() as db:
            current=validate_claim(db,fid,cid,row['revision'])
            finish(db,current,'read',{'listed':True},'worksheets_ready',worksheets_json=dumps(sheets),source_verified_at=clock())
    except Exception as exc:
        fail(row,cid,exc);raise
    return safe(get(fid)),200


def preview(fid, body, *, retry=False):
    from ..notes.import_service import create_preview
    from ..notes.routes import gateway
    row=get(fid)
    if type(body.get('sheet_id')) is not int or body['sheet_id'] not in [s['sheet_id'] for s in json.loads(row['worksheets_json'] or '[]')]:raise ApiError(400,'INVALID_REQUEST')
    if type(body.get('choice_revision')) is not int:raise ApiError(400,'INVALID_REQUEST')
    from ..notes.models import normalize_lecture_name
    if body.get('custom_title') is not None and (not isinstance(body['custom_title'],str) or len(body['custom_title'])>100):raise ApiError(400,'INVALID_REQUEST')
    normalize_lecture_name(body.get('name_mode','source'),body.get('custom_title'))
    # Retain the exact validated request; service owns name normalization.
    body={'choice_revision':body['choice_revision'],'sheet_id':body['sheet_id'],'name_mode':body.get('name_mode','source'),'custom_title':body.get('custom_title')}
    row,cid,done=claim(fid,'preview',body,retry=retry)
    if cid is None:return done,201
    def guard(db,pid):
        current=validate_claim(db,fid,cid,row['revision'])
        db.execute('INSERT INTO workspace_preview_flows VALUES(?,?,?)',(pid,fid,clock()))
        result={'preview_id':pid,'preview_url':'/teacher/notes/import-previews/'+pid,'flow_url':'/teacher/workspace/imports/'+fid}
        finish(db,current,'preview',result,'preview_ready',current_preview_id=pid)
    try:
        pid=create_preview(require_teacher(),gateway(require_teacher()),row['spreadsheet_id'],body['sheet_id'],body['name_mode'],body['custom_title'],row['course_id'],flow_guard=guard)
    except Exception as exc:
        fail(row,cid,exc);raise
    return {'preview_id':pid,'preview_url':'/teacher/notes/import-previews/'+pid,'flow_url':'/teacher/workspace/imports/'+fid},201


def revise(fid, expected):
    get(fid)
    with write_transaction() as db:
        row=load(db,fid)
        if type(expected) is not int or expected!=row['revision']:raise ApiError(409,'FLOW_STEP_CONFLICT')
        if row['status']=='reading' and row['claim_until']>clock():raise ApiError(409,'FLOW_BUSY',retry_after=1)
        if not row['worksheets_json'] or row['status'] not in ('worksheets_ready','preview_ready','failed','reading'):raise ApiError(409,'FLOW_STEP_CONFLICT')
        state=json.loads(row['request_state_json']);previous=state.pop('preview',{}).get('input',{});state.pop('confirm',None)
        db.execute("UPDATE notes_import_previews SET status='invalidated' WHERE status='ready' AND preview_id IN (SELECT preview_id FROM workspace_preview_flows WHERE flow_id=?)",(fid,))
        db.execute("UPDATE workspace_import_flows SET status='worksheets_ready',current_preview_id=NULL,claim_id=NULL,claim_action=NULL,claim_until=NULL,retry_action=NULL,choice_revision=choice_revision+1,revision=revision+1,request_state_json=?,updated_at=? WHERE flow_id=?",(dumps(state),clock(),fid))
    result=safe(get(fid));result['previous_choice']=previous
    return result


def retry(fid):
    row=get(fid)
    if row['status']=='reading' and row['claim_until']>clock():raise ApiError(409,'FLOW_BUSY',retry_after=1)
    if row['status'] not in ('failed','reading') or not row['retry_action']:raise ApiError(409,'FLOW_STEP_CONFLICT')
    action=row['retry_action'];body=json.loads(row['request_state_json'])[action]['input']
    if action=='read':return read(fid,retry=True)
    if action=='preview':return preview(fid,body,retry=True)
    from ..google_login.picker_service import select
    return select(fid,body,retry=True)


def cancel(fid):
    get(fid)
    with write_transaction() as db:
        row=load(db,fid)
        if row['status']=='completed':raise ApiError(409,'FLOW_STEP_CONFLICT')
        invalidate(db,fid,'cancelled',clock())
    return {'flow_id':fid,'status':'cancelled'}


def preview_context(db,pid):
    if not current_app.config.get('CLASSROOM_MODE') or current_app.config.get('TEACHER_AUTH_MODE')!='google':return None
    return db.execute('SELECT flow_id FROM workspace_preview_flows WHERE preview_id=?',(pid,)).fetchone()


def guard_preview(db,pid,existing_id, *, expected_revision=None):
    context=preview_context(db,pid)
    if not context:return None
    row=load(db,context['flow_id'])
    if row['status'] not in ('preview_ready','completed') or row['current_preview_id']!=pid or (expected_revision is not None and row['revision']!=expected_revision):raise ApiError(409,'PREVIEW_STALE')
    state=json.loads(row['request_state_json']);body={'preview_id':pid,'existing_import_id':existing_id}
    old=state.get('confirm')
    if old and old['input']!=body:raise ApiError(409,'FLOW_STEP_CONFLICT')
    return row


def published(db,row,pid,existing_id,catalog=None,next_pid=None):
    if row is None:return
    if next_pid:
        db.execute('INSERT INTO workspace_preview_flows VALUES(?,?,?)',(next_pid,row['flow_id'],clock()))
        state=json.loads(row['request_state_json']);state.pop('confirm',None)
        state.pop('preview',None)
        db.execute('UPDATE workspace_import_flows SET current_preview_id=?,request_state_json=?,revision=revision+1,updated_at=? WHERE flow_id=?',(next_pid,dumps(state),clock(),row['flow_id']))
    elif row['status']!='completed':
        state=json.loads(row['request_state_json']);body={'preview_id':pid,'existing_import_id':existing_id}
        state['confirm']={'input':body,'fingerprint':request_key(body),'result':{'import_id':catalog['import_id'],'import_version':catalog['import_version']}}
        db.execute("UPDATE workspace_import_flows SET status='completed',confirmed_import_id=?,confirmed_version=?,request_state_json=?,revision=revision+1,updated_at=? WHERE flow_id=?",(catalog['import_id'],catalog['import_version'],dumps(state),clock(),row['flow_id']))
