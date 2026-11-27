"""Fixed-endpoint Google OAuth/OIDC adapter; never trust browser supplied claims."""
import json
import math
import secrets
import time
from pathlib import Path

import requests
from flask import current_app
from google.auth import exceptions as google_errors
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from oauthlib.oauth2 import OAuth2Error
from requests_oauthlib import OAuth2Session

from ..http import ApiError

ISSUER = 'https://accounts.google.com'
TOKEN_URI = 'https://oauth2.googleapis.com/token'
AUTH_URI = 'https://accounts.google.com/o/oauth2/v2/auth'
CERT_URI = 'https://www.googleapis.com/oauth2/v1/certs'
LOGIN_SCOPES = ('openid', 'email', 'profile')
SHEETS_SCOPE = 'https://www.googleapis.com/auth/spreadsheets'
CLOCK_SKEW_SECONDS = 60


def load_client(path, redirect_uri, root):
    try:
        target = Path(path).resolve()
        if target.is_relative_to(Path(root).resolve()):
            raise ValueError()
        value = json.loads(target.read_text(encoding='utf-8'))
        web = value['web']
        if 'installed' in value or not isinstance(web, dict):
            raise ValueError()
        if not all(isinstance(web.get(k), str) and web[k] for k in ('client_id', 'client_secret')):
            raise ValueError()
        if web.get('token_uri') != TOKEN_URI or web.get('auth_uri') not in (AUTH_URI, 'https://accounts.google.com/o/oauth2/auth'):
            raise ValueError()
        if redirect_uri != 'http://127.0.0.1:5000/auth/google/callback' or not isinstance(web.get('redirect_uris'), list) or redirect_uri not in web['redirect_uris']:
            raise ValueError()
        return {'web': {**web, 'auth_uri': AUTH_URI}}
    except (OSError, ValueError, KeyError, TypeError):
        raise ApiError(503, 'GOOGLE_NOT_CONFIGURED') from None


def configuration():
    origin = current_app.config['PUBLIC_ORIGIN']
    uri = current_app.config['GOOGLE_REDIRECT_URI']
    if origin != 'http://127.0.0.1:5000' or uri != origin + '/auth/google/callback':
        raise ApiError(503, 'GOOGLE_NOT_CONFIGURED')
    return load_client(current_app.config.get('GOOGLE_WEB_CLIENT_SECRETS'), uri, Path(__file__).resolve().parents[3])


class Budget:
    def __init__(self, seconds=20):
        self.deadline = time.monotonic() + seconds
        self.counts = {}

    def check(self):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise ApiError(503, 'GOOGLE_REFRESH_TIMEOUT', retry_after=1)
        return remaining

    def timeout(self, endpoint):
        remaining = self.check()
        self.counts[endpoint] = self.counts.get(endpoint, 0) + 1
        if self.counts[endpoint] > 1:
            raise ApiError(503, 'GOOGLE_UNAVAILABLE')
        return min(3, remaining / 2), min(10, remaining / 2)


class FixedSession(requests.Session):
    def __init__(self, budget):
        super().__init__()
        self.budget = budget

    def request(self, method, url, **kwargs):
        expected = TOKEN_URI if method.upper() == 'POST' else CERT_URI
        if url != expected:
            raise ApiError(503, 'GOOGLE_UNAVAILABLE')
        kwargs['allow_redirects'] = False
        kwargs['timeout'] = self.budget.timeout(expected)
        result = super().request(method, url, **kwargs)
        self.budget.check()
        if 300 <= result.status_code < 400:
            raise ApiError(503, 'GOOGLE_UNAVAILABLE')
        return result


class FixedOAuthSession(OAuth2Session):
    def __init__(self, *args, budget, **kwargs):
        super().__init__(*args, **kwargs)
        self.budget = budget

    def request(self, method, url, **kwargs):
        if method.upper() != 'POST' or url != TOKEN_URI:
            raise ApiError(503, 'GOOGLE_UNAVAILABLE')
        kwargs['allow_redirects'] = False
        kwargs['timeout'] = self.budget.timeout(TOKEN_URI)
        response = super().request(method, url, **kwargs)
        self.budget.check()
        if 300 <= response.status_code < 400:
            raise ApiError(503, 'GOOGLE_UNAVAILABLE')
        return response


def validate_claims(claims, client_id, nonce=None):
    now = time.time()
    try:
        if claims['iss'] not in (ISSUER, 'accounts.google.com') or claims['aud'] != client_id:
            raise ValueError()
        if not isinstance(claims['sub'], str) or not claims['sub'].strip():
            raise ValueError()
        if not math.isfinite(float(claims['exp'])) or not math.isfinite(float(claims['iat'])) or float(claims['exp']) <= now or float(claims['iat']) > now + CLOCK_SKEW_SECONDS:
            raise ValueError()
        if claims.get('azp', client_id) != client_id:
            raise ValueError()
        if nonce is not None and (not isinstance(claims.get('nonce'), str) or not secrets.compare_digest(claims['nonce'], nonce)):
            raise ValueError()
    except (KeyError, ValueError, TypeError):
        raise ApiError(400, 'GOOGLE_FLOW_INVALID') from None
    return {'issuer': ISSUER, 'subject': claims['sub'],
            'display_name': claims.get('name') if isinstance(claims.get('name'), str) else None,
            'email': claims.get('email') if isinstance(claims.get('email'), str) else None,
            'email_verified': claims.get('email_verified') is True}


def actual_scopes(token):
    value = token.get('scope')
    scopes = set(value.split() if isinstance(value, str) else value or [])
    aliases = {'https://www.googleapis.com/auth/userinfo.email': 'email',
               'https://www.googleapis.com/auth/userinfo.profile': 'profile'}
    return {aliases.get(s, s) for s in scopes}


