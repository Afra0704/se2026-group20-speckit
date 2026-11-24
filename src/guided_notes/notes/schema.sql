CREATE TABLE IF NOT EXISTS notes_sources (
    source_id TEXT PRIMARY KEY,
    teacher_id INTEGER NOT NULL REFERENCES teachers(id),
    spreadsheet_id TEXT NOT NULL,
    sheet_id INTEGER NOT NULL CHECK(sheet_id >= 0),
    display_title TEXT NOT NULL,
    UNIQUE(teacher_id, spreadsheet_id, sheet_id)
);
CREATE TABLE IF NOT EXISTS notes_imports (
    import_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES notes_sources(source_id)
);
CREATE TABLE IF NOT EXISTS notes_catalogs (
    import_id TEXT NOT NULL REFERENCES notes_imports(import_id),
    version INTEGER NOT NULL CHECK(version > 0),
    dto TEXT NOT NULL,
    recognized TEXT NOT NULL,
    semantic_hash TEXT NOT NULL,
    structure_hash TEXT NOT NULL,
    value_hash TEXT NOT NULL,
    confirmed_at TEXT NOT NULL,
    PRIMARY KEY(import_id, version)
);
CREATE TABLE IF NOT EXISTS notes_questions (
    question_id TEXT PRIMARY KEY,
    import_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    display_number TEXT NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN ('single','question_set')),
    order_index INTEGER NOT NULL,
    FOREIGN KEY(import_id,version) REFERENCES notes_catalogs(import_id,version),
    UNIQUE(import_id,version,display_number),
    UNIQUE(import_id,version,order_index)
);
CREATE TABLE IF NOT EXISTS notes_answer_items (
    item_id TEXT PRIMARY KEY,
    question_id TEXT NOT NULL REFERENCES notes_questions(question_id),
    subitem_label TEXT,
    normalized_subnumber INTEGER,
    order_index INTEGER NOT NULL,
    prompt_text TEXT NOT NULL,
    UNIQUE(question_id,order_index),
    UNIQUE(question_id,normalized_subnumber)
);
CREATE TABLE IF NOT EXISTS notes_blanks (
    blank_id TEXT PRIMARY KEY,
    item_id TEXT NOT NULL UNIQUE REFERENCES notes_answer_items(item_id)
);
CREATE TABLE IF NOT EXISTS notes_source_bindings (
    blank_id TEXT PRIMARY KEY REFERENCES notes_blanks(blank_id),
    number_range TEXT NOT NULL,
    label_range TEXT,
    answer_range TEXT NOT NULL,
    anchor_row INTEGER NOT NULL,
    anchor_column INTEGER NOT NULL,
    observed_user_value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS notes_import_previews (
    preview_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES notes_sources(source_id),
    recognized TEXT NOT NULL,
    semantic_hash TEXT NOT NULL,
    structure_hash TEXT NOT NULL,
    value_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('ready','confirmed','invalidated')),
    requested_import_id TEXT,
    confirmed_import_id TEXT,
    confirmed_version INTEGER,
    FOREIGN KEY(confirmed_import_id,confirmed_version) REFERENCES notes_catalogs(import_id,version),
    CHECK ((status = 'confirmed' AND confirmed_import_id IS NOT NULL AND confirmed_version IS NOT NULL)
           OR (status != 'confirmed' AND confirmed_import_id IS NULL AND confirmed_version IS NULL))
);
CREATE TRIGGER IF NOT EXISTS notes_catalogs_no_update
BEFORE UPDATE ON notes_catalogs BEGIN SELECT RAISE(ABORT,'confirmed catalog is immutable'); END;
CREATE TRIGGER IF NOT EXISTS notes_catalogs_no_delete
BEFORE DELETE ON notes_catalogs BEGIN SELECT RAISE(ABORT,'confirmed catalog is immutable'); END;

