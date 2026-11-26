"""Visibility applies to new references; historical owner lookups stay unchanged."""
from ..auth import require_teacher
from ..db import connection, write_transaction
from ..http import ApiError
from . import repository as repo
from .course_catalogs import get_owned_course, import_course_id


def require_active_import(db,teacher_id,import_id,expected_course_id=None):
    repo.owned_import(db,teacher_id,import_id)
    if expected_course_id is not None and import_course_id(db,import_id)!=expected_course_id:raise ApiError(404,'CATALOG_NOT_FOUND')
    if db.execute('SELECT 1 FROM notes_lecture_removals WHERE import_id=?',(import_id,)).fetchone():raise ApiError(410,'LECTURE_REMOVED')


def require_available_for_activity(teacher,course_id,import_id,version,db):
    if require_teacher(db)!=teacher:raise ApiError(403,'FORBIDDEN')
    require_active_import(db,teacher.teacher_id,import_id,course_id)
    repo.catalog_row(db,teacher.teacher_id,import_id,version)


def remove(teacher,course_id,import_id):
    get_owned_course(teacher,course_id)
    with write_transaction() as db:
        if require_teacher(db)!=teacher:raise ApiError(403,'FORBIDDEN')
        repo.owned_import(db,teacher.teacher_id,import_id)
        if import_course_id(db,import_id)!=course_id:raise ApiError(404,'CATALOG_NOT_FOUND')
        db.execute('INSERT INTO notes_lecture_removals VALUES(?,?,?) ON CONFLICT DO NOTHING',(import_id,teacher.teacher_id,repo.now()))
    return {'import_id':import_id,'removed':True}
