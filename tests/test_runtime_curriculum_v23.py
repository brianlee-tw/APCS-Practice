import json
import tempfile
import unittest
from pathlib import Path

from tools.runtime_curriculum import (
    RuntimeCurriculum,
    RuntimeCurriculumError,
)


class RuntimeCurriculumV23Test(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.snapshot = self.root / "published.v23.json"

    def tearDown(self):
        self.temp.cleanup()

    def write_snapshot(self, data):
        self.snapshot.write_text(
            json.dumps(
                data,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def base_snapshot(self):
        return {
            "schema_version": "v2.3-published-1",
            "contract_version": "v2.3-draft-0",
            "curriculum_version": "fixture",
            "skills": [
                {
                    "uid": "S22_Prefix_Sum",
                    "name": "Prefix Sum",
                    "unit": "U-PFX",
                    "path_stage": "Bridge",
                    "path_order": 22,
                    "tracks": [
                        "Reading",
                        "Implementation",
                    ],
                    "prerequisites": [],
                    "conceptual_requirement": "prefix model",
                    "implementation_requirement": "build prefix",
                    "relevance": {
                        "3+3": "Required",
                        "5+5": "Required",
                    },
                },
                {
                    "uid": "S99_Extension",
                    "name": "Extension",
                    "unit": "U-MIX",
                    "path_stage": "Extension",
                    "path_order": 99,
                    "relevance": {
                        "3+3": "Not Required",
                        "5+5": "Extension",
                    },
                },
            ],
            "problems": [
                {
                    "pb_uid": "PB-001",
                    "problem_id": "a693",
                    "title": "Prefix Sum",
                    "source_platform": "ZeroJudge",
                    "judge_platform": "ZeroJudge",
                    "url": "https://example.invalid/a693",
                    "difficulty": "D2",
                }
            ],
            "placements": [
                {
                    "placement_uid": "PL-001",
                    "pb_uid": "PB-001",
                    "primary_skill": "S22_Prefix_Sum",
                    "supporting_skills": [
                        "S05_Array",
                    ],
                    "role": "Core Independent",
                    "lesson_uid": "L-PFX-01",
                    "lesson_order": 2,
                },
                {
                    "placement_uid": "PL-002",
                    "pb_uid": "PB-001",
                    "primary_skill": "S30_Complexity",
                    "supporting_skills": [],
                    "role": "Transfer Challenge",
                    "lesson_uid": "L-PSV-02",
                    "lesson_order": 3,
                },
            ],
            "stats": {},
        }

    def test_missing_snapshot_is_unavailable(self):
        runtime = RuntimeCurriculum(
            self.snapshot
        )

        self.assertFalse(
            runtime.available()
        )

        with self.assertRaisesRegex(
            RuntimeCurriculumError,
            "尚未建立",
        ):
            runtime.load()

    def test_problem_resolves_all_published_placements(self):
        self.write_snapshot(
            self.base_snapshot()
        )

        runtime = RuntimeCurriculum(
            self.snapshot
        )

        contexts = (
            runtime.placements_for_problem(
                "A693"
            )
        )

        self.assertEqual(
            len(contexts),
            2,
        )

        first = contexts[0]

        self.assertEqual(
            first.pb_uid,
            "PB-001",
        )
        self.assertEqual(
            first.primary_skill,
            "S22_Prefix_Sum",
        )
        self.assertEqual(
            first.url,
            "https://example.invalid/a693",
        )
        self.assertEqual(
            first.supporting_skills,
            ("S05_Array",),
        )
        self.assertEqual(
            first.role,
            "Core Independent",
        )

    def test_unknown_problem_returns_empty(self):
        self.write_snapshot(
            self.base_snapshot()
        )

        runtime = RuntimeCurriculum(
            self.snapshot
        )

        self.assertEqual(
            runtime.placements_for_problem(
                "b999"
            ),
            (),
        )

    def test_skill_context_and_importance_are_available(self):
        self.write_snapshot(
            self.base_snapshot()
        )

        runtime = RuntimeCurriculum(
            self.snapshot
        )

        context = runtime.skill_context(
            "S22_Prefix_Sum"
        )

        self.assertIsNotNone(
            context
        )
        self.assertEqual(
            context.name,
            "Prefix Sum",
        )
        self.assertEqual(
            runtime.importance_for_skill(
                "S22_Prefix_Sum",
                target="3+3",
            ),
            "required",
        )
        self.assertEqual(
            runtime.importance_for_skill(
                "S99_Extension",
                target="5+5",
            ),
            "extension",
        )

    def test_skill_context_exposes_prerequisite_contract_fields(self):
        self.write_snapshot(
            self.base_snapshot()
        )

        runtime = RuntimeCurriculum(
            self.snapshot
        )
        context = runtime.skill_context(
            "S22_Prefix_Sum"
        )

        self.assertEqual(
            context.tracks,
            (
                "Reading",
                "Implementation",
            ),
        )
        self.assertEqual(
            context.prerequisites,
            (),
        )
        self.assertEqual(
            context.conceptual_requirement,
            "prefix model",
        )
        self.assertEqual(
            context.implementation_requirement,
            "build prefix",
        )
        self.assertEqual(
            [
                item.uid
                for item in runtime.skill_contexts()
            ],
            [
                "S22_Prefix_Sum",
                "S99_Extension",
            ],
        )

    def test_placement_uid_is_runtime_identity(self):
        self.write_snapshot(
            self.base_snapshot()
        )

        runtime = RuntimeCurriculum(
            self.snapshot
        )
        placement = runtime.placement_by_uid(
            "PL-001"
        )

        self.assertIsNotNone(
            placement
        )
        self.assertEqual(
            placement.problem_id,
            "a693",
        )
        self.assertEqual(
            placement.source_platform,
            "ZeroJudge",
        )
        self.assertEqual(
            placement.judge_platform,
            "ZeroJudge",
        )

    def test_not_required_does_not_become_required_by_substring(self):
        self.write_snapshot(
            self.base_snapshot()
        )

        runtime = RuntimeCurriculum(
            self.snapshot
        )

        self.assertEqual(
            runtime.importance_for_skill(
                "S99_Extension",
                target="3+3",
            ),
            "supporting",
        )

    def test_placements_for_skill_returns_primary_skill_placements(self):
        self.write_snapshot(
            self.base_snapshot()
        )

        runtime = RuntimeCurriculum(
            self.snapshot
        )

        contexts = runtime.placements_for_skill(
            "S22_Prefix_Sum"
        )

        self.assertEqual(
            len(contexts),
            1,
        )
        self.assertEqual(
            contexts[0].problem_id,
            "a693",
        )
        self.assertEqual(
            contexts[0].role,
            "Core Independent",
        )

    def test_unknown_skill_falls_back_to_supporting_importance(self):
        self.write_snapshot(
            self.base_snapshot()
        )

        runtime = RuntimeCurriculum(
            self.snapshot
        )

        self.assertIsNone(
            runtime.skill_context(
                "S404_Missing"
            )
        )
        self.assertEqual(
            runtime.importance_for_skill(
                "S404_Missing"
            ),
            "supporting",
        )

    def test_invalid_schema_is_rejected(self):
        data = self.base_snapshot()
        data["schema_version"] = "old"

        self.write_snapshot(data)

        runtime = RuntimeCurriculum(
            self.snapshot
        )

        with self.assertRaisesRegex(
            RuntimeCurriculumError,
            "schema 不相容",
        ):
            runtime.load()

    def test_placement_order_is_deterministic(self):
        data = self.base_snapshot()
        data["placements"].reverse()

        self.write_snapshot(data)

        runtime = RuntimeCurriculum(
            self.snapshot
        )

        contexts = (
            runtime.placements_for_problem(
                "a693"
            )
        )

        self.assertEqual(
            [
                item.placement_uid
                for item in contexts
            ],
            [
                "PL-001",
                "PL-002",
            ],
        )


if __name__ == "__main__":
    unittest.main()
