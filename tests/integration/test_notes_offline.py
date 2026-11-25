"""Component handoff tests, not HTTP/authentication or real Google validation."""
import copy
import json
from pathlib import Path
import unittest

from guided_notes.notes.models import validate_catalog, validate_snapshot
from guided_notes.notes.recognition import recognize
from guided_notes.notes.sheets_gateway import SheetsGateway


class ReadOnlyService:
    def __init__(self, sheet):
        self.sheet = sheet
        self.calls = []

    def spreadsheets(self):
        return self

    def getByDataFilter(self, **kwargs):
        self.calls.append(kwargs)
        return self

    def execute(self, num_retries):
        assert num_retries == 0
        return {"sheets": [copy.deepcopy(self.sheet)]}


class OfflineHandoffTests(unittest.TestCase):
    def test_gateway_to_recognition_on_original_and_moved_layout(self):
        path = Path(__file__).parents[1] / "fixtures/sheets_layouts.json"
        layouts = json.loads(path.read_text(encoding="utf-8"))
        for name in ("mixed", "moved"):
            with self.subTest(layout=name):
                service = ReadOnlyService(layouts[name])
                candidates = recognize(SheetsGateway(service).read_sheet("synthetic-id", 7))
                self.assertEqual((candidates.question_count, candidates.answer_item_count), (2, 3))
                self.assertEqual(len(service.calls), 1)
                self.assertEqual([i.normalized_subnumber for i in candidates.questions[0].items], [1, 2])

    def test_catalog_and_snapshot_handoff_retains_literals_and_no_source_fields(self):
        path = Path(__file__).parents[2] / "specs/001-guided-notes/contracts/examples.json"
        examples = json.loads(path.read_text(encoding="utf-8"))
        catalog = validate_catalog(examples["catalog"])
        case = next(c for c in examples["cases"] if c["name"] == "literal_text_preserved")
        result = validate_snapshot(case["snapshot"], catalog, activity_id="activity-demo")
        self.assertEqual(result["units"][0]["answers"][0]["answer_text"], "=SUM(1,2)")
        self.assertNotIn("answer_range", json.dumps(catalog))
        # This proves DTO exchange only, not publication, trusted ownership, or settlement.
