from flask import jsonify, request

from .db import DatabaseBusy


class ApiError(Exception):
    def __init__(self, status, code):
        self.status = status
        self.code = code


def payload():
    data = request.get_json(silent=True) if request.is_json else request.form
    if not hasattr(data, "get"):
        raise ApiError(400, "INVALID_REQUEST")
    return data


def string(data, name, maximum=256, *, strip=True):
    value = data.get(name)
    if not isinstance(value, str) or len(value) > maximum or not value.strip():
        raise ApiError(400, "INVALID_REQUEST")
    return value.strip() if strip else value


def init_app(app):
    @app.errorhandler(ApiError)
    def api_error(error):
        return jsonify(error=error.code), error.status

    @app.errorhandler(DatabaseBusy)
    def busy(_error):
        return jsonify(error="TEMPORARILY_UNAVAILABLE"), 503

    @app.after_request
    def privacy(response):
        response.headers["Cache-Control"] = "no-store"
        return response
