from contextlib import contextmanager
from pathlib import Path
import sqlite3
import time
import click
from functools import wraps

from flask import current_app, g


class DatabaseBusy(Exception):
    pass


def read_view(view):
    """Authorize and materialize a response from one request-local snapshot."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        db = connection()
        owns = not db.in_transaction
        if owns:
            db.execute('BEGIN')
        try:
            return view(*args, **kwargs)
        finally:
            if owns and db.in_transaction:
                db.execute('ROLLBACK')
    return wrapped


def connection():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"], autocommit=True, timeout=0.25)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@contextmanager
def write_transaction(db=None):
    db = db if db is not None else connection()
    try:
        for attempt in range(3):
            try:
                db.execute("BEGIN IMMEDIATE")
                break
            except sqlite3.OperationalError as error:
                if error.sqlite_errorcode & 255 != sqlite3.SQLITE_BUSY:
                    raise
                if attempt == 2:
                    raise DatabaseBusy from error
                time.sleep(0.025 * (attempt + 1))
        yield db
        db.execute("COMMIT")
    except BaseException as error:
        if db.in_transaction:
            db.execute("ROLLBACK")
        if isinstance(error, sqlite3.OperationalError) and error.sqlite_errorcode & 255 == sqlite3.SQLITE_BUSY:
            raise DatabaseBusy from error
        raise


def execute_schema_statements(db, sql):
    """Execute DDL inside the caller's transaction without script-level commits."""
    if not db.in_transaction:
        raise RuntimeError('Schema statements require an active transaction.')
    statement = ''
    for line in sql.splitlines(keepends=True):
        statement += line
        if sqlite3.complete_statement(statement):
            db.execute(statement)
            statement = ''
    if statement.strip():
        raise RuntimeError('Incomplete schema statement')


def initialize_application_schema():
    # Private connection: foreign_keys=OFF must never escape into request g.db.
    bootstrap = sqlite3.connect(current_app.config['DATABASE'], autocommit=True, timeout=0.25)
    bootstrap.row_factory = sqlite3.Row
    bootstrap.execute('PRAGMA foreign_keys=ON')
    try:
        if current_app.config['CLASSROOM_MODE']:
            from .activities.classroom_migration import needs_rebuild
            if needs_rebuild(bootstrap):
                bootstrap.execute('PRAGMA foreign_keys=OFF')
        _initialize_application_schema(bootstrap)
    finally:
        if bootstrap.in_transaction:
            bootstrap.execute('ROLLBACK')
        try:
            bootstrap.execute('PRAGMA foreign_keys=ON')
            if bootstrap.execute('PRAGMA foreign_keys').fetchone()[0] != 1:
                raise RuntimeError('Could not restore bootstrap foreign key enforcement.')
        finally:
            bootstrap.close()


def _initialize_application_schema(bootstrap):
    """Core tables and Google database identity form one recoverable unit."""
    schemas = Path(__file__).parent / 'activities'
    with write_transaction(bootstrap) as db:
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if current_app.config['TEACHER_AUTH_MODE'] == 'google' and tables and 'auth_instance' not in tables:
            raise RuntimeError('007 Google login requires a new empty database; existing data was preserved.')
        if current_app.config['CLASSROOM_MODE'] and 'activities' in tables and 'classrooms' not in tables:
            raise RuntimeError('004 classroom mode requires a separate database; the selected database uses 002.')
        if not current_app.config['CLASSROOM_MODE'] and 'classrooms' in tables:
            raise RuntimeError('The selected database uses 004 classroom mode.')
        sql = (schemas / 'schema.sql').read_text(encoding='utf-8')
        if current_app.config['CLASSROOM_MODE']:
            from .activities.classroom_migration import upgrade
            classroom_sql = (schemas / 'classroom_schema.sql').read_text(encoding='utf-8')
            upgrade(db, classroom_sql, execute_schema_statements)
            sql += '\n' + classroom_sql
        execute_schema_statements(db, sql)
        if current_app.config['CLASSROOM_MODE']:
            from .activities.classroom_migration import validate
            validate(db)
        if current_app.config['TEACHER_AUTH_MODE'] == 'google':
            from .google_login.repository import initialize
            initialize(db)


def init_app(app):
    Path(app.config["DATABASE"]).resolve().parent.mkdir(parents=True, exist_ok=True)

    @app.teardown_appcontext
    def close(_error):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with app.app_context():
        initialize_application_schema()

    @app.cli.command("init-db")
    def init_db():
        from .notes.repository import init_schema
        initialize_application_schema()
        init_schema()
        if app.config["TEACHER_AUTH_MODE"] == "google" and app.config["CLASSROOM_MODE"]:
            from .workspace.repository import initialize as initialize_workspace
            initialize_workspace()
        click.echo("Database schema is ready; existing records were preserved.")
