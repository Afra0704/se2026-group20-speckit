import copy
import json
from pathlib import Path
import unittest

from guided_notes.notes.export_service import (
    build_export_preview, build_recovery_preview, prepare_writes, classify_readback)
from guided_notes.notes.import_service import build_import_bundle
from guided_notes.notes.models import ContractError
from guided_notes.notes.recognition import recognize


class RecoveryCoreTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).parents[1] / "fixtures/sheets_layouts.json"
        self.layouts = json.loads(path.read_text(encoding="utf-8"))
        self.current = recognize(self.layouts["mixed"])
        self.bundle = build_import_bundle("synthetic", self.current)
        units = []
        for question in self.bundle.catalog["questions"]:
            units.append({"question_id": question["question_id"], "winner_group_id": "group-A",
                "no_winner": False, "answers": [{"item_id": item["item_id"], "blank_id": item["blank_id"],
                    "answer_text": f"答案 {index}"} for index, item in enumerate(question["items"])]})
        self.snapshot = {"contract_version": 1, "activity_id": "activity-test",
            "import_id": self.bundle.catalog["import_id"], "import_version": 1,
            "result_version": "results-1", "ended": True, "units": units}

    def preview(self):
        return build_export_preview(self.bundle, self.current, self.snapshot, activity_id="activity-test")

    def test_complete_group_yields_one_request_and_no_winner_is_skipped(self):
        self.snapshot["units"][1].update(winner_group_id=None, no_winner=True, answers=[])
        preview = self.preview()
        writes = prepare_writes(preview, self.current, self.snapshot,
                                activity_id="activity-test", overwrite_item_ids=[])
        self.assertEqual([len(unit) for unit in writes], [2])
        self.assertEqual(preview.items[-1].action, "skip")

    def test_source_movement_invalidates_confirmation_and_recovery_relocates(self):
        preview = self.preview()
        moved = recognize(self.layouts["moved"])
        with self.assertRaises(ContractError) as caught:
            prepare_writes(preview, moved, self.snapshot, activity_id="activity-test", overwrite_item_ids=[])
        self.assertEqual(caught.exception.code, "PREVIEW_STALE")
        recovery = build_recovery_preview(preview, moved, self.snapshot, activity_id="activity-test")
        self.assertEqual(recovery.items[0].binding.answer_range.anchor, (7, 8))

    def test_recovery_reads_current_values_and_keeps_original_winner(self):
        original = self.preview()
        sheet = copy.deepcopy(self.layouts["moved"])
        sheet["data"][0]["rowData"][4]["values"].append({"userEnteredValue": {"stringValue": "答案 0"}})
        recovery = build_recovery_preview(original, recognize(sheet), self.snapshot, activity_id="activity-test")
        self.assertEqual(recovery.items[0].action, "already_matches")
        self.assertEqual(recovery.items[1].action, "write")
        writes = prepare_writes(recovery, recognize(sheet), self.snapshot,
                                activity_id="activity-test", overwrite_item_ids=[])
        self.assertEqual(len(writes[0]), 1)
        self.assertEqual(recovery.snapshot["units"][0]["winner_group_id"], "group-A")

    def test_conflict_requires_exact_explicit_overwrite_confirmation(self):
        original = self.preview()
        sheet = copy.deepcopy(self.layouts["mixed"])
        sheet["data"][0]["rowData"][4]["values"].append({"userEnteredValue": {"stringValue": "外部修改"}})
        changed = recognize(sheet)
        recovery = build_recovery_preview(original, changed, self.snapshot, activity_id="activity-test")
        required = [recovery.items[0].item_id]
        self.assertEqual(recovery.items[0].action, "requires_overwrite_confirmation")
        for supplied in ([], required * 2, required + ["unknown"]):
            with self.subTest(supplied=supplied), self.assertRaises(ContractError):
                prepare_writes(recovery, changed, self.snapshot,
                               activity_id="activity-test", overwrite_item_ids=supplied)
        self.assertEqual(len(prepare_writes(recovery, changed, self.snapshot,
            activity_id="activity-test", overwrite_item_ids=required)), 2)

    def test_formula_same_display_is_not_verified(self):
        preview = self.preview()
        values = {item.blank_id: {"formulaValue": '=IF(TRUE,"答案 0","")'} for item in preview.items}
        outcomes = {q["question_id"]: "unknown" for q in self.bundle.catalog["questions"]}
        report = classify_readback(preview, values, outcomes)
        self.assertNotEqual(report["status"], "completed")
        self.assertNotIn("verified", [i["status"] for i in report["items"]])

    def test_success_unknown_failed_and_not_sent_are_distinct(self):
        preview = self.preview()
        first, second = [q["question_id"] for q in self.bundle.catalog["questions"]]
        values = {preview.items[0].blank_id: {"stringValue": "答案 0"}}
        report = classify_readback(preview, values, {first: "unknown"})
        self.assertEqual([i["status"] for i in report["items"]], ["verified", "unknown", "not_processed"])
        report = classify_readback(preview, {}, {first: "failed", second: "unknown"})
        self.assertEqual([i["status"] for i in report["items"]], ["failed", "failed", "unknown"])
        complete = {i.blank_id: {"stringValue": i.proposed_text} for i in preview.items}
        self.assertEqual(classify_readback(preview, complete, {first: "accepted", second: "accepted"})["status"], "completed")

    def test_result_change_never_replaces_winner_during_recovery(self):
        preview = self.preview()
        for change in ("winner", "version"):
            altered = copy.deepcopy(self.snapshot)
            if change == "winner":
                altered["units"][0]["winner_group_id"] = "group-B"
            else:
                altered["result_version"] = "results-2"
            with self.subTest(change=change), self.assertRaises(ContractError) as caught:
                build_recovery_preview(preview, self.current, altered, activity_id="activity-test")
            self.assertEqual(caught.exception.code, "RESULT_VERSION_CHANGED")

    def test_no_winners_can_complete_without_any_writes(self):
        for unit in self.snapshot["units"]:
            unit.update(winner_group_id=None, no_winner=True, answers=[])
        preview = self.preview()
        self.assertEqual(prepare_writes(preview, self.current, self.snapshot,
            activity_id="activity-test", overwrite_item_ids=[]), [])
        self.assertEqual(classify_readback(preview, {}, {})["status"], "completed")
