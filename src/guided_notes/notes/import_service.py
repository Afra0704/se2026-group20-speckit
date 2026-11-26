"""Import-domain core; publication and preview persistence require the shared DB."""
from dataclasses import asdict, dataclass
import hashlib
import json
from uuid import UUID, uuid4, uuid5

from .models import ContractError, normalize_lecture_name, validate_catalog
from .recognition import RecognitionResult


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Fingerprints:
    semantic_hash: str
    structure_hash: str
    value_hash: str


def fingerprints(recognized):
    semantics, structure, values = [], [], []
    for question in recognized.questions:
        semantics.append([question.display_number, question.kind, [
            [item.normalized_subnumber, item.prompt_text] for item in question.items]])
        structure.append([asdict(question.number_range), [
            [asdict(item.label_range) if item.label_range else None, asdict(item.answer_range)]
            for item in question.items]])
        values.append([item.observed_user_value for item in question.items])
    return Fingerprints(digest(semantics), digest([recognized.sheet_id,
        [asdict(h) for h in recognized.headers], structure]), digest(values))


@dataclass(frozen=True)
class ImportBundle:
    spreadsheet_id: str
    catalog: dict
    recognized: RecognitionResult


def build_import_bundle(spreadsheet_id, recognized, *, import_id=None, import_version=1):
    """Construct candidate IDs and private bindings, without publishing a version.

    The repository must allocate versions atomically and persist this bundle.
    Calling this pure function alone never makes a catalog available to activities.
    """
    iid = str(uuid4()) if import_id is None else import_id
    # Validate import identity/version before using UUID5.
    try:
        namespace = UUID(iid)
    except (ValueError, TypeError, AttributeError):
        raise ContractError("CATALOG_INVALID") from None
    questions = []
    for question in recognized.questions:
        qid = uuid5(namespace, f"version:{import_version}:question:{question.display_number}")
        items = []
        for item in question.items:
            iid_item = uuid5(qid, f"item:{item.normalized_subnumber or 'single'}")
            items.append({"item_id": str(iid_item), "blank_id": str(uuid5(iid_item, "blank")),
                          "subitem_label": item.subitem_label})
        questions.append({"question_id": str(qid), "display_number": question.display_number,
                          "kind": question.kind, "items": items})
    catalog = validate_catalog({"contract_version": 1, "import_id": iid, "import_version": import_version,
        "question_count": recognized.question_count, "submission_unit_count": recognized.question_count,
        "answer_item_count": recognized.answer_item_count, "questions": questions})
    return ImportBundle(spreadsheet_id, catalog, recognized)


def match_source(bundle, current):
    """Reidentify current ranges before reading/recovering any former operation."""
    if (bundle.recognized.sheet_id != current.sheet_id
            or fingerprints(bundle.recognized).semantic_hash != fingerprints(current).semantic_hash):
        raise ContractError("SOURCE_STRUCTURE_CHANGED")
    mapping = {}
    for catalog_question, question in zip(bundle.catalog["questions"], current.questions, strict=True):
        for catalog_item, item in zip(catalog_question["items"], question.items, strict=True):
            mapping[catalog_item["blank_id"]] = item
    return mapping


def get_catalog(teacher_context, import_id, import_version):
    """Published version provider for 002; never substitutes the latest version."""
    from ..auth import require_teacher
    from ..db import connection
    from ..http import ApiError
    from .repository import catalog_row
    if teacher_context != require_teacher():
        raise ApiError(403, "TEACHER_REQUIRED")
    if type(import_version) is not int or import_version <= 0:
        raise ApiError(400, "INVALID_REQUEST")
    from .lecture_lifecycle import require_active_import
    require_active_import(connection(), teacher_context.teacher_id, import_id)
    return validate_catalog(json.loads(catalog_row(connection(), teacher_context.teacher_id,
                                                   import_id, import_version)["dto"]))


def create_preview(teacher_context, gateway, spreadsheet_id, sheet_id, name_mode="source", custom_title=None,
                   course_id=None, *, flow_guard=None):
    from ..auth import require_teacher
    from ..db import write_transaction
    from .recognition import recognize
    from . import repository as repo
    from .course_catalogs import get_owned_course
    name_mode, custom_title = normalize_lecture_name(name_mode, custom_title)
    if course_id is not None:
        get_owned_course(teacher_context, course_id)
    sheet = gateway.read_sheet(spreadsheet_id, sheet_id)
    recognized = recognize(sheet)
    hashes = fingerprints(recognized)
    if course_id is not None:
        get_owned_course(teacher_context, course_id)
    with write_transaction() as db:
        current_teacher = require_teacher(db)
        if current_teacher != teacher_context:
            from ..http import ApiError
            raise ApiError(403, "TEACHER_REQUIRED")
        source_id = repo.source(db, teacher_context.teacher_id, spreadsheet_id, sheet_id,
                                sheet["properties"].get("title", str(sheet_id)))
        pid = repo.insert_preview(db, source_id, recognized, hashes, name_mode, custom_title, course_id)
        if flow_guard is not None:
            flow_guard(db, pid)
        return pid


