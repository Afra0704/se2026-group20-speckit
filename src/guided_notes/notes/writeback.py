"""Durable, synchronous write-back. No network call holds a SQLite transaction."""
from contextlib import contextmanager
import json
import secrets
import threading
import time
from uuid import uuid4

from flask import current_app

from ..activities.teacher import get_activity_reference
from ..auth import require_teacher
from ..db import connection, write_transaction
from ..http import ApiError
from ..quiz.results_gateway import get_ended_snapshot
from . import repository as repo
from .export_service import (build_recovery_preview, classify_readback, get_saved_preview,
                             prepare_writes, _check_result)
from .import_service import digest, fingerprints, match_source
from .models import ContractError
from .google_authorization import AuthError
from .recognition import RecognitionError, recognize
from .sheets_gateway import GatewayError
from .export_context import validate as validate_context, decorate, activity_context

_locks = {}
_locks_guard = threading.Lock()


@contextmanager
def _source_mutex(row):
    key = (current_app.config["DATABASE"], row["spreadsheet_id"], row["sheet_id"])
    with _locks_guard:
        lock = _locks.setdefault(key, threading.Lock())
    if not lock.acquire(blocking=False):
        raise ApiError(409, "SOURCE_BUSY")
    try:
        yield
    finally:
        lock.release()


def _auth(teacher):
    if require_teacher() != teacher:
        raise ApiError(403, "TEACHER_REQUIRED")


def _snapshot(teacher, preview):
    aid = preview.snapshot["activity_id"]
    reference = get_activity_reference(teacher, aid)
    catalog = preview.bundle.catalog
    if (reference["import_id"], reference["import_version"]) != (catalog["import_id"], catalog["import_version"]):
        raise ContractError("RESULT_VERSION_CHANGED")
    value = get_ended_snapshot(teacher, aid)
    _check_result(preview, value, aid)
    validate_context(teacher, value)
    return value


def _claim_lease(db, row, operation_id, *, root=None):
    current = db.execute("SELECT * FROM notes_source_leases WHERE spreadsheet_id=? AND sheet_id=?",
                         (row["spreadsheet_id"], row["sheet_id"])).fetchone()
    if current is not None and current["expires_at"] > time.time():
        raise ApiError(409, "SOURCE_BUSY")
    blockers = db.execute("""SELECT o.operation_id,o.root_operation_id FROM notes_write_operations o
        JOIN notes_export_previews p USING(preview_id) JOIN notes_sources s USING(source_id)
        WHERE s.spreadsheet_id=? AND s.sheet_id=? AND o.blocks_source=1 AND o.operation_id!=?""",
        (row["spreadsheet_id"], row["sheet_id"], operation_id)).fetchall()
    if any((b["root_operation_id"] or b["operation_id"]) != root for b in blockers):
        raise ApiError(409, "SOURCE_BUSY")
    token = secrets.token_hex(24)
    db.execute("""INSERT INTO notes_source_leases VALUES(?,?,?,?,?)
        ON CONFLICT(spreadsheet_id,sheet_id) DO UPDATE SET operation_id=excluded.operation_id,
        owner_token=excluded.owner_token,expires_at=excluded.expires_at""",
        (row["spreadsheet_id"], row["sheet_id"], operation_id, token, time.time() + 300))
    return token


def _renew(db, operation_id, token):
    changed = db.execute("""UPDATE notes_source_leases SET expires_at=?
        WHERE operation_id=? AND owner_token=? AND expires_at>?""", (time.time() + 300, operation_id, token, time.time())).rowcount
    if changed != 1:
        raise ApiError(409, "SOURCE_BUSY")


def _release(operation_id, token):
    with write_transaction() as db:
        db.execute("DELETE FROM notes_source_leases WHERE operation_id=? AND owner_token=?", (operation_id, token))


def _save_items(operation_id, token, items, observations, *, error=None, only_question=None):
    with write_transaction() as db:
        _renew(db, operation_id, token)
        for item in items:
            if only_question is not None and item["question_id"] != only_question:
                continue
            status = item["status"]
            item_error = error or {"unknown": "SOURCE_READ_UNAVAILABLE", "failed": "READBACK_MISMATCH",
                                   "conflict": "SOURCE_CHANGED"}.get(status)
            db.execute("""UPDATE notes_write_items SET status=?,error_code=?,verified_at=?,observed_value=?
                WHERE operation_id=? AND blank_id=?""", (status,
                item_error if status not in {"verified", "skipped"} else None,
                repo.now() if status == "verified" else None,
                repo.dumps(observations[item["blank_id"]]) if item["blank_id"] in observations else None,
                operation_id, item["blank_id"]))
        db.execute("UPDATE notes_write_operations SET updated_at=? WHERE operation_id=?", (repo.now(), operation_id))


