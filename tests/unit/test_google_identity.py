import base64
import hashlib
import json
import time
from datetime import datetime, timezone
from urllib.parse import parse_qs,urlsplit

import pytest
import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from google.auth import jwt
from google.auth.crypt import RSASigner

from google_support import google_app
from guided_notes.google_login.provider import GoogleProvider, ISSUER, SHEETS_SCOPE, validate_claims, actual_scopes, Budget, FixedSession
from guided_notes.http import ApiError


def claims():
    return {'iss':ISSUER,'aud':'synthetic-client','sub':'A','nonce':'expected-nonce',
            'iat':int(time.time()),'exp':int(time.time())+3600,'email':'a@example.test'}


@pytest.mark.parametrize('field,value',[('iss','https://evil.test'),('aud','wrong'),('sub',''),('exp',0),('iat',99999999999),('nonce','wrong'),('azp','wrong')])
def test_oidc_claim_rejection(field,value):
    value_claims={**claims(),field:value}
    with pytest.raises(ApiError): validate_claims(value_claims,'synthetic-client','expected-nonce')


def test_scope_aliases_and_missing():
    assert actual_scopes({})==set()
    assert actual_scopes({'scope':'openid https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile '+SHEETS_SCOPE})=={'openid','email','profile',SHEETS_SCOPE}


@pytest.mark.parametrize('purpose',['login','sheets'])
def test_actual_flow_s256_scopes_online(google_app,purpose):
    attempt={'attempt_id':'synthetic-provider-unit-attempt','purpose':purpose,'state':'one-state','redirect_uri':google_app.config['GOOGLE_REDIRECT_URI'],
             'secrets':{'nonce':'expected-nonce','verifier':'a'*64}}
    with google_app.app_context(): url=GoogleProvider().authorization_request(attempt)
    query=parse_qs(urlsplit(url).query)
    assert query['state']==['one-state'] and query['nonce']==['expected-nonce']
    assert query['code_challenge_method']==['S256']
    assert query['code_challenge']==[base64.urlsafe_b64encode(hashlib.sha256(b'a'*64).digest()).decode().rstrip('=')]
    assert query['access_type']==['online' if purpose=='login' else 'offline']
    assert (SHEETS_SCOPE in query['scope'][0]) == (purpose=='sheets')


@pytest.mark.parametrize('mutation',['valid','bad_signature','bad_nonce','partial','extra',
                                    'future_1','future_60','future_61','expired','bad_audience'])
def test_real_exchange_and_official_signature_verifier(google_app,monkeypatch,mutation):
    now = int(time.time())
    monkeypatch.setattr(time, 'time', lambda: now)
    monkeypatch.setattr('google.auth._helpers.utcnow',
                        lambda: datetime.fromtimestamp(now, timezone.utc).replace(tzinfo=None))
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    pem=key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())
    public=key.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    signer=RSASigner.from_string(pem,key_id='synthetic-kid')
    values=claims()
    if mutation=='bad_nonce': values['nonce']='wrong'
    if mutation.startswith('future_'): values['iat'] = now + int(mutation.split('_')[1])
    if mutation=='expired': values['exp'] = now - 1
    if mutation=='bad_audience': values['aud'] = 'another-client'
    raw=jwt.encode(signer,values).decode()
    if mutation=='bad_signature': raw=raw[:-8]+'AAAAAAAA'
    scopes='openid email profile'
    if mutation=='partial':scopes='openid'
    if mutation=='extra':scopes+=' '+SHEETS_SCOPE
    calls=[]
    def request(self,method,url,**kwargs):
        calls.append((method,url,kwargs))
        response=requests.Response();response.status_code=200
        if method.upper()=='POST':
            assert kwargs['allow_redirects'] is False
            assert kwargs['data']['code_verifier'] == 'a'*64
            assert kwargs['auth'] is not None  # HTTP Basic Web client authentication
            value={'access_token':'synthetic-access','token_type':'Bearer','expires_in':3600,'scope':scopes,'id_token':raw}
        else:value={'synthetic-kid':public}
        response._content=json.dumps(value).encode()
        response.request=requests.Request(method,url,data=kwargs.get('data')).prepare()
        return response
    monkeypatch.setattr(requests.Session,'request',request)
    attempt={'attempt_id':'synthetic-provider-unit-attempt','purpose':'login','state':'one-state','redirect_uri':google_app.config['GOOGLE_REDIRECT_URI'],
             'secrets':{'nonce':'expected-nonce','verifier':'a'*64}}
    with google_app.app_context():
        if mutation in ('valid','extra','future_1','future_60'):
            result=GoogleProvider().exchange_and_verify(attempt,'code')
            assert result['identity']['subject']=='A'
        else:
            with pytest.raises(ApiError):GoogleProvider().exchange_and_verify(attempt,'code')
    assert sum(method.upper()=='POST' for method,_,_ in calls)==1
    assert sum(method.upper()=='GET' for method,_,_ in calls)<=1


