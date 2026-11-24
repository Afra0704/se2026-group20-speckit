import copy
import json
from pathlib import Path

import pytest

from guided_notes.notes.models import ContractError, validate_snapshot


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "extra", "wrong_blank", "mixed_winner", "old_version"])
def test_exact_question_set_membership(mutation):
    examples = json.loads((Path(__file__).parents[2] / "specs/001-guided-notes/contracts/examples.json").read_text(encoding="utf-8"))
    catalog = examples["catalog"]
    snapshot = copy.deepcopy(examples["cases"][0]["snapshot"])
    unit = next(u for u in snapshot["units"] if len(u["answers"]) == 2)
    if mutation == "missing":
        unit["answers"].pop()
    elif mutation == "duplicate":
        unit["answers"][1] = copy.deepcopy(unit["answers"][0])
    elif mutation == "extra":
        unit["answers"].append(copy.deepcopy(unit["answers"][0]))
    elif mutation == "wrong_blank":
        unit["answers"][0]["blank_id"] = "00000000-0000-4000-8000-000000000000"
    elif mutation == "mixed_winner":
        unit["answers"][0]["winner_group_id"] = "other"
    else:
        snapshot["import_version"] += 1
    with pytest.raises(ContractError):
        validate_snapshot(snapshot, catalog, activity_id=snapshot["activity_id"])


def test_two_questions_three_items_keep_source_order_and_one_set_winner():
    examples = json.loads((Path(__file__).parents[2] / "specs/001-guided-notes/contracts/examples.json").read_text(encoding="utf-8"))
    catalog = examples["catalog"]
    snapshot = examples["cases"][0]["snapshot"]
    assert (catalog["question_count"], catalog["answer_item_count"]) == (2, 3)
    result = validate_snapshot(snapshot, catalog, activity_id=snapshot["activity_id"])
    assert result == snapshot
    assert [len(q["items"]) for q in catalog["questions"]] == [2, 1]
