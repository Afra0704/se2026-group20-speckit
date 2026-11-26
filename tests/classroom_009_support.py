"""Synthetic legacy databases; never open an operator database."""
from pathlib import Path
import sqlite3

from guided_notes import create_app


def legacy_database(tmp_path):
    from guided_notes import db
    target = tmp_path / 'legacy-008.sqlite3'
    with sqlite3.connect(target) as conn:
        conn.executescript((Path(db.__file__).parent / 'activities/schema.sql').read_text(encoding='utf-8'))
        conn.executescript((Path(__file__).parent / 'fixtures/classroom-008.sql').read_text(encoding='utf-8'))
        conn.execute("INSERT INTO teachers(id,username,password_hash) VALUES (1,'fixture','synthetic')")
        conn.execute("INSERT INTO courses(id,teacher_id,title) VALUES ('course',1,'saved')")
        conn.execute("INSERT INTO classrooms(id,course_id,title,code) VALUES ('room','course','saved','AB123')")
        conn.execute("INSERT INTO activities(id,teacher_id,code,import_id,import_version) VALUES ('activity',1,'legacy-activity','fixed-version',1)")
        conn.execute("INSERT INTO classroom_activities(activity_id,classroom_id,title) VALUES ('activity','room','saved activity')")
        conn.execute("UPDATE classrooms SET current_activity_id='activity' WHERE id='room'")
        conn.execute("INSERT INTO questions VALUES ('activity','q',0,'{}')")
        conn.execute("INSERT INTO classroom_groups(id,classroom_id,name) VALUES (1,'room','A')")
        conn.execute("INSERT INTO classroom_memberships VALUES (1,'room',1,'synthetic-proof',9999999999)")
        conn.execute("INSERT INTO classroom_grants VALUES ('synthetic-grant',1,9999999999,0)")
        conn.execute('CREATE TABLE preserved_ciphertexts(id TEXT PRIMARY KEY, value BLOB)')
        conn.execute("INSERT INTO preserved_ciphertexts VALUES ('uuid',?)", (b'synthetic-encrypted-data',))
    return target


def downgrade_classrooms(target):
    """Reconstruct the old boundary solely within a test-created database."""
    import re
    schema = (Path(__file__).parent / 'fixtures/classroom-008.sql').read_text(encoding='utf-8')
    statement = re.search(r'CREATE TABLE IF NOT EXISTS classrooms \(.*?\n\);', schema, re.S)[0]
    with sqlite3.connect(target, autocommit=True) as db:
        db.execute('PRAGMA foreign_keys=OFF')
        db.execute('BEGIN IMMEDIATE')
        db.execute(statement.replace('IF NOT EXISTS classrooms', 'legacy_classrooms', 1))
        db.execute('INSERT INTO legacy_classrooms SELECT * FROM classrooms')
        db.execute('DROP TABLE classrooms')
        db.execute('ALTER TABLE legacy_classrooms RENAME TO classrooms')
        db.execute('DROP TABLE classroom_schema_versions')
        db.execute('COMMIT')


def config(target):
    return dict(TESTING=True, TEACHER_AUTH_MODE='test_password', SECRET_KEY='test-only',
                CLASSROOM_MODE=True, DATABASE=str(target))


def rows(target):
    with sqlite3.connect(target) as conn:
        return {name: conn.execute('SELECT * FROM "' + name + '"').fetchall()
                for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
                if name != 'classroom_schema_versions'}


def restart(target):
    return create_app(config(target))
