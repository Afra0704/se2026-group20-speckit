import json

from flask import current_app

from ..http import ApiError


def operation_scope(context):
    return (context["activity_id"], context["question"]["question_id"], context["group_id"])


def replay(db, context, answers):
    row = db.execute(
        """SELECT answers FROM quiz_submissions
           WHERE activity_id=? AND question_id=? AND group_id=? AND operation_id=?""",
        (*operation_scope(context), context["operation_id"]),
    ).fetchone()
    if row is None:
        return False
    if json.loads(row["answers"]) != answers:
        raise ApiError(409, "SUBMISSION_REPLAY_CONFLICT")
    return True


def accept(db, context, answers):
    scope = operation_scope(context)
    cursor = db.execute(
        """INSERT INTO quiz_submissions(activity_id,question_id,group_id,operation_id,answers)
           VALUES (?,?,?,?,?)""",
        (*scope, context["operation_id"], json.dumps(answers, ensure_ascii=True, sort_keys=True)),
    )
    db.execute(
        """INSERT INTO quiz_effective(activity_id,question_id,group_id,accept_seq)
           VALUES (?,?,?,?) ON CONFLICT(activity_id,question_id,group_id)
           DO UPDATE SET accept_seq=excluded.accept_seq""", (*scope, cursor.lastrowid),
    )


def activity_groups(db, activity_id):
    if current_app.config["CLASSROOM_MODE"]:
        return db.execute(
            """SELECT g.id, g.name FROM classroom_groups g JOIN classroom_activities a
               ON a.classroom_id=g.classroom_id WHERE a.activity_id=? ORDER BY g.id""", (activity_id,),
        ).fetchall()
    return db.execute("SELECT id,name FROM activity_groups WHERE activity_id=? ORDER BY id", (activity_id,)).fetchall()


def progress(db, activity_id):
    submitted = {(r["question_id"], r["group_id"]) for r in db.execute(
        "SELECT question_id,group_id FROM quiz_effective WHERE activity_id=?", (activity_id,),
    )}
    questions = db.execute(
        "SELECT question_id FROM questions WHERE activity_id=? ORDER BY position", (activity_id,),
    ).fetchall()
    groups = activity_groups(db, activity_id)
    return [{"question_id": q["question_id"], "group_name": g["name"],
             "submitted": (q["question_id"], g["id"]) in submitted} for q in questions for g in groups]
