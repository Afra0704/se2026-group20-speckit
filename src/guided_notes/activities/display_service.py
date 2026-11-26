"""Immutable activity text snapshots, saved inside the caller's transaction."""
from importlib import import_module
import json

from flask import current_app

from ..http import ApiError
from ..notes.display_models import validate_display_content


def get_display_content(teacher, import_id, version, questions):
    provider = current_app.config.get('GET_DISPLAY_CONTENT')
    if provider is None:
        try:
            module = import_module('..notes.display_service', __package__)
        except ModuleNotFoundError as error:
            if error.name not in {'guided_notes.notes', 'guided_notes.notes.display_service'}:
                raise
            raise ApiError(503, 'DISPLAY_CONTENT_UNAVAILABLE') from None
        provider = getattr(module, 'get_display_content', None)
    if not callable(provider):
        raise ApiError(503, 'DISPLAY_CONTENT_UNAVAILABLE')
    return validate_display_content(provider(teacher, import_id, version),
        dict(import_id=import_id, import_version=version, questions=questions))


def save_display(db, activity_id, display):
    db.execute('INSERT INTO activity_displays(activity_id,dto) VALUES(?,?)',
               (activity_id, json.dumps(display, ensure_ascii=False, allow_nan=False)))


def read_display(db, activity, questions):
    row = db.execute('SELECT dto FROM activity_displays WHERE activity_id=?', (activity['id'],)).fetchone()
    if row is None:
        return None
    try:
        value = json.loads(row['dto'])
    except (TypeError, ValueError):
        raise ApiError(409, 'DISPLAY_CONTENT_MISMATCH') from None
    return validate_display_content(value, dict(import_id=activity['import_id'],
        import_version=activity['import_version'], questions=questions))
