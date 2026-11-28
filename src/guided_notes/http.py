import sqlite3
from flask import jsonify, request

from .db import DatabaseBusy


class ApiError(Exception):
    def __init__(self, status, code, *, retry_after=None, invalid_item_ids=None):
        self.status = status
        self.code = code
        self.retry_after = retry_after
        self.invalid_item_ids = invalid_item_ids


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
        body = {"error": error.code}
        if error.invalid_item_ids is not None:
            body["invalid_item_ids"] = error.invalid_item_ids
        headers = {}
        if error.retry_after is not None:
            body["retry_after"] = error.retry_after
            headers["Retry-After"] = str(error.retry_after)
        return jsonify(body), error.status, headers

    @app.errorhandler(sqlite3.IntegrityError)
    def visibility_error(error):
        if str(error) != "lecture_removed":
            raise error
        return jsonify(error={"code":"LECTURE_REMOVED","message":"講義已移除，請選擇其他講義。","retryable":False,"context":{}}),410

    @app.errorhandler(DatabaseBusy)
    def busy(_error):
        return jsonify(error="TEMPORARILY_UNAVAILABLE"), 503

    @app.after_request
    def privacy(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers['Referrer-Policy'] = ('strict-origin-when-cross-origin' if request.endpoint == 'workspace.import_page' and response.mimetype == 'text/html' and not request.query_string else 'no-referrer')
        return response