def _scope_warning(operation):
    try:
        return operation()
    except Warning as error:
        # oauthlib 3.x/4.x reports a scope change after parsing the HTTPS response.
        if not isinstance(getattr(error, 'token', None), dict) or not hasattr(error, 'new_scope'):
            raise ApiError(400, 'GOOGLE_FLOW_INVALID') from None
        return error.token


class GoogleProvider:
    def authorization_request(self, attempt):
        from .flow_context import client_for, context
        config = client_for(attempt)
        ctx = context(attempt)
        picker = ctx is not None and ctx["credential_kind"] == "picker"
        scopes = list(LOGIN_SCOPES) + (['https://www.googleapis.com/auth/drive.file'] if picker else [SHEETS_SCOPE] if attempt['purpose'] == 'sheets' else [])
        flow = Flow.from_client_config(config, scopes=scopes, state=attempt['state'],
            redirect_uri=attempt['redirect_uri'], code_verifier=attempt['secrets']['verifier'],
            autogenerate_code_verifier=False)
        options = {'nonce': attempt['secrets']['nonce'], 'prompt': 'select_account', 'access_type': 'online'}
        if picker:
            options = {'nonce': attempt['secrets']['nonce'], 'access_type':'online', 'include_granted_scopes':'false'}
        elif attempt['purpose'] == 'sheets':
            options.update(access_type='offline', include_granted_scopes='true', prompt='consent select_account')
        return flow.authorization_url(**options)[0]

    def exchange_and_verify(self, attempt, code):
        from .flow_context import client_for, context
        config = client_for(attempt)
        ctx = context(attempt)
        picker = ctx is not None and ctx["credential_kind"] == "picker"
        web = config['web']
        budget = Budget()
        scopes = list(LOGIN_SCOPES) + (['https://www.googleapis.com/auth/drive.file'] if picker else [SHEETS_SCOPE] if attempt['purpose'] == 'sheets' else [])
        oauth = FixedOAuthSession(web['client_id'], scope=scopes, state=attempt['state'],
            redirect_uri=attempt['redirect_uri'], budget=budget)
        flow = Flow(oauth, 'web', config, redirect_uri=attempt['redirect_uri'],
                    code_verifier=attempt['secrets']['verifier'], autogenerate_code_verifier=False)
        stage = 'token_exchange'
        try:
            token = dict(_scope_warning(lambda: flow.fetch_token(code=code)))
            stage = 'identity_verification'
            identity = self.verify(token.get('id_token'), web['client_id'], budget, attempt['secrets']['nonce'])
            stage = 'required_scopes'
            if not set(LOGIN_SCOPES).issubset(actual_scopes(token)):
                raise ApiError(400, 'GOOGLE_FLOW_INVALID')
            budget.check()
            return {'identity': identity, 'token': token}
        except ApiError as error:
            current_app.logger.warning('Google verification failed: stage=%s code=%s', stage, error.code)
            raise
        except (requests.RequestException, google_errors.TransportError):
            raise ApiError(503, 'GOOGLE_UNAVAILABLE') from None
        except (OAuth2Error, ValueError, TypeError) as error:
            current_app.logger.warning('Google verification failed: stage=%s type=%s', stage, type(error).__name__)
            raise ApiError(400, 'GOOGLE_FLOW_INVALID') from None

    def verify(self, raw, client_id, budget, nonce=None):
        if not isinstance(raw, str) or not raw:
            raise ApiError(400, 'GOOGLE_FLOW_INVALID')
        try:
            claims = id_token.verify_oauth2_token(
                raw, Request(session=FixedSession(budget)), audience=client_id,
                clock_skew_in_seconds=CLOCK_SKEW_SECONDS,
            )
        except google_errors.InvalidValue as error:
            # Match fixed library messages without logging claims, tokens or client identifiers.
            reason = 'other_invalid_value'
            for prefix, category in (
                ('Token used too early', 'issued_in_future'),
                ('Token expired', 'expired'),
                ('Token has wrong audience', 'audience_mismatch'),
                ('Unsupported signature algorithm', 'unsupported_algorithm'),
                ('The key algorithm', 'algorithm_dependency'),
                ('Could not verify token signature', 'signature_invalid'),
            ):
                if str(error).startswith(prefix):
                    reason = category
                    break
            current_app.logger.warning('Google identity validation rejected: reason=%s', reason)
            raise
        return validate_claims(claims, client_id, nonce)

    def refresh(self, secret, client, budget):
        try:
            response = FixedSession(budget).post(TOKEN_URI, data={
                'grant_type': 'refresh_token', 'refresh_token': secret['refresh_token'],
                'client_id': client['client_id'], 'client_secret': client['client_secret']})
            value = response.json()
            if value.get('error') == 'invalid_grant':
                raise ApiError(409, 'GOOGLE_REAUTH_REQUIRED')
            if response.status_code != 200 or not isinstance(value.get('access_token'), str):
                raise ApiError(503, 'GOOGLE_UNAVAILABLE')
            if value.get('id_token'):
                value['_identity'] = self.verify(value['id_token'], client['client_id'], budget)
            budget.check()
            return value
        except (requests.Timeout, requests.ConnectionError):
            raise ApiError(503, 'GOOGLE_REFRESH_TIMEOUT', retry_after=1) from None
        except (ValueError, google_errors.GoogleAuthError):
            raise ApiError(503, 'GOOGLE_UNAVAILABLE') from None


def provider():
    substitute = current_app.config.get('GOOGLE_PROVIDER')
    if substitute is not None and current_app.testing:
        return substitute
    return GoogleProvider()
