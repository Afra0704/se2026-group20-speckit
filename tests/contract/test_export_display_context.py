from copy import deepcopy
from urllib.parse import parse_qs, urlsplit

import pytest

from google_support import google_app, google_teacher, complete, post
from workspace_support import flow, path, published


@pytest.fixture
def display_export(google_app, google_teacher, flow):
    catalog, _ = published(google_teacher, flow)
    cid = google_teacher.get(path(flow), headers={'Accept':'application/json'}).json['course_id']
    room = post(google_teacher, f'/teacher/courses/{cid}/classrooms', title='契約課堂').json
    student = google_app.test_client()
    joined = post(student, '/classroom-memberships', code=room['code'], group_name='42').json
    root = f"/teacher/classrooms/{room['classroom_id']}/activities"
    aid = post(google_teacher, root, title='契約活動', import_id=catalog['import_id'], import_version=1).json['activity_id']
    post(google_teacher, f'{root}/{aid}/finish')
    snapshot = {'contract_version':1, 'activity_id':aid, 'import_id':catalog['import_id'], 'import_version':1,
                'result_version':'contract-1', 'ended':True, 'units':[
                    {'question_id':q['question_id'], 'winner_group_id':str(joined['group_id']), 'no_winner':False,
                     'answers':[{'item_id':i['item_id'], 'blank_id':i['blank_id'], 'answer_text':'=literal'}
                                for i in q['items']]} for q in catalog['questions']]}
    google_app.config['GET_SETTLED_RESULTS'] = lambda db, value: {'snapshot':snapshot,'results':[]} if value == aid else None
    return aid, snapshot


def test_teacher_projection_is_additive_and_html_uses_same_context(google_app, google_teacher, display_export):
    aid, snapshot = display_export
    before = deepcopy(snapshot)
    csrf = google_teacher.get('/csrf').json['csrf']
    result = google_teacher.post('/teacher/notes/export-previews', data={'activity_id':aid,'csrf_token':csrf},
                                 headers={'Accept':'text/html'})
    assert result.status_code == 303
    data = google_teacher.get(result.location, headers={'Accept':'application/json'}).json
    assert data['activity_context']['activity_title'] == '契約活動'
    assert data['activity_context']['import_version'] == 1
    assert data['activity_context']['source_title']
    assert {i['winner_group_label'] for i in data['items']} == {'第 42 組'}
    reads = len(google_app.config['NOTES_GATEWAY'].calls)
    page = google_teacher.get(result.location, headers={'Accept':'text/html'})
    assert '契約課堂' in page.text and '第 42 組' in page.text
    assert '台北時間' in page.text and '返回原活動結果' in page.text
    assert len(google_app.config['NOTES_GATEWAY'].calls) == reads
    assert snapshot == before


@pytest.mark.parametrize('oauth_error', [None, 'access_denied', 'server_error'])
def test_real_activity_reconnect_keeps_selection_without_implicit_source_read(google_app, google_teacher, display_export, oauth_error):
    aid, _ = display_export
    target = f'/teacher/notes/export-previews?activity_id={aid}'
    started = post(google_teacher, '/teacher/google/sheets/connect', return_to=target)
    state = parse_qs(urlsplit(started.location).query)['state'][0]
    reads = len(google_app.config['NOTES_GATEWAY'].calls)
    response = (google_teacher.get('/auth/google/callback', query_string={'state':state,'error':oauth_error})
                if oauth_error else complete(google_teacher, state))
    assert response.location.startswith(target)
    returned = google_teacher.get(response.location, headers={'Accept':'text/html'})
    assert returned.status_code == 200 and f'value="{aid}"' in returned.text
    assert '契約活動' in returned.text
    assert len(google_app.config['NOTES_GATEWAY'].calls) == reads