def _finish(operation_id, token, *, error=None, aborted=False):
    with write_transaction() as db:
        _renew(db, operation_id, token)
        complete = db.execute("""SELECT count(*) FROM notes_write_items WHERE operation_id=?
            AND status NOT IN ('verified','skipped')""", (operation_id,)).fetchone()[0] == 0
        db.execute("""UPDATE notes_write_operations SET status=?,error_code=?,blocks_source=?,updated_at=?
            WHERE operation_id=?""", ("completed" if complete else "needs_attention", None if complete else error,
            int(not complete and not aborted), repo.now(), operation_id))
        if complete:
            root = db.execute("SELECT root_operation_id FROM notes_write_operations WHERE operation_id=?", (operation_id,)).fetchone()[0]
            if root:
                db.execute("UPDATE notes_write_operations SET blocks_source=0 WHERE operation_id=? OR root_operation_id=?", (root, root))


def get_report(teacher, operation_id, *, refresh=True):
    _auth(teacher)
    row = repo.owned_operation(connection(), teacher.teacher_id, operation_id)
    activity_context(teacher, row['activity_id'])
    if refresh and row["status"] in {"writing", "queued"}:
        lease = connection().execute("SELECT expires_at FROM notes_source_leases WHERE operation_id=?", (operation_id,)).fetchone()
        if lease is None or lease[0] <= time.time():
            with write_transaction() as db:
                db.execute("""UPDATE notes_write_operations SET status='recovering',updated_at=?
                    WHERE operation_id=? AND status IN ('writing','queued') AND NOT EXISTS
                    (SELECT 1 FROM notes_source_leases WHERE operation_id=? AND expires_at>?)""",
                    (repo.now(), operation_id, operation_id, time.time()))
            row = repo.owned_operation(connection(), teacher.teacher_id, operation_id)
    snapshot = json.loads(repo.owned_export_preview(connection(), teacher.teacher_id, row["preview_id"])["snapshot"])
    records = connection().execute("SELECT * FROM notes_write_items WHERE operation_id=?", (operation_id,)).fetchall()
    indexed = {record["blank_id"]: record for record in records}
    units = []
    for unit in snapshot["units"]:
        members = [dict(item_id=r["item_id"], blank_id=r["blank_id"], status=r["status"],
                        error_code=r["error_code"], verified_at=r["verified_at"])
                   for r in indexed.values() if r["question_id"] == unit["question_id"]]
        statuses = {item["status"] for item in members}
        units.append({"question_id": unit["question_id"], "winner_group_id": unit["winner_group_id"],
            "status": "skipped" if statuses == {"skipped"} else "completed" if statuses == {"verified"} else "needs_attention",
            "items": members})
    result = {"operation_id": operation_id, "origin_operation_id": row["origin_operation_id"],
        "activity_id": row["activity_id"], "import_id": row["import_id"], "import_version": row["import_version"],
        "result_version": row["result_version"], "status": row["status"], "error_code": row["error_code"],
        "units": units, "counts": {status: sum(r["status"] == status for r in records) for status in (
            "not_processed", "verified", "failed", "unknown", "skipped", "conflict")}, "updated_at": row["updated_at"]}
    decorate(teacher, result, snapshot['units'])
    if result.get('activity_context'):
        source = repo.owned_export_preview(connection(), teacher.teacher_id, row['preview_id'])
        result['activity_context'].update(
            lecture_title=source['custom_title'] if source['name_mode'] == 'custom' else source['display_title'],
            source_title=source['display_title'], sheet_id=source['sheet_id'])
    return result


def _observations(preview, current):
    return {bid: binding.observed_user_value for bid, binding in match_source(preview.bundle, current).items()}


def _existing(teacher, key, request_hash, *, refresh=True):
    found = repo.operation_by_key(connection(), teacher.teacher_id, key)
    if found is None:
        return None
    if found["request_hash"] != request_hash:
        raise ApiError(409, "IDEMPOTENCY_CONFLICT")
    return get_report(teacher, found["operation_id"], refresh=refresh)


