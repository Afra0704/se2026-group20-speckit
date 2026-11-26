from google_support import google_app, google_teacher, post, start, complete, login, connect
from guided_notes.db import connection


def test_newest_start_wins_and_other_browser_independent(google_app):
    a,b=google_app.test_client(),google_app.test_client()
    old=start(a);independent=start(b);new=start(a)
    assert 'GOOGLE_FLOW_SUPERSEDED' in complete(a,old).location
    assert complete(a,new).location=='/teacher'
    assert complete(b,independent).location=='/teacher'


def test_logout_during_exchange_cannot_finalize(google_app,google_teacher):
    state=start(google_teacher)
    def revoke():
        # Separate connection simulates a logout committed while HTTPS is in flight.
        import sqlite3
        db=sqlite3.connect(google_app.config['DATABASE'])
        db.execute('UPDATE auth_browsers SET epoch=epoch+1,teacher_grant_hash=NULL')
        db.commit();db.close()
    google_app.config['GOOGLE_PROVIDER'].hook=revoke
    assert 'GOOGLE_FLOW_SUPERSEDED' in complete(google_teacher,state).location
    assert google_teacher.get('/teacher/session').json['authenticated'] is False


def test_disable_during_exchange(google_app,google_teacher):
    state=start(google_teacher)
    google_app.config['GOOGLE_PROVIDER'].hook=lambda: connection().execute('UPDATE teachers SET active=0 WHERE id=1')
    assert 'TEACHER_DISABLED' in complete(google_teacher,state).location


def test_switch_revokes_only_this_browser(google_app,google_teacher):
    other=login(google_app.test_client(),google_app)
    old=google_teacher.get_cookie('session').value
    login(google_teacher,google_app,'B')
    assert other.get('/teacher/session').json['teacher']['display_name']=='Teacher A'
    google_teacher.set_cookie('session',old)
    assert not google_teacher.get('/teacher/session').json['authenticated']
