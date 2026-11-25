import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from guided_notes.notes.sheets_gateway import GatewayError, build_google_service


class ClientFactoryTests(unittest.TestCase):
    def dependencies(self):
        modules = {name: ModuleType(name) for name in (
            "httplib2", "google_auth_httplib2", "googleapiclient", "googleapiclient.discovery")}
        modules["httplib2"].Http = Mock(return_value="http")
        modules["google_auth_httplib2"].AuthorizedHttp = Mock(return_value="authorized-http")
        modules["googleapiclient.discovery"].build = Mock(return_value="service")
        return modules

    def test_explicit_timeout_and_no_automatic_refresh_replay(self):
        modules = self.dependencies()
        credentials = SimpleNamespace(valid=True)
        with patch.dict(sys.modules, modules):
            self.assertEqual(build_google_service(credentials), "service")
        modules["httplib2"].Http.assert_called_once_with(timeout=30)
        modules["google_auth_httplib2"].AuthorizedHttp.assert_called_once_with(
            credentials, http="http", refresh_status_codes=(), max_refresh_attempts=0)
        modules["googleapiclient.discovery"].build.assert_called_once_with(
            "sheets", "v4", http="authorized-http", cache_discovery=False)

    def test_expired_credentials_fail_before_service_creation(self):
        modules = self.dependencies()
        with patch.dict(sys.modules, modules), self.assertRaises(GatewayError) as caught:
            build_google_service(SimpleNamespace(valid=False))
        self.assertEqual(caught.exception.code, "GOOGLE_REAUTH_REQUIRED")
        modules["googleapiclient.discovery"].build.assert_not_called()

    def test_client_creation_errors_are_sanitized(self):
        modules = self.dependencies()
        modules["googleapiclient.discovery"].build.side_effect = RuntimeError("SECRET_TOKEN")
        with patch.dict(sys.modules, modules), self.assertRaises(GatewayError) as caught:
            build_google_service(SimpleNamespace(valid=True))
        self.assertNotIn("SECRET", str(caught.exception))
