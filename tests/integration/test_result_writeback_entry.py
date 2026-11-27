from conftest import post
from guided_notes.db import connection
from result_writeback_support import export_room, result_teacher
from test_export_routes import confirm_export


def test_context_entry_history_and_return(classroom_app, result_teacher):
    cid, room, aid, group, snapshot = export_room(classroom_app, result_teacher)
    result = post(result_teacher, '/teacher/notes/export-previews', activity_id=aid)
    assert result.status_code == 201
    data = result.json
    context = data['activity_context']
    assert context['activity_id'] == aid and context['classroom_id'] == room['classroom_id']
    assert context['activity_title'] == '同名活動'
    assert f'activity_id={aid}' in context['result_url']
    assert {i['winner_group_label'] for i in data['items']} == {'第 42 組'}
    gateway = classroom_app.config['NOTES_GATEWAY']
    reads = gateway.calls.count("read")
    for path in (data['preview_url'], context['result_url'], f'/teacher/notes/export-previews?activity_id={aid}'):
        page = result_teacher.get(path, headers={'Accept': 'text/html'})
        assert page.status_code == 200
    assert gateway.calls.count("read") == reads
    returned = result_teacher.get(context['result_url'])
    assert f'data-selected-activity-id="{aid}"' in returned.text
    report = confirm_export(result_teacher, data['preview_id']).json
    assert report['activity_context']['activity_id'] == aid
    assert {u['winner_group_label'] for u in report['units']} == {'第 42 組'}
    assert report['result_version'] == snapshot['result_version']


def test_mapping_blocks_before_read_and_keeps_existing_report(classroom_app, result_teacher):
    _, room, aid, group, _ = export_room(classroom_app, result_teacher)
    preview = post(result_teacher, '/teacher/notes/export-previews', activity_id=aid).json
    report = confirm_export(result_teacher, preview['preview_id']).json
    with classroom_app.app_context():
        connection().execute("UPDATE classroom_groups SET name='第一組' WHERE id=?", (group['group_id'],))
    gateway = classroom_app.config['NOTES_GATEWAY']
    before = gateway.calls.count("read"), len(gateway.writes)
    result = post(result_teacher, '/teacher/notes/export-previews', activity_id=aid)
    assert result.status_code == 422
    assert result.json['error']['context']['reason'] == 'WINNER_GROUP_SCOPE_MISMATCH'
    old = result_teacher.get(f"/teacher/notes/operations/{report['operation_id']}", headers={'Accept':'application/json'})
    assert old.status_code == 200 and old.json['context_error']['code'] == 'RESULT_INVALID'
    assert old.json['status'] == 'completed'
    page = result_teacher.get(preview['preview_url'], headers={'Accept':'text/html'})
    assert '勝組資料與原課堂不一致' in page.text
    assert 'data-writeback-confirm' not in page.text
    assert (gateway.calls.count("read"), len(gateway.writes)) == before


def test_no_winner_and_query_guards(classroom_app, result_teacher):
    cid, room, aid, _, _ = export_room(classroom_app, result_teacher, no_winner=True)
    preview = post(result_teacher, '/teacher/notes/export-previews', activity_id=aid).json
    page = result_teacher.get(preview['preview_url'], headers={'Accept':'text/html'})
    assert '沒有勝組可回填' in page.text and 'data-writeback-confirm' not in page.text
    base = f"/teacher/workspace/courses/{cid}/classrooms/{room['classroom_id']}"
    for query in ('?activity_id=', f'?activity_id={aid}&activity_id={aid}'):
        assert result_teacher.get(base+query).status_code == 400
    assert result_teacher.get(base+'?activity_id=missing').status_code == 404
    assert post(result_teacher, '/teacher/notes/export-previews', activity_id=aid, winner_group_id='5').status_code == 400
