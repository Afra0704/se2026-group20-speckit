import copy
import json
from pathlib import Path
import unittest
from uuid import uuid4

from guided_notes.notes.import_service import build_import_bundle, fingerprints, match_source
from guided_notes.notes.models import ContractError, validate_catalog
from guided_notes.notes.recognition import recognize

FIXTURES = Path(__file__).parents[1] / "fixtures/sheets_layouts.json"


class ImportCoreTests(unittest.TestCase):
    def setUp(self):
        self.layouts = json.loads(FIXTURES.read_text(encoding="utf-8"))
        self.original = recognize(self.layouts["mixed"])
        self.moved = recognize(self.layouts["moved"])

    def test_catalog_identity_is_versioned_and_not_coordinate_based(self):
        iid = str(uuid4())
        one = build_import_bundle("synthetic", self.original, import_id=iid)
        moved = build_import_bundle("synthetic", self.moved, import_id=iid)
        next_version = build_import_bundle("synthetic", self.original, import_id=iid, import_version=2)
        self.assertEqual(one.catalog, moved.catalog)
        self.assertNotEqual(one.catalog["questions"][0]["question_id"],
                            next_version.catalog["questions"][0]["question_id"])
        self.assertEqual(validate_catalog(one.catalog)["answer_item_count"], 3)

    def test_fingerprints_separate_semantics_structure_and_values(self):
        original, moved = fingerprints(self.original), fingerprints(self.moved)
        self.assertEqual(original.semantic_hash, moved.semantic_hash)
        self.assertNotEqual(original.structure_hash, moved.structure_hash)
        self.assertEqual(original.value_hash, moved.value_hash)
        changed = copy.deepcopy(self.layouts["mixed"])
        changed["data"][0]["rowData"][4]["values"].append({"userEnteredValue": {"stringValue": "CPU"}})
        updated = fingerprints(recognize(changed))
        self.assertEqual(original.semantic_hash, updated.semantic_hash)
        self.assertEqual(original.structure_hash, updated.structure_hash)
        self.assertNotEqual(original.value_hash, updated.value_hash)

    def test_prompt_and_membership_change_require_reimport(self):
        bundle = build_import_bundle("synthetic", self.original)
        for change in ("prompt", "number"):
            sheet = copy.deepcopy(self.layouts["mixed"])
            column = 2 if change == "prompt" else 1
            sheet["data"][0]["rowData"][7]["values"][column] = {
                "userEnteredValue": {"stringValue": "新題目" if change == "prompt" else "3"}}
            with self.subTest(change=change), self.assertRaises(ContractError) as caught:
                match_source(bundle, recognize(sheet))
            self.assertEqual(caught.exception.code, "SOURCE_STRUCTURE_CHANGED")

    def test_moved_bindings_preserve_blank_identity(self):
        bundle = build_import_bundle("synthetic", self.original)
        bindings = match_source(bundle, self.moved)
        first = bundle.catalog["questions"][0]["items"][0]
        self.assertEqual(bindings[first["blank_id"]].answer_range.anchor, (7, 8))

    def test_semantic_hash_preserves_spaces_and_ignores_sheet_title(self):
        sheet = copy.deepcopy(self.layouts["mixed"])
        sheet["properties"]["title"] = "重新命名"
        self.assertEqual(fingerprints(self.original), fingerprints(recognize(sheet)))
        sheet["data"][0]["rowData"][4]["values"][2]["userEnteredValue"]["stringValue"] += " "
        self.assertNotEqual(fingerprints(self.original).semantic_hash,
                            fingerprints(recognize(sheet)).semantic_hash)
