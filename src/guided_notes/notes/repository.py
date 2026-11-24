"""001-owned tables, sharing 002's request connection and short transactions."""
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

from ..db import connection
from ..http import ApiError
from .recognition import GridRange, RecognizedItem, RecognizedQuestion, RecognitionResult


def dumps(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def now():
    return datetime.now(timezone.utc).isoformat()


def init_schema():
    connection().executescript(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))


def unpack_recognition(payload):
    value = json.loads(payload)
    questions = []
    for question in value["questions"]:
        items = [RecognizedItem(item["subitem_label"], item["normalized_subnumber"], item["prompt_text"],
            GridRange(**item["label_range"]) if item["label_range"] else None,
            GridRange(**item["answer_range"]), item["observed_user_value"]) for item in question["items"]]
        questions.append(RecognizedQuestion(question["display_number"], question["kind"],
                                           GridRange(**question["number_range"]), tuple(items)))
    return RecognitionResult(value["sheet_id"], tuple(GridRange(**h) for h in value["headers"]), tuple(questions))


def source(db, teacher_id, spreadsheet_id, sheet_id, title):
    db.execute("""INSERT INTO notes_sources VALUES(?,?,?,?,?)
        ON CONFLICT(teacher_id,spreadsheet_id,sheet_id) DO UPDATE SET display_title=excluded.display_title""",
        (str(uuid4()), teacher_id, spreadsheet_id, sheet_id, title))
    return db.execute("SELECT source_id FROM notes_sources WHERE teacher_id=? AND spreadsheet_id=? AND sheet_id=?",
                      (teacher_id, spreadsheet_id, sheet_id)).fetchone()["source_id"]


def insert_preview(db, source_id, recognized, hashes, name_mode="source", custom_title=None, course_id=None):
    pid = str(uuid4())
    db.execute("""INSERT INTO notes_import_previews
        (preview_id,source_id,recognized,semantic_hash,structure_hash,value_hash,created_at,status)
        VALUES(?,?,?,?,?,?,?,'ready')""", (pid, source_id, dumps(asdict(recognized)),
            hashes.semantic_hash, hashes.structure_hash, hashes.value_hash, now()))
    db.execute("INSERT INTO notes_preview_names VALUES(?,?,?)", (pid, name_mode, custom_title))
    if course_id is not None:
        db.execute("INSERT INTO notes_preview_courses VALUES(?,?)", (pid, course_id))
    return pid


def owned_preview(db, teacher_id, preview_id):
    row = db.execute("""SELECT p.*,s.teacher_id,s.spreadsheet_id,s.sheet_id,s.display_title,
        coalesce(n.name_mode,'source') AS name_mode,n.custom_title,pc.course_id
        FROM notes_import_previews p JOIN notes_sources s USING(source_id)
        LEFT JOIN notes_preview_names n USING(preview_id)
        LEFT JOIN notes_preview_courses pc USING(preview_id)
        WHERE p.preview_id=? AND s.teacher_id=?""", (preview_id, teacher_id)).fetchone()
    if row is None:
        raise ApiError(404, "PREVIEW_NOT_FOUND")
    return row


def owned_import(db, teacher_id, import_id):
    row = db.execute("""SELECT i.*,s.teacher_id,s.spreadsheet_id,s.sheet_id,s.display_title
        FROM notes_imports i JOIN notes_sources s USING(source_id)
        WHERE i.import_id=? AND s.teacher_id=?""", (import_id, teacher_id)).fetchone()
    if row is None:
        raise ApiError(404, "CATALOG_NOT_FOUND")
    return row


def catalog_row(db, teacher_id, import_id, version):
    owned_import(db, teacher_id, import_id)
    row = db.execute("""SELECT c.*,coalesce(n.name_mode,'source') AS name_mode,n.custom_title
        FROM notes_catalogs c LEFT JOIN notes_catalog_names n USING(import_id,version)
        WHERE c.import_id=? AND c.version=?""", (import_id, version)).fetchone()
    if row is None:
        raise ApiError(404, "CATALOG_NOT_FOUND")
    return row


