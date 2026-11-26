from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from ..auth import require_teacher, csrf_token
from ..db import connection
from ..http import ApiError
from ..activities.course_service import get_owned_course
from ..activities.classroom_access import owned_classroom
from ..notes.course_catalogs import list_course_catalogs

workspace = Blueprint('workspace', __name__)


@workspace.errorhandler(ApiError)
def error_response(error):
    if error.status == 401 and not request.is_json and request.accept_mimetypes.best != 'application/json':
        return redirect('/teacher/login', code=303)
    messages = {
        'FLOW_BUSY':'正在處理，請稍候；讀取逾時後可按重試。',
        'FLOW_STEP_CONFLICT':'這筆操作已被較新的選擇取代，請重新整理後繼續。',
        'FLOW_EXPIRED':'匯入已逾時，請返回課程重新匯入。',
        'FLOW_INVALIDATED':'登入或匯入資格已改變，請返回課程重新開始。',
        'PICKER_NOT_CONFIGURED':'尚未設定雲端選檔，可先改用貼上Google Sheets連結。',
        'PICKER_REAUTH_REQUIRED':'選檔授權已到期，請重新開啟雲端選檔。',
        'PICKER_SCOPE_UNSAFE':'選檔授權範圍不符，請檢查專用Google選檔設定。',
        'PICKER_SCOPE_REQUIRED':'需要同意選檔權限才能繼續。',
        'GOOGLE_ACCOUNT_MISMATCH':'請使用與目前教師相同的Google帳號授權。',
        'SOURCE_READ_FORBIDDEN':'無法讀取來源，請確認Google帳號與講義分享權限。',
        'SOURCE_READ_UNAVAILABLE':'暫時無法讀取Google Sheets，請稍後重試。',
        'SOURCE_NOT_GOOGLE_SHEETS':'請選擇Google Sheets檔案。',
        'SOURCE_TRASHED':'來源已在垃圾桶，請選擇其他講義。',
        'PREVIEW_STALE':'這份預覽已失效，請使用目前的新預覽。',
        'LECTURE_REMOVED':'講義已移除，請選擇其他講義。',
        'INVALID_REQUEST':'輸入內容不完整或格式不正確，請檢查後重試。',
        'INVALID_CSRF':'頁面驗證已過期，請重新整理。',
    }
    response=jsonify(error={'code': error.code, 'message': messages.get(error.code,'操作未完成，請核對權限與來源後重試。'), 'retryable': error.retry_after is not None, 'context': {}})
    response.status_code=error.status
    if error.retry_after is not None:response.headers['Retry-After']=str(error.retry_after)
    return response


def page(name, **values):
    require_teacher()
    return render_template('workspace/' + name + '.html', csrf=csrf_token(), **values)


@workspace.get('/teacher/workspace')
def courses():
    teacher = require_teacher()
    rows = connection().execute('SELECT id AS course_id,title FROM courses WHERE teacher_id=? ORDER BY created_at,id', (teacher.teacher_id,)).fetchall()
    return page('courses', courses=rows)


@workspace.get('/teacher/workspace/courses/<course_id>')
def overview(course_id):
    return page('overview', course=get_owned_course(require_teacher(), course_id), section='overview')


@workspace.get('/teacher/workspace/courses/<course_id>/lectures')
def lectures(course_id):
    teacher = require_teacher()
    return page('lectures', course=get_owned_course(teacher, course_id), section='lectures', lectures=list_course_catalogs(teacher, course_id)['lectures'])


@workspace.get('/teacher/workspace/courses/<course_id>/classrooms')
def classrooms(course_id):
    course = get_owned_course(require_teacher(), course_id)
    rooms = connection().execute('SELECT * FROM classrooms WHERE course_id=? ORDER BY created_at DESC', (course_id,)).fetchall()
    return page('classrooms', course=course, rooms=rooms, section='classrooms')


@workspace.get('/teacher/workspace/courses/<course_id>/classrooms/<classroom_id>')
def classroom(course_id, classroom_id):
    teacher = require_teacher()
    course = get_owned_course(teacher, course_id)
    room = owned_classroom(connection(), teacher, classroom_id)
    if room['course_id'] != course_id:
        raise ApiError(404, 'CLASSROOM_NOT_FOUND')
    return page('classroom', course=course, room=room, section='classrooms')


from . import import_flows as flows
from ..notes.sheets_gateway import GatewayError
from ..notes.models import ContractError
from ..notes.recognition import RecognitionError


@workspace.errorhandler(GatewayError)
@workspace.errorhandler(ContractError)
def domain_error(error):
    return error_response(ApiError(error.http_status,error.code))


@workspace.errorhandler(RecognitionError)
def recognition_error(error):
    return jsonify(error={'code':error.issues[0].code,'message':'講義結構無法辨識，請核對來源。','retryable':False,'context':{'issues':[{'code':i.code} for i in error.issues]}}),422


def body(allowed):
    from ..http import payload
    value=dict(payload())
    value.pop('csrf_token',None)
    if set(value)-set(allowed):raise ApiError(400,'INVALID_REQUEST')
    return value


@workspace.post('/teacher/workspace/courses/<course_id>/imports')
def create_import(course_id):
    data=body(('source_kind','spreadsheet_url'))
    row=flows.create(course_id,data.get('source_kind'),data.get('spreadsheet_url'))
    result=flows.safe(row);result['flow_url']=url_for('workspace.import_page',flow_id=row['flow_id'])
    if not request.is_json:return redirect(result['flow_url'],code=303)
    return jsonify(result),201


