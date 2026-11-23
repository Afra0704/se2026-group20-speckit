import secrets
import time

from flask import current_app

from ..auth import digest, grant, issue_grant, require_teacher
from ..http import ApiError


def join(db, code, group_name):
    activity = db.execute("SELECT * FROM activities WHERE code = ?", (code,)).fetchone()
    if activity is None:
        raise ApiError(403, "JOIN_DENIED")
    if activity["phase"] == "CLOSED":
        raise ApiError(409, "INVALID_PHASE")
    activity_id = activity["id"]
    db.execute(
        "INSERT INTO activity_groups(activity_id, name) VALUES (?, ?) ON CONFLICT(activity_id, name) DO NOTHING",
        (activity_id, group_name),
    )
    group = db.execute(
        "SELECT * FROM activity_groups WHERE activity_id = ? AND name = ?", (activity_id, group_name)
    ).fetchone()
    proof = secrets.token_urlsafe(32)
    cursor = db.execute(
        "INSERT INTO memberships(activity_id, group_id, proof, expires) VALUES (?, ?, ?, ?)",
        (activity_id, group["id"], digest(proof), int(time.time()) + current_app.config["RECOVERY_SECONDS"]),
    )
    return activity, group, proof, issue_grant(db, membership_id=cursor.lastrowid)


def restore(db, activity_id, proof):
    if not proof:
        raise ApiError(403, "RECOVERY_DENIED")
    row = db.execute(
        """SELECT m.id FROM memberships m JOIN activities a ON a.id = m.activity_id
           WHERE m.activity_id = ? AND m.proof = ? AND m.expires > ?
           AND m.revoked = 0 AND a.phase = 'CLOSED'""",
        (activity_id, digest(proof), int(time.time())),
    ).fetchone()
    if row is None:
        raise ApiError(403, "RECOVERY_DENIED")
    return issue_grant(db, membership_id=row["id"], read_only=True)


def activity_scope(db, activity_id, *, for_submission=False):
    identity = grant(db, "student" if for_submission else None)
    activity = db.execute("SELECT * FROM activities WHERE id = ?", (activity_id,)).fetchone()
    if activity is None:
        raise ApiError(403, "FORBIDDEN")
    if identity["teacher_id"] is not None:
        if for_submission or activity["teacher_id"] != require_teacher(db).teacher_id:
            raise ApiError(403, "FORBIDDEN")
        return activity, None
    group = db.execute(
        """SELECT g.* FROM memberships m JOIN activity_groups g
           ON m.activity_id = g.activity_id AND m.group_id = g.id
           WHERE m.id = ? AND m.activity_id = ? AND m.revoked = 0""",
        (identity["membership_id"], activity_id),
    ).fetchone()
    if group is None or (for_submission and identity["read_only"]):
        raise ApiError(403, "FORBIDDEN")
    return activity, group
