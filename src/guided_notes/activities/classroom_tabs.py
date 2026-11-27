"""Browser-bound classroom tab credentials and atomic group selection."""
import hmac
import json
import secrets
import time

from flask import current_app, request

from ..auth import digest
from ..http import ApiError
from . import classroom_presence as presence

COOKIE = 'classroom_browser'
TOKEN_SECONDS = 900


def set_browser_cookie(response):
    if not request.cookies.get(COOKIE):
        response.set_cookie(COOKIE, secrets.token_urlsafe(32), httponly=True,
                            secure=current_app.config['SESSION_COOKIE_SECURE'],
                            samesite='Lax',
                            max_age=current_app.config['RECOVERY_SECONDS'])
    return response


def browser_key():
    value = request.cookies.get(COOKIE)
    return digest(value) if value else None


def material(kind, *parts):
    key = current_app.secret_key
    if isinstance(key, str):
        key = key.encode()
    return hmac.digest(key, json.dumps((kind, *parts)).encode(), 'sha256').hex()


def prior_operation(db, scope, fingerprint):
    row = db.execute(
        """SELECT * FROM classroom_tab_operations
           WHERE classroom_id=? AND browser_key=? AND action=? AND request_id=?""", scope
    ).fetchone()
    if row is not None and row['request_hash'] != fingerprint:
        raise ApiError(409, 'CLASSROOM_TAB_REQUEST_CONFLICT')
    return row


def grant_by_page(db, room, browser, page):
    return db.execute(
        GRANT_QUERY + ' WHERE t.classroom_id=? AND t.browser_key=? AND t.page_id=?',
        (room, browser, page),
    ).fetchone()


GRANT_QUERY = """
    SELECT g.*, t.browser_key, t.page_id, t.membership_id, t.token_expires_at,
           t.resume_expires_at, t.revoked_at, t.generation, b.generation AS current_generation,
           b.group_id AS current_group, c.state AS classroom_state, c.state_version, 0 AS read_only
    FROM classroom_tab_grants t
    JOIN classroom_memberships m ON m.id=t.membership_id AND m.classroom_id=t.classroom_id
    JOIN classroom_groups g ON g.classroom_id=m.classroom_id AND g.id=m.group_id
    JOIN classrooms c ON c.id=t.classroom_id
    JOIN classroom_browser_groups b ON b.classroom_id=t.classroom_id AND b.browser_key=t.browser_key
"""


def require_current(grant):
    if (grant is None or grant['revoked_at'] is not None
            or grant['resume_expires_at'] <= int(time.time())
            or grant['generation'] != grant['current_generation']
            or grant['id'] != grant['current_group']):
        raise ApiError(401, 'CLASSROOM_REJOIN_REQUIRED')
    return grant


def enroll(db, code, name, page, request_id):
    from .classroom_membership import create_membership

    browser = browser_key()
    if browser is None:
        raise ApiError(401, 'CLASSROOM_TAB_REQUIRED')
    room = db.execute("SELECT id FROM classrooms WHERE code=? AND state='OPEN'", (code,)).fetchone()
    if room is None:
        raise ApiError(403, 'JOIN_DENIED')
    rid = room['id']
    scope = (rid, browser, 'join', request_id)
    fingerprint = material('join-request', code, name, page)
    resume = material('resume', *scope, fingerprint)
    prior = prior_operation(db, scope, fingerprint)
    if prior is not None:
        grant = require_current(grant_by_page(db, rid, browser, page))
        return dict(classroom_id=rid, group_id=grant['id'], resume_id=resume)

    active = db.execute(
        """SELECT g.name, b.generation,
                  EXISTS(SELECT 1 FROM classroom_presence p
                         WHERE p.classroom_id=b.classroom_id AND p.browser_key=b.browser_key
                           AND p.expires_at>?) AS online
           FROM classroom_browser_groups b
           JOIN classroom_groups g ON g.classroom_id=b.classroom_id AND g.id=b.group_id
           WHERE b.classroom_id=? AND b.browser_key=?""", (presence.now(), rid, browser)
    ).fetchone()
    if active is not None and active['name'] != name and active['online']:
        raise ApiError(409, 'CLASSROOM_GROUP_IN_USE')
    if grant_by_page(db, rid, browser, page) is not None:
        raise ApiError(409, 'CLASSROOM_TAB_REQUEST_CONFLICT')

    expires = int(time.time()) + current_app.config['RECOVERY_SECONDS']
    group, membership = create_membership(db, rid, name, digest(secrets.token_urlsafe(32)), expires)
    generation = 1 if active is None else active['generation'] + (active['name'] != name)
    db.execute(
        """INSERT INTO classroom_browser_groups VALUES (?,?,?,?)
           ON CONFLICT(classroom_id,browser_key) DO UPDATE
           SET group_id=excluded.group_id, generation=excluded.generation""",
        (rid, browser, group, generation),
    )
    db.execute(
        """INSERT INTO classroom_tab_grants
           (classroom_id,browser_key,page_id,membership_id,generation,resume_hash,resume_expires_at)
           VALUES (?,?,?,?,?,?,?)""", (rid, browser, page, membership, generation, digest(resume), expires),
    )
    record(db, scope, fingerprint, page)
    presence.refresh(db, rid, browser, page, group, membership)
    return dict(classroom_id=rid, group_id=group, resume_id=resume)


def record(db, scope, fingerprint, page, continued=False):
    db.execute('INSERT INTO classroom_tab_operations VALUES (?,?,?,?,?,?,?)',
               (*scope, fingerprint, page, continued))


