"""Credential-core tests; Flask command registration is tested in integration."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from contextlib import redirect_stdout
import io

from guided_notes.notes.google_authorization import AuthError, SCOPES, authorize, validate_paths


class AuthorizationTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).parents[2] / "tmp"
        root.mkdir(exist_ok=True)
        self.temp = TemporaryDirectory(dir=root)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / "repository"
        self.repo.mkdir()
        self.client = self.base / "client.json"
        self.token = self.base / "token.json"
        self.config = {"installed": {"client_id": "synthetic-client", "client_secret": "synthetic-secret",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token", "redirect_uris": ["http://localhost"]}}
        self.client.write_text(json.dumps(self.config), encoding="utf-8")
        self.creds = SimpleNamespace(valid=True, expired=False, refresh_token="synthetic-refresh",
            has_scopes=lambda scopes: scopes == SCOPES,
            granted_scopes=None, refresh=Mock(), to_json=lambda: json.dumps(self.token_data()))
        self.flow = SimpleNamespace(run_local_server=Mock(return_value=self.creds))
        self.libraries = SimpleNamespace(load=Mock(return_value=self.creds),
            flow=Mock(return_value=self.flow), request=Mock(return_value="request"))

    def token_data(self):
        return {"token": "synthetic-token", "refresh_token": "synthetic-refresh", "scopes": SCOPES,
            "client_id": "synthetic-client", "client_secret": "synthetic-secret",
            "token_uri": "https://oauth2.googleapis.com/token", "type": "authorized_user"}

    def call(self, **kwargs):
        return authorize(self.client, self.token, repo_root=self.repo, libraries=self.libraries, **kwargs)

    def test_client_and_token_must_be_distinct_and_outside_repo(self):
        for client, token in ((self.repo / "c.json", self.token),
                              (self.client, self.repo / "t.json"), (self.client, self.client)):
            with self.subTest(client=client), self.assertRaises(AuthError):
                validate_paths(client, token, self.repo)

    def test_missing_token_never_opens_browser_in_normal_requests(self):
        with self.assertRaises(AuthError) as caught:
            self.call()
        self.assertEqual(caught.exception.code, "GOOGLE_REAUTH_REQUIRED")
        self.libraries.flow.assert_not_called()

    def test_desktop_loopback_and_atomic_token_save(self):
        self.assertIs(self.call(interactive=True), self.creds)
        self.assertEqual(json.loads(self.token.read_text(encoding="utf-8"))["token"], "synthetic-token")
        kwargs = self.flow.run_local_server.call_args.kwargs
        self.assertEqual((kwargs["host"], kwargs["port"]), ("127.0.0.1", 0))
        self.assertEqual(kwargs["authorization_prompt_message"], "")
        self.assertEqual(self.libraries.flow.call_args.args[1], SCOPES)
        self.assertEqual(list(self.base.glob("*.tmp")), [])

    def test_valid_token_is_loaded_without_browser_or_refresh(self):
        self.token.write_text(json.dumps(self.token_data()), encoding="utf-8")
        self.assertIs(self.call(), self.creds)
        self.creds.refresh.assert_not_called()
        self.libraries.flow.assert_not_called()

    def test_refresh_persists_updated_token(self):
        self.token.write_text(json.dumps(self.token_data()), encoding="utf-8")
        self.creds.valid = False
        self.creds.expired = True
        self.creds.refresh.side_effect = lambda _: setattr(self.creds, "valid", True)
        self.assertIs(self.call(), self.creds)
        self.creds.refresh.assert_called_once_with("request")
        self.libraries.flow.assert_not_called()

    def test_invalid_grant_is_sanitized_and_original_token_retained(self):
        original = json.dumps(self.token_data())
        self.token.write_text(original, encoding="utf-8")
        self.creds.valid = False
        self.creds.expired = True
        self.creds.refresh.side_effect = RuntimeError("invalid_grant SECRET_TOKEN")
        with self.assertRaises(AuthError) as caught:
            self.call()
        self.assertEqual(caught.exception.code, "GOOGLE_REAUTH_REQUIRED")
        self.assertNotIn("SECRET", str(caught.exception))
        self.assertEqual(self.token.read_text(encoding="utf-8"), original)

    def test_wrong_client_or_readonly_scope_requires_reauthorization(self):
        for changes in ({"client_id": "other-client"}, {"scopes": [SCOPES[0] + ".readonly"]},
                        {"token_uri": "https://evil.invalid/token"}):
            self.token.write_text(json.dumps({**self.token_data(), **changes}), encoding="utf-8")
            with self.subTest(changes=changes), self.assertRaises(AuthError):
                self.call()
        self.libraries.load.assert_not_called()

    def test_web_client_is_rejected_before_authorizing(self):
        self.client.write_text(json.dumps({"web": self.config["installed"]}), encoding="utf-8")
        with self.assertRaises(AuthError):
            self.call(interactive=True)
        self.libraries.flow.assert_not_called()

    def test_atomic_save_failure_preserves_previous_token(self):
        original = json.dumps(self.token_data())
        self.token.write_text(original, encoding="utf-8")
        self.creds.valid = False
        self.creds.expired = True
        self.creds.refresh.side_effect = lambda _: setattr(self.creds, "valid", True)
        with patch("guided_notes.notes.google_authorization.os.replace", side_effect=OSError("SECRET")):
            with self.assertRaises(AuthError) as caught:
                self.call()
        self.assertEqual(caught.exception.code, "GOOGLE_TOKEN_SAVE_FAILED")
        self.assertEqual(self.token.read_text(encoding="utf-8"), original)
        self.assertEqual(list(self.base.glob(".notes-token-*.tmp")), [])

    def test_cli_check_config_never_authorizes_or_prints_secrets(self):
        from guided_notes.notes.cli import main
        output = io.StringIO()
        with patch("guided_notes.notes.cli.authorize") as authorize_mock, redirect_stdout(output):
            code = main(["check-config", "--client", str(self.client), "--token", str(self.token),
                         "--repo-root", str(self.repo)])
        self.assertEqual(code, 0)
        authorize_mock.assert_not_called()
        self.assertNotIn("synthetic-secret", output.getvalue())

    def test_cli_failure_only_reports_safe_code(self):
        from guided_notes.notes.cli import main
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["check-config", "--client", str(self.repo / "bad.json"),
                         "--token", str(self.token), "--repo-root", str(self.repo)])
        self.assertEqual(code, 1)
        self.assertIn("GOOGLE_CREDENTIAL_PATH_INVALID", output.getvalue())
        self.assertNotIn(str(self.repo), output.getvalue())
