from contextlib import contextmanager
import sqlite3

from ..db import write_transaction
from ..http import ApiError
from .course_service import get_owned_course


def require_no_unfinished(db, classroom_id, *, excluding=None):
    row = db.execute(
        """SELECT 1 FROM classroom_activities c JOIN activities a ON a.id=c.activity_id
           WHERE c.classroom_id=? AND a.phase IN ('PREPARING','LIVE')
           AND (? IS NULL OR a.id<>?) LIMIT 1""",
        (classroom_id, excluding, excluding),
    ).fetchone()
    if row:
        raise ApiError(409, "ACTIVITY_IN_PROGRESS")


@contextmanager
def activity_transaction():
    try:
        with write_transaction() as db:
            yield db
    except sqlite3.IntegrityError as error:
        if str(error) in ('classroom_permanently_closed', 'classroom_identity_immutable'):
            raise ApiError(409, 'CLASSROOM_CLOSED' if str(error) == 'classroom_permanently_closed' else 'INVALID_REQUEST') from error
        if str(error) == "lecture_removed":
            raise ApiError(410, "LECTURE_REMOVED") from None
        if str(error) == "classroom_unfinished":
            raise ApiError(409, "ACTIVITY_IN_PROGRESS") from error
        if str(error) == "classroom_closed_activity":
            raise ApiError(409, "INVALID_PHASE") from error
        raise


def classroom(db, classroom_id):
    row = db.execute("SELECT * FROM classrooms WHERE id = ?", (classroom_id,)).fetchone()
    if row is None:
        raise ApiError(404, "CLASSROOM_NOT_FOUND")
    return row


def owned_classroom(db, teacher, classroom_id):
    row = classroom(db, classroom_id)
    get_owned_course(teacher, row["course_id"], db=db)
    return row


def requested_activity(db, activity_id):
    row = db.execute(
        """SELECT a.*, ca.classroom_id, ca.title FROM activities a
           JOIN classroom_activities ca ON ca.activity_id = a.id WHERE a.id = ?""",
        (activity_id,),
    ).fetchone()
    if row is None:
        raise ApiError(404, "ACTIVITY_NOT_FOUND")
    return row
