"""Reauthorization returns to a safe read-only page; never automatically writes."""
from urllib.parse import parse_qs, urlsplit

import pytest

from google_support import google_app, google_teacher, complete, post
from workspace_support import flow, path
from guided_notes.db import connection
from guided_notes.notes.sheets_gateway import GatewayError


@pytest.mark.parametrize('target', [
    '/teacher/notes/export-previews?activity_id=activity-1',
    '/teacher/notes/operations/operation-1',
    '/teacher/notes/export-previews/preview-1',
])
def test_reconnect_returns_to_original_page_and_is_one_use(google_app, google_teacher, target):
    started = post(google_teacher, '/teacher/google/sheets/connect', return_to=target)
    state = parse_qs(urlsplit(started.location).query)['state'][0]
    result = complete(google_teacher, state, return_to='https://evil.example')
    assert result.location == target
    # Callback query parameters cannot replace the server-bound destination.
    assert complete(google_teacher, state).location != target
    with google_app.app_context():
        assert connection().execute('SELECT count(*) FROM notes_write_operations').fetchone()[0] == 0
    if 'activity_id=' in target:
        assert 'value="activity-1"' in google_teacher.get(target).text


@pytest.mark.parametrize('target', [
    'https://evil.example', '//evil.example/teacher/notes', '/teacher/session/logout',
    '/teacher/notes/export-previews/id/confirm', '/teacher/notes/../login',
    '/teacher/notes?token=private', '/teacher/notes#fragment', '/teacher/notes\\evil',
    '/teacher/notes/export-previews?activity_id=a&activity_id=b',
    '/teacher/notes/export-previews?activity_id=%0a', 'http://[', 123,
])
def test_reconnect_rejects_external_or_action_destinations(google_app, google_teacher, target):
    before = len(google_app.config['GOOGLE_PROVIDER'].calls)
    assert post(google_teacher, '/teacher/google/sheets/connect', return_to=target).status_code == 400
    assert len(google_app.config['GOOGLE_PROVIDER'].calls) == before


def test_reconnect_requires_teacher_and_csrf(google_app, google_teacher):
    assert post(google_app.test_client(), '/teacher/google/sheets/connect', return_to='/teacher/notes').status_code == 401
    assert google_teacher.post('/teacher/google/sheets/connect', data={'return_to': '/teacher/notes'}).status_code == 403


def test_export_auth_error_offers_reconnect_and_preserves_activity(google_app, google_teacher, monkeypatch):
    def denied(*args):
        raise GatewayError('GOOGLE_REAUTH_REQUIRED')
    monkeypatch.setattr('guided_notes.notes.export_service.create_saved_preview', denied)
    csrf = google_teacher.get('/csrf').json['csrf']
    response = google_teacher.post('/teacher/notes/export-previews',
        data={'csrf_token': csrf, 'activity_id': 'activity-1'}, headers={'Accept': 'text/html'})
    assert '重新連接 Google Sheets' in response.text
    assert 'action="/teacher/google/sheets/connect"' in response.text
    assert 'value="/teacher/notes/export-previews?activity_id=activity-1"' in response.text
    assert '不會自動回填' in response.text


def test_failed_link_reconnect_keeps_flow_and_requires_explicit_read(google_app, google_teacher, flow):
    gateway = google_app.config['NOTES_GATEWAY']
    def denied():
        raise GatewayError('GOOGLE_REAUTH_REQUIRED')
    gateway.hook = denied
    assert post(google_teacher, path(flow, 'read')).json['error']['code'] == 'GOOGLE_REAUTH_REQUIRED'
    page = google_teacher.get(path(flow), headers={'Accept': 'text/html'})
    assert 'id="link-import-reconnect"' in page.text
    assert 'value="'+path(flow)+'"' in page.text
    assert '重新連接 Google Sheets' in page.text
    # The form is visible, not merely present in hidden markup.
    from html.parser import HTMLParser
    class Forms(HTMLParser):
        attributes = None
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == 'form' and attrs.get('id') == 'link-import-reconnect':
                self.attributes = attrs
    forms = Forms(); forms.feed(page.text)
    assert 'hidden' not in forms.attributes
    started = post(google_teacher, '/teacher/google/sheets/connect', return_to=path(flow))
    state = parse_qs(urlsplit(started.location).query)['state'][0]
    before = len(gateway.calls)
    assert complete(google_teacher, state).location == path(flow)
    assert len(gateway.calls) == before  # No implicit source read or save.
    gateway.hook = None
    assert post(google_teacher, path(flow, 'retry')).status_code == 200
    with google_app.app_context():
        assert connection().execute('SELECT count(*) FROM workspace_import_flows').fetchone()[0] == 1
        assert connection().execute('SELECT count(*) FROM notes_imports').fetchone()[0] == 0


def test_cancel_reconnect_preserves_activity_and_existing_teacher(google_app, google_teacher):
    started = post(google_teacher, '/teacher/google/sheets/connect',
        return_to='/teacher/notes/export-previews?activity_id=original')
    state = parse_qs(urlsplit(started.location).query)['state'][0]
    response = google_teacher.get('/auth/google/callback', query_string={'state': state, 'error': 'access_denied'})
    assert response.location == '/teacher/notes/export-previews?activity_id=original&error=GOOGLE_LOGIN_CANCELLED'
    assert google_teacher.get('/teacher/session').json['authenticated']
