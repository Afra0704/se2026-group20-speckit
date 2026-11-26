from datetime import datetime, timedelta, timezone

import pytest

from guided_notes.google_login.transport import CredentialSnapshot, CredentialSnapshotExpired
from guided_notes.notes.sheets_gateway import SheetsGateway, build_google_service, AnchorWrite, GatewayError


class Http:
    def __init__(self,status=200):
        self.calls=[]
        self.status=status
        self.connections={}
    def request(self,uri,method='GET',body=None,headers=None,**kwargs):
        import httplib2
        self.calls.append((uri,method,body,headers))
        return httplib2.Response({'status':str(self.status),'content-type':'application/json'}), b'{"sheets":[]}'


def sdk_gateway(monkeypatch,status=200):
    import httplib2
    http=Http(status)
    monkeypatch.setattr(httplib2,'Http',lambda **kwargs:http)
    snapshot=CredentialSnapshot('synthetic',datetime.now(timezone.utc)+timedelta(hours=1))
    service=build_google_service(snapshot)
    return SheetsGateway(service),http,snapshot


def test_real_sdk_401_is_one_request_no_refresh(monkeypatch):
    gateway,http,snapshot=sdk_gateway(monkeypatch,401)
    with pytest.raises(GatewayError) as error:gateway.list_worksheets('synthetic')
    assert error.value.code=='GOOGLE_REAUTH_REQUIRED' and len(http.calls)==1
    assert not hasattr(snapshot,'refresh_token') and not hasattr(snapshot,'client_secret')


@pytest.mark.parametrize('operation',['read','write'])
def test_real_sdk_expiry_before_send_has_zero_http(monkeypatch,operation):
    gateway,http,snapshot=sdk_gateway(monkeypatch)
    snapshot.expiry=datetime.now(timezone.utc)-timedelta(seconds=1)
    with pytest.raises(GatewayError) as error:
        if operation=='read':gateway.list_worksheets('synthetic')
        else:gateway.write_unit('synthetic',7,[AnchorWrite('q1',4,5,' =001 ')])
    assert error.value.code=='GOOGLE_CREDENTIALS_REFRESH_REQUIRED' and http.calls==[]
    if operation=='write':assert error.value.write_outcome=='failed'


def test_real_sdk_write_keeps_raw_and_never_replays_401(monkeypatch):
    import json
    gateway,http,snapshot=sdk_gateway(monkeypatch,401)
    with pytest.raises(GatewayError) as error:gateway.write_unit('synthetic',7,[AnchorWrite('q1',4,5,' =001 ')])
    assert len(http.calls)==1 and error.value.write_outcome=='failed'
    body=json.loads(http.calls[0][2])
    assert body['valueInputOption']=='RAW' and body['data'][0]['values']==[[' =001 ']]


def test_snapshot_never_refreshes_or_hides_expiry():
    expiry = datetime.now(timezone.utc) + timedelta(hours=1)
    snapshot = CredentialSnapshot('synthetic-access', expiry)
    assert snapshot.valid
    headers = {}
    snapshot.before_request(lambda *a, **k: pytest.fail('network refresh'), 'GET', 'https://example.test', headers)
    assert headers['authorization'] == 'Bearer synthetic-access'
    with pytest.raises(CredentialSnapshotExpired):
        snapshot.refresh(None)
    snapshot.expiry = datetime.now(timezone.utc) - timedelta(seconds=1)
    assert not snapshot.valid
    with pytest.raises(CredentialSnapshotExpired):
        snapshot.before_request(None, 'GET', 'https://example.test', {})
