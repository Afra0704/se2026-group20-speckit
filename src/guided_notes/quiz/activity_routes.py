from flask import Blueprint, request

from ..http import payload, string
from .results_gateway import results_for
from .submission_gateway import submit

quiz = Blueprint("quiz", __name__)


@quiz.post("/activities/<activity_id>/submissions")
def submission(activity_id):
    data = payload()
    return submit(activity_id, string(data, "question_id"), data.get("items"),
                  request.headers.get("Idempotency-Key")), 201


@quiz.get("/activities/<activity_id>/results")
def results(activity_id):
    return results_for(activity_id)
