from copy import deepcopy

import pytest

from conftest import post
from guided_notes.db import connection
from result_writeback_support import export_room, result_teacher
from test_export_routes import confirm_export
from test_import_routes import URL


def test_same_number_distinct_rooms_and_closed_removed_history(classroom_app, result_teacher):
    saved = []
    for _ in range(2):
        cid, room, aid, group, snapshot = export_room(classroom_app, result_teacher, number='1')
        preview = post(result_teacher, '/teacher/notes/export-previews', activity_id=aid).json
        saved.append((cid, room, aid, group, snapshot, preview))
    assert saved[0][3]['group_id'] != saved[1][3]['group_id']
    for cid, room, aid, group, snapshot, preview in saved:
        assert post(result_teacher, f"/teacher/classrooms/{room['classroom_id']}/close", confirm=True).status_code == 200
        assert post(result_teacher, f"/teacher/notes/courses/{cid}/lectures/{snapshot['import_id']}/remove", confirm=True).status_code == 200
        data = result_teacher.get(preview['preview_url'], headers={'Accept':'application/json'}).json
        assert data['activity_context']['activity_id'] == aid
        assert data['activity_context']['classroom_state'] == 'CLOSED'
        assert {item['winner_group_label'] for item in data['items']} == {'第 1 組'}
        # Both rooms target the same source. Refresh its observation after prior writes.
        fresh = post(result_teacher, '/teacher/notes/export-previews', activity_id=aid).json
        report = confirm_export(result_teacher, fresh['preview_id'], key=aid)
        assert report.status_code == 200 and report.json['status'] == 'completed'
        assert report.json['activity_context']['classroom_id'] == room['classroom_id']
        assert result_teacher.get(data['activity_context']['result_url']).status_code == 200


@pytest.mark.parametrize('role', ['student', 'other'])
def test_all_entry_points_deny_other_principals(classroom_app, result_teacher, role):
    _, _, aid, _, _ = export_room(classroom_app, result_teacher)
    preview = post(result_teacher, '/teacher/notes/export-previews', activity_id=aid).json
    report = confirm_export(result_teacher, preview['preview_id']).json
    client = classroom_app.test_client()
    if role == 'other':
        assert post(client, '/teacher/session', username='other', password='test-password').status_code == 204
    gateway = classroom_app.config['NOTES_GATEWAY']
    before = len(gateway.calls), len(gateway.writes)
    for path in (preview['preview_url'], f"/teacher/notes/operations/{report['operation_id']}",
                 f'/teacher/notes/export-previews?activity_id={aid}', preview['activity_context']['result_url']):
        response = client.get(path, headers={'Accept':'application/json'})
        assert response.status_code in (401,403,404)
        assert '答案 42' not in response.text and 'activity_context' not in response.text
    assert post(client, '/teacher/notes/export-previews', activity_id=aid).status_code in (401,403,404)
    assert confirm_export(client, preview['preview_id']).status_code in (401,403,404)
    assert post(client, f"/teacher/notes/operations/{report['operation_id']}/recovery-preview").status_code in (401,403,404)
    assert (len(gateway.calls), len(gateway.writes)) == before


def test_cross_room_mapping_and_return_are_rejected(classroom_app, result_teacher):
    _, room1, aid1, _, snapshot1 = export_room(classroom_app, result_teacher)
    cid2, room2, aid2, group2, _ = export_room(classroom_app, result_teacher)
    snapshot1['units'][0]['winner_group_id'] = str(group2['group_id'])
    gateway = classroom_app.config['NOTES_GATEWAY']
    before = len(gateway.calls)
    response = post(result_teacher, '/teacher/notes/export-previews', activity_id=aid1)
    assert response.status_code == 422 and len(gateway.calls) == before
    path = f"/teacher/workspace/courses/{cid2}/classrooms/{room2['classroom_id']}?activity_id={aid1}"
    assert result_teacher.get(path).status_code == 404


def test_saved_preview_cannot_write_or_recover_after_mapping_breaks(classroom_app, result_teacher):
    _, _, aid, group, _ = export_room(classroom_app, result_teacher)
    preview = post(result_teacher, '/teacher/notes/export-previews', activity_id=aid).json
    gateway = classroom_app.config['NOTES_GATEWAY']
    gateway.fail_at = 1
    gateway.uncertain = True
    report = confirm_export(result_teacher, preview['preview_id']).json
    assert report['status'] == 'needs_attention'
    with classroom_app.app_context():
        connection().execute("UPDATE classroom_groups SET name='01' WHERE id=?", (group['group_id'],))
    before = len(gateway.calls), len(gateway.writes)
    # Original idempotency key still reads its original report without retrying writes.
    again = confirm_export(result_teacher, preview['preview_id'])
    assert again.status_code == 200 and again.json['context_error']
    assert confirm_export(result_teacher, preview['preview_id'], key='new').status_code == 422
    assert post(result_teacher, f"/teacher/notes/operations/{report['operation_id']}/recovery-preview").status_code == 422
    page = result_teacher.get(f"/teacher/notes/operations/{report['operation_id']}", headers={'Accept':'text/html'})
    assert page.status_code == 200 and '勝組資料與原課堂不一致' in page.text
    assert '先回讀並建立恢復預覽</button>' not in page.text
    assert (len(gateway.calls), len(gateway.writes)) == before


