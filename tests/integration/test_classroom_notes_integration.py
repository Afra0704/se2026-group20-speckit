import json

from conftest import post
from guided_notes.db import connection, write_transaction
from test_export_routes import confirm_export
from test_import_routes import URL
from writeback_support import WritableSheets


def prepare_real_course(classroom_app, classroom_teacher):
    classroom_app.config.update(LIST_COURSE_CATALOGS=None, GET_COURSE_CATALOG=None,
                               GET_CATALOG=None, NOTES_GATEWAY=WritableSheets())
    course = post(classroom_teacher, "/teacher/courses", title="真實課程 provider").json
    cid = course["course_id"]
    preview = post(classroom_teacher, "/teacher/notes/import-previews", spreadsheet_url=URL,
                   sheet_id=7, course_id=cid).json
    catalog = post(classroom_teacher, f"/teacher/notes/import-previews/{preview['preview_id']}/confirm", confirm=True).json
    room = post(classroom_teacher, f"/teacher/courses/{cid}/classrooms", title="整合課堂").json
    return cid, catalog, room


def test_real_course_catalog_binding_switch_and_writeback_adapter(classroom_app, classroom_teacher):
    cid, catalog, room = prepare_real_course(classroom_app, classroom_teacher)
    choices = classroom_teacher.get(f"/teacher/courses/{cid}/catalogs").json
    assert choices["lectures"][0]["import_id"] == catalog["import_id"]
    other = post(classroom_teacher, "/teacher/courses", title="其他課程").json["course_id"]
    other_room = post(classroom_teacher, f"/teacher/courses/{other}/classrooms", title="另一課堂").json
    assert post(classroom_teacher, f"/teacher/classrooms/{other_room['classroom_id']}/activities",
                import_id=catalog["import_id"], import_version=1).status_code == 404
    path = f"/teacher/classrooms/{room['classroom_id']}/activities"
    ids = []
    student = classroom_app.test_client()
    joined = post(student, "/classroom-memberships", code=room["code"], group_name="1").json
    for _ in range(2):
        aid = post(classroom_teacher, path, import_id=catalog["import_id"], import_version=1).json["activity_id"]
        ids.append(aid)
        assert post(classroom_teacher, f"{path}/{aid}/start").status_code == 200
        state = student.get(f"/classrooms/{room['classroom_id']}/state").json
        assert state["current_activity_id"] == aid
        assert post(classroom_teacher, f"{path}/{aid}/finish").status_code == 200
    aid = ids[0]
    snapshot = {"contract_version":1,"activity_id":aid,"import_id":catalog["import_id"],"import_version":1,
        "result_version":"integration-1","ended":True,"units":[{
            "question_id":q["question_id"],"winner_group_id":str(joined["group_id"]),"no_winner":False,
            "answers":[{"item_id":i["item_id"],"blank_id":i["blank_id"],"answer_text":"  原字串  "} for i in q["items"]]
        } for q in catalog["questions"]]}
    classroom_app.config["GET_SETTLED_RESULTS"] = lambda db, activity_id: {"snapshot":snapshot,"results":[]} if activity_id==aid else None
    preview = post(classroom_teacher, "/teacher/notes/export-previews", activity_id=aid)
    assert preview.status_code == 201
    assert {item["winner_group_id"] for item in preview.json["items"]} == {str(joined["group_id"])}
    page = classroom_teacher.get(preview.json["preview_url"], headers={"Accept": "text/html"})
    assert "第 1 組" in page.text
    report = confirm_export(classroom_teacher, preview.json["preview_id"], key="integration").json
    assert report["status"] == "completed" and report["counts"]["verified"] == 3
    page = classroom_teacher.get(f"/teacher/notes/operations/{report['operation_id']}",
                                 headers={"Accept": "text/html"})
    assert "第 1 組" in page.text
    assert [len(batch) for batch in classroom_app.config["NOTES_GATEWAY"].writes] == [2,1]
    assert student.get(f"/classrooms/{room['classroom_id']}/results").json["activities"][0]["activity_id"] == aid
    assert post(classroom_teacher, f"/teacher/classrooms/{room['classroom_id']}/close", confirm=True).status_code == 200
    assert student.get(f"/classrooms/{room['classroom_id']}/results").status_code == 409
    # Closing student access must not remove the owner's original export history.
    assert post(classroom_teacher, '/teacher/notes/export-previews', activity_id=aid).status_code == 201


