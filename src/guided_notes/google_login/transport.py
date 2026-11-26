"""A token snapshot, deliberately incapable of network refresh or replay."""
from datetime import datetime, timedelta, timezone

from google.auth.credentials import Credentials


class CredentialSnapshotExpired(Exception):
    pass


class CredentialSnapshot(Credentials):
    def __init__(self, token, expiry, scopes=(), guard=None):
        super().__init__()
        self.token = token
        self.expiry = expiry
        self.scopes = tuple(scopes)
        self._guard = guard

    @property
    def expired(self):
        return self.expiry is None or self.expiry <= datetime.now(timezone.utc) + timedelta(seconds=30)

    @property
    def valid(self):
        return bool(self.token) and not self.expired

    def refresh(self, request):
        raise CredentialSnapshotExpired()

    def before_request(self, request, method, url, headers):
        if self._guard:
            self._guard()
        if not self.valid:
            raise CredentialSnapshotExpired()
        self.apply(headers)
