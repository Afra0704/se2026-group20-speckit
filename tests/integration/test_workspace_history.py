from conftest import post
from test_classroom_notes_integration import prepare_real_course
from test_export_routes import confirm_export


def test_removed_lecture_keeps_existing_unknown_writeback_recovery(classroom_app,classroom_teacher):
    cid,catalog,room=prepare_real_course(classroom_app,classroom_teacher)
    root=f"/teacher/classrooms/{room['classroom_id']}/activities"
    activity=post(classroom_teacher,root,import_id=catalog['import_id'],import_version=1).json
    aid=activity['activity_id']
    assert post(classroom_teacher,root+'/'+aid+'/finish').status_code==200
    snapshot={'contract_version':1,'activity_id':aid,'import_id':catalog['import_id'],'import_version':1,'result_version':'controlled-history','ended':True,'units':[
        {'question_id':q['question_id'],'winner_group_id':'group-A','no_winner':False,'answers':[{'item_id':i['item_id'],'blank_id':i['blank_id'],'answer_text':'  原字串  '} for i in q['items']]} for q in catalog['questions']]}
    classroom_app.config['GET_SETTLED_RESULTS']=lambda db,activity_id:{'snapshot':snapshot,'results':[]}
    preview=post(classroom_teacher,'/teacher/notes/export-previews',activity_id=aid)
    assert preview.status_code==201,preview.text
    assert post(classroom_teacher,f"/teacher/notes/courses/{cid}/lectures/{catalog['import_id']}/remove",confirm=True).status_code==200
    gateway=classroom_app.config['NOTES_GATEWAY'];gateway.fail_at=1;gateway.unknown_applies=True
    first=confirm_export(classroom_teacher,preview.json['preview_id']).json
    fresh=post(classroom_teacher,f"/teacher/notes/operations/{first['operation_id']}/recovery-preview")
    assert fresh.status_code==201,fresh.text
    assert fresh.json['counts']['already_matches']>=2
    report=confirm_export(classroom_teacher,fresh.json['preview_id'],key='removed-history-recovery')
    assert report.status_code==200,report.text
    assert report.json['status']=='completed'
    assert {u['winner_group_id'] for u in report.json['units']}=={'group-A'}
    assert [len(batch) for batch in gateway.writes]==[2,1]
