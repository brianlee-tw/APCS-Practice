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
            "skills": [],
            "problems": [
                {
                    "pb_uid": "PB-001",
                    "problem_id": "a693",
                    "title": "Prefix Sum",
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
