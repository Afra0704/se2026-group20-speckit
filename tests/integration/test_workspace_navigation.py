from google_support import google_app,google_teacher,post
from workspace_support import flow,path,published


def test_two_groups_follow_fixed_workspace_without_rejoining(google_app,google_teacher,flow):
    catalog,_=published(google_teacher,flow)
    cid=google_teacher.get(path(flow),headers={'Accept':'application/json'}).json['course_id']
    room=post(google_teacher,f'/teacher/courses/{cid}/classrooms',title='本次課堂').json
    students=[google_app.test_client(),google_app.test_client()]
    for client,name in zip(students,['甲組','乙組']):assert post(client,'/classroom-memberships',code=room['code'],group_name=name).status_code==201
    for _ in range(2):
        root=f"/teacher/classrooms/{room['classroom_id']}/activities"
        activity=post(google_teacher,root,import_id=catalog['import_id'],import_version=1).json
        assert google_teacher.get(f"/teacher/workspace/courses/{cid}/classrooms/{room['classroom_id']}").status_code==200
        for client,name in zip(students,['甲組','乙組']):
            state=client.get(f"/classrooms/{room['classroom_id']}/state").json
            assert state['group_name']==name and state['activity']['phase']=='PREPARING'
            assert state['activity']['questions'][0]['items'][0]['prompt_text']
        assert post(google_teacher,root,import_id=catalog['import_id'],import_version=1).status_code==409
        assert post(google_teacher,root+'/'+activity['activity_id']+'/finish').status_code==200
    post(google_teacher,'/teacher/session/logout')
    for client in students:assert client.get(f"/classrooms/{room['classroom_id']}/state").status_code==200
