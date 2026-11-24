from contextlib import contextmanager
from pathlib import Path
import sqlite3
import time
import click

from flask import current_app, g


class DatabaseBusy(Exception):
    pass


def connection():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"], autocommit=True, timeout=0.25)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@contextmanager
def write_transaction():
    db = connection()
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


def init_app(app):
    Path(app.config["DATABASE"]).resolve().parent.mkdir(parents=True, exist_ok=True)

    @app.teardown_appcontext
    def close(_error):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with app.app_context():
        connection().executescript(
            (Path(__file__).parent / "activities" / "schema.sql").read_text(encoding="utf-8")
        )

    @app.cli.command("init-db")
    def init_db():
        from .notes.repository import init_schema
        connection().executescript((Path(__file__).parent / "activities" / "schema.sql").read_text(encoding="utf-8"))
        init_schema()
        click.echo("Database schema is ready; existing records were preserved.")
