import json

from ..http import ApiError
from .membership import activity_scope


def submission_context(db, activity_id, question_id):
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
