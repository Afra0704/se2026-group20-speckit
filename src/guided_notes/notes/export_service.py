"""Preview/recovery decisions and teacher-owned read-only preview persistence.

Pure core inputs come from server repositories/providers after ownership and
settlement checks. HTTP preview orchestration below never performs a write.
"""
from copy import deepcopy
from dataclasses import dataclass, replace
import json

from .import_service import Fingerprints, ImportBundle, digest, fingerprints, match_source
from .models import ContractError, validate_catalog, validate_snapshot
from .recognition import RecognizedItem
from .sheets_gateway import AnchorWrite


@dataclass(frozen=True)
class PreviewItem:
    question_id: str
    item_id: str
    blank_id: str
    binding: RecognizedItem
    original_user_value: dict
    proposed_text: str | None
    action: str


@dataclass(frozen=True)
class ExportPreview:
    bundle: ImportBundle
    snapshot: dict
    source_fingerprints: Fingerprints
    items: tuple[PreviewItem, ...]


def _matches(value, text):
    return isinstance(value, dict) and set(value) == {"stringValue"} and value["stringValue"] == text


def build_export_preview(bundle, current, snapshot, *, activity_id):
    snapshot = validate_snapshot(snapshot, bundle.catalog, activity_id=activity_id)
    bindings = match_source(bundle, current)
    units = {unit["question_id"]: unit for unit in snapshot["units"]}
    items = []
    for question in bundle.catalog["questions"]:
        unit = units[question["question_id"]]
        answers = {answer["item_id"]: answer["answer_text"] for answer in unit["answers"]}
        for item in question["items"]:
            binding = bindings[item["blank_id"]]
            value = deepcopy(binding.observed_user_value)
            text = None if unit["no_winner"] else answers[item["item_id"]]
            if text is None:
                action = "skip"
            elif _matches(value, text):
                action = "already_matches"
            elif not value:
                action = "write"
            else:
                action = "requires_overwrite_confirmation"
            items.append(PreviewItem(question["question_id"], item["item_id"], item["blank_id"],
                                     binding, value, text, action))
    return ExportPreview(deepcopy(bundle), snapshot, fingerprints(current), tuple(items))


def _check_result(preview, snapshot, activity_id):
    clean = validate_snapshot(snapshot, preview.bundle.catalog, activity_id=activity_id,
                              result_version=preview.snapshot["result_version"])
    if digest(clean) != digest(preview.snapshot):
        raise ContractError("RESULT_VERSION_CHANGED")


def build_recovery_preview(previous, current, snapshot, *, activity_id):
    _check_result(previous, snapshot, activity_id)
    # build_export_preview first reidentifies and validates all semantics; no old
    # coordinates are ever used to decide whether moved answers are complete.
    fresh = build_export_preview(previous.bundle, current, snapshot, activity_id=activity_id)
    old = {item.blank_id: item for item in previous.items}
    items = []
    for item in fresh.items:
        if item.action not in ("skip", "already_matches"):
            action = ("write" if item.original_user_value == old[item.blank_id].original_user_value
                      else "requires_overwrite_confirmation")
            item = PreviewItem(item.question_id, item.item_id, item.blank_id, item.binding,
                               item.original_user_value, item.proposed_text, action)
        items.append(item)
    return ExportPreview(fresh.bundle, fresh.snapshot, fresh.source_fingerprints, tuple(items))


def prepare_writes(preview, current, snapshot, *, activity_id, overwrite_item_ids):
    """Prepare grouped writes only; caller must still hold a current source lease.

    The DB must consume a server-owned preview exactly once and recheck teacher
    authorization before invoking this. No network request happens in this core.
    """
    _check_result(preview, snapshot, activity_id)
    match_source(preview.bundle, current)
    if fingerprints(current) != preview.source_fingerprints:
        raise ContractError("PREVIEW_STALE")
    required = {item.item_id for item in preview.items if item.action == "requires_overwrite_confirmation"}
    if (not isinstance(overwrite_item_ids, list)
            or any(not isinstance(iid, str) for iid in overwrite_item_ids)
            or len(overwrite_item_ids) != len(set(overwrite_item_ids))
            or set(overwrite_item_ids) != required):
        raise ContractError("OVERWRITE_CONFIRMATION_REQUIRED")
    groups = {}
    for item in preview.items:
        if item.action in ("skip", "already_matches"):
            continue
        row, col = item.binding.answer_range.anchor
        groups.setdefault(item.question_id, []).append(AnchorWrite(item.question_id, row, col, item.proposed_text))
    return list(groups.values())


