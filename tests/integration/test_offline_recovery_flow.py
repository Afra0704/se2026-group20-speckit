"""A simulated write/recovery flow; no app, DB or real Sheets access."""
import copy
import json
from pathlib import Path
import unittest

from guided_notes.notes.export_service import (
    build_export_preview, build_recovery_preview, classify_readback, prepare_writes)
from guided_notes.notes.import_service import build_import_bundle, match_source
from guided_notes.notes.recognition import recognize
from guided_notes.notes.sheets_gateway import GatewayError, SheetsGateway


class InMemorySheets:
    def __init__(self, sheet):
        self.sheet = copy.deepcopy(sheet)
        self.sent = []
        self.next_request = None
        self.timeout_next = False

    def spreadsheets(self):
        return self

    def values(self):
        return self

    def getByDataFilter(self, **kwargs):
        self.next_request = ("read", kwargs)
        return self

    def batchUpdateByDataFilter(self, **kwargs):
        self.next_request = ("write", kwargs)
        return self

    def execute(self, num_retries):
        assert num_retries == 0
        method, args = self.next_request
        if method == "read":
            return {"sheets": [copy.deepcopy(self.sheet)]}
        self.sent.append(args["body"])
        # Apply the whole request, then simulate lost response. This is one
        # valid timeout outcome, not evidence that every timeout is committed.
        for item in args["body"]["data"]:
            area = item["dataFilter"]["gridRange"]
            self.sheet.setdefault("data", []).append({"startRow": area["startRowIndex"],
                "startColumn": area["startColumnIndex"], "rowData": [{"values": [
                    {"userEnteredValue": {"stringValue": item["values"][0][0]}}]}]})
        if self.timeout_next:
            self.timeout_next = False
            raise TimeoutError("simulated lost response")
        return {}


class OfflineRecoveryFlowTests(unittest.TestCase):
    def test_lost_response_recovery_relocates_and_does_not_repeat_verified_items(self):
        layouts = json.loads((Path(__file__).parents[1] / "fixtures/sheets_layouts.json").read_text(encoding="utf-8"))
        api = InMemorySheets(layouts["mixed"])
        gateway = SheetsGateway(api)
        initial = recognize(gateway.read_sheet("synthetic", 7))
        bundle = build_import_bundle("synthetic", initial)
        units = [{"question_id": q["question_id"], "winner_group_id": "group-A", "no_winner": False,
            "answers": [{"item_id": i["item_id"], "blank_id": i["blank_id"], "answer_text": "=文字"}
                        for i in q["items"]]} for q in bundle.catalog["questions"]]
        snapshot = {"contract_version": 1, "activity_id": "activity-test", "import_id": bundle.catalog["import_id"],
                    "import_version": 1, "result_version": "v1", "ended": True, "units": units}
        preview = build_export_preview(bundle, initial, snapshot, activity_id="activity-test")
        writes = prepare_writes(preview, initial, snapshot, activity_id="activity-test", overwrite_item_ids=[])
        gateway.write_unit("synthetic", 7, writes[0])
        api.timeout_next = True
        with self.assertRaises(GatewayError) as caught:
            gateway.write_unit("synthetic", 7, writes[1])
        self.assertEqual(caught.exception.write_outcome, "unknown")
        # Read back after the lost response. No automatic write retry occurred.
        current = recognize(gateway.read_sheet("synthetic", 7))
        mapping = match_source(bundle, current)
        observed = {bid: item.observed_user_value for bid, item in mapping.items()}
        outcomes = {units[0]["question_id"]: "accepted", units[1]["question_id"]: "unknown"}
        report = classify_readback(preview, observed, outcomes)
        self.assertEqual(report["status"], "completed")
        self.assertEqual([u["status"] for u in report["units"]], ["completed", "completed"])
        recovery = build_recovery_preview(preview, current, snapshot, activity_id="activity-test")
        self.assertEqual(prepare_writes(recovery, current, snapshot,
            activity_id="activity-test", overwrite_item_ids=[]), [])
        self.assertEqual(len(api.sent), 2)
        self.assertEqual([len(body["data"]) for body in api.sent], [2, 1])
