"""Small shared persistence helpers; never hold a transaction over a network call."""
from pathlib import Path
from uuid import uuid4

from flask import current_app

from ..db import connection


def google_mode():
    return current_app.config['TEACHER_AUTH_MODE'] == 'google'


def initialize(db):
    db.executescript(Path(__file__).with_name('schema.sql').read_text(encoding='utf-8'))
    db.execute('INSERT INTO auth_instance(singleton,instance_uuid) VALUES(1,?) ON CONFLICT DO NOTHING', (str(uuid4()),))


def instance_id(db=None):
    return (db or connection()).execute('SELECT instance_uuid FROM auth_instance WHERE singleton=1').fetchone()[0]


def identity(teacher_id, db=None):
    return (db or connection()).execute('SELECT i.*,t.active FROM google_identities i JOIN teachers t ON t.id=i.teacher_id WHERE i.teacher_id=?',
                                      (teacher_id,)).fetchone()
