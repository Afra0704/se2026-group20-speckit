from uuid import UUID

from flask import current_app

from ..activities.submission_context import submission_context
from ..db import write_transaction
from ..http import ApiError
from .repository import accept as formal_accept, replay


def submit(activity_id, question_id, items, operation_id=None):
    with write_transaction() as db:
        accept = current_app.config.get("ACCEPT_SUBMISSION")
        formal = accept is formal_accept
        context = submission_context(db, activity_id, question_id, for_replay=formal and operation_id is not None)
        answers = validated_answers(context["question"], items)
        if not callable(accept):
            raise ApiError(503, "QUIZ_UNAVAILABLE")
        if formal:
            key = validated_operation_id(operation_id)
            if not replay(db, dict(context, operation_id=key), answers):
                context = submission_context(db, activity_id, question_id)
                accept(db, dict(context, operation_id=key), answers)
        else:
            accept(db, context, answers)
    return {"status": "accepted"}


def validated_operation_id(value):
    if not isinstance(value, str) or len(value) != 36:
        raise ApiError(400, "INVALID_REQUEST")
    try:
        normalized = str(UUID(value))
    except ValueError as error:
        raise ApiError(400, "INVALID_REQUEST") from error
    if normalized != value.lower():
        raise ApiError(400, "INVALID_REQUEST")
    return normalized


def validated_answers(question, items):
    expected = {item["item_id"] for item in question["items"]}
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
    return answers
