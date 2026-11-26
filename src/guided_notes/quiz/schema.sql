CREATE TABLE IF NOT EXISTS quiz_submissions (
    accept_seq INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    group_id INTEGER NOT NULL,
    operation_id TEXT NOT NULL,
    answers TEXT NOT NULL,
    UNIQUE (activity_id, question_id, group_id, operation_id),
    UNIQUE (activity_id, question_id, group_id, accept_seq),
    FOREIGN KEY (activity_id, question_id) REFERENCES questions(activity_id, question_id)
);
CREATE TABLE IF NOT EXISTS quiz_effective (
    activity_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    group_id INTEGER NOT NULL,
    accept_seq INTEGER NOT NULL,
    PRIMARY KEY (activity_id, question_id, group_id),
    FOREIGN KEY (activity_id, question_id, group_id, accept_seq)
        REFERENCES quiz_submissions(activity_id, question_id, group_id, accept_seq)
);
CREATE TABLE IF NOT EXISTS quiz_settlements (
    activity_id TEXT PRIMARY KEY REFERENCES activities(id),
    result_version TEXT,
    snapshot TEXT,
    results TEXT,
    CHECK ((result_version IS NULL AND snapshot IS NULL AND results IS NULL)
        OR (result_version IS NOT NULL AND snapshot IS NOT NULL AND results IS NOT NULL))
);
CREATE TRIGGER IF NOT EXISTS quiz_settlements_immutable_update
BEFORE UPDATE ON quiz_settlements WHEN OLD.result_version IS NOT NULL
BEGIN SELECT RAISE(ABORT, 'Quiz result is immutable'); END;
CREATE TRIGGER IF NOT EXISTS quiz_settlements_immutable_delete
BEFORE DELETE ON quiz_settlements WHEN OLD.result_version IS NOT NULL
BEGIN SELECT RAISE(ABORT, 'Quiz result is immutable'); END;
