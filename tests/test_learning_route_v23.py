import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.evidence_outbox import build_envelope
from tools.learning_route import (
    START_LEVEL,
    derive_evidence_lower_bounds,
    select_new_learning_plan,
)
from tools.runtime_curriculum import RuntimeCurriculum
import tools.apcs_control as control


TZ = dt.timezone(dt.timedelta(hours=8))
NOW = dt.datetime(2026, 10, 1, 20, 0, tzinfo=TZ)


def evidence(
    *,
    writeback_id,
    pb_uid,
    problem_id,
    skill_uid,
    track="Implementation",
    activity="Guided Drill",
    assistance=2,
    independent=False,
    novelty="new",
    outcome="PASS",
    judge_result="AC",
):
    return build_envelope(
        problem_id=problem_id,
        pb_uid=pb_uid,
        started_at=None,
        finished_at=NOW,
        language="cpp",
        judge_result=judge_result,
        assistance=assistance,
        independent=independent,
        attempt_count=1,
        active_minutes=10,
        timed=False,
        novelty=novelty,
        activity=activity,
        evidence=[
            (
                skill_uid,
                track,
                outcome,
                "fixture",
            )
        ],
        attempt_id=f"att_{writeback_id}",
        writeback_id=writeback_id,
        created_at=NOW,
    )


