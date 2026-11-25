"""Desktop OAuth helpers, independent of Flask and the shared application DB."""
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
TOKEN_URI = "https://oauth2.googleapis.com/token"


class AuthError(RuntimeError):
    def __init__(self, code):
        self.code = code
        self.http_status = 503
        super().__init__(code)


def validate_paths(client_path, token_path, repo_root):
    try:
        if not client_path or not token_path:
            raise ValueError
        root = Path(repo_root).resolve()
        client, token = Path(client_path).expanduser().resolve(), Path(token_path).expanduser().resolve()
        if (client.is_relative_to(root) or token.is_relative_to(root) or client == token
                or (client.exists() and token.exists() and client.samefile(token))
                or token.is_dir() or not client.is_file()):
            raise ValueError
        return client, token
    except (OSError, ValueError, TypeError, RuntimeError):
        raise AuthError("GOOGLE_CREDENTIAL_PATH_INVALID") from None


def _read_client(client):
    try:
        config = json.loads(client.read_text(encoding="utf-8-sig"))
        installed = config["installed"]
        if (not isinstance(installed["client_id"], str) or not installed["client_id"]
                or not isinstance(installed["client_secret"], str) or not installed["client_secret"]
                or installed["token_uri"] != TOKEN_URI
                or installed["auth_uri"] not in ("https://accounts.google.com/o/oauth2/auth",
                                                "https://accounts.google.com/o/oauth2/v2/auth")):
            raise ValueError
        return config
    except (OSError, ValueError, KeyError, TypeError):
        raise AuthError("GOOGLE_CLIENT_CONFIG_INVALID") from None


def _libraries():
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        raise AuthError("GOOGLE_DEPENDENCIES_MISSING") from None
    return SimpleNamespace(load=Credentials.from_authorized_user_info,
        flow=lambda config, scopes: InstalledAppFlow.from_client_config(
            config, scopes=scopes, autogenerate_code_verifier=True), request=Request)


def _save(token_path, credentials):
    temporary = None
    try:
        payload = credentials.to_json()
        json.loads(payload)
        token_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd, temporary = tempfile.mkstemp(prefix=".notes-token-", suffix=".tmp", dir=token_path.parent)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, token_path)
        temporary = None
    except (OSError, ValueError, TypeError):
        raise AuthError("GOOGLE_TOKEN_SAVE_FAILED") from None
    finally:
        if temporary is not None:
            try:
                Path(temporary).unlink(missing_ok=True)
            except OSError:
                pass


def authorize(client_path, token_path, *, repo_root, interactive=False, libraries=None):
    """Load/refresh credentials; open a browser only on an explicit CLI action.

    Never call inside a database transaction or a write operation's source lease.
    Normal requests fail closed when consent is needed. Do not log returned creds.
    """
    client, token = validate_paths(client_path, token_path, repo_root)
    config = _read_client(client)
    libraries = libraries or _libraries()
    credentials = None
    if token.is_file():
        try:
            info = json.loads(token.read_text(encoding="utf-8"))
            if (info["client_id"] != config["installed"]["client_id"] or info["token_uri"] != TOKEN_URI
                    or not isinstance(info["scopes"], list) or not set(SCOPES) <= set(info["scopes"])):
                raise ValueError
            credentials = libraries.load(info)
            refreshed = False
            if not credentials.valid and credentials.expired and credentials.refresh_token:
                credentials.refresh(libraries.request())
                if not credentials.valid:
                    raise ValueError
                refreshed = True
            if (not credentials.valid or not credentials.has_scopes(SCOPES)
                    or (credentials.granted_scopes is not None
                        and not set(SCOPES) <= set(credentials.granted_scopes))):
                raise ValueError
            if refreshed:
                _save(token, credentials)
            return credentials
        except AuthError:
            raise
        except Exception:
            if not interactive:
                raise AuthError("GOOGLE_REAUTH_REQUIRED") from None
    if not interactive:
        raise AuthError("GOOGLE_REAUTH_REQUIRED")
    try:
        flow = libraries.flow(config, SCOPES)
        credentials = flow.run_local_server(host="127.0.0.1", port=0, open_browser=True,
            authorization_prompt_message="", success_message="Authorization completed. You may close this window.",
            timeout_seconds=120, prompt="consent")
        if (not credentials.valid or not credentials.has_scopes(SCOPES)
                or (credentials.granted_scopes is not None
                    and not set(SCOPES) <= set(credentials.granted_scopes))):
            raise ValueError
    except Exception:
        raise AuthError("GOOGLE_REAUTH_REQUIRED") from None
    _save(token, credentials)
    return credentials