def save_catalog(db, bundle, hashes, name_mode="source", custom_title=None):
    catalog = bundle.catalog
    import_id, version = catalog["import_id"], catalog["import_version"]
    db.execute("INSERT INTO notes_catalogs VALUES(?,?,?,?,?,?,?,?)",
        (import_id, version, dumps(catalog), dumps(asdict(bundle.recognized)),
         hashes.semantic_hash, hashes.structure_hash, hashes.value_hash, now()))
    db.execute("INSERT INTO notes_catalog_names VALUES(?,?,?,?)", (import_id, version, name_mode, custom_title))
    for order, (question, candidate) in enumerate(zip(catalog["questions"], bundle.recognized.questions, strict=True)):
        db.execute("INSERT INTO notes_questions VALUES(?,?,?,?,?,?)", (question["question_id"], import_id,
            version, question["display_number"], question["kind"], order))
        for position, (item, recognized) in enumerate(zip(question["items"], candidate.items, strict=True)):
            db.execute("INSERT INTO notes_answer_items VALUES(?,?,?,?,?,?)", (item["item_id"], question["question_id"],
                item["subitem_label"], recognized.normalized_subnumber, position, recognized.prompt_text))
            db.execute("INSERT INTO notes_blanks VALUES(?,?)", (item["blank_id"], item["item_id"]))
            db.execute("INSERT INTO notes_source_bindings VALUES(?,?,?,?,?,?,?)", (item["blank_id"],
                dumps(asdict(candidate.number_range)), dumps(asdict(recognized.label_range)) if recognized.label_range else None,
                dumps(asdict(recognized.answer_range)), *recognized.answer_range.anchor,
                dumps(recognized.observed_user_value)))


def insert_export_preview(db, source_id, preview, observed_recognition, origin_operation_id=None):
    pid = str(uuid4())
    catalog, snapshot = preview.bundle.catalog, preview.snapshot
    db.execute("""INSERT INTO notes_export_previews VALUES(?,?,?,?,?,?,?,?,?,?,?,?,'ready')""",
        (pid, source_id, catalog["import_id"], catalog["import_version"], snapshot["activity_id"],
         snapshot["result_version"], dumps(snapshot), dumps(asdict(observed_recognition)),
         preview.source_fingerprints.semantic_hash, preview.source_fingerprints.structure_hash,
         preview.source_fingerprints.value_hash, now()))
    db.execute("INSERT INTO notes_export_context VALUES(?,?,?)", (pid, origin_operation_id,
        dumps({item.blank_id: item.action for item in preview.items})))
    return pid


def owned_export_preview(db, teacher_id, preview_id):
    row = db.execute("""SELECT p.*,s.teacher_id,s.spreadsheet_id,s.sheet_id,s.display_title,
        coalesce(n.name_mode,'source') AS name_mode,n.custom_title,x.origin_operation_id,x.actions
        FROM notes_export_previews p JOIN notes_sources s USING(source_id)
        LEFT JOIN notes_export_context x USING(preview_id)
        LEFT JOIN notes_catalog_names n ON n.import_id=p.import_id AND n.version=p.import_version
        WHERE p.preview_id=? AND s.teacher_id=?""", (preview_id, teacher_id)).fetchone()
    if row is None:
        raise ApiError(404, "PREVIEW_NOT_FOUND")
    return row


def owned_operation(db, teacher_id, operation_id):
    row = db.execute("""SELECT o.*,p.activity_id,p.import_id,p.import_version,p.result_version,
        p.source_id,s.spreadsheet_id,s.sheet_id FROM notes_write_operations o
        JOIN notes_export_previews p USING(preview_id) JOIN notes_sources s USING(source_id)
        WHERE o.operation_id=? AND o.teacher_id=? AND s.teacher_id=?""",
        (operation_id, teacher_id, teacher_id)).fetchone()
    if row is None:
        raise ApiError(404, "OPERATION_NOT_FOUND")
    return row


def operation_by_key(db, teacher_id, key):
    return db.execute("SELECT operation_id,request_hash FROM notes_write_operations WHERE teacher_id=? AND idempotency_key=?",
                      (teacher_id, key)).fetchone()
