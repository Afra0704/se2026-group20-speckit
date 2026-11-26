import time
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from google_support import google_app,google_teacher,post,login
from workspace_support import flow,Sheets,path
from guided_notes.db import connection


def clone(app,client):
    copy=app.test_client();copy.set_cookie('session',client.get_cookie('session').value);return copy


def test_claim_timeout_takeover_and_late_result(google_app,google_teacher,flow):
    started=Event();release=Event();second=Event();release_second=Event()
    now=[time.time()];google_app.config['WORKSPACE_CLOCK']=lambda:now[0]
    gateway=google_app.config['NOTES_GATEWAY'];calls=[0]
    def hook():
        calls[0]+=1
        if calls[0]==1:
            started.set();assert release.wait(10)
        elif calls[0]==2:
            second.set();assert release_second.wait(10)
    gateway.hook=hook
    a=clone(google_app,google_teacher);b=clone(google_app,google_teacher)
    with ThreadPoolExecutor(2) as pool:
        old=pool.submit(post,a,path(flow,'read'))
        assert started.wait(5)
        now[0]+=119
        assert post(google_teacher,path(flow,'retry')).status_code==409
        now[0]+=1
        new=pool.submit(post,b,path(flow,'retry'))
        assert second.wait(5)
        assert post(google_teacher,path(flow,'retry')).status_code==409
        release.set();assert old.result(5).status_code==409
        release_second.set();assert new.result(5).status_code==200
    assert calls[0]==2
    assert google_teacher.get(path(flow),headers={'Accept':'application/json'}).json['status']=='worksheets_ready'


def test_late_read_after_logout_cannot_persist(google_app,google_teacher,flow):
    other=clone(google_app,google_teacher)
    google_app.config['NOTES_GATEWAY'].hook=lambda:post(other,'/teacher/session/logout')
    assert post(google_teacher,path(flow,'read')).status_code==401
    with google_app.app_context():assert connection().execute('SELECT worksheets_json FROM workspace_import_flows WHERE flow_id=?',(flow,)).fetchone()[0] is None


def test_other_teacher_cannot_read_flow(google_app,google_teacher,flow):
    other=login(google_app.test_client(),google_app,'B')
    assert other.get(path(flow),headers={'Accept':'application/json'}).status_code==404
    assert post(other,path(flow,'read')).status_code==404
