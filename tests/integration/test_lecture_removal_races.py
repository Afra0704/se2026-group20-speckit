from concurrent.futures import ThreadPoolExecutor
from threading import Event
import sqlite3
import pytest
from google_support import google_app,google_teacher,post
from workspace_support import flow,path,published,Sheets
from guided_notes.db import connection


def clone(app,client):
    copy=app.test_client();copy.set_cookie('session',client.get_cookie('session').value);return copy


def test_remove_wins_after_catalog_was_fetched(google_app,google_teacher,flow,monkeypatch):
    from guided_notes.activities import classroom_routes
    catalog,_=published(google_teacher,flow)
    cid=google_teacher.get(path(flow),headers={'Accept':'application/json'}).json['course_id'];iid=catalog['import_id']
    room=post(google_teacher,f'/teacher/courses/{cid}/classrooms',title='上課').json['classroom_id']
    entered=Event();release=Event();original=classroom_routes.get_display_content
    def held(*args):
        result=original(*args);entered.set();assert release.wait(10);return result
    monkeypatch.setattr(classroom_routes,'get_display_content',held)
    client=clone(google_app,google_teacher)
    with ThreadPoolExecutor(1) as pool:
        future=pool.submit(post,client,f'/teacher/classrooms/{room}/activities',import_id=iid,import_version=1)
        assert entered.wait(5)
        assert post(google_teacher,f'/teacher/notes/courses/{cid}/lectures/{iid}/remove',confirm=True).status_code==200
        release.set();assert future.result(5).status_code==410
    with google_app.app_context():
        assert connection().execute('SELECT count(*) FROM activities').fetchone()[0]==0
        assert connection().execute('SELECT current_activity_id FROM classrooms WHERE id=?',(room,)).fetchone()[0] is None


def test_remove_wins_during_version_source_read(google_app,google_teacher,flow):
    catalog,_=published(google_teacher,flow);iid=catalog['import_id']
    cid=google_teacher.get(path(flow),headers={'Accept':'application/json'}).json['course_id']
    pid=post(google_teacher,'/teacher/notes/import-previews',spreadsheet_url='https://docs.google.com/spreadsheets/d/synthetic/edit',sheet_id=7,course_id=cid).json['preview_id']
    entered=Event();release=Event()
    def held():entered.set();assert release.wait(10)
    google_app.config['NOTES_GATEWAY'].hook=held
    client=clone(google_app,google_teacher)
    with ThreadPoolExecutor(1) as pool:
        future=pool.submit(post,client,f'/teacher/notes/import-previews/{pid}/confirm',confirm=True,existing_import_id=iid)
        assert entered.wait(5)
        assert post(google_teacher,f'/teacher/notes/courses/{cid}/lectures/{iid}/remove',confirm=True).status_code==200
        release.set();assert future.result(5).status_code==410
    with google_app.app_context():assert connection().execute('SELECT count(*) FROM notes_catalogs WHERE import_id=?',(iid,)).fetchone()[0]==1


def test_version_wins_then_entire_lecture_removed_and_reimport_new(google_app,google_teacher,flow):
    catalog,_=published(google_teacher,flow);iid=catalog['import_id']
    cid=google_teacher.get(path(flow),headers={'Accept':'application/json'}).json['course_id']
    def preview():return post(google_teacher,'/teacher/notes/import-previews',spreadsheet_url='https://docs.google.com/spreadsheets/d/synthetic/edit',sheet_id=7,course_id=cid).json['preview_id']
    pid=preview()
    assert post(google_teacher,f'/teacher/notes/import-previews/{pid}/confirm',confirm=True,existing_import_id=iid).json['import_version']==2
    assert post(google_teacher,f'/teacher/notes/courses/{cid}/lectures/{iid}/remove',confirm=True).status_code==200
    assert google_teacher.get(f'/teacher/courses/{cid}/catalogs').json['lectures']==[]
    new_pid=preview();saved=post(google_teacher,f'/teacher/notes/import-previews/{new_pid}/confirm',confirm=True)
    assert saved.status_code==200 and saved.json['import_id']!=iid and saved.json['import_version']==1
    with google_app.app_context():
        db=connection()
        with pytest.raises(sqlite3.IntegrityError,match='lecture_removed'):
            db.execute("INSERT INTO activities(id,teacher_id,code,import_id,import_version) VALUES('blocked',1,'BLOCKED',?,1)",(iid,))
