"""Offline format-contract tests; no Flask, Google account, or network required."""
import copy
import json
from pathlib import Path
import unittest

from guided_notes.notes.recognition import RecognitionError, recognize


FIXTURES = Path(__file__).parents[1] / "fixtures" / "sheets_layouts.json"


class RecognitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layouts = json.loads(FIXTURES.read_text(encoding="utf-8"))

    def test_single_preserves_merged_answer_and_formula(self):
        result = recognize(self.layouts["single"])
        self.assertEqual((result.question_count, result.answer_item_count), (1, 1))
        item = result.questions[0].items[0]
        self.assertEqual(item.answer_range.anchor, (4, 5))
        self.assertEqual(item.answer_range.end_column, 7)
        self.assertEqual(item.observed_user_value, {"formulaValue": "=1+1"})
        self.assertIsNone(item.subitem_label)

    def test_mixed_question_set_and_single(self):
        result = recognize(self.layouts["mixed"])
        self.assertEqual((result.question_count, result.answer_item_count), (2, 3))
        question = result.questions[0]
        self.assertEqual(question.kind, "question_set")
        self.assertEqual([i.normalized_subnumber for i in question.items], [1, 2])
        self.assertEqual([i.subitem_label for i in question.items], ["(1)", "（2）"])
        self.assertEqual([i.answer_range.anchor for i in question.items], [(4, 6), (5, 6)])
        self.assertEqual(result.questions[1].display_number, "2")

    def test_moved_griddata_and_wider_answers(self):
        result = recognize(self.layouts["moved"])
        self.assertEqual((result.question_count, result.answer_item_count), (2, 3))
        self.assertEqual(result.questions[0].items[1].answer_range.anchor, (8, 8))
        self.assertEqual(result.questions[0].items[1].answer_range.end_column, 11)

    def test_input_not_mutated_and_values_not_shared(self):
        payload = copy.deepcopy(self.layouts["single"])
        original = copy.deepcopy(payload)
        result = recognize(payload)
        result.questions[0].items[0].observed_user_value["formulaValue"] = "changed"
        self.assertEqual(payload, original)

    def test_invalid_layouts_report_locatable_errors(self):
        cases = {
            "missing_header": "HEADER_MISSING",
            "duplicate_header": "HEADER_AMBIGUOUS",
            "duplicate_question": "DUPLICATE_QUESTION",
            "duplicate_subitem": "DUPLICATE_SUBITEM",
            "answer_overlap": "ANSWER_OVERLAP",
            "ambiguous_answer": "ANSWER_AMBIGUOUS",
        }
        for name, code in cases.items():
            with self.subTest(name=name), self.assertRaises(RecognitionError) as caught:
                recognize(self.layouts[name])
            self.assertIn(code, [issue.code for issue in caught.exception.issues])
            self.assertTrue(all(i.sheet_id == 7 for i in caught.exception.issues))

    def test_number_normalization_detects_duplicate(self):
        payload = copy.deepcopy(self.layouts["mixed"])
        payload["data"][0]["rowData"][7]["values"][1] = {
            "userEnteredValue": {"stringValue": "01"}, "formattedValue": "01"
        }
        with self.assertRaises(RecognitionError) as caught:
            recognize(payload)
        self.assertIn("DUPLICATE_QUESTION", [i.code for i in caught.exception.issues])

    def test_unmerged_single_blank_is_valid(self):
        from importlib.util import module_from_spec, spec_from_file_location
        spec = spec_from_file_location("fixture_builder", FIXTURES.with_name("build_layouts.py"))
        builder = module_from_spec(spec)
        spec.loader.exec_module(builder)
        payload = builder.layout(width=1)
        payload["merges"] = [m for m in payload["merges"] if not (
            m["startRowIndex"] == 4 and m["startColumnIndex"] == 5)]
        result = recognize(payload)
        self.assertEqual(result.questions[0].items[0].answer_range.end_column, 6)

    def test_blank_tail_not_returned_by_google_is_recognized(self):
        result = recognize(self.layouts["mixed"])
        self.assertEqual(result.questions[0].items[1].observed_user_value, {})

    def test_prompt_change_preserved_for_later_semantic_validation(self):
        payload = copy.deepcopy(self.layouts["mixed"])
        payload["data"][0]["rowData"][5]["values"][2] = {
            "userEnteredValue": {"stringValue": "不同題目\r\n保留 空白 "}}
        result = recognize(payload)
        self.assertEqual(result.questions[0].items[1].prompt_text, "不同題目\n保留 空白 ")

    def test_unmapped_group_row_is_rejected(self):
        payload = copy.deepcopy(self.layouts["mixed"])
        payload["merges"][3]["endRowIndex"] = 7
        with self.assertRaises(RecognitionError):
            recognize(payload)

    def test_overlapping_merges_are_rejected(self):
        payload = copy.deepcopy(self.layouts["single"])
        payload["merges"].append(copy.deepcopy(payload["merges"][-1]))
        with self.assertRaises(RecognitionError) as caught:
            recognize(payload)
        self.assertEqual(caught.exception.issues[0].code, "ANSWER_OVERLAP")


if __name__ == "__main__":
    unittest.main()
