import json
import unittest
from pathlib import Path

from tools.curriculum_compiler import compile_source, validate_source


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "curriculum" / "source.v23.json"
PUBLISHED = ROOT / "curriculum" / "published.v23.json"
RESOLUTION = (
    ROOT
    / "curriculum"
    / "migration"
    / "primary_skill_resolution.v23.json"
)


class PublishedCurriculumV23Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads(
            SOURCE.read_text(encoding="utf-8")
        )
        cls.published = json.loads(
            PUBLISHED.read_text(encoding="utf-8")
        )
        cls.resolution = json.loads(
            RESOLUTION.read_text(encoding="utf-8")
        )

    def test_source_validates(self):
        validate_source(self.source)

    def test_published_snapshot_is_exact_compiler_output(self):
        self.assertEqual(
            compile_source(self.source),
            self.published,
        )

    def test_first_real_snapshot_inventory(self):
        self.assertEqual(
            self.published["stats"],
            {
                "skills": 39,
                "problems": 127,
                "placements": 127,
            },
        )
        lessons = {
            row["lesson_uid"]
            for row in self.published["placements"]
        }
        self.assertEqual(len(lessons), 51)
        self.assertNotIn("L-MIX-04", lessons)

    def test_every_placement_has_reviewed_resolution(self):
        rows = {
            row["pb_uid"]: row
            for row in self.resolution["rows"]
        }
        self.assertEqual(len(rows), 127)

        for placement in self.source["placements"]:
            pb_uid = placement["pb_uid"]
            resolution = rows[pb_uid]
            self.assertEqual(
                resolution["lesson_uid"],
                placement["lesson_uid"],
            )
            self.assertEqual(
                resolution["primary_skill"],
                placement["primary_skill"],
            )
            self.assertEqual(
                resolution["supporting_skills"],
                placement["supporting_skills"],
            )
            self.assertIn(
                placement["primary_skill"],
                resolution["relation_skills"],
            )

    def test_required_gate_grade_implementation_skills_have_core_primary_path(self):
        required = {
            row["uid"]
            for row in self.published["skills"]
            if (
                row["relevance"]["3+3"] == "Required"
                and row["evidence_suitability"] == "Gate-grade"
                and "Implementation" in row["tracks"]
            )
        }
        core_primary = {
            row["primary_skill"]
            for row in self.published["placements"]
            if row["role"] == "Core Independent"
        }

        self.assertEqual(
            required - core_primary,
            set(),
        )

    def test_phase1b_condition_array_repairs_are_explicit(self):
        placements = {
            row["pb_uid"]: row
            for row in self.published["placements"]
        }
        problems = {
            row["pb_uid"]: row
            for row in self.published["problems"]
        }

        self.assertEqual(
            placements["PB-182"]["primary_skill"],
            "S02_Conditionals",
        )
        self.assertEqual(
            placements["PB-182"]["role"],
            "Core Independent",
        )
        self.assertEqual(
            problems["PB-182"]["problem_id"],
            "ZJ-d067",
        )

        self.assertEqual(
            placements["PB-183"]["primary_skill"],
            "S05_Array",
        )
        self.assertEqual(
            placements["PB-183"]["role"],
            "Core Independent",
        )
        self.assertEqual(
            problems["PB-183"]["problem_id"],
            "ZJ-d097",
        )
        self.assertEqual(
            problems["PB-183"]["alternate_solution_risk"],
            "Medium",
        )

    def test_mix_process_repairs_are_explicit(self):
        rows = {
            row["pb_uid"]: row
            for row in self.resolution["rows"]
        }
        self.assertEqual(
            rows["PB-119"]["primary_skill"],
            "S30_Complexity",
        )
        self.assertEqual(
            rows["PB-125"]["primary_skill"],
            "S39_Code_Reasoning",
        )
        self.assertEqual(
            rows["PB-116"]["primary_skill"],
            "S39_Code_Reasoning",
        )


if __name__ == "__main__":
    unittest.main()
