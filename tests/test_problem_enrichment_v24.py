from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from tools.problem_enrichment import (
    AI_CANDIDATE,
    COMPILE_VERIFIED,
    DIFFERENTIAL_VERIFIED,
    OJ_ACCEPTED,
    PASS,
    SAMPLE_VERIFIED,
    ProblemEnrichmentError,
    ProblemEnrichmentStore,
)
from tools.problem_intelligence import ProblemIntelligenceStore


class ProblemEnrichmentV24Test(unittest.TestCase):
    def make_stores(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        profiles = ProblemIntelligenceStore(root / "profiles")
        enrichment = ProblemEnrichmentStore(
            profiles,
            root / "enrichment",
        )
        return profiles, enrichment

    def add_candidate(self, profiles, problem_id="d050"):
        profiles.import_urls(
            [f"https://zerojudge.tw/ShowProblem?problemid={problem_id}"]
        )
        return profiles.apply_classification(
            "zerojudge",
            problem_id,
            {
                "confidence": 0.95,
                "primary_skill_candidate": "S01_IO",
                "difficulty_candidate": "D1",
            },
        )

    def payload(self, *, sample_output="3\n"):
        return {
            "problem_model": "讀入兩個整數並計算結果。",
            "key_observation": "輸出只依賴目前輸入，不需要額外狀態。",
            "correctness_reasoning": "程式直接計算 a+b，因此輸出等於定義要求。",
            "invariant": "運算前 a、b 保持為輸入值。",
            "time_complexity": "O(1)",
            "space_complexity": "O(1)",
            "common_pitfalls": ["輸入輸出格式錯誤"],
            "edge_cases": ["0 0"],
            "hints": {
                "A1": "先確認輸入與輸出各是什麼。",
                "A2": "只需要一次整數運算。",
                "A3": "讀入 a、b，計算 a+b。",
                "A4": "檢查 cin / cout 的型別與格式。",
                "A5": "完整做法是讀入兩數後直接輸出總和。",
            },
            "alternate_approaches": [],
            "transfer_signals": ["固定筆數輸入、直接轉換"],
            "official_samples": [
                {"input": "1 2\n", "output": sample_output},
            ],
            "generated_cases": [
                {"input": "0 0\n"},
                {"input": "7 -3\n"},
                {"input": "-10 -20\n"},
            ],
            "generation_source": "AI_CANDIDATE",
        }

    @property
    def correct_solution(self):
        return (
            "#include <iostream>\n"
            "using namespace std;\n"
            "int main(){ long long a,b; if(!(cin>>a>>b)) return 0; "
            "cout << a+b << '\\n'; }\n"
        )

    @property
    def wrong_solution(self):
        return (
            "#include <iostream>\n"
            "using namespace std;\n"
            "int main(){ long long a,b; cin>>a>>b; "
            "cout << a-b << '\\n'; }\n"
        )

    def test_l2_requires_l1_candidate(self):
        profiles, enrichment = self.make_stores()
        profiles.import_urls(
            ["https://zerojudge.tw/ShowProblem?problemid=d050"]
        )

        with self.assertRaisesRegex(
            ProblemEnrichmentError,
            "L1 已分類",
        ):
            enrichment.create(
                "zerojudge",
                "d050",
                self.payload(),
                self.correct_solution,
            )

    def test_needs_qa_cannot_enter_l2(self):
        profiles, enrichment = self.make_stores()
        profiles.import_urls(
            ["https://zerojudge.tw/ShowProblem?problemid=d050"]
        )
        profiles.apply_classification(
            "zerojudge",
            "d050",
            {
                "confidence": 0.4,
                "primary_skill_candidate": "S01_IO",
                "difficulty_candidate": "D1",
            },
        )

        with self.assertRaisesRegex(
            ProblemEnrichmentError,
            "NEEDS_QA",
        ):
            enrichment.create(
                "zerojudge",
                "d050",
                self.payload(),
                self.correct_solution,
            )

    def test_create_l2_starts_as_ai_candidate(self):
        profiles, enrichment = self.make_stores()
        self.add_candidate(profiles)

        package = enrichment.create(
            "zerojudge",
            "d050",
            self.payload(),
            self.correct_solution,
        )

        self.assertEqual(
            package["verification"]["trust_status"],
            AI_CANDIDATE,
        )
        self.assertTrue(
            enrichment.solution_path(
                "zerojudge",
                "d050",
            ).is_file()
        )
        self.assertEqual(
            set(package["teaching"]["hints"]),
            {"A1", "A2", "A3", "A4", "A5"},
        )
        self.assertEqual(enrichment.validate_all(), [])

    def test_missing_hint_fails_closed(self):
        profiles, enrichment = self.make_stores()
        self.add_candidate(profiles)
        payload = self.payload()
        del payload["hints"]["A3"]

        with self.assertRaisesRegex(
            ProblemEnrichmentError,
            "A1–A5",
        ):
            enrichment.create(
                "zerojudge",
                "d050",
                payload,
                self.correct_solution,
            )

    @unittest.skipUnless(shutil.which("g++"), "需要 g++")
    def test_compile_verification_only_proves_compile(self):
        profiles, enrichment = self.make_stores()
        self.add_candidate(profiles)
        enrichment.create(
            "zerojudge",
            "d050",
            self.payload(),
            self.correct_solution,
        )

        package = enrichment.verify_compile(
            "zerojudge",
            "d050",
        )

        self.assertEqual(
            package["verification"]["compile"],
            PASS,
        )
        self.assertEqual(
            package["verification"]["trust_status"],
            COMPILE_VERIFIED,
        )
        self.assertNotEqual(
            package["verification"]["trust_status"],
            SAMPLE_VERIFIED,
        )

    @unittest.skipUnless(shutil.which("g++"), "需要 g++")
    def test_sample_verification_requires_actual_sample_match(self):
        profiles, enrichment = self.make_stores()
        self.add_candidate(profiles)
        enrichment.create(
            "zerojudge",
            "d050",
            self.payload(),
            self.correct_solution,
        )

        package = enrichment.verify_samples(
            "zerojudge",
            "d050",
        )

        self.assertEqual(
            package["verification"]["samples"],
            PASS,
        )
        self.assertEqual(
            package["verification"]["trust_status"],
            SAMPLE_VERIFIED,
        )

    @unittest.skipUnless(shutil.which("g++"), "需要 g++")
    def test_sample_failure_does_not_claim_sample_verified(self):
        profiles, enrichment = self.make_stores()
        self.add_candidate(profiles)
        enrichment.create(
            "zerojudge",
            "d050",
            self.payload(),
            self.wrong_solution,
        )

        package = enrichment.verify_samples(
            "zerojudge",
            "d050",
        )

        self.assertEqual(
            package["verification"]["trust_status"],
            COMPILE_VERIFIED,
        )
        self.assertNotEqual(
            package["verification"]["samples"],
            PASS,
        )

    @unittest.skipUnless(shutil.which("g++"), "需要 g++")
    def test_differential_verification_compares_with_oracle(self):
        profiles, enrichment = self.make_stores()
        self.add_candidate(profiles)
        enrichment.create(
            "zerojudge",
            "d050",
            self.payload(),
            self.correct_solution,
        )

        package = enrichment.verify_differential(
            "zerojudge",
            "d050",
            self.correct_solution,
        )

        self.assertEqual(
            package["verification"]["differential"],
            PASS,
        )
        self.assertEqual(
            package["verification"]["trust_status"],
            DIFFERENTIAL_VERIFIED,
        )

    def test_oj_accepted_requires_external_reference(self):
        profiles, enrichment = self.make_stores()
        self.add_candidate(profiles)
        enrichment.create(
            "zerojudge",
            "d050",
            self.payload(),
            self.correct_solution,
        )

        with self.assertRaisesRegex(
            ProblemEnrichmentError,
            "reference",
        ):
            enrichment.mark_oj_accepted(
                "zerojudge",
                "d050",
                "",
            )

        package = enrichment.mark_oj_accepted(
            "zerojudge",
            "d050",
            "https://zerojudge.tw/Submissions?problemid=d050",
        )
        self.assertEqual(
            package["verification"]["trust_status"],
            OJ_ACCEPTED,
        )
        self.assertEqual(
            package["verification"]["oj"],
            PASS,
        )


if __name__ == "__main__":
    unittest.main()
