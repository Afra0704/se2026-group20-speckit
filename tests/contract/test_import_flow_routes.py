from google_support import google_app,google_teacher,post
from guided_notes.db import connection
from workspace_support import flow,Sheets,path

def test_two_tabs_confirm_only_the_preview_each_page_displayed(google_app,google_teacher,flow):
    post(google_teacher,path(flow,'read'))
    old=post(google_teacher,path(flow,'previews'),choice_revision=1,sheet_id=7,name_mode='source').json['preview_id']
    page_a=google_teacher.get(path(flow),headers={'Accept':'text/html'})
    assert f'name="preview_id" value="{old}"' in page_a.text
    revision=google_teacher.get(path(flow),headers={'Accept':'application/json'}).json['revision']
    post(google_teacher,path(flow,'revise'),expected_revision=revision)
    new=post(google_teacher,path(flow,'previews'),choice_revision=2,sheet_id=7,name_mode='custom',custom_title='分頁B的新預覽').json['preview_id']
    assert new!=old
    assert f'name="preview_id" value="{new}"' in google_teacher.get(path(flow),headers={'Accept':'text/html'}).text
    response=post(google_teacher,path(flow,'confirm'),confirm=True,preview_id=old)
    assert response.status_code==409 and response.json['error']['code']=='PREVIEW_STALE'
    with google_app.app_context():
        assert connection().execute('SELECT count(*) FROM notes_catalogs').fetchone()[0]==0
    assert post(google_teacher,path(flow,'confirm'),confirm=True,preview_id=new).status_code==200

def test_link_preview_revise_confirm(google_app, google_teacher, flow):
    assert post(google_teacher,path(flow,'read')).status_code==200
    body=dict(choice_revision=1,sheet_id=7,name_mode='source')
    first=post(google_teacher,path(flow,'previews'),**body)
    assert first.status_code==201,first.text
    pid=first.json['preview_id']; calls=len(google_app.config['NOTES_GATEWAY'].calls)
    assert post(google_teacher,path(flow,'previews'),**body).json['preview_id']==pid
    assert len(google_app.config['NOTES_GATEWAY'].calls)==calls
    assert post(google_teacher,path(flow,'previews'),**{**body,'name_mode':'custom','custom_title':'第二份'}).status_code==409
    current=google_teacher.get(path(flow),headers={'Accept':'application/json'}).json
    assert post(google_teacher,path(flow,'revise'),expected_revision=current['revision']).status_code==200
    assert post(google_teacher,f'/teacher/notes/import-previews/{pid}/confirm',confirm=True).status_code in (409,410)
    assert post(google_teacher,path(flow,'previews'),**body).status_code==409
    new=post(google_teacher,path(flow,'previews'),choice_revision=2,sheet_id=7,name_mode='custom',custom_title='第二份')
    assert new.status_code==201,new.text
    result=post(google_teacher,path(flow,'confirm'),confirm=True,preview_id=new.json['preview_id'])
    assert result.status_code==200,result.text
    assert result.json['catalog']['question_count']==2
    assert post(google_teacher,path(flow,'read')).status_code==409
    assert post(google_teacher,path(flow,'confirm'),confirm=True,preview_id=new.json['preview_id']).json['catalog']==result.json['catalog']
    assert post(google_teacher,path(flow,'revise'),expected_revision=google_teacher.get(path(flow),headers={'Accept':'application/json'}).json['revision']).status_code==409


def test_flow_expires_and_cancels_old_preview(google_app,google_teacher,flow):
    post(google_teacher,path(flow,'read'))
    pid=post(google_teacher,path(flow,'previews'),choice_revision=1,sheet_id=7,name_mode='source').json['preview_id']
    with google_app.app_context():connection().execute('UPDATE workspace_import_flows SET expires_at=0 WHERE flow_id=?',(flow,))
    assert post(google_teacher,path(flow,'retry')).status_code==410
    assert post(google_teacher,f'/teacher/notes/import-previews/{pid}/confirm',confirm=True).status_code in (409,410)


def test_rejects_unknown_fields_and_malformed_choice_before_persist(google_teacher,flow):
    assert post(google_teacher,path(flow,'read'),teacher_id=1).status_code==400
    assert post(google_teacher,path(flow,'read')).status_code==200
    assert post(google_teacher,path(flow,'previews'),choice_revision=True,sheet_id=7,name_mode='source').status_code==400
    assert post(google_teacher,path(flow,'previews'),choice_revision=1,sheet_id=7,name_mode='source',custom_title={'unexpected':1}).status_code==400
    response=post(google_teacher,path(flow,'previews'),choice_revision=1,sheet_id=7,name_mode='source')
    assert response.status_code==201
    assert post(google_teacher,path(flow,'confirm'),confirm=True,preview_id=response.json['preview_id'],existing_import_id=[]).status_code==400
