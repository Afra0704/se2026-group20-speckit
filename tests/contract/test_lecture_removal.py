from google_support import google_app, google_teacher, post, login
from workspace_support import flow, Sheets, path
from guided_notes.db import connection


def save(teacher,fid):
    post(teacher,path(fid,'read'))
    pid=post(teacher,path(fid,'previews'),choice_revision=1,sheet_id=7,name_mode='source').json['preview_id']
    result=post(teacher,path(fid,'confirm'),confirm=True,preview_id=pid)
    assert result.status_code==200,result.text
    return result.json['catalog'],pid


def test_remove_hides_all_versions_keeps_history(google_app,google_teacher,flow):
    catalog,pid=save(google_teacher,flow);iid=catalog['import_id']
    cid=google_teacher.get(path(flow),headers={'Accept':'application/json'}).json['course_id']
    room=post(google_teacher,f'/teacher/courses/{cid}/classrooms',title='上午').json['classroom_id']
    activity=post(google_teacher,f'/teacher/classrooms/{room}/activities',import_id=iid,import_version=1)
    assert activity.status_code==201,activity.text
    aid=activity.json['activity_id']
    remove=f'/teacher/notes/courses/{cid}/lectures/{iid}/remove'
    assert post(google_teacher,remove,confirm=False).status_code==400
    assert post(google_teacher,remove,confirm=True).status_code==200
    assert post(google_teacher,remove,confirm=True).status_code==200
    assert google_teacher.get(f'/teacher/courses/{cid}/catalogs').json['lectures']==[]
    assert google_teacher.get(f'/teacher/notes/catalogs/{iid}/versions/1').status_code==410
    assert post(google_teacher,f'/teacher/notes/import-previews/{pid}/confirm',confirm=True).status_code==410
    history=google_teacher.get(f'/teacher/workspace/activities/{aid}/lecture')
    assert history.status_code==200 and '已移除' in history.text
    assert post(google_teacher,f'/teacher/classrooms/{room}/activities/{aid}/start').status_code==200
    assert post(google_teacher,f'/teacher/classrooms/{room}/activities/{aid}/finish').status_code==200
    assert post(google_teacher,f'/teacher/classrooms/{room}/activities',import_id=iid,import_version=1).status_code==410
    other=login(google_app.test_client(),google_app,'B')
    assert post(other,remove,confirm=True).status_code==404
    with google_app.app_context():
        assert connection().execute('SELECT count(*) FROM notes_catalogs WHERE import_id=?',(iid,)).fetchone()[0]==1
