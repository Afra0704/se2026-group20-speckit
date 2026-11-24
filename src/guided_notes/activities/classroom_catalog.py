from importlib import import_module

from flask import current_app

from ..http import ApiError
from .demo_catalog import get_demo_catalog


def provider(name, config_name):
    supplied = current_app.config.get(config_name)
    if supplied is None:
        try:
            module = import_module("..notes.course_catalogs", __package__)
        except ModuleNotFoundError as error:
            if error.name not in {"guided_notes.notes", "guided_notes.notes.course_catalogs"}:
                raise
            raise ApiError(503, "CATALOG_UNAVAILABLE") from error
        supplied = getattr(module, name, None)
    if not callable(supplied):
        raise ApiError(503, "CATALOG_UNAVAILABLE")
    return supplied


def list_catalogs(teacher, course):
    if current_app.config["DEMO_CATALOG"]:
        return {
            "course_id": course["course_id"], "title": course["title"],
            "lectures": [{"import_id": "demo", "versions": [
                {"import_version": 2, "title": "示範講義 v2"},
                {"import_version": 1, "title": "示範講義 v1"},
            ]}],
        }
    return provider("list_course_catalogs", "LIST_COURSE_CATALOGS")(teacher, course["course_id"])


def get_catalog(teacher, course_id, import_id, version):
    if current_app.config["DEMO_CATALOG"]:
        return get_demo_catalog(teacher, import_id, version)
    return provider("get_course_catalog", "GET_COURSE_CATALOG")(teacher, course_id, import_id, version)
