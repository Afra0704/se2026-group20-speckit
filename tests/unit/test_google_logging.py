import logging
from google_support import google_app


def test_callback_access_log_is_redacted(google_app,caplog):
    with caplog.at_level(logging.INFO,logger='werkzeug'):
        logging.getLogger('werkzeug').info('GET /auth/google/callback?code=secret-code&state=secret-state&error_description=secret-description HTTP/1.1')
    assert '/auth/google/callback?[redacted]' in caplog.text
    assert not any(value in caplog.text for value in ('secret-code','secret-state','secret-description'))


def test_oauth_debug_bodies_are_disabled_even_with_root_debug(google_app,caplog):
    with caplog.at_level(logging.DEBUG):
        logging.getLogger('requests_oauthlib.oauth2_session').debug('access_token=private-token client_secret=private-secret')
        logging.getLogger('oauthlib.oauth2.rfc6749').debug('refresh_token=private-refresh')
    assert not any(value in caplog.text for value in ('private-token','private-secret','private-refresh'))
