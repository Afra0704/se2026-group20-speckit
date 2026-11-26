"""Classroom presence is independent of quiz submissions."""
from time import time

from flask import session

from ..auth import digest
from .classroom_membership import group_for


def now():
    return int(time())


def heartbeat(db, classroom_id, page_id):
    group = group_for(db, classroom_id, submitting=True)
    current = now()
    db.execute('DELETE FROM classroom_presence WHERE expires_at <= ?', (current,))
    db.execute(
        """INSERT INTO classroom_presence VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(classroom_id, browser_key, page_id) DO UPDATE SET
             group_id=excluded.group_id, membership_id=excluded.membership_id,
             expires_at=excluded.expires_at
           WHERE excluded.membership_id >= classroom_presence.membership_id""",
        (classroom_id, digest(session['csrf']), page_id, group['id'],
         group['membership_id'], current + 25),
    )


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
