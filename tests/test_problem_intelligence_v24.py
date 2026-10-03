from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.problem_intelligence import (
    CLASS_CANDIDATE,
    CLASS_NEEDS_QA,
    CLASS_UNCLASSIFIED,
    L0_INDEXED,
    L1_CLASSIFIED,
    ProblemIntelligenceError,
    ProblemIntelligenceStore,
    normalize_problem_url,
)


class ProblemIntelligenceV24Test(unittest.TestCase):
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
        self.assertEqual(identity.key, "zerojudge:d050")

    def test_unsupported_source_fails_closed(self):
        with self.assertRaisesRegex(
            ProblemIntelligenceError,
            "只支援 ZeroJudge",
        ):
            normalize_problem_url(
                "https://cses.fi/problemset/task/1669"
            )

    def test_import_single_and_batch_deduplicates_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            store = ProblemIntelligenceStore(Path(temp))

            first = store.import_urls(
                [
                    "https://zerojudge.tw/ShowProblem?problemid=d050",
                    "https://www.zerojudge.tw/ShowProblem?problemid=D050",
                    "zerojudge.tw/ShowProblem?problemid=a001",
                ]
            )

            self.assertEqual(
                first.added,
                ("zerojudge:d050", "zerojudge:a001"),
            )
            self.assertEqual(
                first.existing,
                ("zerojudge:d050",),
            )
            self.assertEqual(first.errors, ())

            second = store.import_urls(
                [
                    "https://zerojudge.tw/ShowProblem?problemid=d050",
                ]
            )
            self.assertEqual(second.added, ())
            self.assertEqual(
                second.existing,
                ("zerojudge:d050",),
            )

            self.assertEqual(
                len(store.all_paths()),
                2,
            )
            self.assertEqual(
                store.validate_all(),
                [],
            )

    def test_invalid_item_does_not_create_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            store = ProblemIntelligenceStore(Path(temp))

            result = store.import_urls(
                [
                    "https://zerojudge.tw/ShowProblem?problemid=d050",
                    "https://example.com/problem/1",
                ]
            )

            self.assertEqual(
                result.added,
                ("zerojudge:d050",),
            )
            self.assertEqual(len(result.errors), 1)
            self.assertEqual(
                len(store.all_paths()),
                1,
            )

    def test_l0_record_is_unclassified_and_not_runtime_eligible(self):
        with tempfile.TemporaryDirectory() as temp:
            store = ProblemIntelligenceStore(Path(temp))
            store.import_urls(
                [
                    "https://zerojudge.tw/ShowProblem?problemid=d050",
                ]
            )

            record = store.load("zerojudge", "d050")

            self.assertEqual(record["lifecycle"], L0_INDEXED)
            self.assertEqual(
                record["classification"]["status"],
                CLASS_UNCLASSIFIED,
            )
            self.assertIs(
                record["integration"]["runtime_eligible"],
                False,
            )
            self.assertEqual(
                record["integration"]["problem_bank_status"],
                "UNLINKED",
            )
            self.assertIsNone(
                record["integration"]["pb_uid"],
            )

    def test_source_metadata_can_be_added_without_promoting_problem(self):
        with tempfile.TemporaryDirectory() as temp:
            store = ProblemIntelligenceStore(Path(temp))
            store.import_urls(
                [
                    "https://zerojudge.tw/ShowProblem?problemid=d050",
                ]
            )

            record = store.update_source_metadata(
                "zerojudge",
                "d050",
                {
                    "title": "妳那邊幾點",
                    "statement_summary": "依時差轉換時間。",
                    "constraints": [
                        "輸入為合法整數時間",
                    ],
                    "metadata_source": "AI_EXTRACTED_FROM_SOURCE",
                },
            )

            self.assertEqual(
                record["source_metadata"]["title"],
                "妳那邊幾點",
            )
            self.assertEqual(
                record["lifecycle"],
                L0_INDEXED,
            )
            self.assertIs(
                record["integration"]["runtime_eligible"],
                False,
            )

    def test_high_confidence_complete_classification_becomes_candidate(self):
        with tempfile.TemporaryDirectory() as temp:
            store = ProblemIntelligenceStore(Path(temp))
            store.import_urls(
                [
                    "https://zerojudge.tw/ShowProblem?problemid=d050",
                ]
            )

            record = store.apply_classification(
                "zerojudge",
                "d050",
                {
                    "confidence": 0.93,
                    "primary_skill_candidate": "S01_IO",
                    "supporting_skill_candidates": [
                        "S03_Conditionals",
                    ],
                    "difficulty_candidate": "D1",
                    "prerequisite_candidates": [
                        "S01_IO",
                    ],
                    "expected_complexity_candidate": "O(1)",
                    "role_candidate": "Guided Drill",
                    "alternate_solution_risk_candidate": "Low",
                    "evidence_suitability_candidate": "Both",
                    "rationale": "主要考輸入、輸出與簡單時間轉換。",
                    "classification_source": "AI_CANDIDATE",
                },
            )

            self.assertEqual(record["lifecycle"], L1_CLASSIFIED)
            self.assertEqual(
                record["classification"]["status"],
                CLASS_CANDIDATE,
            )
            self.assertEqual(
                record["classification"]["qa_reasons"],
                [],
            )
            self.assertIs(
                record["integration"]["runtime_eligible"],
                False,
            )

    def test_low_confidence_classification_becomes_needs_qa(self):
        with tempfile.TemporaryDirectory() as temp:
            store = ProblemIntelligenceStore(Path(temp))
            store.import_urls(
                [
                    "https://zerojudge.tw/ShowProblem?problemid=a001",
                ]
            )

            record = store.apply_classification(
                "zerojudge",
                "a001",
                {
                    "confidence": 0.55,
                    "primary_skill_candidate": "S01_IO",
                    "difficulty_candidate": "D1",
                    "classification_source": "AI_CANDIDATE",
                },
            )

            self.assertEqual(
                record["classification"]["status"],
                CLASS_NEEDS_QA,
            )
            self.assertTrue(
                any(
                    "0.80" in reason
                    for reason in record["classification"]["qa_reasons"]
                )
            )

    def test_ambiguity_forces_needs_qa_even_with_high_confidence(self):
        with tempfile.TemporaryDirectory() as temp:
            store = ProblemIntelligenceStore(Path(temp))
            store.import_urls(
                [
                    "https://zerojudge.tw/ShowProblem?problemid=a693",
                ]
            )

            record = store.apply_classification(
                "zerojudge",
                "a693",
                {
                    "confidence": 0.95,
                    "primary_skill_candidate": "S11_Prefix_Sum",
                    "difficulty_candidate": "D2",
                    "ambiguity_notes": [
                        "需要確認主要教學目標是否應放在前綴和而非陣列操作"
                    ],
                },
            )

            self.assertEqual(
                record["classification"]["status"],
                CLASS_NEEDS_QA,
            )
            self.assertTrue(
                record["classification"]["qa_reasons"],
            )

    def test_ai_classification_cannot_smuggle_publish_fields(self):
        with tempfile.TemporaryDirectory() as temp:
            store = ProblemIntelligenceStore(Path(temp))
            store.import_urls(
                [
                    "https://zerojudge.tw/ShowProblem?problemid=d050",
                ]
            )

            with self.assertRaisesRegex(
                ProblemIntelligenceError,
                "未知欄位",
            ):
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

    def test_tampered_runtime_eligible_record_fails_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            store = ProblemIntelligenceStore(data_dir)
            store.import_urls(
                [
                    "https://zerojudge.tw/ShowProblem?problemid=d050",
                ]
            )

            path = data_dir / "zerojudge" / "d050.json"
            record = json.loads(
                path.read_text(encoding="utf-8")
            )
            record["integration"]["runtime_eligible"] = True
            path.write_text(
                json.dumps(
                    record,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            errors = store.validate_all()
            self.assertEqual(len(errors), 1)
            self.assertIn(
                "不得直接成為 runtime eligible",
                errors[0],
            )

    def test_external_id_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            store = ProblemIntelligenceStore(Path(temp))

            with self.assertRaisesRegex(
                ProblemIntelligenceError,
                "problemid 格式不合法",
            ):
                store.load(
                    "zerojudge",
                    "../secret",
                )


if __name__ == "__main__":
    unittest.main()
