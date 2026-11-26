from importlib import import_module

from flask import current_app

from ..http import ApiError
from ..notes.display_models import validate_display_content


def provider(name, config_name, error_code="CATALOG_UNAVAILABLE"):
    supplied = current_app.config.get(config_name)
    if supplied is None:
        try:
            module = import_module("..notes.course_catalogs", __package__)
        except ModuleNotFoundError as error:
            if error.name not in {"guided_notes.notes", "guided_notes.notes.course_catalogs"}:
                raise
            raise ApiError(503, error_code) from error
        supplied = getattr(module, name, None)
    if not callable(supplied):
        raise ApiError(503, error_code)
    return supplied


def list_catalogs(teacher, course):
    return provider("list_course_catalogs", "LIST_COURSE_CATALOGS")(teacher, course["course_id"])


def get_catalog(teacher, course_id, import_id, version):
    return provider("get_course_catalog", "GET_COURSE_CATALOG")(teacher, course_id, import_id, version)


def get_display_content(teacher, course_id, import_id, version, questions):
    value = provider('get_course_display_content', 'GET_COURSE_DISPLAY_CONTENT',
                     'DISPLAY_CONTENT_UNAVAILABLE')(teacher, course_id, import_id, version)
    return validate_display_content(value, dict(import_id=import_id, import_version=version, questions=questions))
