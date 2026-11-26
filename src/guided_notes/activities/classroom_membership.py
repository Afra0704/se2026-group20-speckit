import secrets
import time

from flask import current_app, session

from ..auth import digest
from ..http import ApiError


def issue(db, membership_id, *, read_only=False):
    token = secrets.token_urlsafe(32)
    db.execute(
        "INSERT INTO classroom_grants VALUES (?, ?, ?, ?)",
        (digest(token), membership_id, int(time.time()) + current_app.config["AUTH_SECONDS"], read_only),
    )
    return token


def join(db, code, name):
    room = db.execute("SELECT * FROM classrooms WHERE code = ? AND state='OPEN'", (code,)).fetchone()
    if room is None:
        raise ApiError(403, "JOIN_DENIED")
    if room["state"] != "OPEN":
        raise ApiError(409, "CLASSROOM_CLOSED")
    target = (room["id"], name)
    db.execute(
        """INSERT INTO classroom_groups(classroom_id, name) VALUES (?, ?)
           ON CONFLICT(classroom_id, name) DO NOTHING""",
        target,
    )
    group = db.execute("SELECT * FROM classroom_groups WHERE classroom_id = ? AND name = ?", target).fetchone()
    proof = secrets.token_urlsafe(32)
    result = db.execute(
        """INSERT INTO classroom_memberships(classroom_id, group_id, proof, expires)
           VALUES (?, ?, ?, ?)""",
        (room["id"], group["id"], digest(proof), int(time.time()) + current_app.config["RECOVERY_SECONDS"]),
    )
    return room["id"], group["id"], proof, issue(db, result.lastrowid)


def identity_for(db, classroom_id, *, submitting=False):
    token = session.get("classroom_grant")
    if not token:
        raise ApiError(401, "AUTH_REQUIRED")
    row = db.execute(
        """SELECT g.*, s.read_only, c.state AS classroom_state, c.state_version FROM classroom_grants s
           JOIN classroom_memberships m ON m.id = s.membership_id
           JOIN classroom_groups g ON g.classroom_id = m.classroom_id AND g.id = m.group_id
           JOIN classrooms c ON c.id=m.classroom_id
           WHERE s.token = ? AND s.expires > ?""",
        (digest(token), int(time.time())),
    ).fetchone()
    if row is None:
        raise ApiError(401, "AUTH_REQUIRED")
    if row["classroom_id"] != classroom_id or (submitting and row["read_only"]):
        raise ApiError(403, "FORBIDDEN")
    return row


def group_for(db, classroom_id, *, submitting=False):
    row = identity_for(db, classroom_id, submitting=submitting)
    if row['classroom_state'] != 'OPEN':
        raise ApiError(409, 'CLASSROOM_CLOSED')
    return row


def recover(db, classroom_id, proof):
    if not proof:
        raise ApiError(403, "RECOVERY_DENIED")
    row = db.execute(
        """SELECT m.id, c.state FROM classroom_memberships m JOIN classrooms c ON c.id = m.classroom_id
           WHERE c.id = ? AND m.proof = ? AND m.expires > ?""",
        (classroom_id, digest(proof), int(time.time())),
    ).fetchone()
    if row is None:
        raise ApiError(403, "RECOVERY_DENIED")
    if row['state'] != 'OPEN':
        raise ApiError(409, 'CLASSROOM_CLOSED')
    return issue(db, row["id"])
