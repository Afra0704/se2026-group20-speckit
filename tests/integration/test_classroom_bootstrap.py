import sqlite3
from pathlib import Path

import pytest

from guided_notes import create_app


def test_classroom_bootstrap_is_separate_and_idempotent(app, tmp_path):
    original = app.config["DATABASE"]
    original_bytes = Path(original).read_bytes()
    with pytest.raises(RuntimeError, match="separate database"):
        create_app({"TESTING": True, "SECRET_KEY": "test-only", "CLASSROOM_MODE": True, "DATABASE": original})
    assert Path(original).read_bytes() == original_bytes
    config = {"TESTING": True, "SECRET_KEY": "test-only", "CLASSROOM_MODE": True,
              "DATABASE": str(tmp_path / "separate.sqlite3")}
    create_app(config)
    with sqlite3.connect(config["DATABASE"]) as db:
        db.execute("INSERT INTO teachers(username,password_hash) VALUES ('saved','fixture')")
    create_app(config)
    with sqlite3.connect(config["DATABASE"]) as db:
        assert db.execute("SELECT username FROM teachers").fetchone() == ("saved",)
