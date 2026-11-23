"""Import-domain core; publication and preview persistence require the shared DB."""
from dataclasses import asdict, dataclass
import hashlib
import json
from uuid import UUID, uuid4, uuid5

from .models import ContractError, validate_catalog
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
