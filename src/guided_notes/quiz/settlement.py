import json
from collections import defaultdict
from uuid import uuid4

from flask import current_app

from ..db import connection, write_transaction
from ..notes.models import validate_snapshot
from ..notes.repository import catalog_row
from .repository import activity_groups


def queue(db, activity_id):
    db.execute("INSERT INTO quiz_settlements(activity_id) VALUES (?) ON CONFLICT DO NOTHING", (activity_id,))


def status(db, activity_id):
    row = db.execute("SELECT result_version FROM quiz_settlements WHERE activity_id=?", (activity_id,)).fetchone()
    if row is None:
        return "unavailable"
    return "settled" if row["result_version"] is not None else "pending"


def settled(db, activity_id):
    row = db.execute("SELECT snapshot, results FROM quiz_settlements WHERE activity_id=? AND result_version IS NOT NULL",
                     (activity_id,)).fetchone()
    if row is None:
        return None
    return {"snapshot": json.loads(row["snapshot"]), "results": json.loads(row["results"])}


def publish(db, activity_id):
    activity = db.execute("SELECT * FROM activities WHERE id=? AND phase='CLOSED'", (activity_id,)).fetchone()
    if activity is None or status(db, activity_id) != "pending":
        return
    catalog = json.loads(catalog_row(db, activity["teacher_id"], activity["import_id"],
                                     activity["import_version"])["dto"])
    groups = {row["id"]: row["name"] for row in activity_groups(db, activity_id)}
    submissions = defaultdict(list)
    for row in db.execute(
        """SELECT s.question_id,s.group_id,s.answers
           FROM quiz_effective e JOIN quiz_submissions s USING(accept_seq)
           WHERE e.activity_id=? ORDER BY s.accept_seq""", (activity_id,),
    ):
        submissions[row["question_id"]].append(row)

    units, results = [], []
    for record in db.execute("SELECT content FROM questions WHERE activity_id=? ORDER BY position", (activity_id,)):
        question = json.loads(record["content"])
        result, unit = question_result(question, submissions[question["question_id"]], groups)
        results.append(result)
        units.append(unit)
    version = uuid4().hex
    snapshot = validate_snapshot({
        "contract_version": 1, "activity_id": activity_id, "import_id": activity["import_id"],
        "import_version": activity["import_version"], "result_version": version, "ended": True, "units": units,
    }, catalog, activity_id=activity_id)
    db.execute("UPDATE quiz_settlements SET result_version=?,snapshot=?,results=? WHERE activity_id=?",
               (version, json.dumps(snapshot), json.dumps(results), activity_id))


def question_result(question, submissions, groups):
    question_id = question["question_id"]
    items = question["items"]
    entries = []
    for rank, row in enumerate(submissions, 1):
        answers = json.loads(row["answers"])
        entries.append({"group_id": row["group_id"], "group_name": groups[row["group_id"]], "rank": rank,
                        "answer": answers[items[0]["item_id"]] if len(items) == 1 else answers,
                        "items": [{"item_id": item["item_id"], "subitem_label": item["subitem_label"],
                                   "answer_text": answers[item["item_id"]]} for item in items]})
    winner = entries[0] if entries else None
    blanks = {item["item_id"]: item["blank_id"] for item in items}
    result = {"question_id": question_id, "display_number": question["display_number"], "no_winner": winner is None,
              "winner_name": winner["group_name"] if winner else None,
              "winner_answer": winner["answer"] if winner else None,
              "winner_items": winner["items"] if winner else [], "groups": entries}
    unit = {"question_id": question_id, "winner_group_id": str(winner["group_id"]) if winner else None,
            "no_winner": winner is None, "answers": [
                {"item_id": item["item_id"], "blank_id": blanks[item["item_id"]], "answer_text": item["answer_text"]}
                for item in result["winner_items"]]}
    return result, unit


def try_pending(activity_id):
    if current_app.config.get("GET_SETTLED_RESULTS") is not settled:
        return
    try:
        if status(connection(), activity_id) == "pending":
            with write_transaction() as db:
                publish(db, activity_id)
    except Exception as error:
        # CLOSED has already committed. A retry can finish this independent job.
        current_app.logger.warning("Quiz settlement deferred for %s (%s)", activity_id, type(error).__name__)


def recover_pending(limit=16):
    if current_app.config.get("GET_SETTLED_RESULTS") is not settled:
        return
    rows = connection().execute(
        "SELECT activity_id FROM quiz_settlements WHERE result_version IS NULL ORDER BY rowid LIMIT ?", (limit,),
    ).fetchall()
    for row in rows:
        try_pending(row["activity_id"])