def test_budget_forbids_repeat_redirect_and_late_result(monkeypatch):
    budget=Budget();budget.timeout('POST')
    with pytest.raises(ApiError): budget.timeout('POST')
    budget.deadline=0
    with pytest.raises(ApiError) as error:budget.check()
    assert error.value.code=='GOOGLE_REFRESH_TIMEOUT'
    response=requests.Response();response.status_code=302
    monkeypatch.setattr(requests.Session,'request',lambda *a,**k:response)
    with pytest.raises(ApiError):FixedSession(Budget()).post('https://oauth2.googleapis.com/token')


def test_monotonic_clock_deadline_is_shared_and_timeout_shrinks(monkeypatch):
    clock=[100.0]
    monkeypatch.setattr(time,'monotonic',lambda:clock[0])
    budget=Budget(20)
    assert budget.timeout('POST')==(3,10)
    clock[0]=119.0
    assert budget.timeout('GET')==(.5,.5)
    clock[0]=120.0
    with pytest.raises(ApiError) as error:budget.check()
    assert error.value.code=='GOOGLE_REFRESH_TIMEOUT'


@pytest.mark.parametrize('response_kind',['no_id','new_id','wrong_id','invalid_grant','timeout'])
def test_refresh_fixed_post_and_optional_official_verification(google_app,monkeypatch,response_kind):
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    pem=key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())
    public=key.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    values=claims()
    if response_kind=='wrong_id':values['aud']='another-client'
    raw=jwt.encode(RSASigner.from_string(pem,key_id='kid'),values).decode()
    calls=[]
    def request(self,method,url,**kwargs):
        calls.append((method,url))
        assert kwargs['allow_redirects'] is False and max(kwargs['timeout'])<=10
        if response_kind=='timeout':raise requests.Timeout()
        response=requests.Response();response.status_code=200
        if method.upper()=='GET':value={'kid':public}
        else:
            value={'access_token':'fresh','expires_in':3600}
            if response_kind in ('new_id','wrong_id'):value['id_token']=raw
            if response_kind=='invalid_grant':value={'error':'invalid_grant'};response.status_code=400
        response._content=json.dumps(value).encode();return response
    monkeypatch.setattr(requests.Session,'request',request)
    with google_app.app_context():
        client={'client_id':'synthetic-client','client_secret':'synthetic-secret'}
        if response_kind in ('wrong_id','invalid_grant','timeout'):
            with pytest.raises(ApiError):GoogleProvider().refresh({'refresh_token':'synthetic'},client,Budget())
        else:
            result=GoogleProvider().refresh({'refresh_token':'synthetic'},client,Budget())
            assert result['access_token']=='fresh'
            assert ('_identity' in result)==(response_kind=='new_id')
    assert sum(method.upper()=='POST' for method,_ in calls)==1
    assert sum(method.upper()=='GET' for method,_ in calls)<=1