def confirm_preview(teacher_context, preview_id, gateway_factory, existing_import_id=None):
    from ..auth import require_teacher
    from ..db import connection, write_transaction
    from ..http import ApiError
    from .recognition import recognize
    from . import repository as repo
    from .course_catalogs import check_import_context, get_owned_course

    from .lecture_lifecycle import require_active_import

    def existing_result(row, db):
        if row["status"] == "confirmed":
            if row["requested_import_id"] != existing_import_id:
                raise ApiError(409, "PREVIEW_STALE")
            require_active_import(db, teacher_context.teacher_id, row["confirmed_import_id"])
            return validate_catalog(json.loads(repo.catalog_row(db, teacher_context.teacher_id,
                row["confirmed_import_id"], row["confirmed_version"])["dto"]))
        if row["status"] != "ready":
            raise ApiError(409, "PREVIEW_STALE")
        return None

    from ..workspace.import_flows import guard_preview, published
    db = connection()
    flow = guard_preview(db, preview_id, existing_import_id)
    row = repo.owned_preview(db, teacher_context.teacher_id, preview_id)
    course_id = row["course_id"]
    if course_id is not None:
        get_owned_course(teacher_context, course_id)
    result = existing_result(row, db)
    if result is not None:
        return result, None
    if existing_import_id is not None:
        require_active_import(db, teacher_context.teacher_id, existing_import_id)
        check_import_context(db, teacher_context.teacher_id, existing_import_id, course_id)
        target = repo.owned_import(db, teacher_context.teacher_id, existing_import_id)
        if target["source_id"] != row["source_id"]:
            raise ApiError(409, "SOURCE_CHANGED")
    # All network activity ends before BEGIN IMMEDIATE.
    current_sheet = gateway_factory().read_sheet(row["spreadsheet_id"], row["sheet_id"])
    current = recognize(current_sheet)
    title = current_sheet["properties"].get("title", row["display_title"])
    hashes = fingerprints(current)
    if course_id is not None:
        get_owned_course(teacher_context, course_id)
    with write_transaction() as db:
        if require_teacher(db) != teacher_context:
            raise ApiError(403, "TEACHER_REQUIRED")
        current_flow = guard_preview(db, preview_id, existing_import_id, expected_revision=flow["revision"] if flow else None)
        row = repo.owned_preview(db, teacher_context.teacher_id, preview_id)
        result = existing_result(row, db)
        if result is not None:
            return result, None
        db.execute("UPDATE notes_sources SET display_title=? WHERE source_id=?", (title, row["source_id"]))
        if (row["semantic_hash"], row["structure_hash"], row["value_hash"]) != (
                hashes.semantic_hash, hashes.structure_hash, hashes.value_hash):
            db.execute("UPDATE notes_import_previews SET status='invalidated' WHERE preview_id=?", (preview_id,))
            next_id = repo.insert_preview(db, row["source_id"], current, hashes, row["name_mode"], row["custom_title"], course_id)
            published(db, current_flow, preview_id, existing_import_id, next_pid=next_id)
            return None, next_id
        if existing_import_id is None:
            import_id = str(uuid4())
            version = 1
            db.execute("INSERT INTO notes_imports VALUES(?,?)", (import_id, row["source_id"]))
            if course_id is not None:
                db.execute("INSERT INTO notes_import_courses VALUES(?,?,?)", (import_id, course_id, repo.now()))
        else:
            require_active_import(db, teacher_context.teacher_id, existing_import_id)
            check_import_context(db, teacher_context.teacher_id, existing_import_id, course_id)
            target = repo.owned_import(db, teacher_context.teacher_id, existing_import_id)
            if target["source_id"] != row["source_id"]:
                raise ApiError(409, "SOURCE_CHANGED")
            import_id = existing_import_id
            version = db.execute("SELECT coalesce(max(version),0)+1 FROM notes_catalogs WHERE import_id=?",
                                 (import_id,)).fetchone()[0]
        bundle = build_import_bundle(row["spreadsheet_id"], current, import_id=import_id, import_version=version)
        repo.save_catalog(db, bundle, hashes, row["name_mode"], row["custom_title"])
        db.execute("""UPDATE notes_import_previews SET status='confirmed',requested_import_id=?,
            confirmed_import_id=?,confirmed_version=? WHERE preview_id=?""",
            (existing_import_id, import_id, version, preview_id))
        published(db, current_flow, preview_id, existing_import_id, catalog=bundle.catalog)
        return bundle.catalog, None
