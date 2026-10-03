from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.problem_intelligence import (
    CANDIDATE,
    L0,
    L1,
    NEEDS_QA,
    UNCLASSIFIED,
    ProblemIntelligenceError,
    ProblemIntelligenceStore,
    normalize_problem_url,
)


class ProblemIntelligenceV24Test(unittest.TestCase):
    def make_store(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return ProblemIntelligenceStore(Path(temp.name))

    def import_one(self, store, problem_id="d050"):
        result = store.import_urls(
            [f"https://zerojudge.tw/ShowProblem?problemid={problem_id}"]
        )
        self.assertEqual(result.errors, ())
        return result

    def test_zerojudge_url_normalizes_to_stable_identity(self):
        identity = normalize_problem_url(
            "HTTP://WWW.ZEROJUDGE.TW/ShowProblem?problemid=D050&utm_source=x"
        )
        self.assertEqual(identity.source, "zerojudge")
        self.assertEqual(identity.external_id, "d050")
        self.assertEqual(
            identity.canonical_url,
            "https://zerojudge.tw/ShowProblem?problemid=d050",
        )

    def test_unsupported_source_fails_closed(self):
        with self.assertRaisesRegex(ProblemIntelligenceError, "只支援 ZeroJudge"):
            normalize_problem_url("https://cses.fi/problemset/task/1669")

    def test_batch_import_deduplicates_variants(self):
        store = self.make_store()
        result = store.import_urls(
            [
                "https://zerojudge.tw/ShowProblem?problemid=d050",
                "https://www.zerojudge.tw/ShowProblem?problemid=D050",
                "zerojudge.tw/ShowProblem?problemid=a001",
            ]
        )
        self.assertEqual(result.added, ("zerojudge:d050", "zerojudge:a001"))
        self.assertEqual(result.existing, ("zerojudge:d050",))
        self.assertEqual(result.errors, ())
        self.assertEqual(len(store.all_paths()), 2)
        self.assertEqual(store.validate_all(), [])

    def test_invalid_batch_item_fails_only_that_item(self):
        store = self.make_store()
        result = store.import_urls(
            [
                "https://zerojudge.tw/ShowProblem?problemid=d050",
                "https://example.com/problem/1",
            ]
        )
        self.assertEqual(result.added, ("zerojudge:d050",))
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(len(store.all_paths()), 1)

    def test_l0_is_unclassified_and_never_runtime_eligible(self):
        store = self.make_store()
        self.import_one(store)
        record = store.load("zerojudge", "d050")
        self.assertEqual(record["lifecycle"], L0)
        self.assertEqual(record["classification"]["status"], UNCLASSIFIED)
        self.assertFalse(record["integration"]["runtime_eligible"])
        self.assertIsNone(record["integration"]["pb_uid"])

    def test_source_metadata_does_not_promote_problem(self):
        store = self.make_store()
        self.import_one(store)
        record = store.update_source_metadata(
            "zerojudge",
            "d050",
            {
                "title": "妳那邊幾點",
                "statement_summary": "依時差轉換時間。",
                "constraints": ["輸入為合法整數時間"],
                "metadata_source": "AI_EXTRACTED_FROM_SOURCE",
            },
        )
        self.assertEqual(record["source_metadata"]["title"], "妳那邊幾點")
        self.assertEqual(record["lifecycle"], L0)
        self.assertFalse(record["integration"]["runtime_eligible"])

    def test_complete_high_confidence_l1_becomes_candidate(self):
        store = self.make_store()
        self.import_one(store)
        record = store.apply_classification(
            "zerojudge",
            "d050",
            {
                "confidence": 0.93,
                "primary_skill_candidate": "S01_IO",
                "difficulty_candidate": "D1",
                "expected_complexity_candidate": "O(1)",
                "role_candidate": "Guided Drill",
                "alternate_solution_risk_candidate": "Low",
                "evidence_suitability_candidate": "Both",
                "rationale": "主要考輸入輸出與簡單時間轉換。",
            },
        )
        self.assertEqual(record["lifecycle"], L1)
        self.assertEqual(record["classification"]["status"], CANDIDATE)
        self.assertEqual(record["classification"]["qa_reasons"], [])
        self.assertFalse(record["integration"]["runtime_eligible"])

    def test_low_confidence_l1_fails_closed_to_needs_qa(self):
        store = self.make_store()
        self.import_one(store, "a001")
        record = store.apply_classification(
            "zerojudge",
            "a001",
            {
                "confidence": 0.55,
                "primary_skill_candidate": "S01_IO",
                "difficulty_candidate": "D1",
            },
        )
        self.assertEqual(record["classification"]["status"], NEEDS_QA)
        self.assertTrue(
            any("0.80" in x for x in record["classification"]["qa_reasons"])
        )

    def test_ambiguity_forces_needs_qa(self):
        store = self.make_store()
        self.import_one(store, "a693")
        record = store.apply_classification(
            "zerojudge",
            "a693",
            {
                "confidence": 0.95,
                "primary_skill_candidate": "S11_Prefix_Sum",
                "difficulty_candidate": "D2",
                "ambiguity_notes": ["需確認是否主要考前綴和"],
            },
        )
        self.assertEqual(record["classification"]["status"], NEEDS_QA)

    def test_ai_cannot_smuggle_publish_field(self):
        store = self.make_store()
        self.import_one(store)
        with self.assertRaisesRegex(ProblemIntelligenceError, "未知欄位"):
            store.apply_classification(
                "zerojudge",
                "d050",
                {
                    "confidence": 0.99,
                    "primary_skill_candidate": "S01_IO",
                    "difficulty_candidate": "D1",
                    "published": True,
                },
            )

    def test_tampered_runtime_eligible_fails_validation(self):
        store = self.make_store()
        self.import_one(store)
        path = store.all_paths()[0]
        record = json.loads(path.read_text(encoding="utf-8"))
        record["integration"]["runtime_eligible"] = True
        path.write_text(
            json.dumps(record, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        errors = store.validate_all()
        self.assertEqual(len(errors), 1)
        self.assertIn("不得直接成為 runtime eligible", errors[0])

    def test_external_id_path_traversal_is_rejected(self):
        store = self.make_store()
        with self.assertRaisesRegex(ProblemIntelligenceError, "problemid 格式不合法"):
            store.load("zerojudge", "../secret")


if __name__ == "__main__":
    unittest.main()
