import os
from pathlib import Path


def defaults(instance_path):
    secret = os.environ.get("GUIDED_NOTES_SECRET_KEY")
    if secret == "replace-with-a-local-random-secret":
        secret = None
    return {
        "SECRET_KEY": secret,
        "DATABASE": os.environ.get(
            "GUIDED_NOTES_DATABASE", str(Path(instance_path) / "guided-notes.sqlite3")
        ),
        "SESSION_COOKIE_SECURE": os.environ.get("GUIDED_NOTES_HTTPS") == "1",
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "MAX_CONTENT_LENGTH": 64 * 1024,
        "DEMO_CATALOG": os.environ.get("GUIDED_NOTES_DEMO_CATALOG") == "1",
        "AUTH_SECONDS": 8 * 60 * 60,
        "RECOVERY_SECONDS": 7 * 24 * 60 * 60,
        "NOTES_GOOGLE_CLIENT_SECRETS": os.environ.get("NOTES_GOOGLE_CLIENT_SECRETS"),
        "NOTES_GOOGLE_TOKEN": os.environ.get("NOTES_GOOGLE_TOKEN"),
        "NOTES_GOOGLE_TEACHER_ID": (
            int(os.environ["NOTES_GOOGLE_TEACHER_ID"])
            if os.environ.get("NOTES_GOOGLE_TEACHER_ID", "").isdigit() else None),
    }
