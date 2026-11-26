import json
import sqlite3
from pathlib import Path
import pytest
from guided_notes import create_app
from guided_notes.db import connection
from guided_notes.workspace.repository import execute_schema
from google_support import google_app,google_teacher,post,connect
from workspace_support import Sheets


def test_populated_007_additive_init_and_credentials_preserved(google_app,google_teacher):
    connect(google_teacher)
    google_app.config['NOTES_GATEWAY']=Sheets()
    cid=post(google_teacher,'/teacher/courses',title='原007課程').json['course_id']
    pid=post(google_teacher,'/teacher/notes/import-previews',spreadsheet_url='https://docs.google.com/spreadsheets/d/synthetic/edit',sheet_id=7,course_id=cid).json['preview_id']
    catalog=post(google_teacher,f'/teacher/notes/import-previews/{pid}/confirm',confirm=True).json
    with google_app.app_context():
        db=connection()
        before={table:[tuple(row) for row in db.execute('SELECT * FROM '+table)] for table in ('teachers','courses','auth_instance','google_sheets_credentials','notes_catalogs')}
        # Reconstruct the pre-008 additive boundary only inside this test's tmp_path DB.
        for table in ('google_oauth_attempt_context','workspace_picker_tickets','workspace_preview_flows','google_picker_credentials','workspace_import_flows','workspace_schema_versions'):
            db.execute('DROP TABLE '+table)
        for name in ('notes_removed_no_activity','notes_removed_no_catalog'):db.execute('DROP TRIGGER '+name)
        db.execute('DROP TABLE notes_lecture_removals')
    config={key:google_app.config[key] for key in ('TESTING','TEACHER_AUTH_MODE','CLASSROOM_MODE','DATABASE','SECRET_KEY','GOOGLE_WEB_CLIENT_SECRETS','GOOGLE_TOKEN_KEY_FILE','GOOGLE_PROVIDER')}
    for _ in range(2):
        again=create_app(config)
        result=again.test_cli_runner().invoke(args=['init-db'])
        assert result.exit_code==0,result.output
        with again.app_context():
            db=connection()
            for table,values in before.items():assert [tuple(row) for row in db.execute('SELECT * FROM '+table)]==values
            assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
            assert db.execute('SELECT count(*) FROM workspace_schema_versions').fetchone()[0]==1


def test_additive_schema_failure_rolls_back_its_segment(google_app):
    with google_app.app_context():
        db=connection()
        before=db.execute('SELECT instance_uuid FROM auth_instance').fetchone()[0]
        with pytest.raises(sqlite3.OperationalError):execute_schema(db,"""CREATE TABLE injected_partial(id INTEGER);
INSERT INTO absent_table VALUES(1);
""")
        assert not db.in_transaction
        assert not db.execute("SELECT 1 FROM sqlite_master WHERE name='injected_partial'").fetchone()
        assert db.execute('SELECT instance_uuid FROM auth_instance').fetchone()[0]==before


def test_schema_constraints_and_24h_attempt_cleanup(google_app,google_teacher):
    from google_support import start
    with google_app.app_context():
        db=connection()
        with pytest.raises(sqlite3.IntegrityError):db.execute('INSERT INTO workspace_schema_versions VALUES(1,0)')
    # Original OAuth cleanup still succeeds after 008 has installed its sidecar FKs.
    state=start(google_teacher,'sheets')
    with google_app.app_context():connection().execute("UPDATE google_oauth_attempts SET status='failed',expires_at=0,secret_blob=NULL")
    assert start(google_teacher,'sheets')
