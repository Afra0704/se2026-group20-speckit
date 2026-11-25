import copy
import json
from pathlib import Path
import unittest

from guided_notes.notes.models import ContractError, validate_catalog

EXAMPLES = Path(__file__).parents[2] / "specs/001-guided-notes/contracts/examples.json"


class CatalogContractTests(unittest.TestCase):
    def setUp(self):
        self.catalog = json.loads(EXAMPLES.read_text(encoding="utf-8"))["catalog"]

    def test_shared_catalog_is_valid_and_detached(self):
        result = validate_catalog(self.catalog)
        self.assertEqual(result, self.catalog)
        result["questions"].clear()
        self.assertEqual(len(self.catalog["questions"]), 2)

    def test_invalid_counts_identity_kind_and_labels(self):
        mutations = [
            lambda c: c.update(question_count=3),
            lambda c: c.update(answer_item_count=2),
            lambda c: c.update(submission_unit_count=3),
            lambda c: c.update(import_version=True),
            lambda c: c.update(import_id="not-a-uuid"),
            lambda c: c["questions"][0].update(kind="single"),
            lambda c: c["questions"][1]["items"][0].update(subitem_label="(1)"),
            lambda c: c["questions"][0]["items"][1].update(subitem_label="（1）"),
            lambda c: c["questions"][1].update(display_number="01"),
            lambda c: c["questions"][0].update(unit_id=c["questions"][1]["question_id"]),
            lambda c: c["questions"][0]["items"][1].update(
                blank_id=c["questions"][0]["items"][0]["blank_id"]),
            lambda c: c["questions"][1].update(question_id=c["questions"][0]["question_id"]),
            lambda c: c["questions"][0]["items"][1].update(
                item_id=c["questions"][0]["items"][0]["item_id"]),
        ]
        for mutation in mutations:
            candidate = copy.deepcopy(self.catalog)
            mutation(candidate)
            with self.subTest(candidate=candidate), self.assertRaises(ContractError):
                validate_catalog(candidate)

    def test_teacher_fields_never_accepted_in_public_catalog(self):
        for target in (self.catalog, self.catalog["questions"][0], self.catalog["questions"][0]["items"][0]):
            for key in ("token", "answer_range", "prompt_text", "winner_group_id"):
                candidate = copy.deepcopy(self.catalog)
                node = candidate if target is self.catalog else (
                    candidate["questions"][0] if target is self.catalog["questions"][0]
                    else candidate["questions"][0]["items"][0])
                node[key] = "private"
                with self.subTest(key=key), self.assertRaises(ContractError):
                    validate_catalog(candidate)

    def test_single_catalog_and_matching_unit_alias(self):
        catalog = self.catalog
        catalog["questions"] = catalog["questions"][1:]
        catalog.update(question_count=1, submission_unit_count=1, answer_item_count=1)
        catalog["questions"][0]["unit_id"] = catalog["questions"][0]["question_id"]
        self.assertEqual(validate_catalog(catalog)["question_count"], 1)

    def test_missing_or_non_object_payloads_fail_cleanly(self):
        for payload in (None, [], {}, {**self.catalog, "questions": None}):
            with self.subTest(payload=payload), self.assertRaises(ContractError):
                validate_catalog(payload)
