CREATE TABLE IF NOT EXISTS workspace_import_flows (
 flow_id TEXT PRIMARY KEY NOT NULL,
 teacher_id INTEGER NOT NULL REFERENCES teachers(id),
 course_id TEXT NOT NULL REFERENCES courses(id),
 instance_uuid TEXT NOT NULL,
 browser_hash TEXT NOT NULL REFERENCES auth_browsers(binding_hash),
 expected_grant_hash TEXT NOT NULL,
 source_kind TEXT NOT NULL CHECK(source_kind IN ('cloud','link')),
 spreadsheet_url TEXT, spreadsheet_id TEXT, suggested_sheet_id INTEGER, source_verified_at REAL,
 status TEXT NOT NULL CHECK(status IN ('source_pending','awaiting_picker_auth','picking','awaiting_sheets_auth','reading','worksheets_ready','preview_ready','completed','cancelled','expired','invalidated','failed')),
 revision INTEGER NOT NULL DEFAULT 1 CHECK(revision>0),
 choice_revision INTEGER NOT NULL DEFAULT 1 CHECK(choice_revision>0),
 request_state_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(request_state_json) AND length(request_state_json)<=32768),
 retry_action TEXT CHECK(retry_action IN ('selection','read','preview')),
 oauth_attempt_id TEXT REFERENCES google_oauth_attempts(attempt_id) ON DELETE SET NULL,
 worksheets_json TEXT CHECK(worksheets_json IS NULL OR json_valid(worksheets_json)),
 current_preview_id TEXT REFERENCES notes_import_previews(preview_id),
 confirmed_import_id TEXT, confirmed_version INTEGER,
 claim_id TEXT, claim_action TEXT CHECK(claim_action IN ('selection','read','preview')), claim_until REAL,
 error_code TEXT,
 created_at REAL NOT NULL, expires_at REAL NOT NULL, updated_at REAL NOT NULL,
 FOREIGN KEY(confirmed_import_id,confirmed_version) REFERENCES notes_catalogs(import_id,version),
 CHECK((status='reading' AND claim_id IS NOT NULL AND claim_action IS NOT NULL AND claim_until IS NOT NULL) OR (status<>'reading' AND claim_id IS NULL AND claim_action IS NULL AND claim_until IS NULL)),
 CHECK(status<>'completed' OR (confirmed_import_id IS NOT NULL AND confirmed_version IS NOT NULL))
);
CREATE TABLE IF NOT EXISTS google_oauth_attempt_context (
 attempt_id TEXT PRIMARY KEY REFERENCES google_oauth_attempts(attempt_id) ON DELETE CASCADE,
 flow_id TEXT NOT NULL REFERENCES workspace_import_flows(flow_id) ON DELETE CASCADE,
 credential_kind TEXT NOT NULL CHECK(credential_kind IN ('picker','sheets')), created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS google_picker_credentials (
 teacher_id INTEGER PRIMARY KEY REFERENCES google_identities(teacher_id),
 instance_uuid TEXT NOT NULL, issuer TEXT NOT NULL, subject TEXT NOT NULL, client_id TEXT NOT NULL,
 credential_id TEXT NOT NULL, revision INTEGER NOT NULL CHECK(revision>0),
 actual_scopes TEXT NOT NULL CHECK(json_valid(actual_scopes)), expires_at REAL NOT NULL,
 secret_blob BLOB NOT NULL, created_at REAL NOT NULL, updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS workspace_picker_tickets (
 ticket_id TEXT PRIMARY KEY NOT NULL,
 flow_id TEXT NOT NULL REFERENCES workspace_import_flows(flow_id) ON DELETE CASCADE,
 credential_id TEXT NOT NULL, credential_revision INTEGER NOT NULL,
 expires_at REAL NOT NULL, used_at REAL, created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS workspace_preview_flows (
 preview_id TEXT PRIMARY KEY REFERENCES notes_import_previews(preview_id),
 flow_id TEXT NOT NULL REFERENCES workspace_import_flows(flow_id) ON DELETE CASCADE,
 created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS workspace_schema_versions(version INTEGER PRIMARY KEY, applied_at REAL NOT NULL);
INSERT INTO workspace_schema_versions VALUES(1,unixepoch()) ON CONFLICT DO NOTHING;
