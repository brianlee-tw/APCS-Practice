import unittest

from tools.curriculum_migration import (
    CurriculumMigrationError,
    project_formal_problem_rows,
)


class CurriculumMigrationTest(unittest.TestCase):
    def setUp(self):
        self.main_lessons = {
            "L-PFX-01",
            "L-MIX-04",
        }
        self.skill_map = {
            "https://notion/skill-prefix": (
                "S22_Prefix_Sum"
            ),
            "https://notion/skill-array": (
                "S05_Array"
            ),
        }
        self.primary = {
            "PB-25": "S22_Prefix_Sum",
        }

    def row(self):
        return {
            "pb_uid": "PB-25",
            "problem_id": "ZJ-e339",
            "title": "e339 前綴和練習",
            "source_platform": "ZeroJudge",
            "judge_platform": "ZeroJudge",
            "url": (
                "https://zerojudge.tw/"
                "ShowProblem?problemid=e339"
            ),
            "difficulty": "D1 入門",
            "exam_band": "",
            "suitability_33": "Not for 3+3",
            "suitability_55": "Bridge",
            "alternate_solution_risk": "Low",
            "training_purpose": "建立 prefix",
            "status": "Active",
            "placement_qa": "PASS",
            "primary_lesson": "L-PFX-01",
            "lesson_order": 2,
            "role": "Guided Drill",
            "unit": "U-PFX 前綴與差分",
            "skill_urls": [
                "https://notion/skill-prefix",
                "https://notion/skill-array",
            ],
        }

    def test_projects_reviewed_formal_row(self):
        problems, placements = (
            project_formal_problem_rows(
                [self.row()],
                main_lessons=self.main_lessons,
                skill_uid_by_url=self.skill_map,
                primary_skill_by_pb=self.primary,
            )
        )

        self.assertEqual(
            problems[0]["publish_state"],
            "Published",
        )
        self.assertEqual(
            problems[0]["difficulty"],
            "D1",
        )
        self.assertEqual(
            placements[0]["primary_skill"],
            "S22_Prefix_Sum",
        )
        self.assertEqual(
            placements[0][
                "supporting_skills"
            ],
            ["S05_Array"],
        )
        self.assertEqual(
            placements[0]["placement_uid"],
            "PL-PB-25-L-PFX-01",
        )

    def test_relation_order_does_not_define_primary(self):
        row = self.row()
        row["skill_urls"].reverse()

        _, placements = (
            project_formal_problem_rows(
                [row],
                main_lessons=self.main_lessons,
                skill_uid_by_url=self.skill_map,
                primary_skill_by_pb=self.primary,
            )
        )

        self.assertEqual(
            placements[0]["primary_skill"],
            "S22_Prefix_Sum",
        )

    def test_missing_explicit_primary_fails_closed(self):
        with self.assertRaisesRegex(
            CurriculumMigrationError,
            "missing explicit Primary Skill",
        ):
            project_formal_problem_rows(
                [self.row()],
                main_lessons=self.main_lessons,
                skill_uid_by_url=self.skill_map,
                primary_skill_by_pb={},
            )

    def test_resolved_primary_must_exist_in_relations(self):
        with self.assertRaisesRegex(
            CurriculumMigrationError,
            "is not present",
        ):
            project_formal_problem_rows(
                [self.row()],
                main_lessons=self.main_lessons,
                skill_uid_by_url=self.skill_map,
                primary_skill_by_pb={
                    "PB-25": "S31_Difference",
                },
            )

    def test_non_pass_main_placement_fails_closed(self):
        row = self.row()
        row["placement_qa"] = "REVIEW"

        with self.assertRaisesRegex(
            CurriculumMigrationError,
            "requires Placement QA PASS",
        ):
            project_formal_problem_rows(
                [row],
                main_lessons=self.main_lessons,
                skill_uid_by_url=self.skill_map,
                primary_skill_by_pb=self.primary,
            )

    def test_needs_qa_main_placement_fails_closed(self):
        row = self.row()
        row["status"] = "Needs QA"

        with self.assertRaisesRegex(
            CurriculumMigrationError,
            "must be Active",
        ):
            project_formal_problem_rows(
                [row],
                main_lessons=self.main_lessons,
                skill_uid_by_url=self.skill_map,
                primary_skill_by_pb=self.primary,
            )

    def test_non_main_or_benchmark_row_is_not_published(self):
        row = self.row()
        row["pb_uid"] = "PB-MOCK"
        row["primary_lesson"] = ""
        row["status"] = "Active"

        problems, placements = (
            project_formal_problem_rows(
                [row],
                main_lessons=self.main_lessons,
                skill_uid_by_url=self.skill_map,
                primary_skill_by_pb={},
            )
        )

        self.assertEqual(problems, [])
        self.assertEqual(placements, [])

    def test_unknown_skill_relation_fails_closed(self):
        row = self.row()
        row["skill_urls"].append(
            "https://notion/skill-unknown"
        )

        with self.assertRaisesRegex(
            CurriculumMigrationError,
            "unknown Skill relation",
        ):
            project_formal_problem_rows(
                [row],
                main_lessons=self.main_lessons,
                skill_uid_by_url=self.skill_map,
                primary_skill_by_pb=self.primary,
            )


if __name__ == "__main__":
    unittest.main()
