CREATE TABLE IF NOT EXISTS courses (
    id TEXT PRIMARY KEY,
    teacher_id INTEGER NOT NULL REFERENCES teachers(id),
    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS classrooms (
    id TEXT PRIMARY KEY,
    course_id TEXT NOT NULL REFERENCES courses(id),
    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
    code TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'OPEN' CHECK (state IN ('OPEN', 'CLOSED')),
    state_version INTEGER NOT NULL DEFAULT 0,
    current_activity_id TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    closed_at TEXT,
    FOREIGN KEY (id, current_activity_id) REFERENCES classroom_activities(classroom_id, activity_id)
);

CREATE TABLE IF NOT EXISTS classroom_activities (
    activity_id TEXT PRIMARY KEY REFERENCES activities(id),
    classroom_id TEXT NOT NULL REFERENCES classrooms(id),
    title TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TEXT,
    closed_at TEXT,
    UNIQUE (classroom_id, activity_id)
);

CREATE TRIGGER IF NOT EXISTS classroom_only_one_live
BEFORE UPDATE OF phase ON activities
WHEN NEW.phase = 'LIVE' AND EXISTS (
    SELECT 1 FROM classroom_activities target
    JOIN classroom_activities other ON other.classroom_id = target.classroom_id
    JOIN activities live ON live.id = other.activity_id
    WHERE target.activity_id = NEW.id AND live.id <> NEW.id AND live.phase = 'LIVE'
)
BEGIN
    SELECT RAISE(ABORT, 'classroom already has a live activity');
END;

CREATE TABLE IF NOT EXISTS classroom_groups (
    id INTEGER PRIMARY KEY,
    classroom_id TEXT NOT NULL REFERENCES classrooms(id),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    UNIQUE (classroom_id, name),
    UNIQUE (classroom_id, id)
);

CREATE TRIGGER IF NOT EXISTS classroom_single_unfinished_insert
BEFORE INSERT ON classroom_activities
WHEN (SELECT phase FROM activities WHERE id=NEW.activity_id) IN ('PREPARING','LIVE')
AND EXISTS (
    SELECT 1 FROM classroom_activities c JOIN activities a ON a.id=c.activity_id
    WHERE c.classroom_id=NEW.classroom_id AND a.phase IN ('PREPARING','LIVE')
)
BEGIN
    SELECT RAISE(ABORT, 'classroom_unfinished');
END;

CREATE TRIGGER IF NOT EXISTS classroom_single_unfinished_phase
BEFORE UPDATE OF phase ON activities
WHEN NEW.phase IN ('PREPARING','LIVE') AND EXISTS (
    SELECT 1 FROM classroom_activities target
    JOIN classroom_activities other ON target.classroom_id=other.classroom_id
    JOIN activities a ON a.id=other.activity_id
    WHERE target.activity_id=NEW.id AND a.id<>NEW.id AND a.phase IN ('PREPARING','LIVE')
)
BEGIN
    SELECT RAISE(ABORT, 'classroom_unfinished');
END;

CREATE TRIGGER IF NOT EXISTS classroom_closed_activity_stays_closed
BEFORE UPDATE OF phase ON activities
WHEN OLD.phase='CLOSED' AND NEW.phase<>'CLOSED'
AND EXISTS (SELECT 1 FROM classroom_activities WHERE activity_id=NEW.id)
BEGIN
    SELECT RAISE(ABORT, 'classroom_closed_activity');
END;

CREATE TABLE IF NOT EXISTS classroom_memberships (
    id INTEGER PRIMARY KEY,
    classroom_id TEXT NOT NULL,
    group_id INTEGER NOT NULL,
    proof TEXT NOT NULL UNIQUE,
    expires INTEGER NOT NULL,
    FOREIGN KEY (classroom_id, group_id) REFERENCES classroom_groups(classroom_id, id)
);

CREATE TABLE IF NOT EXISTS classroom_grants (
    token TEXT PRIMARY KEY,
    membership_id INTEGER NOT NULL REFERENCES classroom_memberships(id),
    expires INTEGER NOT NULL,
    read_only INTEGER NOT NULL DEFAULT 0 CHECK (read_only IN (0, 1))
);

CREATE UNIQUE INDEX IF NOT EXISTS classrooms_open_code_unique ON classrooms(code) WHERE state='OPEN';

CREATE TRIGGER IF NOT EXISTS classroom_permanently_closed
BEFORE UPDATE OF state ON classrooms
WHEN OLD.state='CLOSED' AND NEW.state<>'CLOSED'
BEGIN SELECT RAISE(ABORT, 'classroom_permanently_closed'); END;

CREATE TRIGGER IF NOT EXISTS classroom_identity_immutable
BEFORE UPDATE OF id,course_id,code ON classrooms
WHEN NEW.id<>OLD.id OR NEW.course_id<>OLD.course_id OR NEW.code<>OLD.code
BEGIN SELECT RAISE(ABORT, 'classroom_identity_immutable'); END;

CREATE TABLE IF NOT EXISTS classroom_schema_versions (
    version INTEGER PRIMARY KEY CHECK (version=9),
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO classroom_schema_versions(version) VALUES (9) ON CONFLICT DO NOTHING;
