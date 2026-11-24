from ..http import ApiError
from .course_service import get_owned_course


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
