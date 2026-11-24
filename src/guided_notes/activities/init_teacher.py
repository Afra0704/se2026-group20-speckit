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
    if not username or len(username) > 128 or not 4 <= len(password) <= 1024 or not password.strip():
        raise click.ClickException("Use a valid username and a password of at least four characters.")
    with write_transaction() as db:
        cursor = db.execute(
            "INSERT INTO teachers(username, password_hash) VALUES (?, ?) ON CONFLICT(username) DO NOTHING",
            (username, generate_password_hash(password)),
        )
        if not cursor.rowcount:
            raise click.ClickException("Teacher already exists.")
    click.echo("Teacher created.")