def offer_handoff(db, grant, handoff):
    current = int(time.time())
    db.execute(
        """INSERT INTO classroom_tab_handoffs
           (classroom_id,browser_key,page_id,handoff_hash,expires_at) VALUES (?,?,?,?,?)
           ON CONFLICT(classroom_id,browser_key,page_id) DO NOTHING""",
        (grant['classroom_id'], grant['browser_key'], grant['page_id'],
         digest(handoff), current + 120),
    )


def consume_handoff(db, source, handoff):
    if handoff is None:
        return False
    result = db.execute(
        """UPDATE classroom_tab_handoffs SET consumed=1
           WHERE classroom_id=? AND browser_key=? AND page_id=? AND handoff_hash=?
             AND expires_at>? AND consumed=0""",
        (source['classroom_id'], source['browser_key'], source['page_id'],
         digest(handoff), int(time.time())),
    )
    return result.rowcount == 1


def access(db, room, resume, page, request_id, handoff=None, previous_token=None):
    browser = browser_key()
    if browser is None:
        raise ApiError(401, 'CLASSROOM_TAB_REQUIRED')
    scope = (room, browser, 'access', request_id)
    fingerprint = material('access-request', resume, page, handoff, previous_token)
    next_resume = material('resume', *scope, fingerprint)
    token = material('token', *scope, fingerprint)
    prior = prior_operation(db, scope, fingerprint)
    if prior is not None:
        grant = require_current(grant_by_page(db, room, browser, page))
        if grant['classroom_state'] != 'OPEN':
            raise ApiError(409, 'CLASSROOM_CLOSED')
        if grant['token_expires_at'] <= int(time.time()):
            raise ApiError(401, 'CLASSROOM_REJOIN_REQUIRED')
        return access_result(grant, next_resume, token, prior['continued_operation_scope'])

    source = db.execute(GRANT_QUERY + ' WHERE t.resume_hash=?', (digest(resume),)).fetchone()
    if source is not None and (source['browser_key'] != browser or source['classroom_id'] != room):
        raise ApiError(403, 'FORBIDDEN')
    source = require_current(source)
    if source['classroom_state'] != 'OPEN':
        raise ApiError(409, 'CLASSROOM_CLOSED')
    if grant_by_page(db, room, browser, page) is not None:
        raise ApiError(409, 'CLASSROOM_TAB_REQUEST_CONFLICT')
    if previous_token:
        previous = bound_grant(db, room, previous_token)
        if previous['page_id'] != source['page_id']:
            raise ApiError(403, 'FORBIDDEN')

    expires = min(int(time.time()) + TOKEN_SECONDS, source['resume_expires_at'])
    db.execute(
        """INSERT INTO classroom_tab_grants
           (classroom_id,browser_key,page_id,membership_id,generation,resume_hash,
            token_hash,token_expires_at,resume_expires_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (room, browser, page, source['membership_id'], source['generation'], digest(next_resume),
         digest(token), expires, source['resume_expires_at']),
    )
    continued = bool(previous_token) or consume_handoff(db, source, handoff)
    record(db, scope, fingerprint, page, continued)
    # The initial join's reservation is handed over to the first activated document.
    if source['token_expires_at'] is None:
        db.execute('DELETE FROM classroom_presence WHERE classroom_id=? AND browser_key=? AND page_id=?',
                   (room, browser, source['page_id']))
    elif previous_token:
        presence.depart(db, room, browser, source['page_id'])
    presence.refresh(db, room, browser, page, source['id'], source['membership_id'])
    return access_result(grant_by_page(db, room, browser, page), next_resume, token, continued)


def access_result(grant, resume, token, continued):
    return dict(classroom_id=grant['classroom_id'], group_id=grant['id'], resume_id=resume,
                page_token=token, expires_at=grant['token_expires_at'],
                continued_operation_scope=bool(continued))


def bound_grant(db, room, token):
    if not token or len(token) > 128:
        raise ApiError(401, 'CLASSROOM_TAB_REQUIRED')
    grant = db.execute(GRANT_QUERY + ' WHERE t.token_hash=?', (digest(token),)).fetchone()
    if grant is None:
        raise ApiError(401, 'CLASSROOM_TAB_REQUIRED')
    if grant['classroom_id'] != room or grant['browser_key'] != browser_key():
        raise ApiError(403, 'FORBIDDEN')
    return grant


def identity(db, room, token):
    grant = bound_grant(db, room, token)
    require_current(grant)
    if grant['token_expires_at'] <= int(time.time()):
        raise ApiError(401, 'CLASSROOM_REJOIN_REQUIRED')
    return grant


def revoke(db, room, token, request_id):
    grant = bound_grant(db, room, token)
    browser, page = grant['browser_key'], grant['page_id']
    scope = (room, browser, 'revoke', request_id)
    fingerprint = material('revoke-request', token)
    if prior_operation(db, scope, fingerprint) is not None:
        return
    require_current(grant)
    if grant['token_expires_at'] <= int(time.time()):
        raise ApiError(401, 'CLASSROOM_REJOIN_REQUIRED')
    if grant['classroom_state'] != 'OPEN':
        raise ApiError(409, 'CLASSROOM_CLOSED')
    fields = (room, browser, page)
    db.execute('UPDATE classroom_tab_grants SET revoked_at=? '
               'WHERE classroom_id=? AND browser_key=? AND page_id=?',
               (int(time.time()), *fields))
    db.execute('DELETE FROM classroom_presence WHERE classroom_id=? AND browser_key=? AND page_id=?',
               fields)
    db.execute('DELETE FROM classroom_tab_handoffs WHERE classroom_id=? AND browser_key=? AND page_id=?',
               fields)
    record(db, scope, fingerprint, page)
