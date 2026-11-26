"""First-start failures must never leave an apparently legacy Google database."""
import sqlite3
import pytest
from guided_notes import create_app
from guided_notes.db import connection
from guided_notes.google_login import repository
from google_support import google_app,google_teacher,post


@pytest.mark.parametrize('classroom_mode',[False,True])
@pytest.mark.parametrize('failure_point',['before_metadata','after_metadata'])
def test_interrupted_first_start_rolls_back_and_can_retry(tmp_path,monkeypatch,classroom_mode,failure_point):
    target=tmp_path/'first-start.sqlite3'
    config={'TESTING':True,'SECRET_KEY':'synthetic-test-key','TEACHER_AUTH_MODE':'google',
            'CLASSROOM_MODE':classroom_mode,'DATABASE':str(target)}
    original=repository.initialize
    def fail(db):
        if failure_point=='after_metadata':original(db)
        raise RuntimeError('injected Google initialization failure')
    monkeypatch.setattr(repository,'initialize',fail)
    with pytest.raises(RuntimeError,match='injected Google initialization failure'):create_app(config)
    with sqlite3.connect(target) as check:
        assert check.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()==[]
    monkeypatch.setattr(repository,'initialize',original)
    again=create_app(config)
    with again.app_context():
        db=connection()
        instance=db.execute('SELECT instance_uuid FROM auth_instance').fetchone()[0]
        assert db.execute('SELECT count(*) FROM auth_instance').fetchone()[0]==1
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
    restarted=create_app(config)
    with restarted.app_context():
        assert connection().execute('SELECT instance_uuid FROM auth_instance').fetchone()[0]==instance


def test_init_db_failure_rolls_back_new_schema_and_preserves_existing_data(google_app,google_teacher,monkeypatch):
    post(google_teacher,'/teacher/courses',title='既有課程')
    with google_app.app_context():
        db=connection()
        before={name:[tuple(row) for row in db.execute('SELECT * FROM '+name)]
                for name in ('teachers','courses','auth_instance','google_identities')}
    original=repository.initialize
    def fail(db):
        original(db)
        db.execute('CREATE TABLE partial_init_should_rollback(id INTEGER)')
        raise RuntimeError('injected init-db failure')
    monkeypatch.setattr(repository,'initialize',fail)
    result=google_app.test_cli_runner().invoke(args=['init-db'])
    assert result.exit_code!=0
    with google_app.app_context():
        db=connection()
        assert not db.in_transaction
        assert not db.execute("SELECT 1 FROM sqlite_master WHERE name='partial_init_should_rollback'").fetchone()
        for name,rows in before.items():assert [tuple(row) for row in db.execute('SELECT * FROM '+name)]==rows
    monkeypatch.setattr(repository,'initialize',original)
    assert google_app.test_cli_runner().invoke(args=['init-db']).exit_code==0
