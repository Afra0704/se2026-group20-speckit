from conftest import post
from test_classroom_notes_integration import prepare_real_course
from test_export_routes import confirm_export
from quiz_support import submit


def test_removed_lecture_keeps_existing_unknown_writeback_recovery(classroom_app,classroom_teacher):
    cid,catalog,room=prepare_real_course(classroom_app,classroom_teacher)
    root=f"/teacher/classrooms/{room['classroom_id']}/activities"
    activity=post(classroom_teacher,root,import_id=catalog['import_id'],import_version=1).json
    aid=activity['activity_id']
    student=classroom_app.test_client()
    group=post(student,'/classroom-memberships',code=room['code'],group_name='A').json['group_id']
    assert post(classroom_teacher,root+'/'+aid+'/start').status_code==200
    for q in catalog['questions']:
        assert submit(student,aid,question_id=q['question_id'],items=[
            {'item_id':i['item_id'],'answer_text':'  原字串  '} for i in q['items']]).status_code==201
    assert post(classroom_teacher,f"/teacher/notes/courses/{cid}/lectures/{catalog['import_id']}/remove",confirm=True).status_code==200
    assert post(classroom_teacher,root+'/'+aid+'/finish').status_code==200
    preview=post(classroom_teacher,'/teacher/notes/export-previews',activity_id=aid)
    assert preview.status_code==201,preview.text
    gateway=classroom_app.config['NOTES_GATEWAY'];gateway.fail_at=1;gateway.unknown_applies=True
    first=confirm_export(classroom_teacher,preview.json['preview_id']).json
    fresh=post(classroom_teacher,f"/teacher/notes/operations/{first['operation_id']}/recovery-preview")
    assert fresh.status_code==201,fresh.text
    assert fresh.json['counts']['already_matches']>=2
    report=confirm_export(classroom_teacher,fresh.json['preview_id'],key='removed-history-recovery')
    assert report.status_code==200,report.text
    assert report.json['status']=='completed'
    assert {u['winner_group_id'] for u in report.json['units']}=={str(group)}
    assert [len(batch) for batch in gateway.writes]==[2,1]
