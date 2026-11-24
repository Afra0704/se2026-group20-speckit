import json

from flask import Blueprint

from ..db import connection
from .membership import activity_scope

state = Blueprint("state", __name__)


def state_view(db, activity, group):
    rows = db.execute("SELECT content FROM questions WHERE activity_id = ? ORDER BY position", (activity["id"],))
    questions = []
    for row in rows:
        question = json.loads(row["content"])
        question["items"] = [
            dict(item_id=item["item_id"], subitem_label=item["subitem_label"]) for item in question["items"]
        ]
        questions.append(question)
    body = dict(activity_id=activity["id"], phase=activity["phase"], phase_version=activity["phase_version"],
                role="teacher" if group is None else "student", questions=questions)
    if group is not None:
        body.update(group_id=group["id"], group_name=group["name"])
    return body


@state.get("/activities/<activity_id>/state")
def view(activity_id):
    db = connection()
    activity, group = activity_scope(db, activity_id)
    return state_view(db, activity, group)
