import json
from pathlib import Path
from uuid import uuid4

from catalog_support import display, seed_published
from conftest import post
from guided_notes.db import connection


def published_quiz(app, teacher, room=None):
    """Use a valid, pinned 001 DTO for settlement tests."""
    sample = Path(__file__).resolve().parents[1] / "specs/001-guided-notes/contracts/examples.json"
    data = json.loads(sample.read_text(encoding="utf-8"))["catalog"]
    root = "/activities"
    course_id = None
    if room:
        course, classroom = room
        course_id = course["course_id"]
        root = f"/teacher/classrooms/{classroom['classroom_id']}/activities"
        app.config.update(GET_COURSE_CATALOG=lambda *args: data,
                          GET_COURSE_DISPLAY_CONTENT=lambda *args: display(data))
    else:
        app.config.update(GET_CATALOG=lambda *args: data, GET_DISPLAY_CONTENT=lambda *args: display(data))
    with app.app_context():
        seed_published(1, data, course_id)
    response = post(teacher, root, import_id=data["import_id"], import_version=data["import_version"], title="Quiz")
    assert response.status_code == 201, response.json
    return response.json, data["questions"]


def submit_question(client, activity_id, question, *, key=None, answer=" 原答案\n"):
    return submit(client, activity_id, key, question_id=question["question_id"], items=[
        {"item_id": item["item_id"], "answer_text": answer} for item in question["items"]
    ])


def submit(client, activity_id, key=None, answer=" 原答案\n", **body):
    csrf = client.get("/csrf").json["csrf"]
    return client.post(f"/activities/{activity_id}/submissions",
                       json={"question_id": "q1", "items": [{"item_id": "i1-1", "answer_text": answer}], **body},
                       headers={"X-CSRF-Token": csrf, "Idempotency-Key": key or str(uuid4())})