def test_classroom_read_releases_transaction_and_init_db_preserves_notes(classroom_app, classroom_teacher):
    cid, catalog, room = prepare_real_course(classroom_app, classroom_teacher)
    with classroom_app.app_context():
        response = classroom_teacher.get(f"/classrooms/{room['classroom_id']}/state", headers={"X-Activity-Role":"teacher"})
        assert response.status_code == 200
        assert not connection().in_transaction
        with write_transaction() as db:
            db.execute("UPDATE courses SET title='改名' WHERE id=?",(cid,))
    result = classroom_app.test_cli_runner().invoke(args=["init-db"])
    assert result.exit_code == 0, result.output
    page = classroom_teacher.get(f"/teacher/notes/catalogs/{catalog['import_id']}/versions/1",headers={"Accept":"application/json"})
    assert page.json == catalog


def test_export_labels_keep_same_number_groups_in_their_original_classrooms(classroom_app, classroom_teacher):
    cid, catalog, first_room = prepare_real_course(classroom_app, classroom_teacher)
    second_room = post(classroom_teacher, f'/teacher/courses/{cid}/classrooms', title='另一堂').json
    snapshots, expected = {}, []
    for room in (first_room, second_room):
        student = classroom_app.test_client()
        joined = post(student, '/classroom-memberships', code=room['code'], group_name='1').json
        path = f"/teacher/classrooms/{room['classroom_id']}/activities"
        aid = post(classroom_teacher, path, import_id=catalog['import_id'], import_version=1).json['activity_id']
        assert post(classroom_teacher, f'{path}/{aid}/finish').status_code == 200
        snapshots[aid] = {
            'contract_version': 1, 'activity_id': aid, 'import_id': catalog['import_id'],
            'import_version': 1, 'result_version': aid, 'ended': True,
            'units': [{'question_id': q['question_id'], 'winner_group_id': str(joined['group_id']),
                       'no_winner': False,
                       'answers': [{'item_id': i['item_id'], 'blank_id': i['blank_id'], 'answer_text': 'saved'}
                                   for i in q['items']]} for q in catalog['questions']],
        }
        expected.append((aid, joined['group_id']))
    assert expected[0][1] != expected[1][1]
    classroom_app.config['GET_SETTLED_RESULTS'] = lambda db, aid: {'snapshot': snapshots[aid], 'results': []}
    saved = []
    for aid, group_id in expected:
        preview = post(classroom_teacher, '/teacher/notes/export-previews', activity_id=aid)
        assert preview.status_code == 201
        assert {item['winner_group_id'] for item in preview.json['items']} == {str(group_id)}
        report = confirm_export(classroom_teacher, preview.json['preview_id'], key=aid).json
        assert report['status'] == 'completed'
        assert {unit['winner_group_id'] for unit in report['units']} == {str(group_id)}
        saved.append((preview.json['preview_url'], f"/teacher/notes/operations/{report['operation_id']}"))
    # Read the first room again after operating on the second room, including after closure.
    assert post(classroom_teacher, f"/teacher/classrooms/{first_room['classroom_id']}/close", confirm=True).status_code == 200
    for preview_url, report_url in saved:
        for url in (preview_url, report_url):
            page = classroom_teacher.get(url, headers={'Accept': 'text/html'})
            assert page.status_code == 200
            assert page.text.count('第 1 組') == sum(len(q['items']) for q in catalog['questions'])
