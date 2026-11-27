CREATE TABLE IF NOT EXISTS classroom_presence (
    classroom_id TEXT NOT NULL,
    browser_key TEXT NOT NULL,
    page_id TEXT NOT NULL,
    group_id INTEGER NOT NULL,
    membership_id INTEGER NOT NULL REFERENCES classroom_memberships(id),
    expires_at INTEGER NOT NULL,
    PRIMARY KEY (classroom_id, browser_key, page_id),
    FOREIGN KEY (classroom_id, group_id) REFERENCES classroom_groups(classroom_id, id)
);
CREATE INDEX IF NOT EXISTS classroom_presence_expiry ON classroom_presence(expires_at);

CREATE TABLE IF NOT EXISTS classroom_presence_departures (
    classroom_id TEXT NOT NULL REFERENCES classrooms(id),
    browser_key TEXT NOT NULL,
    page_id TEXT NOT NULL,
    expires_at INTEGER NOT NULL,
    PRIMARY KEY (classroom_id, browser_key, page_id)
);