class LearningRouteV23Test(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.snapshot = (
            self.root
            / "published.v23.json"
        )
        self.runtime = (
            self.root
            / ".apcs"
            / "runtime"
        )

        self.snapshot.write_text(
            json.dumps(
                {
                    "schema_version": "v2.3-published-1",
                    "contract_version": "v2.3-draft-0",
                    "curriculum_version": "fixture",
                    "skills": [
                        {
                            "uid": "S01_IO",
                            "name": "I/O",
                            "unit": "U-FND",
                            "path_stage": "Foundation",
                            "path_order": 1,
                            "tracks": [
                                "Reading",
                                "Implementation",
                            ],
                            "prerequisites": [],
                            "relevance": {
                                "3+3": "Required",
                                "5+5": "Required",
                            },
                            "conceptual_requirement": "io model",
                            "implementation_requirement": "write io",
                        },
                        {
                            "uid": "S99_OPTIONAL",
                            "name": "Optional",
                            "unit": "U-X",
                            "path_stage": "Bridge",
                            "path_order": 1.5,
                            "tracks": [
                                "Reading",
                                "Implementation",
                            ],
                            "prerequisites": [],
                            "relevance": {
                                "3+3": "Supporting",
                                "5+5": "Supporting",
                            },
                        },
                        {
                            "uid": "S02_COND",
                            "name": "Conditionals",
                            "unit": "U-FND",
                            "path_stage": "Foundation",
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
                        {
                            "uid": "S10_SUPPORT",
                            "name": "Supporting prerequisite",
                            "unit": "U-BRIDGE",
                            "path_stage": "Bridge",
                            "path_order": 2.5,
                            "tracks": [
                                "Reading",
                                "Implementation",
                            ],
                            "prerequisites": [
                                "S01_IO",
                            ],
                            "relevance": {
                                "3+3": "Supporting",
                                "5+5": "Supporting",
                            },
                        },
                        {
                            "uid": "S03_REQUIRED",
                            "name": "Required after support",
                            "unit": "U-CORE",
                            "path_stage": "APCS 3+3 Core",
                            "path_order": 3,
                            "tracks": [
                                "Reading",
                                "Implementation",
                            ],
                            "prerequisites": [
                                "S10_SUPPORT",
                            ],
                            "relevance": {
                                "3+3": "Required",
                                "5+5": "Required",
                            },
                        },
                    ],
                    "problems": [
                        {
                            "pb_uid": "PB-1",
                            "problem_id": "ZJ-d050",
                            "title": "Guided IO",
                            "source_platform": "ZeroJudge",
                            "judge_platform": "ZeroJudge",
                            "url": "https://zerojudge.tw/ShowProblem?problemid=d050",
                            "difficulty": "D1",
                        },
                        {
                            "pb_uid": "PB-2",
                            "problem_id": "CF-4A",
                            "title": "Conditionals Core",
                            "source_platform": "Codeforces",
                            "judge_platform": "Codeforces",
                            "url": "https://codeforces.com/problemset/problem/4/A",
                            "difficulty": "D1",
                        },
                        {
                            "pb_uid": "PB-10",
                            "problem_id": "CSES-1068",
                            "title": "Supporting Guided",
                            "source_platform": "CSES",
                            "judge_platform": "CSES",
                            "url": "https://cses.fi/problemset/task/1068",
                            "difficulty": "D2",
                        },
                        {
                            "pb_uid": "PB-3",
                            "problem_id": "APCS-ZJ-x001",
                            "title": "Required Core",
                            "source_platform": "APCS",
                            "judge_platform": "ZeroJudge",
                            "url": "https://zerojudge.tw/ShowProblem?problemid=x001",
                            "difficulty": "D2",
                        },
                    ],
                    "placements": [
                        {
                            "placement_uid": "PL-PB-1-L-FND-01",
                            "pb_uid": "PB-1",
                            "primary_skill": "S01_IO",
                            "supporting_skills": [],
                            "role": "Guided Drill",
                            "lesson_uid": "L-FND-01",
                            "lesson_order": 2,
                        },
                        {
                            "placement_uid": "PL-PB-2-L-FND-02",
                            "pb_uid": "PB-2",
                            "primary_skill": "S02_COND",
                            "supporting_skills": [],
                            "role": "Core Independent",
                            "lesson_uid": "L-FND-02",
                            "lesson_order": 3,
                        },
                        {
                            "placement_uid": "PL-PB-10-L-BR-01",
                            "pb_uid": "PB-10",
                            "primary_skill": "S10_SUPPORT",
                            "supporting_skills": [],
                            "role": "Guided Drill",
                            "lesson_uid": "L-BR-01",
                            "lesson_order": 1,
                        },
                        {
                            "placement_uid": "PL-PB-3-L-CORE-01",
                            "pb_uid": "PB-3",
                            "primary_skill": "S03_REQUIRED",
                            "supporting_skills": [],
                            "role": "Core Independent",
                            "lesson_uid": "L-CORE-01",
                            "lesson_order": 1,
                        },
                    ],
                    "stats": {},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        self.curriculum = (
            RuntimeCurriculum(
                self.snapshot
            )
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_meas_lower_bound_guided_a2_supports_level2(self):
        levels = (
            derive_evidence_lower_bounds(
                [
                    evidence(
                        writeback_id="wb1",
                        pb_uid="PB-1",
                        problem_id="ZJ-d050",
                        skill_uid="S01_IO",
                        assistance=2,
                        independent=False,
                    )
                ]
            )
        )

        self.assertEqual(
            levels[
                "S01_IO"
            ].implementation_level,
            2,
        )
        self.assertEqual(
            START_LEVEL,
            2,
        )

    def test_a3_guided_only_supports_level1(self):
        levels = (
            derive_evidence_lower_bounds(
                [
                    evidence(
                        writeback_id="wb1",
                        pb_uid="PB-1",
                        problem_id="ZJ-d050",
                        skill_uid="S01_IO",
                        assistance=3,
                        independent=False,
                    )
                ]
            )
        )

        self.assertEqual(
            levels[
                "S01_IO"
            ].implementation_level,
            1,
        )

    def test_core_a1_independent_supports_level3(self):
        levels = (
            derive_evidence_lower_bounds(
                [
                    evidence(
                        writeback_id="wb1",
                        pb_uid="PB-2",
                        problem_id="CF-4A",
                        skill_uid="S02_COND",
                        activity="Core Independent",
                        assistance=1,
                        independent=True,
                        novelty="new",
                    )
                ]
            )
        )

        self.assertEqual(
            levels[
                "S02_COND"
            ].implementation_level,
            3,
        )

    def test_transfer_a1_independent_supports_level4(self):
        levels = (
            derive_evidence_lower_bounds(
                [
                    evidence(
                        writeback_id="wb1",
                        pb_uid="PB-3",
                        problem_id="APCS-ZJ-x001",
                        skill_uid="S03_REQUIRED",
                        activity="Transfer Challenge",
                        assistance=1,
                        independent=True,
                        novelty="transfer",
                    )
                ]
            )
        )

        self.assertEqual(
            levels[
                "S03_REQUIRED"
            ].implementation_level,
            4,
        )

    def test_same_problem_repeat_cannot_unlock_level2(self):
        levels = (
            derive_evidence_lower_bounds(
                [
                    evidence(
                        writeback_id="wb1",
                        pb_uid="PB-1",
                        problem_id="ZJ-d050",
                        skill_uid="S01_IO",
                        assistance=0,
                        independent=True,
                        novelty="same_problem_repeat",
                    )
                ]
            )
        )

        self.assertEqual(
            levels[
                "S01_IO"
            ].implementation_level,
            1,
        )

    def test_no_evidence_starts_at_first_required_skill(self):
        route = (
            select_new_learning_plan(
                self.curriculum,
                [],
                target="3+3",
            )
        )

        self.assertEqual(
            route.skill.uid,
            "S01_IO",
        )
        self.assertEqual(
            route.status,
            "Ready",
        )
        self.assertEqual(
            route.placement.pb_uid,
            "PB-1",
        )
        self.assertEqual(
            route.placement.role,
            "Guided Drill",
        )
        self.assertNotIn(
            "S99_OPTIONAL",
            route.route_skill_uids,
        )

    def test_implementation_level2_alone_unlocks_dependent_start(self):
        first = evidence(
            writeback_id="wb1",
            pb_uid="PB-1",
            problem_id="ZJ-d050",
            skill_uid="S01_IO",
            assistance=2,
            independent=False,
        )

        route = (
            select_new_learning_plan(
                self.curriculum,
                [first],
                target="3+3",
            )
        )

        self.assertEqual(
            route.skill.uid,
            "S02_COND",
        )
        prereq = (
            route.prerequisites[0]
        )
        self.assertTrue(
            prereq.satisfied
        )
        self.assertEqual(
            prereq.reading_level,
            0,
        )
        self.assertEqual(
            prereq.implementation_level,
            2,
        )

    def test_supporting_skill_enters_route_only_when_required_prerequisite(self):
        rows = [
            evidence(
                writeback_id="wb1",
                pb_uid="PB-1",
                problem_id="ZJ-d050",
                skill_uid="S01_IO",
            ),
            evidence(
                writeback_id="wb2",
                pb_uid="PB-2",
                problem_id="CF-4A",
                skill_uid="S02_COND",
            ),
        ]

        route = (
            select_new_learning_plan(
                self.curriculum,
                rows,
                target="3+3",
            )
        )

        self.assertEqual(
            route.skill.uid,
            "S10_SUPPORT",
        )
        self.assertIn(
            "S10_SUPPORT",
            route.route_skill_uids,
        )
        self.assertNotIn(
            "S99_OPTIONAL",
            route.route_skill_uids,
        )

    def test_started_skill_precedes_fresh_ready_skill(self):
        rows = [
            evidence(
                writeback_id="wb1",
                pb_uid="PB-1",
                problem_id="ZJ-d050",
                skill_uid="S01_IO",
            ),
            evidence(
                writeback_id="wb10",
                pb_uid="PB-10",
                problem_id="CSES-1068",
                skill_uid="S10_SUPPORT",
                assistance=3,
            ),
        ]

        route = (
            select_new_learning_plan(
                self.curriculum,
                rows,
                target="3+3",
            )
        )

        self.assertEqual(
            route.skill.uid,
            "S10_SUPPORT",
        )
        self.assertEqual(
            route.status,
            "Learning",
        )

    def test_published_scratch_identity_does_not_require_legacy_id(self):
        placement = (
            self.curriculum
            .placement_by_uid(
                "PL-PB-2-L-FND-02"
            )
        )

        with (
            patch.object(
                control,
                "RUNTIME_DIR",
                self.runtime,
            ),
            patch.object(
                control,
                "CURRICULUM",
                self.curriculum,
            ),
        ):
            scratch = (
                control
                .create_learning_scratch(
                    placement
                )
            )
            current = (
                control.current_problem(
                    str(scratch)
                )
            )

        self.assertEqual(
            current["id"],
            "cf-4a",
        )
        self.assertEqual(
            current["placement_uid"],
            "PL-PB-2-L-FND-02",
        )
        self.assertTrue(
            current[
                "published_runtime"
            ]
        )
        self.assertIn(
            "__PL-PB-2-L-FND-02.cpp",
            scratch.name,
        )


if __name__ == "__main__":
    unittest.main()
