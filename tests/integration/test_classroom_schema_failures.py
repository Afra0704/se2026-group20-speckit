import sqlite3
import pytest

from classroom_009_support import legacy_database, rows, restart
from google_support import google_app, google_teacher
from concurrent.futures import ThreadPoolExecutor


@pytest.mark.parametrize('point', ['copied', 'replaced', 'restored', 'verified'])
def test_failed_upgrade_rolls_back_all_original_objects(tmp_path, monkeypatch, point):
    from guided_notes.activities import classroom_migration
    target = legacy_database(tmp_path)
    before = rows(target)
    with sqlite3.connect(target) as conn:
        original_schema = conn.execute("SELECT type,name,sql FROM sqlite_master ORDER BY name").fetchall()
    def fail(stage):
        if stage == point:
            raise RuntimeError('injected migration failure')
    monkeypatch.setattr(classroom_migration, '_checkpoint', fail)
    with pytest.raises(RuntimeError, match='injected migration failure'):
        restart(target)
    assert rows(target) == before
    with sqlite3.connect(target) as conn:
        assert conn.execute("SELECT type,name,sql FROM sqlite_master ORDER BY name").fetchall() == original_schema
    monkeypatch.setattr(classroom_migration, '_checkpoint', lambda stage: None)
    restart(target)


def test_two_bootstraps_recheck_version_under_the_write_lock(tmp_path):
    target = legacy_database(tmp_path)
    with ThreadPoolExecutor(2) as pool:
        apps = list(pool.map(lambda _:restart(target), range(2)))
    for app in apps:
        assert app.test_client().get('/student').status_code == 200
    with sqlite3.connect(target) as db:
        assert db.execute('SELECT count(*) FROM classroom_schema_versions').fetchone()[0] == 1
        assert db.execute('PRAGMA foreign_key_check').fetchall() == []


def test_foreign_key_restore_failure_stops_bootstrap_and_closes_private_connection(tmp_path, monkeypatch):
    from guided_notes import db as module
    target = legacy_database(tmp_path)
    real_connect = sqlite3.connect
    tracked = []

    class RestoreFailure(sqlite3.Connection):
        enabled_calls = 0
        was_closed = False

        def execute(self, sql, *args):
            if sql == 'PRAGMA foreign_keys=ON':
                self.enabled_calls += 1
                if self.enabled_calls == 2:
                    raise RuntimeError('injected FK restore failure')
            return super().execute(sql, *args)

        def close(self):
            self.was_closed = True
            return super().close()

    def connect(*args, **kwargs):
        kwargs['factory'] = RestoreFailure
        result = real_connect(*args, **kwargs)
        tracked.append(result)
        return result

    monkeypatch.setattr(module.sqlite3, 'connect', connect)
    with pytest.raises(RuntimeError, match='FK restore failure'):
        restart(target)
    assert tracked and all(db.was_closed for db in tracked)
    monkeypatch.setattr(module.sqlite3, 'connect', real_connect)
    # A post-commit restoration failure must prevent serving, but a clean restart
    # can validate the already committed upgrade without copying data again.
    restart(target)


def test_real_google_identity_ciphertext_and_upgrade_rollback(google_app, google_teacher, monkeypatch):
    from google_support import connect, post
    from guided_notes import create_app
    from guided_notes.db import connection
    from guided_notes.google_login import repository
    from classroom_009_support import downgrade_classrooms
    connect(google_teacher)
    course = post(google_teacher, '/teacher/courses', title='saved').json
    post(google_teacher, f"/teacher/courses/{course['course_id']}/classrooms", title='saved')
    target = google_app.config['DATABASE']
    with google_app.app_context():
        before = {name:[tuple(r) for r in connection().execute('SELECT * FROM '+name)]
                  for name in ('auth_instance','teachers','google_identities','google_sheets_credentials','courses','classrooms')}
    downgrade_classrooms(target)
    original = repository.initialize
    def fail(db):
        original(db)
        raise RuntimeError('injected Google failure after upgrade')
    monkeypatch.setattr(repository, 'initialize', fail)
    with pytest.raises(RuntimeError, match='injected Google failure'):
        create_app(dict(google_app.config))
    with sqlite3.connect(target) as db:
        assert not db.execute("SELECT 1 FROM sqlite_master WHERE name='classroom_schema_versions'").fetchone()
        for name, values in before.items():
            assert db.execute('SELECT * FROM '+name).fetchall() == values
    monkeypatch.setattr(repository, 'initialize', original)
    for _ in range(2):
        app = create_app(dict(google_app.config))
        with app.app_context():
            assert connection().execute('PRAGMA foreign_keys').fetchone()[0] == 1
            for name, values in before.items():
                assert [tuple(r) for r in connection().execute('SELECT * FROM '+name)] == values
