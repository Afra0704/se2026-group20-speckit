from concurrent.futures import ThreadPoolExecutor
from google_support import google_app,google_teacher,post,start,complete,login
from guided_notes.db import connection


def test_parallel_same_subject_only_one_teacher(google_app):
    clients=[google_app.test_client(),google_app.test_client()]
    states=[start(client) for client in clients]
    with ThreadPoolExecutor(2) as pool:
        responses=list(pool.map(lambda pair:complete(*pair),zip(clients,states)))
    assert all(response.location=='/teacher' for response in responses)
    with google_app.app_context():
        assert connection().execute('SELECT count(*) FROM teachers').fetchone()[0]==1
        assert connection().execute('SELECT count(*) FROM grants').fetchone()[0]==2


def test_parallel_same_callback_only_one_exchange(google_app):
    original=google_app.test_client();state=start(original);cookie=original.get_cookie('session').value
    clients=[google_app.test_client(),google_app.test_client()]
    for client in clients:client.set_cookie('session',cookie)
    with ThreadPoolExecutor(2) as pool:responses=list(pool.map(lambda client:complete(client,state),clients))
    assert sum(response.location=='/teacher' for response in responses)==1
    assert sum(call[0]=='exchange' for call in google_app.config['GOOGLE_PROVIDER'].calls)==1


def test_expired_grant_can_reauthenticate(google_app,google_teacher):
    with google_app.app_context():connection().execute('UPDATE grants SET expires=0')
    assert not google_teacher.get('/teacher/session').json['authenticated']
    login(google_teacher,google_app)
    assert google_teacher.get('/teacher/session').json['authenticated']


def test_atomic_finalize_failure_leaves_no_half_teacher(google_app):
    with google_app.app_context():
        connection().executescript("CREATE TRIGGER fail_identity BEFORE INSERT ON google_identities BEGIN SELECT RAISE(ABORT,'injected'); END;")
    client=google_app.test_client()
    assert 'GOOGLE_UNAVAILABLE' in complete(client,start(client)).location
    with google_app.app_context():
        assert connection().execute('SELECT count(*) FROM teachers').fetchone()[0]==0
        assert connection().execute('SELECT count(*) FROM grants').fetchone()[0]==0


def test_failed_switch_keeps_original(google_app,google_teacher):
    from guided_notes.http import ApiError
    def timeout():raise ApiError(503,'GOOGLE_UNAVAILABLE')
    google_app.config['GOOGLE_PROVIDER'].hook=timeout
    assert 'GOOGLE_UNAVAILABLE' in complete(google_teacher,start(google_teacher)).location
    assert google_teacher.get('/teacher/session').json['teacher']['display_name']=='Teacher A'
