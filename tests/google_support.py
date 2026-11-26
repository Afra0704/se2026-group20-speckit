"""Synthetic Google boundary, never a substitute for real account acceptance."""
import json
import time
from urllib.parse import urlencode, urlsplit, parse_qs

import pytest
from cryptography.fernet import Fernet

from guided_notes import create_app
from guided_notes.db import connection
from guided_notes.google_login.provider import LOGIN_SCOPES, SHEETS_SCOPE, ISSUER


class FakeGoogle:
    def __init__(self):
        self.calls = []
        self.hook = None
        self.refresh_hook = None
        self.subject = 'A'
        self.scopes = list(LOGIN_SCOPES)+[SHEETS_SCOPE]
        self.refresh_token = 'synthetic-refresh'

    def authorization_request(self, attempt):
        self.calls.append(('authorize',attempt))
        return 'https://accounts.google.com/o/oauth2/v2/auth?' + urlencode({'state':attempt['state']})

    def exchange_and_verify(self, attempt, code):
        assert not connection().in_transaction
        self.calls.append(('exchange',attempt))
        if self.hook:
            self.hook()
        return {'identity':{'issuer':ISSUER,'subject':self.subject,'display_name':'Teacher '+self.subject,
                'email':'same@example.test','email_verified':True},
                'token':{'access_token':'synthetic-access','refresh_token':self.refresh_token,
                         'scope':self.scopes,'expires_in':3600}}

    def refresh(self, secret, client, budget):
        assert not connection().in_transaction
        self.calls.append(('refresh',secret))
        if self.refresh_hook:
            return self.refresh_hook(secret, client, budget)
        return {'access_token':'synthetic-refreshed','expires_in':3600}


@pytest.fixture
def google_app(tmp_path):
    key = tmp_path/'key'
    key.write_bytes(Fernet.generate_key())
    web = tmp_path/'web.json'
    web.write_text(json.dumps({'web':{'client_id':'synthetic-client','client_secret':'synthetic-client-secret',
        'auth_uri':'https://accounts.google.com/o/oauth2/v2/auth','token_uri':'https://oauth2.googleapis.com/token',
        'redirect_uris':['http://127.0.0.1:5000/auth/google/callback']}}))
    fake = FakeGoogle()
    app = create_app({'TESTING':True, 'TEACHER_AUTH_MODE':'google','SECRET_KEY':'synthetic-cookie-key',
        'CLASSROOM_MODE':True,'DATABASE':str(tmp_path/'google.sqlite3'),
        'GOOGLE_WEB_CLIENT_SECRETS':str(web),'GOOGLE_TOKEN_KEY_FILE':str(key),'GOOGLE_PROVIDER':fake})
    @app.get('/test-google-credentials')
    def test_credentials():
        from guided_notes.auth import require_teacher
        from guided_notes.google_login.sheets_service import credentials
        value = credentials(require_teacher())
        assert not hasattr(value,'refresh_token') and not hasattr(value,'client_secret')
        return {'valid':value.valid}
    return app


def post(client, path, **body):
    csrf = client.get('/csrf').json['csrf']
    return client.post(path,json=body,headers={'X-CSRF-Token':csrf})


def start(client, purpose='login'):
    response = post(client,'/auth/google/start' if purpose=='login' else '/teacher/google/sheets/connect')
    assert response.status_code == 303, response.get_data(as_text=True)
    return parse_qs(urlsplit(response.location).query)['state'][0]


def complete(client,state,**extra):
    return client.get('/auth/google/callback',query_string={'state':state, 'code':'synthetic-code',**extra})


def login(client, app, subject='A'):
    app.config['GOOGLE_PROVIDER'].subject=subject
    response=complete(client,start(client))
    assert response.location == '/teacher', response.location
    return client


def connect(client):
    response=complete(client,start(client,'sheets'))
    assert response.location == '/teacher/notes', response.location


@pytest.fixture
def google_teacher(google_app):
    return login(google_app.test_client(),google_app)
