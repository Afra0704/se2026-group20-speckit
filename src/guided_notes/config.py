import os
from pathlib import Path


def defaults(instance_path):
    classroom_mode = os.environ.get("GUIDED_NOTES_CLASSROOM_MODE") == "1"
    secret = os.environ.get("GUIDED_NOTES_SECRET_KEY")
    if secret == "replace-with-a-local-random-secret":
        secret = None
    return {
        "SECRET_KEY": secret,
        "CLASSROOM_MODE": classroom_mode,
        "DATABASE": os.environ.get(
            "GUIDED_NOTES_DATABASE",
            str(Path(instance_path) / ("classroom-004.sqlite3" if classroom_mode else "guided-notes.sqlite3")),
        ),
        "SESSION_COOKIE_SECURE": os.environ.get("GUIDED_NOTES_HTTPS") == "1",
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "MAX_CONTENT_LENGTH": 64 * 1024,
        "DEMO_CATALOG": os.environ.get("GUIDED_NOTES_DEMO_CATALOG") == "1",
        "AUTH_SECONDS": 8 * 60 * 60,
        "RECOVERY_SECONDS": 7 * 24 * 60 * 60,
    }
