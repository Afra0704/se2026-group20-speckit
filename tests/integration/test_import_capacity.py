import time
import tracemalloc
import unittest

from guided_notes.notes.import_service import build_import_bundle
from guided_notes.notes.recognition import recognize
from guided_notes.notes.export_service import build_export_preview, prepare_writes
from guided_notes.notes.sheets_gateway import SheetsGateway


def capacity_sheet(main_count=100, item_count=10):
    rows = [{"values": [{"userEnteredValue": {"stringValue": "題號"}},
                        {"userEnteredValue": {"stringValue": "題目"}},
                        {"userEnteredValue": {"stringValue": "作答"}}]}]
    merges = [{"sheetId": 7, "startRowIndex": 0, "endRowIndex": 1,
               "startColumnIndex": 2, "endColumnIndex": 4}]
    for number in range(1, main_count + 1):
        start = len(rows)
        merges.append({"sheetId": 7, "startRowIndex": start, "endRowIndex": start + item_count,
                       "startColumnIndex": 0, "endColumnIndex": 1})
        for sub in range(1, item_count + 1):
            values = [{"userEnteredValue": {"numberValue": number}} if sub == 1 else {},
                      {"userEnteredValue": {"stringValue": f"題目 {number}-{sub}"}},
                      {"userEnteredValue": {"stringValue": f"({sub})"}}]
            rows.append({"values": values})
    return {"properties": {"sheetId": 7}, "data": [{"rowData": rows}], "merges": merges}


class CapacityTests(unittest.TestCase):
    def test_hundred_questions_ten_items_each(self):
        tracemalloc.start()
        self.addCleanup(tracemalloc.stop)
        start = time.perf_counter()
        result = recognize(capacity_sheet())
        bundle = build_import_bundle("synthetic", result)
        catalog = bundle.catalog
        self.assertEqual((result.question_count, result.answer_item_count), (100, 1000))
        self.assertEqual(len({i["blank_id"] for q in catalog["questions"] for i in q["items"]}), 1000)
        snapshot = {"contract_version": 1, "activity_id": "capacity", "result_version": "r1", "ended": True,
            "import_id": catalog["import_id"], "import_version": 1, "units": [
                {"question_id": q["question_id"], "winner_group_id": "group-A", "no_winner": False,
                 "answers": [{"item_id": i["item_id"], "blank_id": i["blank_id"], "answer_text": "literal"}
                             for i in q["items"]]} for q in catalog["questions"]]}
        preview = build_export_preview(bundle, result, snapshot, activity_id="capacity")
        batches = prepare_writes(preview, result, snapshot, activity_id="capacity", overwrite_item_ids=[])
        self.assertEqual([len(batch) for batch in batches], [10] * 100)
        class CountingService:
            calls = 0

            def spreadsheets(self):
                return self

            def values(self):
                return self

            def batchUpdateByDataFilter(self, **kwargs):
                self.calls += 1
                assert len(kwargs["body"]["data"]) == 10
                return self

            def execute(self, num_retries):
                assert num_retries == 0
                return {}
        service = CountingService()
        gateway = SheetsGateway(service)
        for batch in batches:
            gateway.write_unit("synthetic", 7, batch)
        self.assertEqual(service.calls, 100)
        _, peak = tracemalloc.get_traced_memory()
        print(f"\nCapacity observation: 100 questions / 1000 items in {time.perf_counter() - start:.3f}s; peak {peak / 1024 / 1024:.2f} MiB")
