import os
from pathlib import Path


def defaults(instance_path):
    classroom_mode = os.environ.get("GUIDED_NOTES_CLASSROOM_MODE") == "1"
    secret = os.environ.get("GUIDED_NOTES_SECRET_KEY")
    if secret == "replace-with-a-local-random-secret":
        secret = None
    return {
        "TEACHER_AUTH_MODE": "google",
        "PUBLIC_ORIGIN": os.environ.get("GUIDED_NOTES_PUBLIC_ORIGIN", "http://127.0.0.1:5000"),
        "GOOGLE_REDIRECT_URI": os.environ.get("GUIDED_NOTES_GOOGLE_REDIRECT_URI", "http://127.0.0.1:5000/auth/google/callback"),
        "GOOGLE_WEB_CLIENT_SECRETS": os.environ.get("GUIDED_NOTES_GOOGLE_WEB_CLIENT_SECRETS"),
        "GOOGLE_TOKEN_KEY_FILE": os.environ.get("GUIDED_NOTES_GOOGLE_TOKEN_KEY_FILE"),
        "GOOGLE_PICKER_CLIENT_SECRETS": os.environ.get("GUIDED_NOTES_GOOGLE_PICKER_CLIENT_SECRETS"),
        "PICKER_API_KEY": os.environ.get("GUIDED_NOTES_PICKER_API_KEY"),
        "PICKER_APP_ID": os.environ.get("GUIDED_NOTES_PICKER_APP_ID"),
        "SECRET_KEY": secret,
        "CLASSROOM_MODE": classroom_mode,
        "DATABASE": os.environ.get(
            "GUIDED_NOTES_DATABASE",
            str(Path(instance_path) / ("classroom-007.sqlite3" if classroom_mode else "guided-notes-007.sqlite3")),
        ),
        "SESSION_COOKIE_SECURE": os.environ.get("GUIDED_NOTES_HTTPS") == "1",
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "MAX_CONTENT_LENGTH": 64 * 1024,
        "AUTH_SECONDS": 8 * 60 * 60,
        "RECOVERY_SECONDS": 7 * 24 * 60 * 60,
        "NOTES_GOOGLE_CLIENT_SECRETS": os.environ.get("NOTES_GOOGLE_CLIENT_SECRETS"),
        "NOTES_GOOGLE_TOKEN": os.environ.get("NOTES_GOOGLE_TOKEN"),
        "NOTES_GOOGLE_TEACHER_ID": (
            int(os.environ["NOTES_GOOGLE_TEACHER_ID"])
            if os.environ.get("NOTES_GOOGLE_TEACHER_ID", "").isdigit() else None),
    }
