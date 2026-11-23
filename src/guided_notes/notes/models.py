"""Framework-independent validation of public v1 exchange DTOs.

These functions validate structure, never establish ownership or settlement.
Only a trusted server-side provider may supply a snapshot to the export service.
"""
from copy import deepcopy
import re
from uuid import UUID


class ContractError(ValueError):
    def __init__(self, code, message="資料不符合交換契約。"):
        self.code = code
        self.http_status = 409 if code in {"ACTIVITY_NOT_ENDED", "RESULT_VERSION_CHANGED"} else 422
        super().__init__(message)


def _require(condition, code):
    if not condition:
        raise ContractError(code)


def _object(value, required, code, optional=()):
    _require(isinstance(value, dict), code)
    _require(set(required) <= value.keys() <= set(required) | set(optional), code)


def _positive(value):
    return type(value) is int and value > 0


def _nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def _uuid(value, code, version=None):
    _require(isinstance(value, str), code)
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError):
        raise ContractError(code) from None
    _require(str(parsed) == value and (version is None or parsed.version == version), code)


def validate_catalog(catalog):
    """Return a detached DTO; reject unknown fields to protect public views."""
    code = "CATALOG_INVALID"
    _object(catalog, ("contract_version", "import_id", "import_version", "question_count",
        "submission_unit_count", "answer_item_count", "questions"), code)
    _require(type(catalog["contract_version"]) is int and catalog["contract_version"] == 1, code)
    _uuid(catalog["import_id"], code, version=4)
    _require(_positive(catalog["import_version"]), code)
    questions = catalog["questions"]
    _require(isinstance(questions, list) and bool(questions), code)
    for count in ("question_count", "submission_unit_count", "answer_item_count"):
        _require(_positive(catalog[count]), code)
    _require(catalog["question_count"] == catalog["submission_unit_count"] == len(questions), code)
    seen_q, seen_number, seen_item, seen_blank = set(), set(), set(), set()
    item_count = 0
    for question in questions:
        _object(question, ("question_id", "display_number", "kind", "items"), code, ("unit_id",))
        qid, number = question["question_id"], question["display_number"]
        _uuid(qid, code)
        _require(qid not in seen_q and question.get("unit_id", qid) == qid, code)
        _require(isinstance(number, str) and re.fullmatch(r"[1-9][0-9]*", number) is not None, code)
        _require(number not in seen_number, code)
        seen_q.add(qid)
        seen_number.add(number)
        items, kind = question["items"], question["kind"]
        _require(isinstance(items, list), code)
        _require((kind == "single" and len(items) == 1)
                 or (kind == "question_set" and len(items) >= 2), code)
        subnumbers = set()
        for item in items:
            _object(item, ("item_id", "blank_id", "subitem_label"), code)
            for key, seen in (("item_id", seen_item), ("blank_id", seen_blank)):
                _uuid(item[key], code)
                _require(item[key] not in seen, code)
                seen.add(item[key])
            label = item["subitem_label"]
            if kind == "single":
                _require(label is None, code)
            else:
                _require(isinstance(label, str), code)
                match = re.fullmatch(r"\s*[（(]\s*([0-9]+)\s*[)）]\s*", label)
                _require(match is not None and int(match[1]) > 0, code)
                subnumber = int(match[1])
                _require(subnumber not in subnumbers, code)
                subnumbers.add(subnumber)
            item_count += 1
    _require(catalog["answer_item_count"] == item_count, code)
    return deepcopy(catalog)


def validate_snapshot(snapshot, catalog, *, activity_id, result_version=None):
    """Validate exact membership and literal answers against one pinned catalog.

    Settlement and teacher ownership must already be checked by 002/003. This
    pure function cannot authorize a caller or verify that a provider is trusted.
    """
    catalog = validate_catalog(catalog)
    code = "RESULT_INVALID"
    _object(snapshot, ("contract_version", "activity_id", "import_id", "import_version",
                      "result_version", "ended", "units"), code)
    _require(type(snapshot["contract_version"]) is int and snapshot["contract_version"] == 1, code)
    _require(_nonempty(activity_id) and snapshot["activity_id"] == activity_id, code)
    _require(snapshot["import_id"] == catalog["import_id"]
             and type(snapshot["import_version"]) is int
             and snapshot["import_version"] == catalog["import_version"], code)
    _require(type(snapshot["ended"]) is bool, code)
    _require(snapshot["ended"], "ACTIVITY_NOT_ENDED")
    _require(_nonempty(snapshot["result_version"]), code)
    if result_version is not None:
        _require(snapshot["result_version"] == result_version, "RESULT_VERSION_CHANGED")
    questions = {q["question_id"]: q for q in catalog["questions"]}
    units = snapshot["units"]
    _require(isinstance(units, list) and len(units) == len(questions), code)
    seen = set()
    for unit in units:
        _object(unit, ("question_id", "winner_group_id", "no_winner", "answers"), code)
        qid = unit["question_id"]
        _require(isinstance(qid, str) and qid in questions and qid not in seen, code)
        seen.add(qid)
        _require(type(unit["no_winner"]) is bool and isinstance(unit["answers"], list), code)
        if unit["no_winner"]:
            _require(unit["winner_group_id"] is None and not unit["answers"], code)
            continue
        _require(_nonempty(unit["winner_group_id"]), code)
        expected = {i["item_id"]: i["blank_id"] for i in questions[qid]["items"]}
        _require(len(unit["answers"]) == len(expected), code)
        seen_items = set()
        for answer in unit["answers"]:
            _object(answer, ("item_id", "blank_id", "answer_text"), code, ("winner_group_id",))
            iid = answer["item_id"]
            _require(isinstance(iid, str) and iid in expected and iid not in seen_items, code)
            _require(answer["blank_id"] == expected[iid] and _nonempty(answer["answer_text"]), code)
            _require(answer.get("winner_group_id", unit["winner_group_id"]) == unit["winner_group_id"], code)
            seen_items.add(iid)
    return deepcopy(snapshot)
