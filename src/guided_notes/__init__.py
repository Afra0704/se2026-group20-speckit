from flask import Flask, jsonify, render_template, request

from . import db, http
from .auth import check_csrf, csrf_token
from .config import defaults


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(defaults(app.instance_path))
    if test_config:
        app.config.update(test_config)
    if not app.secret_key:
        raise RuntimeError("Set GUIDED_NOTES_SECRET_KEY before starting the application.")
    db.init_app(app)
    http.init_app(app)

    from .activities.init_teacher import init_teacher
    from .activities.state_routes import state
    from .activities.student_routes import student
    from .activities.teacher_routes import teacher
    from .quiz.activity_routes import quiz

    app.cli.add_command(init_teacher)
    for blueprint in (teacher, student, state, quiz):
        app.register_blueprint(blueprint)
    notes = app.config.get("NOTES_BLUEPRINT")
    from .notes.repository import init_schema
    from .notes.cli import register_flask_cli
    from .notes.routes import a1_range, taipei_time
    if notes is None:
        from .notes.routes import notes
    with app.app_context():
        init_schema()
    app.register_blueprint(notes)
    register_flask_cli(app)
    app.jinja_env.filters["notes_a1"] = a1_range
    app.jinja_env.filters["notes_time"] = taipei_time
    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.get("/")
    def index():
        return render_template("activities/student.html", csrf=csrf_token())

    @app.get("/csrf")
    def csrf():
        return jsonify(csrf=csrf_token())

    @app.before_request
    def protect_writes():
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            check_csrf()

    return app
