from flask import Blueprint, current_app, jsonify, request, session

from ..auth import limit_attempts
from ..db import write_transaction
from ..http import ApiError, payload, string
from .membership import join, restore
from .state_routes import state_view

student = Blueprint("student", __name__)


@student.post("/activity-memberships")
def enroll():
    data = payload()
    code, group_name = string(data, "code", 32).upper(), string(data, "group_name", 80)
    limit_attempts("join")
    with write_transaction() as db:
        activity, group, proof, token = join(db, code, group_name)
        body = state_view(db, activity, group)
    session["student_grant"] = token
    response = jsonify(body)
    response.set_cookie("membership_proof", proof, httponly=True, samesite="Lax",
                        secure=current_app.config["SESSION_COOKIE_SECURE"],
                        max_age=current_app.config["RECOVERY_SECONDS"],
                        path=f"/activities/{activity['id']}/result-access")
    return response, 201


@student.post("/activities/<activity_id>/result-access")
def recover(activity_id):
    data = payload()
    if "group_id" in data or "group_name" in data:
        raise ApiError(400, "INVALID_REQUEST")
    limit_attempts("recover")
    with write_transaction() as db:
        token = restore(db, activity_id, request.cookies.get("membership_proof"))
    session["student_grant"] = token
    return "", 204
