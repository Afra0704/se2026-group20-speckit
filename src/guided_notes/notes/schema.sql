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
