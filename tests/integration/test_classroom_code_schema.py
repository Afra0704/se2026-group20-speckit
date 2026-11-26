import sqlite3
import pytest

from classroom_009_support import legacy_database, rows, restart


def test_legacy_upgrade_preserves_rows_and_releases_only_closed_codes(tmp_path):
    target = legacy_database(tmp_path)
    before = rows(target)
    app = restart(target)
    after = rows(target)
    assert all(after[name] == values for name, values in before.items())
    with sqlite3.connect(target) as conn:
        conn.execute('PRAGMA foreign_keys=ON')
        assert conn.execute('PRAGMA foreign_key_check').fetchall() == []
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO classrooms(id,course_id,title,code) VALUES ('other','course','other','AB123')")
        conn.execute("UPDATE classrooms SET state='CLOSED' WHERE id='room'")
        conn.execute("INSERT INTO classrooms(id,course_id,title,code) VALUES ('other','course','other','AB123')")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE classrooms SET state='OPEN' WHERE id='room'")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE classrooms SET code='CD456' WHERE id='room'")
    restart(target)
    assert app.test_cli_runner().invoke(args=['init-db']).exit_code == 0


def test_current_activity_composite_foreign_key_survives(tmp_path):
    target = legacy_database(tmp_path)
    restart(target)
    with sqlite3.connect(target) as conn:
        fk = conn.execute('PRAGMA foreign_key_list(classrooms)').fetchall()
        assert any(r[2] == 'classroom_activities' and r[3] == 'current_activity_id' for r in fk)
        assert conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'


def test_unknown_classroom_columns_are_preserved_by_refusing_upgrade(tmp_path):
    target = legacy_database(tmp_path)
    with sqlite3.connect(target) as conn:
        conn.execute('ALTER TABLE classrooms ADD COLUMN unknown_extension TEXT')
    before = rows(target)
    with pytest.raises(RuntimeError, match='schema'):
        restart(target)
    assert rows(target) == before


def test_dependent_view_and_trigger_are_restored(tmp_path):
    target = legacy_database(tmp_path)
    with sqlite3.connect(target) as db:
        db.execute('CREATE VIEW saved_room_view AS SELECT id,code FROM classrooms')
        db.execute("CREATE TRIGGER saved_room_trigger AFTER UPDATE OF title ON courses BEGIN SELECT count(*) FROM classrooms; END")
    restart(target)
    with sqlite3.connect(target) as db:
        assert db.execute('SELECT * FROM saved_room_view').fetchall() == [('room','AB123')]
        assert db.execute("SELECT 1 FROM sqlite_master WHERE name='saved_room_trigger'").fetchone()


def test_marker_does_not_hide_a_wrong_named_index(tmp_path):
    target = legacy_database(tmp_path)
    restart(target)
    with sqlite3.connect(target) as db:
        db.execute('DROP INDEX classrooms_open_code_unique')
        db.execute('CREATE INDEX classrooms_open_code_unique ON classrooms(code)')
    with pytest.raises(RuntimeError, match='schema'):
        restart(target)


def test_unknown_constraint_is_not_silently_removed(tmp_path):
    from guided_notes.db import execute_schema_statements
    from pathlib import Path
    from guided_notes import db as module
    target = tmp_path / 'unknown.sqlite3'
    schema = Path(module.__file__).parent / 'activities'
    with sqlite3.connect(target) as db:
        db.executescript((schema / 'schema.sql').read_text(encoding='utf-8'))
        legacy = (Path(__file__).parents[1] / 'fixtures/classroom-008.sql').read_text(encoding='utf-8')
        db.executescript(legacy.replace('code TEXT NOT NULL UNIQUE,', 'code TEXT NOT NULL UNIQUE CHECK(length(code)=5),'))
    before = rows(target)
    with pytest.raises(RuntimeError, match='schema definition'):
        restart(target)
    assert rows(target) == before
