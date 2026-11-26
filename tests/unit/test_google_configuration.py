import json
from pathlib import Path

import pytest

from guided_notes.google_login.provider import load_client
from guided_notes.http import ApiError
from google_support import google_app


@pytest.mark.parametrize('kind', ['installed', 'missing'])
def test_web_client_required(tmp_path, kind):
    path = tmp_path / 'web.json'
    path.write_text(json.dumps({kind: {}}))
    with pytest.raises(ApiError):
        load_client(str(path), 'http://127.0.0.1:5000/auth/google/callback', Path('D:/os_final'))


@pytest.mark.parametrize('change',['token_endpoint','auth_endpoint','redirect','inside_repo','origin'])
def test_fixed_web_configuration_boundary(google_app,change):
    from guided_notes.google_login.provider import configuration
    path=Path(google_app.config['GOOGLE_WEB_CLIENT_SECRETS'])
    config=json.loads(path.read_text())
    if change=='token_endpoint':config['web']['token_uri']='https://evil.test/token'
    if change=='auth_endpoint':config['web']['auth_uri']='http://accounts.google.com/o/oauth2/auth'
    if change=='redirect':config['web']['redirect_uris']=['http://localhost:5000/auth/google/callback']
    path.write_text(json.dumps(config))
    with google_app.app_context():
        if change=='origin':google_app.config['PUBLIC_ORIGIN']='http://attacker.test'
        with pytest.raises(ApiError) as error:
            if change=='inside_repo':load_client(path,google_app.config['GOOGLE_REDIRECT_URI'],path.parent)
            else:configuration()
        assert error.value.code=='GOOGLE_NOT_CONFIGURED'