def test_partial_unknown_recovery_pins_snapshot_and_skips_completed(classroom_app, result_teacher):
    _, _, aid, _, snapshot = export_room(classroom_app, result_teacher)
    before = deepcopy(snapshot)
    preview = post(result_teacher, '/teacher/notes/export-previews', activity_id=aid).json
    gateway = classroom_app.config['NOTES_GATEWAY']
    gateway.fail_at = 1
    gateway.unknown_applies = True
    first = confirm_export(result_teacher, preview['preview_id']).json
    fresh = post(result_teacher, f"/teacher/notes/operations/{first['operation_id']}/recovery-preview")
    assert fresh.status_code == 201
    assert fresh.json['counts']['already_matches'] >= 2
    final = confirm_export(result_teacher, fresh.json['preview_id'], key='recovery').json
    assert final['status'] == 'completed'
    assert [len(batch) for batch in gateway.writes] == [2,1]
    assert final['result_version'] == snapshot['result_version'] and snapshot == before


@pytest.mark.parametrize('value', [None, '', 'bad', '2026-11-27 03:04:05'])
def test_context_time_fallback_and_names_are_escaped(classroom_app, result_teacher, value):
    cid, room, aid, _, _ = export_room(classroom_app, result_teacher)
    with classroom_app.app_context():
        connection().execute('UPDATE classroom_activities SET title=?,closed_at=? WHERE activity_id=?',
                             ('<script>alert(1)</script>', value, aid))
    preview = post(result_teacher, '/teacher/notes/export-previews', activity_id=aid).json
    page = result_teacher.get(preview['preview_url'], headers={'Accept':'text/html'})
    assert page.status_code == 200
    assert '<script>alert(1)</script>' not in page.text
    assert '&lt;script&gt;' in page.text
    assert preview['activity_context']['times']['closed_at']['status'] in ('known','missing','invalid')


@pytest.mark.parametrize('all_skipped', [True, False])
def test_no_winner_low_level_confirmation_remains_zero_or_partial_write(classroom_app, result_teacher, all_skipped):
    _, _, aid, _, snapshot = export_room(classroom_app, result_teacher, no_winner=all_skipped)
    if not all_skipped:
        snapshot['units'][0].update(no_winner=True, winner_group_id=None, answers=[])
    preview = post(result_teacher, '/teacher/notes/export-previews', activity_id=aid).json
    report = confirm_export(result_teacher, preview['preview_id']).json
    assert report['status'] == 'completed'
    writes = classroom_app.config['NOTES_GATEWAY'].writes
    assert len(writes) == (0 if all_skipped else 1)
    assert report['counts']['skipped'] == (3 if all_skipped else 2)


def test_mapping_rechecked_after_source_read_before_preview_is_saved(classroom_app, result_teacher):
    _, _, aid, group, _ = export_room(classroom_app, result_teacher)
    gateway = classroom_app.config['NOTES_GATEWAY']
    original = gateway.read_sheet
    def read_and_break(*args):
        result = original(*args)
        connection().execute("UPDATE classroom_groups SET name='invalid' WHERE id=?", (group['group_id'],))
        return result
    gateway.read_sheet = read_and_break
    response = post(result_teacher, '/teacher/notes/export-previews', activity_id=aid)
    assert response.status_code == 422
    with classroom_app.app_context():
        assert connection().execute('SELECT count(*) FROM notes_export_previews').fetchone()[0] == 0


def test_same_title_reused_lecture_keeps_each_fixed_version_and_answers(classroom_app, result_teacher):
    cid, room, old_aid, group, first = export_room(classroom_app, result_teacher)
    old_preview = post(result_teacher, '/teacher/notes/export-previews', activity_id=old_aid).json
    draft = post(result_teacher, '/teacher/notes/import-previews', spreadsheet_url=URL, sheet_id=7, course_id=cid).json
    catalog = post(result_teacher, f"/teacher/notes/import-previews/{draft['preview_id']}/confirm",
                   confirm=True, existing_import_id=first['import_id']).json
    assert catalog['import_version'] == 2
    root = f"/teacher/classrooms/{room['classroom_id']}/activities"
    new_aid = post(result_teacher, root, title='同名活動', import_id=catalog['import_id'], import_version=2).json['activity_id']
    post(result_teacher, f'{root}/{new_aid}/finish')
    second = deepcopy(first)
    second.update(activity_id=new_aid, import_version=2, result_version='second-version')
    for unit, question in zip(second['units'], catalog['questions']):
        unit['question_id'] = question['question_id']
        unit['answers'] = [{'item_id':i['item_id'], 'blank_id':i['blank_id'], 'answer_text':'新版答案'} for i in question['items']]
    classroom_app.config['RESULT_WRITEBACK_SNAPSHOTS'][new_aid] = second
    new_preview = post(result_teacher, '/teacher/notes/export-previews', activity_id=new_aid).json
    for preview, version, answer in ((old_preview,1,'答案 42'), (new_preview,2,'新版答案')):
        for _ in range(2):
            data = result_teacher.get(preview['preview_url'], headers={'Accept':'application/json'}).json
            assert data['import_version'] == version
            assert data['activity_context']['activity_id'] == preview['activity_id']
            assert {i['proposed_text'] for i in data['items']} == {answer}
            assert result_teacher.get(data['activity_context']['result_url']).status_code == 200
