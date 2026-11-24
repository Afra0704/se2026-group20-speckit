"""Local-only acceptance for the built-in demonstration catalog."""

import json


def accept_demo_submission(db, context, answers):
    db.execute(
        """CREATE TABLE IF NOT EXISTS demo_submissions (
               id INTEGER PRIMARY KEY,
               activity_id TEXT NOT NULL,
               group_id INTEGER NOT NULL,
               question_id TEXT NOT NULL,
               answers TEXT NOT NULL
           )"""
    )
    db.execute(
        "INSERT INTO demo_submissions(activity_id, group_id, question_id, answers) VALUES (?, ?, ?, ?)",
        (context["activity_id"], context["group_id"], context["question"]["question_id"], json.dumps(answers)),
    )