@workspace.get('/teacher/workspace/imports/<flow_id>')
def import_page(flow_id):
    row=flows.get(flow_id)
    if request.accept_mimetypes.best=='application/json':return jsonify(flows.safe(row))
    data=flows.safe(row)
    preview=None
    if row['current_preview_id']:
        from ..notes.repository import owned_preview
        from ..notes.routes import preview_data
        preview=preview_data(owned_preview(connection(),require_teacher().teacher_id,row['current_preview_id']))
    existing=[]
    if row['current_preview_id']:
        source=connection().execute('SELECT source_id FROM notes_import_previews WHERE preview_id=?',(row['current_preview_id'],)).fetchone()
        existing=connection().execute('SELECT i.import_id,s.display_title FROM notes_imports i JOIN notes_sources s USING(source_id) JOIN notes_import_courses c USING(import_id) WHERE i.source_id=? AND c.course_id=? AND NOT EXISTS(SELECT 1 FROM notes_lecture_removals r WHERE r.import_id=i.import_id)',(source[0],row['course_id'])).fetchall()
    return page('import',existing_imports=existing,course=get_owned_course(require_teacher(),row['course_id']),section='lectures',flow=data,preview=preview)


@workspace.post('/teacher/workspace/imports/<flow_id>/<any(read,previews,confirm,cancel,retry,revise,authorize):action>')
def import_action(flow_id,action):
    fields={'read':(), 'previews':('choice_revision','sheet_id','name_mode','custom_title'), 'confirm':('confirm','preview_id','existing_import_id'), 'cancel':(), 'retry':(), 'revise':('expected_revision',),'authorize':('credential_kind',)}
    data=body(fields[action]);row=flows.get(flow_id)
    if action=='read':result,status=flows.read(flow_id)
    elif action=='previews':result,status=flows.preview(flow_id,data)
    elif action=='revise':result,status=flows.revise(flow_id,data.get('expected_revision')),200
    elif action=='retry':result,status=flows.retry(flow_id)
    elif action=='cancel':result,status=flows.cancel(flow_id),200
    elif action=='authorize':
        from ..google_login.flow_context import authorize
        result,status=authorize(flow_id,data.get('credential_kind')),200
        if not request.is_json and result.get('authorization_url'):return redirect(result['authorization_url'],code=303)
    else:
        from ..notes.import_service import confirm_preview
        from ..notes.routes import gateway
        if (request.is_json and data.get('confirm') is not True) or (not request.is_json and data.get('confirm')!='true'):raise ApiError(400,'INVALID_REQUEST')
        if data.get('preview_id')!=row['current_preview_id']:raise ApiError(409,'PREVIEW_STALE')
        if data.get('existing_import_id') is not None and (not isinstance(data['existing_import_id'],str) or len(data['existing_import_id'])>128):raise ApiError(400,'INVALID_REQUEST')
        catalog,next_pid=confirm_preview(require_teacher(),data['preview_id'],lambda:gateway(require_teacher()),data.get('existing_import_id') or None)
        if next_pid:
            flash('來源已變動，已更新預覽，目前尚未匯入。請核對最新題目與作答格後，再次確認匯入。', 'warning')
            return jsonify(error={'code':'SOURCE_CHANGED','message':'來源已變動，請重新確認預覽。','retryable':False,'context':{'preview_url':url_for('workspace.import_page',flow_id=flow_id)}}),409
        result={'catalog':catalog,'flow_id':flow_id,'course_url':url_for('workspace.lectures',course_id=row['course_id'])};status=200
    if not request.is_json:
        return redirect(result.get('course_url') or url_for('workspace.import_page',flow_id=flow_id),code=303)
    return jsonify(result),status


@workspace.post('/teacher/workspace/imports/<flow_id>/picker/<any(token,selection):action>')
def picker_action(flow_id,action):
    from ..google_login import picker_service
    if action=='token':
        body(())
        return jsonify(picker_service.token(flow_id))
    data=body(('file_id','ticket_id'))
    result,status=picker_service.select(flow_id,data)
    return jsonify(result),status


@workspace.get('/teacher/workspace/activities/<activity_id>/lecture')
def history_lecture(activity_id):
    from ..activities.classroom_access import requested_activity
    from ..notes.repository import catalog_row, unpack_recognition
    teacher=require_teacher();db=connection()
    activity=requested_activity(db,activity_id)
    room=owned_classroom(db,teacher,activity['classroom_id'])
    course=get_owned_course(teacher,room['course_id'])
    catalog=catalog_row(db,teacher.teacher_id,activity['import_id'],activity['import_version'])
    removed=db.execute('SELECT 1 FROM notes_lecture_removals WHERE import_id=?',(activity['import_id'],)).fetchone() is not None
    return page('history_lecture',course=course,section='classrooms',removed=removed,recognized=unpack_recognition(catalog['recognized']),activity=activity)


@workspace.get('/teacher/workspace/courses/<course_id>/classrooms/<classroom_id>/groups')
def classroom_groups(course_id,classroom_id):
    teacher=require_teacher();db=connection()
    get_owned_course(teacher,course_id)
    room=owned_classroom(db,teacher,classroom_id)
    if room['course_id']!=course_id:raise ApiError(404,'CLASSROOM_NOT_FOUND')
    return jsonify(groups=[dict(row) for row in db.execute('SELECT id AS group_id,name FROM classroom_groups WHERE classroom_id=? ORDER BY id',(classroom_id,))])
