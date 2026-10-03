from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from tools.problem_enrichment import ProblemEnrichmentStore
from tools.problem_intelligence import ProblemIntelligenceStore
from tools.problem_library import ProblemLibrary


class FakeOutbox:
    def __init__(self, pb_uids=()):
        self.pb_uids = tuple(pb_uids)

    def all_envelopes(self):
        return tuple(
            SimpleNamespace(
                attempt=SimpleNamespace(pb_uid=uid)
            )
            for uid in self.pb_uids
        )


class ProblemLibraryV24Test(unittest.TestCase):
    def make_library(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        profiles = ProblemIntelligenceStore(root / "profiles")
        enrichment = ProblemEnrichmentStore(
            profiles,
            root / "enrichment",
        )
        library = ProblemLibrary(
            profiles,
            enrichment,
            FakeOutbox(),
        )
        return profiles, enrichment, library

    def add_profile(
        self,
        profiles,
        problem_id,
        *,
        title,
        skill,
        difficulty,
        role,
        pb_uid=None,
    ):
        profiles.import_urls(
            [
                "https://zerojudge.tw/ShowProblem"
                f"?problemid={problem_id}"
            ]
        )
        profiles.update_source_metadata(
            "zerojudge",
            problem_id,
            {
                "title": title,
                "statement_summary": "測試摘要",
                "constraints": ["n <= 1000"],
                "metadata_source": "SOURCE_PAGE",
            },
        )
        record = profiles.apply_classification(
            "zerojudge",
            problem_id,
            {
                "confidence": 0.95,
                "primary_skill_candidate": skill,
                "difficulty_candidate": difficulty,
                "role_candidate": role,
            },
        )

        if pb_uid:
            path = profiles.all_paths()[-1]
            data = profiles._read(path)
            data["integration"]["pb_uid"] = pb_uid
            profiles.validate_record(data, path)
            profiles._write(path, data)

        return record

    def l2_payload(self):
        return {
            "problem_model": "把輸入轉成可直接處理的狀態。",
            "key_observation": "關鍵觀察不應在獨立作答前出現。",
            "correctness_reasoning": "依不變量可得演算法正確。",
            "invariant": "處理過的前綴維持正確。",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "common_pitfalls": ["邊界錯誤"],
            "edge_cases": ["n=1"],
            "hints": {
                "A1": "先確認狀態。",
                "A2": "想想線性掃描。",
                "A3": "維護目前狀態。",
                "A4": "檢查索引。",
                "A5": "完整解法。",
            },
            "alternate_approaches": ["另一種方法"],
            "transfer_signals": ["看 constraints"],
            "official_samples": [],
            "generated_cases": [],
            "generation_source": "AI_CANDIDATE",
        }

    def test_search_by_text_and_skill(self):
        profiles, _, library = self.make_library()
        self.add_profile(
            profiles,
            "d050",
            title="時間轉換",
            skill="S01_IO",
            difficulty="D1",
            role="Guided Drill",
        )
        self.add_profile(
            profiles,
            "a693",
            title="前綴和查詢",
            skill="S11_Prefix_Sum",
            difficulty="D2",
            role="Transfer Challenge",
        )

        self.assertEqual(
            [x.external_id for x in library.search("時間")],
            ["d050"],
        )
        self.assertEqual(
            [
                x.external_id
                for x in library.search(
                    skill="S11_Prefix_Sum"
                )
            ],
            ["a693"],
        )

    def test_transfer_pre_attempt_hides_method(self):
        profiles, enrichment, library = self.make_library()
        self.add_profile(
            profiles,
            "a693",
            title="前綴和查詢",
            skill="S11_Prefix_Sum",
            difficulty="D2",
            role="Transfer Challenge",
        )
        enrichment.create(
            "zerojudge",
            "a693",
            self.l2_payload(),
            "#include <iostream>\nint main(){return 0;}\n",
        )

        item = library.search("a693")[0]
        view = library.learner_view(
            item,
            activity="Transfer Challenge",
            post_attempt=False,
        )

        self.assertNotIn("primary_skill", view)
        self.assertNotIn("supporting_skills", view)
        self.assertNotIn("statement_summary", view)
        self.assertNotIn("key_observation", view)
        self.assertNotIn("hints", view)

    def test_mock_pre_attempt_stays_spoiler_safe(self):
        profiles, _, library = self.make_library()
        self.add_profile(
            profiles,
            "d050",
            title="測試題",
            skill="S10_Binary_Search",
            difficulty="D3",
            role="Mock",
        )

        item = library.search("d050")[0]
        view = library.learner_view(
            item,
            activity="Mock",
            post_attempt=False,
        )

        self.assertNotIn("primary_skill", view)
        self.assertNotIn("statement_summary", view)

    def test_guided_drill_may_show_skill_but_not_solution_reasoning(self):
        profiles, enrichment, library = self.make_library()
        self.add_profile(
            profiles,
            "d050",
            title="教學題",
            skill="S01_IO",
            difficulty="D1",
            role="Guided Drill",
        )
        enrichment.create(
            "zerojudge",
            "d050",
            self.l2_payload(),
            "#include <iostream>\nint main(){return 0;}\n",
        )

        item = library.search("d050")[0]
        view = library.learner_view(
            item,
            activity="Guided Drill",
            post_attempt=False,
        )

        self.assertEqual(view["primary_skill"], "S01_IO")
        self.assertNotIn("key_observation", view)
        self.assertNotIn("hints", view)

    def test_post_attempt_unlocks_l2_teaching(self):
        profiles, enrichment, _ = self.make_library()
        self.add_profile(
            profiles,
            "d050",
            title="教學題",
            skill="S01_IO",
            difficulty="D1",
            role="Core Independent",
            pb_uid="PB-TEST",
        )
        enrichment.create(
            "zerojudge",
            "d050",
            self.l2_payload(),
            "#include <iostream>\nint main(){return 0;}\n",
        )

        library = ProblemLibrary(
            profiles,
            enrichment,
            FakeOutbox(["PB-TEST"]),
        )
        item = library.search("d050")[0]
        self.assertTrue(item.attempted)

        view = library.learner_view(
            item,
            activity="Core Independent",
            post_attempt=True,
        )

        self.assertEqual(view["primary_skill"], "S01_IO")
        self.assertIn("key_observation", view)
        self.assertIn("hints", view)
        self.assertIn("time_complexity", view)

    def test_filtering_does_not_change_spoiler_boundary(self):
        profiles, _, library = self.make_library()
        self.add_profile(
            profiles,
            "a693",
            title="未知方法題",
            skill="S11_Prefix_Sum",
            difficulty="D2",
            role="Transfer Challenge",
        )

        item = library.search(
            skill="S11_Prefix_Sum",
            role="Transfer Challenge",
        )[0]
        view = library.learner_view(
            item,
            activity="Transfer Challenge",
            post_attempt=False,
        )

        self.assertNotIn("primary_skill", view)


if __name__ == "__main__":
    unittest.main()
