import copy
import json
import tempfile
import unittest
from pathlib import Path

from tools.curriculum_compiler import (
    CONTRACT_VERSION,
    PUBLISHED_SCHEMA,
    CurriculumError,
    compile_source,
    main,
    validate_source,
)


def valid_source():
    return {
        "schema_version": "v2.3-authoring-1",
        "curriculum_version": "fixture-1",
        "skills": [
            {
                "uid": "S01_IO",
                "name": "Input / Output",
                "unit": "U-FND",
                "cl": "CL1",
                "path_stage": "Foundation",
                "path_order": 1,
                "tracks": [
                    "Reading",
                    "Implementation",
                ],
                "prerequisites": [],
                "relevance": {
                    "3+3": "Required",
                    "5+5": "Supporting",
                },
            },
            {
                "uid": "S22_Prefix_Sum",
                "name": "Prefix Sum",
                "unit": "U-PFX",
                "cl": "CL3",
                "path_stage": "APCS 3+3 Core",
                "path_order": 2,
                "tracks": [
                    "Reading",
                    "Implementation",
                ],
                "prerequisites": [
                    "S01_IO",
                ],
                "relevance": {
                    "3+3": "Required",
                    "5+5": "Required",
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
                "publish_state": "Published",
                "assessment_only": False,
            },
            {
                "pb_uid": "PB-002",
                "problem_id": "draft1",
                "title": "Draft problem",
                "source_platform": "Custom",
                "judge_platform": "Custom",
                "url": "",
                "difficulty": "",
                "publish_state": "Draft",
                "assessment_only": False,
            },
            {
                "pb_uid": "PB-003",
                "problem_id": "mock1",
                "title": "Mixed Mock",
                "source_platform": "Custom",
                "judge_platform": "Custom",
                "url": "",
                "difficulty": "D4",
                "publish_state": "Published",
                "assessment_only": True,
            },
        ],
        "placements": [
            {
                "placement_uid": "PL-001",
                "pb_uid": "PB-001",
                "primary_skill": "S22_Prefix_Sum",
                "supporting_skills": [
                    "S01_IO",
                ],
                "role": "Core Independent",
                "lesson_uid": "L-PFX-01",
                "lesson_order": 1,
            },
            {
                "placement_uid": "PL-002",
                "pb_uid": "PB-002",
                "primary_skill": "S01_IO",
                "supporting_skills": [],
                "role": "Guided Drill",
                "lesson_uid": "L-FND-01",
                "lesson_order": 2,
            },
        ],
    }


class CurriculumCompilerV23Test(unittest.TestCase):
    def test_valid_source_compiles_published_only(self):
        result = compile_source(valid_source())

        self.assertEqual(
            result["schema_version"],
            PUBLISHED_SCHEMA,
        )
        self.assertEqual(
            result["contract_version"],
            CONTRACT_VERSION,
        )
        self.assertEqual(
            result["stats"],
            {
                "skills": 2,
                "problems": 2,
                "placements": 1,
            },
        )

        self.assertEqual(
            [x["pb_uid"] for x in result["problems"]],
            ["PB-001", "PB-003"],
        )

        self.assertEqual(
            [
                x["placement_uid"]
                for x in result["placements"]
            ],
            ["PL-001"],
        )

    def test_placement_policy_defaults_from_role_and_problem_risk(self):
        source = valid_source()
        source["problems"][0][
            "alternate_solution_risk"
        ] = "High"

        result = compile_source(source)
        placement = result["placements"][0]

        self.assertEqual(
            placement["evidence_level_cap"],
            3,
        )
        self.assertTrue(
            placement[
                "method_confirmation_required"
            ]
        )

    def test_explicit_learning_only_cap_is_preserved(self):
        source = valid_source()
        source["placements"][0][
            "evidence_level_cap"
        ] = 2

        result = compile_source(source)

        self.assertEqual(
            result["placements"][0][
                "evidence_level_cap"
            ],
            2,
        )

    def test_evidence_cap_cannot_exceed_role_cap(self):
        source = valid_source()
        source["placements"][0][
            "evidence_level_cap"
        ] = 4

        with self.assertRaisesRegex(
            CurriculumError,
            "exceeds role cap",
        ):
            validate_source(source)

    def test_method_confirmation_override_must_be_boolean(self):
        source = valid_source()
        source["placements"][0][
            "method_confirmation_required"
        ] = "yes"

        with self.assertRaisesRegex(
            CurriculumError,
            "must be boolean",
        ):
            validate_source(source)

    def test_published_problem_requires_difficulty(self):
        source = valid_source()
        source["problems"][0]["difficulty"] = ""

        with self.assertRaisesRegex(
            CurriculumError,
            "requires difficulty D1-D5",
        ):
            validate_source(source)

    def test_draft_may_be_incomplete(self):
        source = valid_source()
        source["problems"][1]["difficulty"] = ""
        source["problems"][1]["url"] = ""

        validate_source(source)

    def test_non_assessment_published_problem_requires_placement(self):
        source = valid_source()
        source["placements"] = []

        with self.assertRaisesRegex(
            CurriculumError,
            "requires a placement",
        ):
            validate_source(source)

    def test_assessment_only_problem_may_have_no_placement(self):
        source = valid_source()

        validate_source(source)

        result = compile_source(source)

        mock = next(
            row
            for row in result["problems"]
            if row["pb_uid"] == "PB-003"
        )

        self.assertTrue(
            mock["assessment_only"]
        )

    def test_placement_primary_skill_must_exist(self):
        source = valid_source()
        source["placements"][0][
            "primary_skill"
        ] = "S404_Missing"

        with self.assertRaisesRegex(
            CurriculumError,
            "unknown primary_skill",
        ):
            validate_source(source)

    def test_supporting_skill_cannot_duplicate_primary(self):
        source = valid_source()
        source["placements"][0][
            "supporting_skills"
        ] = ["S22_Prefix_Sum"]

        with self.assertRaisesRegex(
            CurriculumError,
            "primary_skill cannot also be supporting",
        ):
            validate_source(source)

    def test_prerequisite_reference_must_exist(self):
        source = valid_source()
        source["skills"][1][
            "prerequisites"
        ] = ["S404_Missing"]

        with self.assertRaisesRegex(
            CurriculumError,
            "unknown prerequisite",
        ):
            validate_source(source)

    def test_prerequisite_cycle_is_rejected(self):
        source = valid_source()
        source["skills"][0][
            "prerequisites"
        ] = ["S22_Prefix_Sum"]

        with self.assertRaisesRegex(
            CurriculumError,
            "prerequisite cycle",
        ):
            validate_source(source)

    def test_same_external_identity_cannot_be_published_twice(self):
        source = valid_source()
        duplicate = copy.deepcopy(
            source["problems"][0]
        )
        duplicate["pb_uid"] = "PB-004"
        source["problems"].append(
            duplicate
        )
        source["placements"].append(
            {
                "placement_uid": "PL-004",
                "pb_uid": "PB-004",
                "primary_skill": "S22_Prefix_Sum",
                "supporting_skills": [],
                "role": "Transfer Challenge",
                "lesson_uid": "",
                "lesson_order": None,
            }
        )

        with self.assertRaisesRegex(
            CurriculumError,
            "duplicate external identity",
        ):
            validate_source(source)

    def test_output_is_deterministic(self):
        source = valid_source()

        first = compile_source(source)

        source["skills"].reverse()
        source["problems"].reverse()
        source["placements"].reverse()

        second = compile_source(source)

        self.assertEqual(
            first,
            second,
        )

    def test_cli_compile_and_check(self):
        source = valid_source()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_path = root / "source.json"
            output_path = root / "published.json"

            source_path.write_text(
                json.dumps(
                    source,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                main(
                    [
                        "compile",
                        str(source_path),
                        str(output_path),
                    ]
                ),
                0,
            )

            self.assertEqual(
                main(
                    [
                        "check",
                        str(source_path),
                        str(output_path),
                    ]
                ),
                0,
            )

            published = json.loads(
                output_path.read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(
                published["schema_version"],
                PUBLISHED_SCHEMA,
            )


if __name__ == "__main__":
    unittest.main()
