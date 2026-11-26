import json

from flask import Blueprint

from ..db import connection
from .membership import activity_scope
from .display_service import read_display

state = Blueprint("state", __name__)


def state_view(db, activity, group):
    rows = db.execute("SELECT content FROM questions WHERE activity_id = ? ORDER BY position", (activity["id"],))
    core = [json.loads(row['content']) for row in rows]
    display = read_display(db, activity, core)
    questions = []
    for n, question in enumerate(core):
        items = [dict(item_id=item['item_id'], subitem_label=item['subitem_label'],
                      prompt_text=display['questions'][n]['items'][j]['prompt_text'] if display else None)
                 for j, item in enumerate(question['items'])]
        questions.append({**{k: question[k] for k in ('question_id', 'display_number', 'kind')}, 'items': items})
    body = dict(activity_id=activity["id"], phase=activity["phase"], phase_version=activity["phase_version"],
                role="teacher" if group is None else "student", questions=questions,
                display_contract_version=1, question_text_status='complete' if display else 'unavailable')
    if group is not None:
        body.update(group_id=group["id"], group_name=group["name"])
    return body


@state.get("/activities/<activity_id>/state")
def view(activity_id):
    db = connection()
    activity, group = activity_scope(db, activity_id)
    return state_view(db, activity, group)
