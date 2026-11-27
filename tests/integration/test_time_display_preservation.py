import json

from guided_notes import create_app
from guided_notes.db import connection, write_transaction
from guided_notes.google_login.repository import initialize
from google_support import google_app, google_teacher, connect
from conftest import post
from quiz_support import published_quiz, submit_question


def dump(app):
    with app.app_context():
        return '\n'.join(connection().iterdump())


def test_display_restart_and_initialization_preserve_all_records(classroom_app,classroom_teacher,classroom_setup):
    app,teacher=classroom_app,classroom_teacher
    activity,questions=published_quiz(app,teacher,classroom_setup)
    aid=activity['activity_id'];room=classroom_setup[1]
    path=f"/teacher/classrooms/{room['classroom_id']}/activities"
    students=[app.test_client(),app.test_client()]
    group_ids=[]
    for number,client in enumerate(students,1):
        joined=post(client,'/classroom-memberships',code=room['code'],group_name=str(number))
        assert joined.status_code==201
        group_ids.append(str(joined.json['group_id']))
    assert post(teacher,path+'/'+aid+'/start').status_code==200
    question=questions[0]
    # Deliberately opposite client clock claims cannot replace server accept_seq.
    for client,clock in zip(students,('9999-12-31','0001-01-01')):
        client.environ_base['HTTP_DATE']=clock
        assert submit_question(client,aid,question,answer='  =001\n原字串  ').status_code==201
    assert post(teacher,path+'/'+aid+'/finish').status_code==200
    results=teacher.get(f'/activities/{aid}/results',headers={'X-Activity-Role':'teacher'}).json
    with app.app_context():
        db=connection()
        with write_transaction(db):
            initialize(db)
        assert db.execute('SELECT result_version FROM quiz_settlements WHERE activity_id=?',(aid,)).fetchone()[0]
        snapshot=json.loads(db.execute('SELECT snapshot FROM quiz_settlements WHERE activity_id=?',(aid,)).fetchone()[0])
        unit=next(u for u in snapshot['units'] if u['question_id']==question['question_id'])
        assert unit['winner_group_id']==group_ids[0]
        assert all(answer['answer_text']=='  =001\n原字串  ' for answer in unit['answers'])
        # Synthetic sealed fixture; never a user credential or used for Google access.
        db.execute("INSERT INTO google_identities(teacher_id,issuer,subject) VALUES (1,'https://accounts.google.com','synthetic-time-test')")
        instance=db.execute('SELECT instance_uuid FROM auth_instance').fetchone()[0]
        db.execute("""INSERT INTO google_sheets_credentials
            (teacher_id,instance_uuid,issuer,subject,client_id,credential_id,revision,status,granted_scopes,expires_at,secret_blob)
            VALUES (1,?,'https://accounts.google.com','synthetic-time-test','synthetic','synthetic',1,'connected','[]',9999999999,?)""",
            (instance,b'synthetic-sealed-not-a-real-credential'))
    # published_quiz seeds a minimal DTO; normalize the existing optional naming
    # metadata once before taking the baseline, using the unmodified initializer.
    baseline_init=app.test_cli_runner().invoke(args=['init-db'])
    assert baseline_init.exit_code==0,baseline_init.output
    before=dump(app)
    history=teacher.get(path).json
    for _ in range(2):
        assert teacher.get(path).json==history
        assert teacher.get(f'/activities/{aid}/results',headers={'X-Activity-Role':'teacher'}).json==results
    assert dump(app)==before
    initialized=app.test_cli_runner().invoke(args=['init-db'])
    assert initialized.exit_code==0,initialized.output
    assert dump(app)==before
    restarted=create_app(dict(app.config))
    assert dump(restarted)==before
    # Original teacher grant remains valid after restart, without another login.
    replacement=restarted.test_client()
    cookie=teacher.get_cookie(app.config['SESSION_COOKIE_NAME'])
    replacement.set_cookie(app.config['SESSION_COOKIE_NAME'],cookie.value)
    assert replacement.get(path).json==history
    assert dump(restarted)==before
    closed=post(teacher,f"/teacher/classrooms/{room['classroom_id']}/close",confirm=True)
    assert closed.status_code==200
    closed_dump=dump(app)
    assert post(teacher,f"/teacher/classrooms/{room['classroom_id']}/close",confirm=True).status_code==200
    # CSRF is read-only; repeated close must not refresh events or settlement.
    assert dump(app)==closed_dump


def test_real_encryption_fixture_and_google_grant_survive_display_and_init(google_app,google_teacher):
    connect(google_teacher)
    course=post(google_teacher,'/teacher/courses',title='time-preservation').json
    room=post(google_teacher,f"/teacher/courses/{course['course_id']}/classrooms",title='time-preservation').json
    path=f"/teacher/classrooms/{room['classroom_id']}/activities"
    before=dump(google_app)
    assert google_teacher.get(path).status_code==200
    assert google_teacher.get('/teacher/google/sheets/status').json=={'status':'connected'}
    assert dump(google_app)==before
    result=google_app.test_cli_runner().invoke(args=['init-db'])
    assert result.exit_code==0,result.output
    assert google_teacher.get('/teacher/google/sheets/status').json=={'status':'connected'}
    assert dump(google_app)==before
