"""Classroom presence is independent of quiz submissions."""
from time import time

from flask import session

from ..auth import digest
from .classroom_membership import group_for

PRESENCE_TTL_SECONDS = 4


def now():
    return int(time())


def heartbeat(db, classroom_id, page_id):
    group = group_for(db, classroom_id, submitting=True)
    browser_key = presence_key(group, page_id)
    refresh(db, classroom_id, browser_key, page_id, group['id'], group['membership_id'])


def presence_key(group, page_id):
    from ..http import ApiError

    if 'browser_key' not in group.keys():
        return digest(session['csrf'])
    if group['page_id'] != page_id:
        raise ApiError(403, 'FORBIDDEN')
    return group['browser_key']


def refresh(db, classroom_id, browser_key, page_id, group_id, membership_id):
    current = now()
    db.execute('DELETE FROM classroom_presence WHERE expires_at <= ?', (current,))
    db.execute('DELETE FROM classroom_presence_departures WHERE expires_at <= ?', (current,))
    if db.execute('SELECT 1 FROM classroom_presence_departures WHERE classroom_id=? AND browser_key=? AND page_id=?',
                  (classroom_id, browser_key, page_id)).fetchone():
        return
    db.execute(
        """INSERT INTO classroom_presence VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(classroom_id, browser_key, page_id) DO UPDATE SET
             group_id=excluded.group_id, membership_id=excluded.membership_id,
             expires_at=excluded.expires_at
           WHERE excluded.membership_id >= classroom_presence.membership_id""",
        (classroom_id, browser_key, page_id, group_id, membership_id, current + PRESENCE_TTL_SECONDS),
    )


def leave(db, classroom_id, page_id, tab_token=None):
    group = group_for(db, classroom_id, submitting=True, tab_token=tab_token)
    depart(db, classroom_id, presence_key(group, page_id), page_id)
    return group


def depart(db, classroom_id, browser_key, page_id):
    key = (classroom_id, browser_key, page_id)
    db.execute('DELETE FROM classroom_presence WHERE classroom_id=? AND browser_key=? AND page_id=?', key)
    # A heartbeat already in flight must not restore the page after its departure.
    db.execute('DELETE FROM classroom_presence_departures WHERE expires_at <= ?', (now(),))
    db.execute('INSERT INTO classroom_presence_departures VALUES (?,?,?,?) '
               'ON CONFLICT(classroom_id,browser_key,page_id) DO UPDATE SET expires_at=excluded.expires_at',
               (*key, now() + 120))


def roster(db, room):
    if room['state'] == 'CLOSED':
        return db.execute(
            'SELECT id AS group_id, name, NULL AS online_count FROM classroom_groups '
            'WHERE classroom_id=? ORDER BY id', (room['id'],),
        )
    return db.execute(
        """WITH current_pages AS (
             SELECT browser_key, group_id,
                    ROW_NUMBER() OVER (PARTITION BY browser_key ORDER BY membership_id DESC) AS position
             FROM classroom_presence WHERE classroom_id=? AND expires_at>?
           )
           SELECT g.id AS group_id, g.name, COUNT(p.browser_key) AS online_count
           FROM classroom_groups g LEFT JOIN current_pages p ON p.group_id=g.id AND p.position=1
           WHERE g.classroom_id=? GROUP BY g.id, g.name ORDER BY g.id""",
        (room['id'], now(), room['id']),
    )
