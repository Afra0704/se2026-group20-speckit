import json

from flask import current_app

from ..http import ApiError
from .membership import activity_scope
from .classroom_access import classroom, requested_activity
from .classroom_membership import group_for


def submission_context(db, activity_id, question_id):
    if current_app.config["CLASSROOM_MODE"]:
        activity = requested_activity(db, activity_id)
        group = group_for(db, activity["classroom_id"], submitting=True)
        room = classroom(db, activity["classroom_id"])
        if room["state"] != "OPEN" or room["current_activity_id"] != activity_id:
            raise ApiError(409, "INVALID_PHASE")
    else:
        activity, group = activity_scope(db, activity_id, for_submission=True)
    if activity["phase"] != "LIVE":
        raise ApiError(409, "INVALID_PHASE")
    question = db.execute(
        "SELECT content FROM questions WHERE activity_id = ? AND question_id = ?",
        (activity_id, question_id),
    ).fetchone()
    if question is None:
        raise ApiError(400, "INVALID_QUESTION")
    return dict(activity_id=activity_id, group_id=group["id"], question=json.loads(question["content"]),
                import_id=activity["import_id"], import_version=activity["import_version"])
