from flask import current_app

from ..activities.membership import activity_scope
from ..auth import require_teacher
from ..db import connection
from ..http import ApiError


def results_for(activity_id):
    db = connection()
    activity, group = activity_scope(db, activity_id)
    if activity["phase"] != "CLOSED":
        progress = current_app.config.get("GET_PROGRESS")
        rows = progress(db, activity_id) if group is None and activity["phase"] == "LIVE" and progress else []
        return {"status": "active", "results": [
            {key: row[key] for key in ("question_id", "group_name", "submitted") if key in row} for row in rows
        ]}
    published = snapshot(db, activity_id)
    if published is None:
        return {"status": "pending"}
    return {"status": "settled", "results": [project(row, group) for row in published["results"]]}


def snapshot(db, activity_id):
    read = current_app.config.get("GET_SETTLED_RESULTS")
    return read(db, activity_id) if read is not None else None


def project(row, group):
    result = {"question_id": row["question_id"], "winner_name": row["winner_name"],
              "winner_answer": row["winner_answer"]}
    entries = row["groups"]
    if group is None:
        result["groups"] = [
            {key: entry[key] for key in ("group_name", "answer", "rank")} for entry in entries
        ]
    else:
        own = next((entry for entry in entries if entry["group_id"] == group["id"]), None)
        result["own"] = {"answer": own["answer"], "rank": own["rank"]} if own else None
    return result


def get_ended_snapshot(teacher_context, activity_id):
    db = connection()
    activity = db.execute("SELECT * FROM activities WHERE id = ?", (activity_id,)).fetchone()
    if (teacher_context != require_teacher(db) or activity is None
            or activity["teacher_id"] != teacher_context.teacher_id):
        raise ApiError(403, "FORBIDDEN")
    if activity["phase"] != "CLOSED":
        raise ApiError(409, "ACTIVITY_NOT_ENDED")
    data = snapshot(db, activity_id)
    if data is None:
        raise ApiError(409, "RESULT_NOT_READY")
    return data["snapshot"]
