from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools import pilot_custom_contracts as qa


class CustomContractSourceQATest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = qa.load(qa.MANIFEST)
        cls.seed = qa.load(qa.SEED)
        cls.published = qa.load(qa.PUBLISHED)

    def check(self, manifest):
        return qa.validate(manifest, self.seed, self.published)

    def test_five_canonical_notion_lesson_contracts_only(self):
        self.assertEqual(self.check(self.manifest), [])
        self.assertEqual(len(self.manifest["entries"]), 5)
        by_uid = {r["pb_uid"]: r for r in self.manifest["entries"]}
        self.assertEqual(by_uid["PB-160"]["assessment"], "LEARNING_ONLY")
        self.assertEqual(by_uid["PB-164"]["grade_route"], "RESPONSE_FIRST_READING_RUBRIC")
        self.assertEqual(by_uid["PB-165"]["grade_route"], "BUG_REPAIR_RUBRIC")
        self.assertEqual(by_uid["PB-169"]["grade_route"], "HOSTED_CUSTOM_OJ_PLUS_METHOD_REVIEW")
        for x in self.manifest["entries"]:
            self.assertEqual(x["source_review_status"], "LESSON_CONTRACT_REVIEWED_TASK_INSTANCE_PENDING")
            self.assertFalse(x["task_statement_retrieved"])
            self.assertFalse(x["ai_approved"])
            self.assertFalse(x["learner_attempt_observed"])
            self.assertFalse(x["learner_evidence_written"])
            self.assertFalse(x["local_test_center_eligible"])
            self.assertTrue(qa.PRE_ATTEMPT_BANS[x["pb_uid"]].issubset(set(x["pre_attempt_forbidden"])))

    def test_pre_attempt_comparator_or_bug_disclosure_is_blocked(self):
        bad = copy.deepcopy(self.manifest)
        row = next(x for x in bad["entries"] if x["pb_uid"] == "PB-169")
        row["pre_attempt_disclosure"].append("stable_sort_choice")
        self.assertTrue(any("spoiler policy" in e for e in self.check(bad)))
        bad = copy.deepcopy(self.manifest)
        row = next(x for x in bad["entries"] if x["pb_uid"] == "PB-165")
        row["pre_attempt_forbidden"].remove("bug_location")
        self.assertTrue(any("spoiler policy" in e for e in self.check(bad)))

    def test_reading_and_implementation_gate_tracks_cannot_be_swapped(self):
        bad = copy.deepcopy(self.manifest)
        row = next(x for x in bad["entries"] if x["pb_uid"] == "PB-164")
        row["track"] = "Implementation"
        self.assertTrue(any("track" in e for e in self.check(bad)))
        bad = copy.deepcopy(self.manifest)
        row = next(x for x in bad["entries"] if x["pb_uid"] == "PB-165")
        row["grade_route"] = "EXACT_OUTPUT"
        self.assertTrue(any("grade_route" in e for e in self.check(bad)))

    def test_missing_debug_regression_artifact_cannot_pass(self):
        bad = copy.deepcopy(self.manifest)
        row = next(x for x in bad["entries"] if x["pb_uid"] == "PB-165")
        row["required_artifacts"].remove("regression_tests_at_least_3")
        self.assertTrue(any("required_artifacts" in e for e in self.check(bad)))

    def test_cannot_claim_fully_verified_task_or_l1_approval(self):
        bad = copy.deepcopy(self.manifest)
        bad["status"] = "TEACHING_READY"
        bad["learner_visibility"] = "PUBLISHED"
        row = bad["entries"][0]
        row["task_statement_retrieved"] = True
        row["ai_approved"] = True
        row["testcases_status"] = "OFFICIAL_VERIFIED"
        row["learner_evidence_written"] = True
        row["official_sample"] = [{"input": "1", "output": "2"}]
        errors = self.check(bad)
        self.assertGreaterEqual(len(errors), 5)
        self.assertTrue(any("task-level verification" in e for e in errors))
        self.assertTrue(any("forbidden answer/evidence/testcase" in e for e in errors))

    def test_explicit_gate_status_preserved_for_guided_vs_core(self):
        bad = copy.deepcopy(self.manifest)
        row = next(x for x in bad["entries"] if x["pb_uid"] == "PB-160")
        row["gate_candidate"] = True
        row["assessment"] = "GATE_CANDIDATE_CONDITIONAL"
        errors = self.check(bad)
        self.assertTrue(any("Gate" in e or "gate_candidate" in e for e in errors))

    def test_cli_never_requires_api_or_mutates_runtime(self):
        result = subprocess.run(
            [sys.executable, str(qa.ROOT / "tools" / "pilot_custom_contracts.py")],
            cwd=qa.ROOT, text=True, capture_output=True, check=False, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("CUSTOM CONTRACT PASS", result.stdout)


if __name__ == "__main__":
    unittest.main()