def classify_readback(preview, observed_by_blank, outcomes_by_question):
    """Derive observations, never infer successful writes from HTTP acceptance.

    Missing observations (including a failed read) differ from observed blank {}.
    An unknown request may still finish remotely; unchanged original values do
    not prove that it failed. Durable status/time/attempt history belongs to DB.
    """
    valid_outcomes = {"accepted", "failed", "unknown"}
    known_questions = {item.question_id for item in preview.items}
    if (not set(outcomes_by_question) <= known_questions
            or any(outcome not in valid_outcomes for outcome in outcomes_by_question.values())):
        raise ContractError("RESULT_INVALID")
    items = []
    for item in preview.items:
        value = observed_by_blank.get(item.blank_id)
        outcome = outcomes_by_question.get(item.question_id)
        if item.action == "skip":
            status = "skipped"
        elif value is not None and _matches(value, item.proposed_text):
            status = "verified"
        elif outcome == "failed":
            status = "failed"
        elif outcome is None:
            status = "not_processed"
        elif value is None:
            status = "unknown"
        elif value != item.original_user_value:
            status = "conflict"
        else:
            status = "unknown" if outcome == "unknown" else "failed"
        items.append({"question_id": item.question_id, "item_id": item.item_id,
                      "blank_id": item.blank_id, "status": status})
    counts = {status: sum(item["status"] == status for item in items) for status in (
        "not_processed", "verified", "failed", "unknown", "skipped", "conflict")}
    complete = all(item["status"] in {"verified", "skipped"} for item in items)
    winners = {unit["question_id"]: unit["winner_group_id"] for unit in preview.snapshot["units"]}
    units = []
    for question in preview.bundle.catalog["questions"]:
        qid = question["question_id"]
        members = [item for item in items if item["question_id"] == qid]
        statuses = {item["status"] for item in members}
        status = ("skipped" if statuses == {"skipped"} else
                  "completed" if statuses == {"verified"} else "needs_attention")
        units.append({"question_id": qid, "winner_group_id": winners[qid], "status": status, "items": members})
    return {"status": "completed" if complete else "needs_attention", "units": units,
            "items": items, "counts": counts}


def _bundle(db, teacher_id, import_id, version):
    from . import repository as repo
    source = repo.owned_import(db, teacher_id, import_id)
    row = repo.catalog_row(db, teacher_id, import_id, version)
    return source, ImportBundle(source["spreadsheet_id"], validate_catalog(json.loads(row["dto"])),
                                repo.unpack_recognition(row["recognized"]))


def create_saved_preview(teacher_context, activity_id, gateway_factory):
    """Pin a trusted ended result and observed source; no write/lease is claimed."""
    from ..activities.teacher import get_activity_reference
    from ..auth import require_teacher
    from ..db import connection, write_transaction
    from ..http import ApiError
    from ..quiz.results_gateway import get_ended_snapshot
    from .recognition import recognize
    from . import repository as repo

    reference = get_activity_reference(teacher_context, activity_id)
    if not reference["ended"]:
        raise ApiError(409, "ACTIVITY_NOT_ENDED")
    source, bundle = _bundle(connection(), teacher_context.teacher_id,
                              reference["import_id"], reference["import_version"])
    # Validate result completeness/binding before even constructing Google client.
    snapshot = validate_snapshot(get_ended_snapshot(teacher_context, activity_id), bundle.catalog,
                                 activity_id=activity_id)
    current = recognize(gateway_factory().read_sheet(source["spreadsheet_id"], source["sheet_id"]))
    preview = build_export_preview(bundle, current, snapshot, activity_id=activity_id)
    if require_teacher() != teacher_context:
        raise ApiError(403, "TEACHER_REQUIRED")
    if get_activity_reference(teacher_context, activity_id) != reference:
        raise ApiError(409, "RESULT_VERSION_CHANGED")
    _check_result(preview, get_ended_snapshot(teacher_context, activity_id), activity_id)
    # Provider/source network calls must all end before opening the short transaction.
    with write_transaction() as db:
        if require_teacher(db) != teacher_context:
            raise ApiError(403, "TEACHER_REQUIRED")
        return repo.insert_export_preview(db, source["source_id"], preview, current)


def get_saved_preview(teacher_context, preview_id):
    """GET uses local observations only, not a freshness check or write trigger."""
    from ..auth import require_teacher
    from ..db import connection
    from ..http import ApiError
    from . import repository as repo
    if require_teacher() != teacher_context:
        raise ApiError(403, "TEACHER_REQUIRED")
    db = connection()
    row = repo.owned_export_preview(db, teacher_context.teacher_id, preview_id)
    _, bundle = _bundle(db, teacher_context.teacher_id, row["import_id"], row["import_version"])
    preview = build_export_preview(bundle, repo.unpack_recognition(row["observed_recognition"]),
                                   json.loads(row["snapshot"]), activity_id=row["activity_id"])
    if row["actions"]:
        actions = json.loads(row["actions"])
        preview = replace(preview, items=tuple(replace(item, action=actions[item.blank_id]) for item in preview.items))
    return row, preview
