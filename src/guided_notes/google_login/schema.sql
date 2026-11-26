CREATE TABLE IF NOT EXISTS auth_instance (
    singleton INTEGER PRIMARY KEY CHECK(singleton=1),
    instance_uuid TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS google_identities (
    teacher_id INTEGER PRIMARY KEY REFERENCES teachers(id),
    issuer TEXT NOT NULL CHECK(issuer='https://accounts.google.com'),
    subject TEXT NOT NULL CHECK(length(subject)>0),
    display_name TEXT,
    email TEXT,
    email_verified INTEGER NOT NULL DEFAULT 0 CHECK(email_verified IN (0,1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(issuer,subject)
);
CREATE TABLE IF NOT EXISTS auth_browsers (
    binding_hash TEXT PRIMARY KEY NOT NULL,
    epoch INTEGER NOT NULL DEFAULT 0 CHECK(epoch>=0),
    teacher_grant_hash TEXT REFERENCES grants(token) ON DELETE SET NULL,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS google_oauth_attempts (
    attempt_id TEXT PRIMARY KEY NOT NULL,
    state_hash TEXT NOT NULL UNIQUE,
    browser_hash TEXT NOT NULL REFERENCES auth_browsers(binding_hash),
    browser_epoch INTEGER NOT NULL,
    purpose TEXT NOT NULL CHECK(purpose IN ('login','sheets')),
    expected_teacher_id INTEGER REFERENCES teachers(id),
    expected_grant_hash TEXT,
    client_id TEXT NOT NULL,
    redirect_uri TEXT NOT NULL,
    instance_uuid TEXT NOT NULL,
    secret_blob BLOB,
    status TEXT NOT NULL CHECK(status IN ('pending','processing','succeeded','failed','expired','superseded')),
    claim_id TEXT,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL,
    consumed_at REAL,
    CHECK(status NOT IN ('pending','processing') OR secret_blob IS NOT NULL),
    CHECK(purpose='login' OR (expected_teacher_id IS NOT NULL AND expected_grant_hash IS NOT NULL))
);
CREATE TABLE IF NOT EXISTS google_sheets_credentials (
    teacher_id INTEGER PRIMARY KEY REFERENCES google_identities(teacher_id),
    instance_uuid TEXT NOT NULL,
    issuer TEXT NOT NULL,
    subject TEXT NOT NULL,
    client_id TEXT NOT NULL,
    credential_id TEXT NOT NULL UNIQUE,
    revision INTEGER NOT NULL CHECK(revision>0),
    status TEXT NOT NULL CHECK(status IN ('connected','reauth_required')),
    granted_scopes TEXT NOT NULL,
    expires_at REAL NOT NULL,
    secret_blob BLOB,
    refresh_lease_id TEXT,
    lease_until REAL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK(status!='connected' OR secret_blob IS NOT NULL),
    CHECK((refresh_lease_id IS NULL)=(lease_until IS NULL))
);
