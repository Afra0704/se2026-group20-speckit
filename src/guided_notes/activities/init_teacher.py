import click
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash

from ..db import write_transaction


@click.command("init-teacher")
@click.argument("username")
@click.password_option()
@with_appcontext
def init_teacher(username, password):
    username = username.strip()
    if not username or len(username) > 128 or len(password) < 8:
        raise click.ClickException("Use a valid username and a password of at least eight characters.")
    with write_transaction() as db:
        cursor = db.execute(
            "INSERT INTO teachers(username, password_hash) VALUES (?, ?) ON CONFLICT(username) DO NOTHING",
            (username, generate_password_hash(password)),
        )
        if not cursor.rowcount:
            raise click.ClickException("Teacher already exists.")
    click.echo(f"Teacher created. ID: {cursor.lastrowid}")
