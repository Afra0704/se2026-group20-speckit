import copy

import pytest

from catalog_support import course_import_id
from conftest import post
from guided_notes.db import connection
from test_export_previews import ended_activity, create
from test_export_routes import confirm_export


def new_activity(teacher, setup):
    course, room = setup
    path = f"/teacher/classrooms/{room['classroom_id']}/activities"
    response = post(teacher, path, import_id=course_import_id(course['course_id']), import_version=1, title='同名活動')
    assert response.status_code == 201, response.text
    return path, response.json['activity_id']


def test_history_lifecycle_preserves_raw_and_internal_counter(classroom_app, classroom_teacher, classroom_setup):
    path, aid = new_activity(classroom_teacher, classroom_setup)
    with classroom_app.app_context():
        connection().execute("UPDATE classroom_activities SET created_at='2026-11-27 03:04:05' WHERE activity_id=?",(aid,))
    row=classroom_teacher.get(path).json['activities'][0]
    assert row['created_at']=='2026-11-27 03:04:05'
    assert row['time_display']['created_at']['text']=='2026-11-27 11:04'
    assert row['time_display']['started_at']['status']=='not_started'
    assert row['time_display']['closed_at']['status']=='not_ended'
    assert 'phase_version' not in row
    assert post(classroom_teacher,path+'/'+aid+'/finish').status_code==200
    row=classroom_teacher.get(path).json['activities'][0]
    assert row['time_display']['started_at']['status']=='skipped_start'
    assert row['time_display']['closed_at']['status']=='known'
    _, second=new_activity(classroom_teacher,classroom_setup)
    assert post(classroom_teacher,path+'/'+second+'/start').status_code==200
    assert classroom_teacher.get(path).json['activities'][1]['time_display']['started_at']['status']=='known'
    assert post(classroom_teacher,path+'/'+second+'/finish').status_code==200
    with classroom_app.app_context():
        connection().execute('UPDATE classroom_activities SET started_at=NULL WHERE activity_id=?',(second,))
    assert classroom_teacher.get(path).json['activities'][1]['time_display']['started_at']['status']=='missing'
    before=classroom_teacher.get(path).json
    assert post(classroom_teacher,path+'/'+second+'/finish').status_code==409
    assert classroom_teacher.get(path).json==before


@pytest.mark.parametrize('raw,status', [('bad','invalid'),('2026-02-30 00:00:00','invalid'),
    ('','missing'),('2026-11-27 03:04:05','known')])
def test_single_bad_event_does_not_break_history(classroom_app,classroom_teacher,classroom_setup,raw,status):
    path,aid=new_activity(classroom_teacher,classroom_setup)
    with classroom_app.app_context():
        connection().execute('UPDATE classroom_activities SET created_at=? WHERE activity_id=?',(raw,aid))
    response=classroom_teacher.get(path)
    assert response.status_code==200
    row=response.json['activities'][0]
    assert row['created_at']==raw and row['time_display']['created_at']['status']==status


def test_history_permissions_and_student_visibility(classroom_app,classroom_teacher,classroom_setup):
    path,aid=new_activity(classroom_teacher,classroom_setup)
    other=classroom_app.test_client()
    assert other.get(path).status_code==401
    assert post(other,'/teacher/session',username='other',password='test-password').status_code==204
    assert other.get(path).status_code==404
    student=classroom_app.test_client()
    room=classroom_setup[1]
    assert post(student,'/classroom-memberships',code=room['code'],group_name='1').status_code==201
    assert student.get(path).status_code==401
    state=student.get(f"/classrooms/{room['classroom_id']}/state")
    assert state.status_code==200 and 'time_display' not in state.text
    assert post(classroom_teacher,f"/teacher/classrooms/{room['classroom_id']}/close",confirm=True).status_code==200
    closed=student.get(f"/classrooms/{room['classroom_id']}/state")
    assert closed.status_code==200 and closed.json.get('activity') is None
    assert closed.json['classroom_state']=='CLOSED'
    assert student.get(f"/classrooms/{room['classroom_id']}/results").status_code==409
    assert classroom_teacher.get(path).json['activities'][0]['time_display']['started_at']['status']=='skipped_start'


def test_notes_html_uses_events_but_keeps_json_original(app,teacher,writable,monkeypatch):
    from guided_notes.notes import repository as repo
    monkeypatch.setattr(repo,'now',lambda:'2026-11-27T03:04:05.123456+00:00')
    aid,catalog,snapshot=ended_activity(app,teacher)
    preview=create(teacher,aid).json
    json_before=copy.deepcopy(preview)
    for path in ('/teacher/notes','/teacher/notes/export-previews',preview['preview_url']):
        page=teacher.get(path)
        assert page.status_code==200
        assert '2026-11-27 11:04' in page.text and 'UTC+08:00' in page.text
        assert '11:04:05' not in page.text
    assert '匯入確認' in teacher.get('/teacher/notes').text
    assert '預覽' in teacher.get(preview['preview_url']).text
    assert teacher.get(preview['preview_url'],headers={'Accept':'application/json'}).json==json_before
    report=confirm_export(teacher,preview['preview_id']).json
    url=f"/teacher/notes/operations/{report['operation_id']}"
    raw=copy.deepcopy(report)
    calls,writes=len(writable.calls),len(writable.writes)
    page=teacher.get(url)
    assert page.status_code==200 and '2026-11-27 11:04' in page.text and 'UTC+08:00' in page.text
    assert teacher.get(url,headers={'Accept':'application/json'}).json==raw
    assert (len(writable.calls),len(writable.writes))==(calls,writes)
    assert all(i['verified_at']=='2026-11-27T03:04:05.123456+00:00' for u in raw['units'] for i in u['items'])
    assert snapshot['result_version']=='settled-1'


@pytest.mark.parametrize('raw,status_text', [('bad','時間資料無法辨識'),('', '時間未記錄'),
    ('2026-11-27 03:04:05','時區未確認')])
def test_bad_notes_preview_still_renders(app,teacher,writable,raw,status_text):
    aid,_,_=ended_activity(app,teacher)
    preview=create(teacher,aid).json
    with app.app_context():
        connection().execute('UPDATE notes_export_previews SET created_at=? WHERE preview_id=?',(raw,preview['preview_id']))
    page=teacher.get(preview['preview_url'])
    assert page.status_code==200 and status_text in page.text


def test_readback_missing_and_non_verified_are_distinct(app,teacher,writable):
    aid,_,_=ended_activity(app,teacher)
    preview=create(teacher,aid).json
    report=confirm_export(teacher,preview['preview_id']).json
    url=f"/teacher/notes/operations/{report['operation_id']}"
    with app.app_context():
        connection().execute('UPDATE notes_write_items SET verified_at=NULL WHERE operation_id=?',(report['operation_id'],))
    assert '時間未記錄' in teacher.get(url).text
    with app.app_context():
        connection().execute("UPDATE notes_write_items SET status='unknown' WHERE operation_id=?",(report['operation_id'],))
    assert '尚未驗證' in teacher.get(url).text
