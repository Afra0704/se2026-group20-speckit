"""Preview guards and read-back rules independent of app authorization/storage."""
import copy
import json
from pathlib import Path
import unittest

from guided_notes.notes.export_service import build_export_preview, classify_readback, prepare_writes
from guided_notes.notes.import_service import build_import_bundle
from guided_notes.notes.models import ContractError
from guided_notes.notes.recognition import recognize


class ExportPreviewTests(unittest.TestCase):
    def setUp(self):
        self.sheet = json.loads((Path(__file__).parents[1] / "fixtures/sheets_layouts.json").read_text(encoding="utf-8"))["single"]
        self.current = recognize(self.sheet)
        self.bundle = build_import_bundle("synthetic", self.current)
        question = self.bundle.catalog["questions"][0]
        item = question["items"][0]
        self.snapshot = {"contract_version": 1, "activity_id": "a", "result_version": "r",
            "import_id": self.bundle.catalog["import_id"], "import_version": 1, "ended": True,
            "units": [{"question_id": question["question_id"], "winner_group_id": "winner", "no_winner": False,
                "answers": [{"item_id": item["item_id"], "blank_id": item["blank_id"], "answer_text": "=001\n中文 "}]}]}

    def test_existing_formula_requires_overwrite_and_literal_answer_is_unchanged(self):
        preview = build_export_preview(self.bundle, self.current, self.snapshot, activity_id="a")
        self.assertEqual(preview.items[0].action, "requires_overwrite_confirmation")
        with self.assertRaises(ContractError):
            prepare_writes(preview, self.current, self.snapshot, activity_id="a", overwrite_item_ids=[])
        writes = prepare_writes(preview, self.current, self.snapshot, activity_id="a",
                                overwrite_item_ids=[preview.items[0].item_id])
        self.assertEqual(writes[0][0].text, "=001\n中文 ")

    def test_post_preview_value_change_is_stale_and_no_write_is_prepared(self):
        preview = build_export_preview(self.bundle, self.current, self.snapshot, activity_id="a")
        changed = copy.deepcopy(self.sheet)
        changed["data"][0]["rowData"][4]["values"][5]["userEnteredValue"] = {"stringValue": "外部新值"}
        with self.assertRaises(ContractError) as caught:
            prepare_writes(preview, recognize(changed), self.snapshot, activity_id="a",
                           overwrite_item_ids=[preview.items[0].item_id])
        self.assertEqual(caught.exception.code, "PREVIEW_STALE")

    def test_success_response_without_readback_is_unknown(self):
        preview = build_export_preview(self.bundle, self.current, self.snapshot, activity_id="a")
        report = classify_readback(preview, {}, {preview.items[0].question_id: "accepted"})
        self.assertEqual(report["items"][0]["status"], "unknown")

    def test_response_accepted_but_original_value_remains_is_not_verified(self):
        preview = build_export_preview(self.bundle, self.current, self.snapshot, activity_id="a")
        item = preview.items[0]
        report = classify_readback(preview, {item.blank_id: item.original_user_value}, {item.question_id: "accepted"})
        self.assertEqual(report["items"][0]["status"], "failed")

    def test_other_observed_content_is_a_conflict(self):
        preview = build_export_preview(self.bundle, self.current, self.snapshot, activity_id="a")
        item = preview.items[0]
        report = classify_readback(preview, {item.blank_id: {"stringValue": "第三種內容"}}, {item.question_id: "unknown"})
        self.assertEqual(report["items"][0]["status"], "conflict")

    def test_preview_detaches_snapshot_from_provider_mutation(self):
        preview = build_export_preview(self.bundle, self.current, self.snapshot, activity_id="a")
        self.snapshot["units"][0]["answers"][0]["answer_text"] = "changed"
        self.assertEqual(preview.snapshot["units"][0]["answers"][0]["answer_text"], "=001\n中文 ")