def confirm(teacher, preview_id, key, overwrite_item_ids, gateway_factory):
    _auth(teacher)
    row, preview = get_saved_preview(teacher, preview_id)
    request_hash = digest([preview_id, sorted(overwrite_item_ids)])
    found = _existing(teacher, key, request_hash)
    if found is not None:
        return found
    validate_context(teacher, preview.snapshot)
    required = {item.item_id for item in preview.items if item.action == "requires_overwrite_confirmation"}
    if set(overwrite_item_ids) != required:
        raise ContractError("OVERWRITE_CONFIRMATION_REQUIRED")
    with _source_mutex(row):
        with write_transaction() as db:
            _auth(teacher)
            found = _existing(teacher, key, request_hash, refresh=False)
            if found is not None:
                return found
            current_row = repo.owned_export_preview(db, teacher.teacher_id, preview_id)
            if current_row["status"] != "ready":
                raise ApiError(409, "PREVIEW_STALE")
            operation_id = str(uuid4())
            origin = row["origin_operation_id"]
            root = None
            if origin:
                origin_row = repo.owned_operation(db, teacher.teacher_id, origin)
                root = origin_row["root_operation_id"] or origin
            db.execute("INSERT INTO notes_write_operations VALUES(?,?,?,?,?,?,?,'writing',1,NULL,?,?)",
                (operation_id, preview_id, teacher.teacher_id, key, request_hash, origin, root, repo.now(), repo.now()))
            token = _claim_lease(db, row, operation_id, root=root)
            db.execute("UPDATE notes_export_previews SET status='consumed' WHERE preview_id=?", (preview_id,))
            db.executemany("INSERT INTO notes_write_items VALUES(?,?,?,?,'not_processed',NULL,NULL,NULL)",
                [(operation_id, item.question_id, item.item_id, item.blank_id) for item in preview.items])
        sent = False
        try:
            gateway = gateway_factory()
            snapshot = _snapshot(teacher, preview)
            current = recognize(gateway.read_sheet(row["spreadsheet_id"], row["sheet_id"]))
            groups = prepare_writes(preview, current, snapshot, activity_id=row["activity_id"],
                                     overwrite_item_ids=overwrite_item_ids)
            _auth(teacher)
            initial = classify_readback(preview, _observations(preview, current), {})
            _save_items(operation_id, token, initial["items"], _observations(preview, current))
            deadline = time.monotonic() + current_app.config.get("NOTES_WRITE_SECONDS", 120)
            error = None
            for group in groups:
                if time.monotonic() >= deadline:
                    error = "EXECUTION_LIMIT"
                    break
                _auth(teacher)
                _snapshot(teacher, preview)
                with write_transaction() as db:
                    _renew(db, operation_id, token)
                current = recognize(gateway.read_sheet(row["spreadsheet_id"], row["sheet_id"]))
                observed = _observations(preview, current)
                if fingerprints(current).structure_hash != preview.source_fingerprints.structure_hash:
                    raise ContractError("PREVIEW_STALE")
                qid = group[0].question_id
                if any(observed[i.blank_id] != i.original_user_value for i in preview.items if i.question_id == qid):
                    raise ContractError("PREVIEW_STALE")
                _auth(teacher)
                _snapshot(teacher, preview)
                with write_transaction() as db:
                    _renew(db, operation_id, token)
                    db.execute("UPDATE notes_write_items SET status='unknown' WHERE operation_id=? AND question_id=? AND status!='verified'",
                               (operation_id, qid))
                sent = True
                outcome, error = "accepted", None
                try:
                    gateway.write_unit(row["spreadsheet_id"], row["sheet_id"], group)
                except GatewayError as failure:
                    outcome, error = failure.write_outcome or "unknown", failure.code
                observations = {}
                try:
                    after = recognize(gateway.read_sheet(row["spreadsheet_id"], row["sheet_id"]))
                    observations = _observations(preview, after)
                except (GatewayError, ContractError, RecognitionError):
                    error = error or "SOURCE_READ_UNAVAILABLE"
                classified = classify_readback(preview, observations, {qid: outcome})
                _save_items(operation_id, token, classified["items"], observations, error=error, only_question=qid)
                if any(i["status"] not in {"verified", "skipped"} for i in classified["items"] if i["question_id"] == qid):
                    break
            _finish(operation_id, token, error=error)
        except (ApiError, ContractError, GatewayError, RecognitionError, AuthError) as failure:
            code = getattr(failure, "code", "SOURCE_STRUCTURE_CHANGED")
            _finish(operation_id, token, error=code, aborted=not sent)
            if not sent:
                with write_transaction() as db:
                    db.execute("UPDATE notes_export_previews SET status='invalidated' WHERE preview_id=?", (preview_id,))
                status = getattr(failure, "http_status", getattr(failure, "status", 422))
                rejected = ApiError(status, code)
                rejected.context = {"operation_id": operation_id}
                raise rejected from None
        finally:
            _release(operation_id, token)
        return get_report(teacher, operation_id)


def recovery_preview(teacher, operation_id, gateway_factory):
    _auth(teacher)
    row = repo.owned_operation(connection(), teacher.teacher_id, operation_id)
    _, previous = get_saved_preview(teacher, row["preview_id"])
    validate_context(teacher, previous.snapshot)
    with _source_mutex(row):
        with write_transaction() as db:
            _auth(teacher)
            token = _claim_lease(db, row, operation_id, root=row["root_operation_id"] or operation_id)
            db.execute("UPDATE notes_write_operations SET status='recovering',updated_at=? WHERE operation_id=?",
                       (repo.now(), operation_id))
        try:
            snapshot = _snapshot(teacher, previous)
            gateway = gateway_factory()
            current = recognize(gateway.read_sheet(row["spreadsheet_id"], row["sheet_id"]))
            fresh = build_recovery_preview(previous, current, snapshot, activity_id=row["activity_id"])
            _auth(teacher)
            _snapshot(teacher, previous)
            observations = _observations(fresh, current)
            classified = classify_readback(fresh, observations, {})
            conflicts = {item.blank_id for item in fresh.items if item.action == "requires_overwrite_confirmation"}
            for item in classified["items"]:
                if item["blank_id"] in conflicts:
                    item["status"] = "conflict"
            _save_items(operation_id, token, classified["items"], observations)
            with write_transaction() as db:
                _renew(db, operation_id, token)
                pid = repo.insert_export_preview(db, row["source_id"], fresh, current, operation_id)
            _finish(operation_id, token)
            return pid
        finally:
            _release(operation_id, token)