-- Additive naming metadata: existing immutable catalogs are never rewritten.
CREATE TABLE IF NOT EXISTS notes_preview_names (
    preview_id TEXT PRIMARY KEY REFERENCES notes_import_previews(preview_id),
    name_mode TEXT NOT NULL CHECK(name_mode IN ('source','custom')),
    custom_title TEXT,
    CHECK ((name_mode='source' AND custom_title IS NULL) OR
           (name_mode='custom' AND custom_title IS NOT NULL AND length(trim(custom_title)) BETWEEN 1 AND 100))
);
CREATE TABLE IF NOT EXISTS notes_catalog_names (
    import_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    name_mode TEXT NOT NULL CHECK(name_mode IN ('source','custom')),
    custom_title TEXT,
    PRIMARY KEY(import_id,version),
    FOREIGN KEY(import_id,version) REFERENCES notes_catalogs(import_id,version),
    CHECK ((name_mode='source' AND custom_title IS NULL) OR
           (name_mode='custom' AND custom_title IS NOT NULL AND length(trim(custom_title)) BETWEEN 1 AND 100))
);
INSERT INTO notes_preview_names(preview_id,name_mode,custom_title)
SELECT preview_id,'source',NULL FROM notes_import_previews WHERE 1
ON CONFLICT(preview_id) DO NOTHING;
INSERT INTO notes_catalog_names(import_id,version,name_mode,custom_title)
SELECT import_id,version,'source',NULL FROM notes_catalogs WHERE 1
ON CONFLICT(import_id,version) DO NOTHING;

-- A preview records observations and intentions only; no write operation exists yet.
CREATE TABLE IF NOT EXISTS notes_export_previews (
    preview_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES notes_sources(source_id),
    import_id TEXT NOT NULL,
    import_version INTEGER NOT NULL,
    activity_id TEXT NOT NULL,
    result_version TEXT NOT NULL,
    snapshot TEXT NOT NULL,
    observed_recognition TEXT NOT NULL,
    semantic_hash TEXT NOT NULL,
    structure_hash TEXT NOT NULL,
    value_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('ready','consumed','invalidated')),
    FOREIGN KEY(import_id,import_version) REFERENCES notes_catalogs(import_id,version)
);
CREATE INDEX IF NOT EXISTS notes_export_previews_source ON notes_export_previews(source_id,created_at);

-- 002 owns courses. No shadow course table or automatic legacy allocation.
CREATE TABLE IF NOT EXISTS notes_import_courses (
    import_id TEXT PRIMARY KEY REFERENCES notes_imports(import_id),
    course_id TEXT NOT NULL CHECK(length(course_id) BETWEEN 1 AND 128),
    assigned_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS notes_import_courses_course ON notes_import_courses(course_id);
CREATE TABLE IF NOT EXISTS notes_preview_courses (
    preview_id TEXT PRIMARY KEY REFERENCES notes_import_previews(preview_id),
    course_id TEXT NOT NULL CHECK(length(course_id) BETWEEN 1 AND 128)
);
CREATE TRIGGER IF NOT EXISTS notes_import_courses_no_move
BEFORE UPDATE ON notes_import_courses BEGIN SELECT RAISE(ABORT,'course assignment is fixed'); END;

CREATE TABLE IF NOT EXISTS notes_write_operations (
    operation_id TEXT PRIMARY KEY,
    preview_id TEXT NOT NULL UNIQUE REFERENCES notes_export_previews(preview_id),
    teacher_id INTEGER NOT NULL REFERENCES teachers(id),
    idempotency_key TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    origin_operation_id TEXT REFERENCES notes_write_operations(operation_id),
    root_operation_id TEXT REFERENCES notes_write_operations(operation_id),
    status TEXT NOT NULL CHECK(status IN ('queued','writing','recovering','completed','needs_attention')),
    blocks_source INTEGER NOT NULL CHECK(blocks_source IN (0,1)),
    error_code TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(teacher_id,idempotency_key)
);
CREATE TABLE IF NOT EXISTS notes_write_items (
    operation_id TEXT NOT NULL REFERENCES notes_write_operations(operation_id),
    question_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    blank_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('not_processed','verified','failed','unknown','skipped','conflict')),
    error_code TEXT,
    verified_at TEXT,
    observed_value TEXT,
    PRIMARY KEY(operation_id,blank_id)
);
CREATE TABLE IF NOT EXISTS notes_source_leases (
    spreadsheet_id TEXT NOT NULL,
    sheet_id INTEGER NOT NULL,
    operation_id TEXT NOT NULL REFERENCES notes_write_operations(operation_id),
    owner_token TEXT NOT NULL,
    expires_at REAL NOT NULL,
    PRIMARY KEY(spreadsheet_id,sheet_id)
);
CREATE TABLE IF NOT EXISTS notes_export_context (
    preview_id TEXT PRIMARY KEY REFERENCES notes_export_previews(preview_id),
    origin_operation_id TEXT REFERENCES notes_write_operations(operation_id),
    actions TEXT NOT NULL
);
