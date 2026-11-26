import json
import pytest
from google_support import google_app, google_teacher, post, start, complete, login
from guided_notes.db import connection


def test_role_home_and_student_without_google(google_app):
    client=google_app.test_client()
    html=client.get('/').get_data(as_text=True)
    assert '我是老師' in html and '我是學生' in html
    assert client.get('/student').status_code == 200
    assert client.get('/teacher').location == '/teacher/login'
    assert client.get('/teacher/session').json == {'authenticated':False,'teacher':None,'sheets':None}
    assert client.post('/auth/google/start').status_code == 403
    assert post(client,'/teacher/session',username='teacher',password='anything').status_code == 410


def test_first_repeat_identity_and_no_secret_in_session(google_app,google_teacher):
    status=google_teacher.get('/teacher/session').json
    assert status['authenticated'] and status['sheets']['status']=='not_connected'
    assert set(status['teacher'])=={'display_name','email'}
    with google_teacher.session_transaction() as cookie:
        assert set(cookie).issubset({'auth_browser','csrf','teacher_grant'})
    login(google_teacher,google_app)
    with google_app.app_context():
        assert connection().execute('SELECT count(*) FROM teachers').fetchone()[0] == 1
    html=google_teacher.get('/teacher').get_data(as_text=True)
    assert 'Teacher A' in html and 'name="password"' not in html


def test_cancel_switch_preserves_original(google_app,google_teacher):
    state=start(google_teacher)
    response=google_teacher.get('/auth/google/callback',query_string={'state':state,'error':'access_denied','error_description':'sentinel'})
    assert response.location.endswith('GOOGLE_LOGIN_CANCELLED')
    assert google_teacher.get('/teacher/session').json['teacher']['display_name']=='Teacher A'
    assert 'sentinel' not in response.get_data(as_text=True)


@pytest.mark.parametrize('query', [{},{'state':'bad','code':'bad'}, {'state':'bad','code':'c','error':'e'}, [('state','a'),('state','b'),('code','c')]])
def test_bad_callback_clean_redirect(google_app,query):
    response=google_app.test_client().get('/auth/google/callback',query_string=query)
    assert response.status_code==303 and 'GOOGLE_FLOW_INVALID' in response.location
    assert response.headers['Referrer-Policy']=='no-referrer'


def test_foreign_browser_replay_and_expired(google_app):
    a,b=google_app.test_client(),google_app.test_client()
    state=start(a)
    assert 'GOOGLE_FLOW_INVALID' in complete(b,state).location
    assert complete(a,state).location=='/teacher'
    assert 'GOOGLE_FLOW_SUPERSEDED' in complete(a,state).location
    state=start(a)
    with google_app.app_context(): connection().execute('UPDATE google_oauth_attempts SET expires_at=0')
    assert 'GOOGLE_FLOW_EXPIRED' in complete(a,state).location


def test_logout_preserves_student_state_and_revokes_old_cookie(google_app,google_teacher):
    with google_teacher.session_transaction() as session:
        session.update(student_grant='student-sentinel',classroom_grant='class-sentinel',proof='proof-sentinel')
    old_cookie=google_teacher.get_cookie('session').value
    assert post(google_teacher,'/teacher/session/logout').status_code==204
    with google_teacher.session_transaction() as session:
        assert session['student_grant']=='student-sentinel' and session['proof']=='proof-sentinel'
    google_teacher.set_cookie('session',old_cookie)
    assert not google_teacher.get('/teacher/session').json['authenticated']
    assert post(google_teacher,'/teacher/courses',title='stale').status_code==401


def test_anonymous_logout_cancels_attempt(google_app):
    client=google_app.test_client();state=start(client)
    assert post(client,'/teacher/session/logout').status_code==204
    assert 'GOOGLE_FLOW_SUPERSEDED' in complete(client,state).location


def test_teacher_disable_and_same_email_distinct_subs(google_app,google_teacher):
    b=login(google_app.test_client(),google_app,'B')
    with google_app.app_context():
        assert connection().execute('SELECT count(*) FROM teachers').fetchone()[0]==2
        connection().execute('UPDATE teachers SET active=0 WHERE id=1')
    assert google_teacher.get('/teacher/session').json['authenticated'] is False
    google_app.config['GOOGLE_PROVIDER'].subject='A'
    assert 'TEACHER_DISABLED' in complete(b,start(b)).location


def test_unconfigured_does_not_block_students(google_app):
    google_app.config['GOOGLE_WEB_CLIENT_SECRETS']=None
    client=google_app.test_client()
    assert client.get('/student').status_code==200
    assert post(client,'/auth/google/start').json['error']=='GOOGLE_NOT_CONFIGURED'


def test_formal_cli_rejects_before_password_prompt(google_app):
    result=google_app.test_cli_runner().invoke(args=['init-teacher','someone'])
    assert result.exit_code!=0 and 'Google login' in result.output
    assert 'Password:' not in result.output
