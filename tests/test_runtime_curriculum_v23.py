import json
import tempfile
import unittest
from pathlib import Path

from tools.runtime_curriculum import (
    PublishedCurriculum,
    RuntimeCurriculumError,
    RuntimeCurriculumUnavailable,
    evidence_activity,
)


def published_fixture():
    return {
        "schema_version": "v2.3-published-1",
        "contract_version": "v2.3-draft-0",
        "curriculum_version": "fixture",
        "skills": [
            {
                "uid": "S05_Array",
                "name": "Array",
                "unit": "U-DAT",
                "path_stage": "Foundation",
                "path_order": 5,
            },
            {
                "uid": "S22_Prefix_Sum",
                "name": "Prefix Sum",
                "unit": "U-PFX",
                "path_stage": "Bridge",
                "path_order": 17,
            },
        ],
        "problems": [
            {
                "pb_uid": "PB-93",
                "problem_id": "a693",
                "title": "吞食天地",
                "url": "https://example.invalid/a693",
                "difficulty": "D2",
                "assessment_only": False,
            },
        ],
        "placements": [
            {
                "placement_uid": "PL-PFX-01-A693",
                "pb_uid": "PB-93",
                "primary_skill": "S22_Prefix_Sum",
                "supporting_skills": [
                    "S05_Array",
                ],
                "role": "Core Independent",
                "lesson_uid": "L-PFX-01",
                "lesson_order": 3,
            },
            {
                "placement_uid": "PL-PFX-R-A693",
                "pb_uid": "PB-93",
                "primary_skill": "S22_Prefix_Sum",
                "supporting_skills": [],
                "role": "Transfer Challenge",
                "lesson_uid": "L-PFX-REVIEW",
                "lesson_order": 9,
            },
        ],
        "stats": {
            "skills": 2,
            "problems": 1,
            "placements": 2,
        },
    }


class RuntimeCurriculumV23Test(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "published.v23.json"

    def tearDown(self):
        self.temp.cleanup()

    def write(self, value=None):
        self.path.write_text(
            json.dumps(
                value or published_fixture(),
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def test_missing_snapshot_is_explicitly_unavailable(self):
        runtime = PublishedCurriculum(
            self.path
        )

        with self.assertRaises(
            RuntimeCurriculumUnavailable
        ):
            runtime.placements_for_problem(
                "a693"
            )

    def test_resolves_problem_to_ordered_placements(self):
        self.write()
        runtime = PublishedCurriculum(
            self.path
        )

        placements = (
            runtime.placements_for_problem(
                "A693"
            )
        )

        self.assertEqual(
            [p.placement_uid for p in placements],
            [
                "PL-PFX-01-A693",
                "PL-PFX-R-A693",
            ],
        )

        first = placements[0]

        self.assertEqual(
            first.pb_uid,
            "PB-93",
        )
        self.assertEqual(
            first.primary_skill.uid,
            "S22_Prefix_Sum",
        )
        self.assertEqual(
            first.primary_skill.name,
            "Prefix Sum",
        )
        self.assertEqual(
            [
                skill.uid
                for skill in first.supporting_skills
            ],
            ["S05_Array"],
        )

    def test_unknown_problem_has_no_context_not_guessed_tags(self):
        self.write()
        runtime = PublishedCurriculum(
            self.path
        )

        self.assertEqual(
            runtime.placements_for_problem(
                "unknown"
            ),
            (),
        )

    def test_missing_skill_reference_is_rejected(self):
        value = published_fixture()
        value["placements"][0][
            "primary_skill"
        ] = "S404"
        self.write(value)

        runtime = PublishedCurriculum(
            self.path
        )

        with self.assertRaisesRegex(
            RuntimeCurriculumError,
            "unknown skill",
        ):
            runtime.placements_for_problem(
                "a693"
            )

    def test_finish_activity_comes_from_placement_role(self):
        self.write()
        placement = (
            PublishedCurriculum(
                self.path
            )
            .placements_for_problem(
                "a693"
            )[0]
        )

        self.assertEqual(
            evidence_activity(
                action="finish",
                placement=placement,
            ),
            "Core Independent",
        )

        self.assertEqual(
            evidence_activity(
                action="review",
                placement=placement,
            ),
            "Review",
        )

    def test_worked_example_does_not_auto_create_evidence_activity(self):
        value = published_fixture()
        value["placements"][0][
            "role"
        ] = "Worked Example"
        self.write(value)

        placement = (
            PublishedCurriculum(
                self.path
            )
            .placements_for_problem(
                "a693"
            )[0]
        )

        self.assertIsNone(
            evidence_activity(
                action="finish",
                placement=placement,
            )
        )


if __name__ == "__main__":
    unittest.main()
