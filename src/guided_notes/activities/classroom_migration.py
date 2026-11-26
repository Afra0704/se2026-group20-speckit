"""009 classroom upgrade, executed only on a private bootstrap connection."""
import hashlib
import re


COLUMNS = ('id', 'course_id', 'title', 'code', 'state', 'state_version',
           'current_activity_id', 'created_at', 'closed_at')


def quote(name):
    return '"' + name.replace('"', '""') + '"'


def needs_rebuild(db):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='classrooms'").fetchone():
        return False
    return any(row['unique'] and not row['partial'] and
               [r['name'] for r in db.execute('PRAGMA index_info(' + quote(row['name']) + ')')] == ['code']
               for row in db.execute('PRAGMA index_list(classrooms)'))


def fingerprints(db):
    result = {}
    for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_stat%'"):
        name = row[0]
        if name == 'classroom_schema_versions':
            continue
        # Do not log data or ciphertext; only compare private in-memory digests.
        contents = sorted(repr(tuple(r)) for r in db.execute('SELECT * FROM ' + quote(name)))
        result[name] = hashlib.sha256(repr(contents).encode()).digest()
    return result


def _checkpoint(stage):
    """Fault-injection seam; no production switch or environment override."""


def table_definition(schema):
    match = re.search(r'CREATE TABLE IF NOT EXISTS classrooms \(.*?\n\);', schema, re.S)
    if match is None:
        raise RuntimeError('Missing classroom schema definition.')
    return match[0]


def canonical(sql):
    # Recognize the shipped layouts; never silently discard extra constraints.
    sql = sql.replace('"classrooms"', 'classrooms')
    return re.sub(r'\s+', '', sql.replace('IF NOT EXISTS ', '')).rstrip(';')


def validate(db):
    indexes = list(db.execute('PRAGMA index_list(classrooms)'))
    index = next((r for r in indexes if r['name'] == 'classrooms_open_code_unique'), None)
    sql = db.execute("SELECT sql FROM sqlite_master WHERE name='classrooms_open_code_unique'").fetchone()
    if (index is None or not index['unique'] or not index['partial'] or sql is None or
            not re.search(r"\bWHERE\s+state\s*=\s*'OPEN'\s*$", sql[0], re.I) or
            [r['name'] for r in db.execute('PRAGMA index_info(classrooms_open_code_unique)')] != ['code'] or
            needs_rebuild(db)):
        raise RuntimeError('Unsupported classroom schema: invalid effective-code constraint.')
    if [r[0] for r in db.execute('SELECT version FROM classroom_schema_versions')] != [9]:
        raise RuntimeError('Unsupported classroom schema version.')
    if db.execute('PRAGMA foreign_key_check').fetchall():
        raise RuntimeError('Classroom schema foreign key check failed.')


def upgrade(db, schema, execute):
    exists = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='classrooms'").fetchone()
    if not exists:
        return
    columns = tuple(row['name'] for row in db.execute('PRAGMA table_info(classrooms)'))
    if columns != COLUMNS:
        raise RuntimeError('Unsupported classroom schema; existing data was preserved.')
    definition = table_definition(schema)
    existing = db.execute("SELECT sql FROM sqlite_master WHERE name='classrooms'").fetchone()[0]
    expected = definition.replace('code TEXT NOT NULL,', 'code TEXT NOT NULL UNIQUE,') if needs_rebuild(db) else definition
    if canonical(existing) != canonical(expected):
        raise RuntimeError('Unsupported classroom schema definition; existing data was preserved.')
    if not needs_rebuild(db):
        indexes = {r['name']: r for r in db.execute('PRAGMA index_list(classrooms)')}
        if 'classrooms_open_code_unique' not in indexes:
            raise RuntimeError('Unsupported classroom schema; effective-code index is missing.')
        return
    if db.execute('PRAGMA foreign_keys').fetchone()[0] != 0 or not db.in_transaction:
        raise RuntimeError('Classroom schema upgrade requires a private bootstrap transaction.')
    before = fingerprints(db)
    objects = [dict(r) for r in db.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_master WHERE sql IS NOT NULL "
        "AND type IN ('trigger','view','index') ORDER BY type,name")
        if r['tbl_name'] == 'classrooms' or re.search(r'\bclassrooms\b', r['sql'], re.I)]
    for obj in objects:
        if obj['type'] in ('trigger', 'view'):
            db.execute('DROP ' + obj['type'].upper() + ' ' + quote(obj['name']))
    statement = definition.replace('IF NOT EXISTS classrooms', 'classrooms_009_new', 1)
    db.execute(statement)
    columns_sql = ','.join(quote(c) for c in COLUMNS)
    db.execute(f'INSERT INTO classrooms_009_new({columns_sql}) SELECT {columns_sql} FROM classrooms')
    _checkpoint('copied')
    db.execute('DROP TABLE classrooms')
    db.execute('ALTER TABLE classrooms_009_new RENAME TO classrooms')
    _checkpoint('replaced')
    for obj in objects:
        db.execute(obj['sql'])
    execute(db, schema)
    _checkpoint('restored')
    if fingerprints(db) != before:
        raise RuntimeError('Classroom schema upgrade changed existing data; rolled back.')
    if db.execute('PRAGMA foreign_key_check').fetchall():
        raise RuntimeError('Classroom schema foreign key check failed; rolled back.')
    if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
        raise RuntimeError('Classroom schema integrity check failed; rolled back.')
    for obj in objects:
        if obj['type'] == 'view':
            db.execute('SELECT * FROM ' + quote(obj['name']) + ' LIMIT 0')
    _checkpoint('verified')
