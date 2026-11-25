import copy
import json
from pathlib import Path
import unittest

from guided_notes.notes.models import ContractError, validate_snapshot


class SnapshotContractTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).parents[2] / "specs/001-guided-notes/contracts/examples.json"
        self.examples = json.loads(path.read_text(encoding="utf-8"))
        self.catalog = self.examples["catalog"]
        self.snapshot = copy.deepcopy(self.examples["cases"][0]["snapshot"])

    def test_all_seven_shared_examples(self):
        for case in self.examples["cases"]:
            with self.subTest(case=case["name"]):
                if case["expected"] == "RESULT_INVALID":
                    with self.assertRaises(ContractError) as caught:
                        validate_snapshot(case["snapshot"], self.catalog, activity_id="activity-demo")
                    self.assertEqual(caught.exception.code, "RESULT_INVALID")
                else:
                    self.assertEqual(validate_snapshot(case["snapshot"], self.catalog,
                        activity_id="activity-demo"), case["snapshot"])

    def test_wrong_activity_unended_and_wrong_result_version(self):
        for changes, expected in (({"activity_id": "other"}, "RESULT_INVALID"),
                                  ({"ended": False}, "ACTIVITY_NOT_ENDED"),
                                  ({"result_version": "other"}, "RESULT_VERSION_CHANGED")):
            with self.subTest(changes=changes), self.assertRaises(ContractError) as caught:
                validate_snapshot({**self.snapshot, **changes}, self.catalog,
                                  activity_id="activity-demo", result_version="result-demo-v1")
            self.assertEqual(caught.exception.code, expected)

    def test_missing_extra_duplicate_and_blank_answers(self):
        mutations = [
            lambda s: s["units"].pop(),
            lambda s: s["units"][0]["answers"].append(copy.deepcopy(s["units"][0]["answers"][0])),
            lambda s: s["units"][0]["answers"][0].update(blank_id=s["units"][1]["answers"][0]["blank_id"]),
            lambda s: s["units"][0]["answers"][0].update(answer_text=" \n\t"),
            lambda s: s["units"][0]["answers"][0].update(answer_text=1),
            lambda s: s["units"][0].update(no_winner=True),
            lambda s: s["units"][0].update(no_winner=0),
        ]
        for mutation in mutations:
            snapshot = copy.deepcopy(self.snapshot)
            mutation(snapshot)
            with self.subTest(mutation=mutation), self.assertRaises(ContractError):
                validate_snapshot(snapshot, self.catalog, activity_id="activity-demo")

    def test_answer_whitespace_and_matching_optional_winner_are_preserved(self):
        answer = self.snapshot["units"][0]["answers"][0]
        answer.update(answer_text=" 001\n中文 ", winner_group_id="group-A")
        result = validate_snapshot(self.snapshot, self.catalog, activity_id="activity-demo")
        self.assertEqual(result["units"][0]["answers"][0]["answer_text"], " 001\n中文 ")

    def test_result_does_not_silently_accept_secrets(self):
        self.snapshot["token"] = "secret"
        with self.assertRaises(ContractError) as caught:
            validate_snapshot(self.snapshot, self.catalog, activity_id="activity-demo")
        self.assertNotIn("secret", str(caught.exception))
