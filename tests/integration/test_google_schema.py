import sqlite3
from pathlib import Path
import pytest
from google_support import google_app, google_teacher
from guided_notes import create_app
from guided_notes.db import connection


def test_instance_is_idempotent_and_constraints(google_app,google_teacher):
    with google_app.app_context():
        db=connection();before=db.execute('SELECT instance_uuid FROM auth_instance').fetchone()[0]
        with pytest.raises(sqlite3.IntegrityError): db.execute("INSERT INTO auth_instance VALUES(2,'other',CURRENT_TIMESTAMP)")
        with pytest.raises(sqlite3.IntegrityError): db.execute("UPDATE auth_browsers SET epoch=-1")
    result=google_app.test_cli_runner().invoke(args=['init-db'])
    assert result.exit_code==0,result.output
    with google_app.app_context():
        assert connection().execute('SELECT instance_uuid FROM auth_instance').fetchone()[0]==before
        assert connection().execute('SELECT count(*) FROM google_identities').fetchone()[0]==1


def test_old_database_guard_does_not_mutate(tmp_path):
    path=tmp_path/'old.db'
    with sqlite3.connect(path) as db: db.execute('CREATE TABLE teachers(id INTEGER PRIMARY KEY)')
    before=path.read_bytes()
    with pytest.raises(RuntimeError,match='new empty database'):
        create_app({'TESTING':True,'SECRET_KEY':'test','DATABASE':str(path)})
    assert path.read_bytes()==before


def test_password_mode_cannot_be_formal(tmp_path):
    with pytest.raises(RuntimeError,match='TESTING'):
        create_app({'SECRET_KEY':'test','TEACHER_AUTH_MODE':'test_password','DATABASE':str(tmp_path/'test.db')})
