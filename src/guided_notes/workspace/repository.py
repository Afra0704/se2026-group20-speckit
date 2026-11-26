"""Additive schema and bounded flow cleanup. No application data reset."""
from pathlib import Path
from ..db import connection, write_transaction, execute_schema_statements


def execute_schema(db, sql):
    if db.in_transaction:
        raise RuntimeError('Schema initialization requires its own transaction.')
    db.execute('BEGIN IMMEDIATE')
    try:
        execute_schema_statements(db, sql)
        db.execute('COMMIT')
    except BaseException:
        db.execute('ROLLBACK')
        raise


def initialize():
    execute_schema(connection(), Path(__file__).with_name('schema.sql').read_text(encoding='utf-8'))


def invalidate(db, flow_id, status, now):
    db.execute("UPDATE notes_import_previews SET status='invalidated' WHERE status='ready' AND preview_id IN (SELECT preview_id FROM workspace_preview_flows WHERE flow_id=?)", (flow_id,))
    db.execute('DELETE FROM workspace_picker_tickets WHERE flow_id=?', (flow_id,))
    db.execute("UPDATE workspace_import_flows SET status=?,revision=revision+1,claim_id=NULL,claim_action=NULL,claim_until=NULL,retry_action=NULL,updated_at=? WHERE flow_id=? AND status<>'completed'", (status,now,flow_id))
