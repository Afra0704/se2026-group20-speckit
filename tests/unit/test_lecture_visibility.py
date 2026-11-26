from google_support import google_app,google_teacher,post
from workspace_support import flow,path,published
from guided_notes.db import connection


def test_removal_keeps_owned_lookup_and_timestamp_immutable(google_app,google_teacher,flow):
    from guided_notes.notes.repository import owned_import,catalog_row
    catalog,_=published(google_teacher,flow);iid=catalog['import_id']
    cid=google_teacher.get(path(flow),headers={'Accept':'application/json'}).json['course_id']
    route=f'/teacher/notes/courses/{cid}/lectures/{iid}/remove'
    assert post(google_teacher,route,confirm=True).status_code==200
    with google_app.app_context():
        db=connection();first=dict(db.execute('SELECT * FROM notes_lecture_removals').fetchone())
        assert owned_import(db,1,iid)['import_id']==iid
        assert catalog_row(db,1,iid,1)['version']==1
    assert post(google_teacher,route,confirm=True).status_code==200
    with google_app.app_context():assert dict(connection().execute('SELECT * FROM notes_lecture_removals').fetchone())==first
    assert google_teacher.delete(f'/teacher/workspace/courses/{cid}',headers={'X-CSRF-Token':google_teacher.get('/csrf').json['csrf']}).status_code in (404,405)
