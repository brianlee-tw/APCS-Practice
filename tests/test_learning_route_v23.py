import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

from tools.evidence_outbox import build_envelope
from tools.learning_route import (
    next_learning_action,
    route_states,
    route_unlocks,
)
from tools.runtime_curriculum import RuntimeCurriculum


TZ = dt.timezone(dt.timedelta(hours=8))
NOW = dt.datetime(2026, 10, 1, 18, 0, tzinfo=TZ)


def attempt(
    *,
    writeback_id,
    problem_id,
    skill_uid,
    activity,
    assistance,
    independent,
    outcome="PASS",
    novelty="new",
):
    return build_envelope(
        problem_id=problem_id,
        pb_uid=f"PB-{problem_id}",
        started_at=None,
        finished_at=NOW,
        language="cpp",
        judge_result=(
            "AC"
            if outcome == "PASS"
            else "WA"
        ),
        assistance=assistance,
        independent=independent,
        attempt_count=1,
        active_minutes=12,
        timed=False,
        novelty=novelty,
        activity=activity,
        evidence=[
            (
                skill_uid,
                "Implementation",
                outcome,
                "",
            )
        ],
        attempt_id=f"att_{writeback_id}",
        writeback_id=writeback_id,
        created_at=NOW,
    )


class LearningRouteV23Test(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.snapshot = (
            Path(self.temp.name)
            / "published.v23.json"
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
                                "5+5": "Required",
                            },
                        },
                        {
                            "uid": "S02_Conditionals",
                            "name": "Conditionals",
                            "unit": "U-FND",
                            "cl": "CL1",
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
                            "uid": "S22_Prefix_Sum",
                            "name": "Prefix Sum",
                            "unit": "U-PFX",
                            "cl": "CL3",
                            "path_stage": "Bridge",
                            "path_order": 20,
                            "tracks": [
                                "Reading",
                                "Implementation",
                            ],
                            "prerequisites": [
                                "S02_Conditionals",
                            ],
                            "relevance": {
                                "3+3": "Not Required",
                                "5+5": "Bridge",
                            },
                        },
                    ],
                    "problems": [
                        {
                            "pb_uid": "PB-1",
                            "problem_id": "P1",
                            "title": "Worked IO",
                            "url": "",
                            "difficulty": "D1",
                        },
                        {
                            "pb_uid": "PB-2",
                            "problem_id": "P2",
                            "title": "Core IO",
                            "url": "",
                            "difficulty": "D1",
                        },
                        {
                            "pb_uid": "PB-3",
                            "problem_id": "P3",
                            "title": "Condition Core",
                            "url": "",
                            "difficulty": "D1",
                        },
                        {
                            "pb_uid": "PB-4",
                            "problem_id": "P4",
                            "title": "Prefix",
                            "url": "",
                            "difficulty": "D2",
                        },
                    ],
                    "placements": [
                        {
                            "placement_uid": "PL-1",
                            "pb_uid": "PB-1",
                            "primary_skill": "S01_IO",
                            "supporting_skills": [],
                            "role": "Worked Example",
                            "lesson_uid": "L-FND-01",
                            "lesson_order": 1,
                        },
                        {
                            "placement_uid": "PL-2",
                            "pb_uid": "PB-2",
                            "primary_skill": "S01_IO",
                            "supporting_skills": [],
                            "role": "Core Independent",
                            "lesson_uid": "L-FND-01",
                            "lesson_order": 2,
                        },
                        {
                            "placement_uid": "PL-3",
                            "pb_uid": "PB-3",
                            "primary_skill": "S02_Conditionals",
                            "supporting_skills": [],
                            "role": "Core Independent",
                            "lesson_uid": "L-FND-02",
                            "lesson_order": 1,
                        },
                        {
                            "placement_uid": "PL-4",
                            "pb_uid": "PB-4",
                            "primary_skill": "S22_Prefix_Sum",
                            "supporting_skills": [],
                            "role": "Guided Drill",
                            "lesson_uid": "L-PFX-01",
                            "lesson_order": 1,
                        },
                    ],
                    "stats": {},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        self.curriculum = RuntimeCurriculum(
            self.snapshot
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_no_evidence_starts_at_first_ready_skill(self):
        action = next_learning_action(
            self.curriculum,
            [],
            target="3+3",
        )

        self.assertIsNotNone(action)
        self.assertEqual(
            action.skill.skill_uid,
            "S01_IO",
        )
        self.assertEqual(
            action.skill.status,
            "READY",
        )
        self.assertEqual(
            action.placement.role,
            "Worked Example",
        )

    def test_guided_or_assisted_pass_does_not_unlock_next_skill(self):
        item = attempt(
            writeback_id="wb1",
            problem_id="P1",
            skill_uid="S01_IO",
            activity="Guided Drill",
            assistance=2,
            independent=False,
        )

        action = next_learning_action(
            self.curriculum,
            [item],
            target="3+3",
        )

        self.assertEqual(
            action.skill.skill_uid,
            "S01_IO",
        )
        self.assertEqual(
            action.skill.status,
            "PRACTICE",
        )
        self.assertEqual(
            action.placement.role,
            "Core Independent",
        )

    def test_clean_core_pass_unlocks_downstream_route_without_claiming_mastery(self):
        item = attempt(
            writeback_id="wb1",
            problem_id="P2",
            skill_uid="S01_IO",
            activity="Core Independent",
            assistance=0,
            independent=True,
        )

        unlocked = route_unlocks(
            [item]
        )

        self.assertEqual(
            unlocked,
            {"S01_IO"},
        )

        states = route_states(
            self.curriculum,
            [item],
            target="3+3",
        )

        by_uid = {
            state.skill_uid: state
            for state in states
        }

        self.assertEqual(
            by_uid["S01_IO"].status,
            "ROUTE_UNLOCKED",
        )
        self.assertEqual(
            by_uid[
                "S02_Conditionals"
            ].status,
            "READY",
        )

    def test_3_plus_3_does_not_open_not_required_bridge_skill(self):
        s1 = attempt(
            writeback_id="wb1",
            problem_id="P2",
            skill_uid="S01_IO",
            activity="Core Independent",
            assistance=0,
            independent=True,
        )
        s2 = attempt(
            writeback_id="wb2",
            problem_id="P3",
            skill_uid="S02_Conditionals",
            activity="Core Independent",
            assistance=0,
            independent=True,
        )

        action = next_learning_action(
            self.curriculum,
            [s1, s2],
            target="3+3",
        )

        self.assertIsNone(action)

        action_55 = next_learning_action(
            self.curriculum,
            [s1, s2],
            target="5+5",
        )

        self.assertIsNotNone(
            action_55
        )
        self.assertEqual(
            action_55.skill.skill_uid,
            "S22_Prefix_Sum",
        )

    def test_same_problem_repeat_does_not_unlock_route(self):
        item = attempt(
            writeback_id="wb1",
            problem_id="P2",
            skill_uid="S01_IO",
            activity="Review",
            assistance=0,
            independent=True,
            novelty="same_problem_repeat",
        )

        self.assertEqual(
            route_unlocks(
                [item]
            ),
            set(),
        )


if __name__ == "__main__":
    unittest.main()
