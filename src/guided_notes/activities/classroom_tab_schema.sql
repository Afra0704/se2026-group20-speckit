CREATE TABLE IF NOT EXISTS classroom_browser_groups (
    classroom_id TEXT NOT NULL,
    browser_key TEXT NOT NULL,
    group_id INTEGER NOT NULL,
    generation INTEGER NOT NULL CHECK (generation > 0),
    PRIMARY KEY (classroom_id, browser_key),
    FOREIGN KEY (classroom_id, group_id) REFERENCES classroom_groups(classroom_id, id)
);

CREATE TABLE IF NOT EXISTS classroom_tab_grants (
    classroom_id TEXT NOT NULL,
    browser_key TEXT NOT NULL,
    page_id TEXT NOT NULL,
    membership_id INTEGER NOT NULL REFERENCES classroom_memberships(id),
    generation INTEGER NOT NULL CHECK (generation > 0),
    resume_hash TEXT NOT NULL UNIQUE,
    token_hash TEXT UNIQUE,
    token_expires_at INTEGER,
    resume_expires_at INTEGER NOT NULL,
    revoked_at INTEGER,
    PRIMARY KEY (classroom_id, browser_key, page_id),
    FOREIGN KEY (classroom_id, browser_key)
        REFERENCES classroom_browser_groups(classroom_id, browser_key),
    CHECK ((token_hash IS NULL) = (token_expires_at IS NULL))
);

CREATE TABLE IF NOT EXISTS classroom_tab_operations (
    classroom_id TEXT NOT NULL,
    browser_key TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('join', 'access', 'revoke')),
    request_id TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    page_id TEXT NOT NULL,
    continued_operation_scope INTEGER NOT NULL DEFAULT 0
        CHECK (continued_operation_scope IN (0, 1)),
    PRIMARY KEY (classroom_id, browser_key, action, request_id),
    FOREIGN KEY (classroom_id, browser_key, page_id)
        REFERENCES classroom_tab_grants(classroom_id, browser_key, page_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS classroom_tab_handoffs (
    classroom_id TEXT NOT NULL,
    browser_key TEXT NOT NULL,
    page_id TEXT NOT NULL,
    handoff_hash TEXT NOT NULL,
    expires_at INTEGER NOT NULL,
    consumed INTEGER NOT NULL DEFAULT 0 CHECK (consumed IN (0, 1)),
    PRIMARY KEY (classroom_id, browser_key, page_id),
    FOREIGN KEY (classroom_id, browser_key, page_id)
        REFERENCES classroom_tab_grants(classroom_id, browser_key, page_id) ON DELETE CASCADE
);
