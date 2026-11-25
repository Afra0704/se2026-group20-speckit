import copy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

from guided_notes.notes.sheets_gateway import AnchorWrite, GatewayError, SheetsGateway, parse_sheets_url


class FakeService:
    """Records official-client requests and scripted responses without network."""
    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.calls = []
        self.retry_options = []

    def spreadsheets(self):
        return self

    def get(self, **kwargs):
        return self.request("get", kwargs)

    def getByDataFilter(self, **kwargs):
        return self.request("getByDataFilter", kwargs)

    def values(self):
        return self

    def batchUpdateByDataFilter(self, **kwargs):
        return self.request("batchUpdateByDataFilter", kwargs)

    def request(self, method, kwargs):
        self.calls.append((method, copy.deepcopy(kwargs)))
        return self

    def execute(self, num_retries):
        self.retry_options.append(num_retries)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return copy.deepcopy(outcome)


class HttpFailure(Exception):
    def __init__(self, status):
        self.resp = SimpleNamespace(status=status)
        super().__init__("SECRET_TOKEN and raw student answers")


class GatewayTests(unittest.TestCase):
    def test_standard_url_and_zero_gid(self):
        self.assertEqual(parse_sheets_url("https://docs.google.com/spreadsheets/d/abc_123-xyz/edit?gid=0"),
                         ("abc_123-xyz", 0))
        self.assertEqual(parse_sheets_url("https://docs.google.com/spreadsheets/d/abc/edit#gid=7"), ("abc", 7))
        self.assertEqual(parse_sheets_url("https://docs.google.com/spreadsheets/d/abc/edit?gid=7#gid=7"), ("abc", 7))

    def test_reject_arbitrary_urls_and_conflicting_gid(self):
        for url in ("http://docs.google.com/spreadsheets/d/abc/edit", "https://evil.test/abc",
                    "https://docs.google.com.evil.test/spreadsheets/d/abc/edit",
                    "https://user@docs.google.com/spreadsheets/d/abc/edit",
                    "https://docs.google.com:443/spreadsheets/d/abc/edit",
                    "https://docs.google.com/spreadsheets/d/abc/edit?gid=x",
                    "https://docs.google.com/spreadsheets/d/abc/edit?gid=1#gid=2",
                    "https://docs.google.com/spreadsheets/d/abc/edit?gid=1&gid=1", None):
            with self.subTest(url=url), self.assertRaises(GatewayError):
                parse_sheets_url(url)

    def test_list_sheets_exposes_only_identity_and_title(self):
        service = FakeService({"sheets": [{"properties": {"sheetId": 0, "title": "學習單", "hidden": False}}]})
        gateway = SheetsGateway(service)
        self.assertEqual(gateway.list_worksheets("abc"), [{"sheet_id": 0, "title": "學習單"}])
        self.assertEqual(service.calls[0][0], "get")
        self.assertNotIn("data", service.calls[0][1]["fields"])

    def test_read_uses_numeric_sheet_id_and_explicit_grid_fields(self):
        fixtures = Path(__file__).parents[1] / "fixtures/sheets_layouts.json"
        sheet = json.loads(fixtures.read_text(encoding="utf-8"))["moved"]
        service = FakeService({"sheets": [sheet]})
        self.assertEqual(SheetsGateway(service).read_sheet("abc", 7), sheet)
        method, args = service.calls[0]
        self.assertEqual(method, "getByDataFilter")
        self.assertEqual(args["body"]["dataFilters"], [{"gridRange": {"sheetId": 7}}])
        for field in ("startRow", "startColumn", "userEnteredValue", "formattedValue", "userEnteredFormat", "merges"):
            self.assertIn(field, args["fields"])
        depth = 0
        for character in args["fields"]:
            depth += (character == "(") - (character == ")")
            self.assertGreaterEqual(depth, 0, "invalid Google fields mask")
        self.assertEqual(depth, 0, "invalid Google fields mask")
        self.assertEqual(service.retry_options, [0])

    def test_read_missing_sheet_is_not_empty_success(self):
        with self.assertRaises(GatewayError) as caught:
            SheetsGateway(FakeService({"sheets": []})).read_sheet("abc", 7)
        self.assertEqual(caught.exception.code, "SOURCE_NOT_FOUND")

    def test_read_retries_are_bounded_with_injected_clock(self):
        service = FakeService(HttpFailure(429), HttpFailure(503), {"sheets": []})
        delays = []
        gateway = SheetsGateway(service, sleep=delays.append, jitter=lambda: 0.25)
        self.assertEqual(gateway.list_worksheets("abc"), [])
        self.assertEqual(delays, [1.25, 2.25])
        self.assertEqual(service.retry_options, [0, 0, 0])

    def test_permission_errors_do_not_retry_or_expose_payload(self):
        for status, code in ((403, "SOURCE_READ_FORBIDDEN"), (401, "GOOGLE_REAUTH_REQUIRED"),
                             (404, "SOURCE_NOT_FOUND")):
            service = FakeService(HttpFailure(status))
            with self.subTest(status=status), self.assertRaises(GatewayError) as caught:
                SheetsGateway(service).read_sheet("abc", 7)
            self.assertEqual(caught.exception.code, code)
            self.assertNotIn("SECRET", str(caught.exception))
            self.assertEqual(len(service.calls), 1)

    def test_retry_exhaustion(self):
        service = FakeService(HttpFailure(503), HttpFailure(503), HttpFailure(503))
        with self.assertRaises(GatewayError) as caught:
            SheetsGateway(service, sleep=lambda _: None).list_worksheets("abc")
        self.assertEqual(caught.exception.code, "SOURCE_READ_UNAVAILABLE")
        self.assertEqual(len(service.calls), 3)

    def test_invalid_sheet_id_fails_before_request(self):
        service = FakeService()
        for sheet_id in (True, -1, "7", None):
            with self.subTest(sheet_id=sheet_id), self.assertRaises(GatewayError):
                SheetsGateway(service).read_sheet("abc", sheet_id)
        self.assertEqual(service.calls, [])

    def test_whole_question_set_uses_one_raw_anchor_only_request(self):
        service = FakeService({"totalUpdatedCells": 2})
        gateway = SheetsGateway(service)
        writes = [AnchorWrite("question-1", 4, 6, "=SUM(1,2)"),
                  AnchorWrite("question-1", 5, 6, "001\n中文")]
        self.assertIsNone(gateway.write_unit("abc", 7, writes))
        self.assertEqual(len(service.calls), 1)
        method, args = service.calls[0]
        self.assertEqual(method, "batchUpdateByDataFilter")
        self.assertEqual(args["body"]["valueInputOption"], "RAW")
        data = args["body"]["data"]
        self.assertEqual([i["values"] for i in data], [[["=SUM(1,2)"]], [["001\n中文"]]])
        self.assertEqual(data[0]["dataFilter"]["gridRange"], {"sheetId": 7,
            "startRowIndex": 4, "endRowIndex": 5, "startColumnIndex": 6, "endColumnIndex": 7})
        self.assertEqual(service.retry_options, [0])

    def test_mixed_units_duplicate_anchors_or_nontext_never_write(self):
        invalid = [[], [AnchorWrite("q1", 4, 6, "A"), AnchorWrite("q2", 5, 6, "B")],
                   [AnchorWrite("q1", 4, 6, "A"), AnchorWrite("q1", 4, 6, "B")],
                   [AnchorWrite("q1", -1, 6, "A")], [AnchorWrite("q1", 4, 6, 42)],
                   [AnchorWrite("q1", True, 6, "A")], [AnchorWrite("q1", 4, 6, " \n")]]
        service = FakeService()
        for writes in invalid:
            with self.subTest(writes=writes), self.assertRaises(GatewayError):
                SheetsGateway(service).write_unit("abc", 7, writes)
        self.assertEqual(service.calls, [])

    def test_uncertain_writes_never_retry_and_never_claim_verified(self):
        for error in (TimeoutError("SECRET"), HttpFailure(503), HttpFailure(500)):
            service = FakeService(error)
            with self.subTest(error=type(error).__name__), self.assertRaises(GatewayError) as caught:
                SheetsGateway(service).write_unit("abc", 7, [AnchorWrite("q1", 4, 6, "A")])
            self.assertEqual(caught.exception.write_outcome, "unknown")
            self.assertEqual(len(service.calls), 1)
            self.assertNotIn("SECRET", str(caught.exception))

    def test_rejected_writes_fail_without_retry(self):
        for status in (400, 401, 403, 404, 429):
            service = FakeService(HttpFailure(status))
            with self.subTest(status=status), self.assertRaises(GatewayError) as caught:
                SheetsGateway(service).write_unit("abc", 7, [AnchorWrite("q1", 4, 6, "A")])
            self.assertEqual(caught.exception.write_outcome, "failed")
            self.assertEqual(len(service.calls), 1)

    def test_readback_distinguishes_formula_number_and_literal_text(self):
        sheet = {"properties": {"sheetId": 7}, "data": [{"startRow": 4, "startColumn": 6,
            "rowData": [{"values": [{"userEnteredValue": {"formulaValue": "=1+1"}, "formattedValue": "2"}]},
                        {"values": [{"userEnteredValue": {"numberValue": 2}, "formattedValue": "2"}]},
                        {"values": [{"userEnteredValue": {"stringValue": "002"}}]}]}]}
        service = FakeService({"sheets": [sheet]})
        values = SheetsGateway(service).read_anchor_values("abc", 7, [(4, 6), (5, 6), (6, 6), (7, 6)])
        self.assertEqual(values, {(4, 6): {"formulaValue": "=1+1"}, (5, 6): {"numberValue": 2},
                                 (6, 6): {"stringValue": "002"}, (7, 6): {}})
