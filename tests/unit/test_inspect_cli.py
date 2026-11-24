import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from guided_notes.notes.cli import main


class InspectCliTests(unittest.TestCase):
    def test_inspection_is_read_only_and_hides_question_and_original_values(self):
        fixtures = json.loads((Path(__file__).parents[1] / "fixtures/sheets_layouts.json").read_text(encoding="utf-8"))
        gateway = Mock()
        gateway.read_sheet.return_value = fixtures["mixed"]
        output = io.StringIO()
        with patch("guided_notes.notes.cli.authorize") as auth, patch(
                "guided_notes.notes.sheets_gateway.build_google_service"), patch(
                "guided_notes.notes.sheets_gateway.SheetsGateway", return_value=gateway), redirect_stdout(output):
            code = main(["inspect-sheet", "--url", "https://docs.google.com/spreadsheets/d/synthetic/edit#gid=7"])
        self.assertEqual(code, 0)
        data = json.loads(output.getvalue())
        self.assertEqual((data["question_count"], data["answer_item_count"]), (2, 3))
        self.assertTrue(data["read_only"])
        self.assertNotIn("interactive", auth.call_args.kwargs)
        gateway.write_unit.assert_not_called()
        self.assertEqual([call[0] for call in gateway.method_calls], ["read_sheet"])
        self.assertNotIn("prompt_text", output.getvalue())
        self.assertNotIn("userEnteredValue", output.getvalue())

    def test_missing_gid_fails_before_loading_credentials(self):
        with patch("guided_notes.notes.cli.authorize") as auth, redirect_stdout(io.StringIO()):
            code = main(["inspect-sheet", "--url", "https://docs.google.com/spreadsheets/d/synthetic/edit"])
        self.assertEqual(code, 1)
        auth.assert_not_called()

    def test_invalid_url_fails_before_loading_credentials(self):
        with patch("guided_notes.notes.cli.authorize") as auth, redirect_stdout(io.StringIO()):
            code = main(["inspect-sheet", "--url", "https://example.com/"])
        self.assertEqual(code, 1)
        auth.assert_not_called()
