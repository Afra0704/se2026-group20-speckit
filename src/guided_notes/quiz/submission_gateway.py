from flask import current_app

from ..activities.submission_context import submission_context
from ..db import write_transaction
from ..http import ApiError
from .demo_submissions import accept_demo_submission


def submit(activity_id, question_id, items):
    with write_transaction() as db:
        context = submission_context(db, activity_id, question_id)
        expected = {item["item_id"] for item in context["question"]["items"]}
        answers = {}
        if not isinstance(items, list):
            raise ApiError(400, "INVALID_ITEMS")
        for item in items:
            if not isinstance(item, dict):
                raise ApiError(400, "INVALID_ITEMS")
            item_id = item.get("item_id")
            answer = item.get("answer_text")
            if (not isinstance(item_id, str) or item_id not in expected
                    or item_id in answers or not isinstance(answer, str) or not answer.strip()):
                raise ApiError(400, "INVALID_ITEMS")
            answers[item_id] = answer
        if answers.keys() != expected:
            raise ApiError(400, "INVALID_ITEMS")
        accept = current_app.config.get("ACCEPT_SUBMISSION")
        if accept is None and current_app.config["DEMO_CATALOG"] and context["import_id"] == "demo":
            accept = accept_demo_submission
        if accept is None:
            raise ApiError(503, "QUIZ_UNAVAILABLE")
        accept(db, context, answers)
    return {"status": "accepted"}
