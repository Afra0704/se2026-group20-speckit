CREATE TABLE IF NOT EXISTS teachers (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE,
    password_hash TEXT,
    active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS activities (
    id TEXT PRIMARY KEY,
    teacher_id INTEGER NOT NULL REFERENCES teachers(id),
    code TEXT NOT NULL UNIQUE,
    import_id TEXT NOT NULL,
    import_version INTEGER NOT NULL,
    phase TEXT NOT NULL DEFAULT 'PREPARING' CHECK (phase IN ('PREPARING', 'LIVE', 'CLOSED')),
    phase_version INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS questions (
    activity_id TEXT NOT NULL REFERENCES activities(id),
    question_id TEXT NOT NULL,
    position INTEGER NOT NULL,
    content TEXT NOT NULL,
    PRIMARY KEY (activity_id, question_id),
    UNIQUE (activity_id, position)
);
CREATE TABLE IF NOT EXISTS activity_groups (
    id INTEGER PRIMARY KEY,
    activity_id TEXT NOT NULL REFERENCES activities(id),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    UNIQUE (activity_id, name),
    UNIQUE (activity_id, id)
);
CREATE TABLE IF NOT EXISTS memberships (
    id INTEGER PRIMARY KEY,
    activity_id TEXT NOT NULL,
    group_id INTEGER NOT NULL,
    proof TEXT NOT NULL UNIQUE,
    expires INTEGER NOT NULL,
    revoked INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (activity_id, group_id) REFERENCES activity_groups(activity_id, id)
);
CREATE TABLE IF NOT EXISTS grants (
    token TEXT PRIMARY KEY,
    teacher_id INTEGER REFERENCES teachers(id),
    membership_id INTEGER REFERENCES memberships(id),
    expires INTEGER NOT NULL,
    read_only INTEGER NOT NULL DEFAULT 0,
    CHECK ((teacher_id IS NULL) <> (membership_id IS NULL)),
    CHECK (read_only = 0 OR membership_id IS NOT NULL)
);
CREATE TABLE IF NOT EXISTS attempts (
    scope TEXT PRIMARY KEY,
    count INTEGER NOT NULL,
    expires INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS activity_displays (
    activity_id TEXT PRIMARY KEY REFERENCES activities(id),
    dto TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TRIGGER IF NOT EXISTS activity_displays_no_update BEFORE UPDATE ON activity_displays
BEGIN SELECT RAISE(ABORT, 'Activity display is immutable'); END;
CREATE TRIGGER IF NOT EXISTS activity_displays_no_delete BEFORE DELETE ON activity_displays
BEGIN SELECT RAISE(ABORT, 'Activity display is immutable'); END;
