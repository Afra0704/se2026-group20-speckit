from flask import Blueprint, jsonify, redirect, render_template, request, url_for

from ..auth import csrf_token, require_teacher
from ..http import ApiError
from . import repository, service, sheets_service
from .provider import provider

google_login = Blueprint('google_login', __name__)

MESSAGES = {
    'GOOGLE_NOT_CONFIGURED':'尚未完成 Google 網頁登入設定，請依操作說明設定 Web client。',
    'GOOGLE_FLOW_INVALID':'登入驗證未通過，請重新開始。',
    'GOOGLE_FLOW_EXPIRED':'登入已逾時，請重新開始。',
    'GOOGLE_FLOW_SUPERSEDED':'本次流程已被新的操作取代，請確認目前登入身分。',
    'GOOGLE_LOGIN_CANCELLED':'你已取消授權，可以重新嘗試。',
    'GOOGLE_UNAVAILABLE':'暫時無法連線 Google，請稍後重試。',
    'TEACHER_DISABLED':'這個教師帳號已停用。',
    'GOOGLE_ACCOUNT_MISMATCH':'請選擇與目前教師相同的 Google 帳號連接講義。',
    'SHEETS_SCOPE_REQUIRED':'需要同意 Google Sheets 讀寫權限才能連接講義。',
    'SHEETS_CONNECT_REQUIRED':'請先按「連接我的 Google Sheets」完成講義授權。',
    'SHEETS_REAUTH_REQUIRED':'講義授權已失效，請重新連接 Google Sheets。',
    'GOOGLE_CREDENTIALS_UNAVAILABLE':'無法讀取授權資料，請檢查伺服器設定。',
    'GOOGLE_REFRESH_TIMEOUT':'更新 Google 授權逾時，請稍後透過原操作或恢復流程重試。',
    'GOOGLE_REFRESH_BUSY':'Google 授權正在更新，請稍後重試。',
    'GOOGLE_CREDENTIALS_REFRESH_REQUIRED':'授權已逾時，請透過原操作或回填恢復流程重試。',
    'GOOGLE_REAUTH_REQUIRED':'Google 拒絕目前授權，請重新連接 Google Sheets。',
}


@google_login.app_template_global()
def google_error_message(code):
    return MESSAGES.get(code,'操作未完成，請重新嘗試。')


def teacher_or_none():
    try:
        return require_teacher()
    except ApiError as error:
        if error.status not in (401,403):
            raise
        return None


def safe_status():
    teacher = teacher_or_none()
    if not teacher:
        return {'authenticated':False,'teacher':None,'sheets':None}
    identity = repository.identity(teacher.teacher_id)
    return {'authenticated':True,'teacher':{'display_name':identity['display_name'],'email':identity['email']},
            'sheets':sheets_service.authorization_status(teacher)}


@google_login.get('/teacher/login')
def login():
    if teacher_or_none():
        return redirect(url_for('teacher.page'), code=303)
    return render_template('identity/login.html', csrf=csrf_token(), error=request.args.get('error'))


@google_login.post('/auth/google/start')
def start():
    return redirect(service.start(), code=303)


@google_login.errorhandler(ApiError)
def auth_error(error):
    if request.is_json or request.accept_mimetypes.best == 'application/json' or error.code in ('AUTH_REQUIRED','FORBIDDEN','INVALID_CSRF'):
        response = jsonify(error=error.code)
        response.status_code = error.status
        if error.retry_after is not None:
            response.headers['Retry-After'] = str(error.retry_after)
        return response
    target = '/teacher' if teacher_or_none() else '/teacher/login'
    return redirect(target+'?error='+error.code,code=303)


@google_login.get('/auth/google/callback')
def callback():
    attempt = None
    target = '/teacher/login'
    try:
        if any(len(request.args.getlist(key)) != 1 for key in request.args) or not request.args.get('state'):
            raise ApiError(400,'GOOGLE_FLOW_INVALID')
        if ('code' in request.args) == ('error' in request.args) or not (request.args.get('code') or request.args.get('error')):
            raise ApiError(400,'GOOGLE_FLOW_INVALID')
        attempt = service.claim(request.args['state'])
        from .flow_context import context
        flow_context = context(attempt)
        if flow_context:
            target = '/teacher/workspace/imports/' + flow_context['flow_id']
        elif attempt['purpose'] == 'sheets':
            target = '/teacher/notes'
        if request.args.get('error'):
            raise ApiError(400,'GOOGLE_LOGIN_CANCELLED')
        result = provider().exchange_and_verify(attempt, request.args['code'])
        service.finish(attempt, result)
        return redirect(target if flow_context else '/teacher/notes' if attempt['purpose']=='sheets' else '/teacher', code=303)
    except ApiError as error:
        service.fail(attempt)
        if target.startswith('/teacher/workspace/imports/'):
            from flask import flash
            flash(MESSAGES.get(error.code, '授權未完成，請重新嘗試。'), 'error')
            return redirect(target, code=303)
        return redirect(target+'?error='+error.code, code=303)
    except Exception:
        service.fail(attempt)
        return redirect(target+'?error=GOOGLE_UNAVAILABLE', code=303)


@google_login.get('/teacher/session')
def status():
    return jsonify(safe_status())


@google_login.post('/teacher/session/logout')
def logout():
    service.logout()
    if request.is_json or request.accept_mimetypes.best == 'application/json':
        return '',204
    return redirect('/',code=303)


@google_login.post('/teacher/google/sheets/connect')
def connect():
    require_teacher()
    return redirect(service.start('sheets'),code=303)


@google_login.get('/teacher/google/sheets/status')
def sheets_status():
    return jsonify(sheets_service.authorization_status(require_teacher()))
