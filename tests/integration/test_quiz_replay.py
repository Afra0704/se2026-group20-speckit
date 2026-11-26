import json
from uuid import uuid4

from conftest import post
from guided_notes.db import connection
from quiz_support import submit


def test_replay_cannot_restore_replaced_answer(app, teacher, activity, joined):
    aid = activity["activity_id"]
    a, b = joined
    first = str(uuid4())
    assert post(teacher, f"/activities/{aid}/start").status_code == 200
    assert submit(a, aid, first).status_code == 201
    assert submit(b, aid).status_code == 201
    assert submit(a, aid, first, "不同答案").json == {"error": "SUBMISSION_REPLAY_CONFLICT"}
    assert submit(a, aid, answer=" 新答案 ").status_code == 201
    assert submit(a, aid, first).json == {"status": "accepted"}
    with app.app_context():
        rows = connection().execute(
            """SELECT s.answers FROM quiz_effective e JOIN quiz_submissions s USING(accept_seq)
               WHERE e.activity_id=? ORDER BY s.accept_seq""", (aid,)
        ).fetchall()
        assert len(rows) == 2 and json.loads(rows[1]["answers"]) == {"i1-1": " 新答案 "}
