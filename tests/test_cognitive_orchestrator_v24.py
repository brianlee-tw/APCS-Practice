from __future__ import annotations

import datetime as dt
import unittest

from tools.cognitive_orchestrator import (
    CognitiveOrchestrator,
    guidance_for,
    repair_instruction,
    skill_states,
)
from tools.evidence_outbox import build_envelope


TZ = dt.timezone(dt.timedelta(hours=8))


def envelope(
    *,
    day: int,
    problem: str,
    skill: str,
    outcome: str,
    assistance: int = 0,
    independent: bool = True,
    novelty: str = "new",
    track: str = "Implementation",
):
    when = dt.datetime(2026, 10, day, 20, 0, tzinfo=TZ)
    return build_envelope(
        problem_id=problem,
        started_at=when - dt.timedelta(minutes=10),
        finished_at=when,
        language="cpp",
        judge_result="AC" if outcome == "PASS" else "WA",
        evidence=[
            (
                skill,
                track,
                outcome,
                "test",
            )
        ],
        assistance=assistance,
        independent=independent,
        attempt_count=1,
        active_minutes=10,
        timed=False,
        novelty=novelty,
        activity="Core Independent",
        attempt_id=f"att_{problem}_{day}",
        writeback_id=f"wb_{problem}_{day}",
        created_at=when,
    )


class CognitiveOrchestratorV24Test(unittest.TestCase):
    def test_no_evidence_produces_no_extra_task(self):
        plan = CognitiveOrchestrator().plan(
            (),
            total_capacity_minutes=60,
            review_selected_minutes=0,
            new_learning_active=True,
        )
        self.assertEqual(plan.selected, ())
        self.assertEqual(
            plan.protected_new_learning_minutes,
            36,
        )

    def test_fail_creates_repair_before_other_tasks(self):
        env = envelope(
            day=1,
            problem="p1",
            skill="S18_DFS",
            outcome="FAIL",
            assistance=2,
            independent=False,
        )
        plan = CognitiveOrchestrator().plan(
            (env,),
            total_capacity_minutes=60,
            review_selected_minutes=0,
            new_learning_active=False,
        )
        self.assertTrue(plan.selected)
        self.assertEqual(plan.selected[0].kind, "repair")
        self.assertEqual(
            plan.selected[0].source_problem_id,
            "p1",
        )

    def test_latest_failure_is_used_for_repair(self):
        old = envelope(
            day=1,
            problem="old",
            skill="S18_DFS",
            outcome="FAIL",
        )
        new = envelope(
            day=2,
            problem="new",
            skill="S20_DP",
            outcome="PARTIAL",
            assistance=2,
            independent=False,
        )
        plan = CognitiveOrchestrator().plan(
            (old, new),
            total_capacity_minutes=60,
            review_selected_minutes=0,
            new_learning_active=False,
        )
        self.assertEqual(
            plan.selected[0].source_problem_id,
            "new",
        )

    def test_strong_pass_without_transfer_creates_transfer_candidate(self):
        env = envelope(
            day=1,
            problem="p1",
            skill="S10_Binary_Search",
            outcome="PASS",
            assistance=0,
            independent=True,
            novelty="new",
        )
        plan = CognitiveOrchestrator().plan(
            (env,),
            total_capacity_minutes=60,
            review_selected_minutes=0,
            new_learning_active=False,
        )
        kinds = [task.kind for task in plan.selected]
        self.assertIn("transfer", kinds)

    def test_existing_transfer_pass_suppresses_transfer_candidate(self):
        first = envelope(
            day=1,
            problem="p1",
            skill="S10_Binary_Search",
            outcome="PASS",
            novelty="new",
        )
        second = envelope(
            day=2,
            problem="p2",
            skill="S10_Binary_Search",
            outcome="PASS",
            novelty="transfer",
        )
        plan = CognitiveOrchestrator().plan(
            (first, second),
            total_capacity_minutes=60,
            review_selected_minutes=0,
            new_learning_active=False,
        )
        self.assertNotIn(
            "transfer",
            [task.kind for task in plan.selected],
        )

    def test_confusable_pair_creates_short_discrimination_task(self):
        env = envelope(
            day=1,
            problem="p1",
            skill="S18_DFS",
            outcome="PASS",
            novelty="new",
        )
        plan = CognitiveOrchestrator().plan(
            (env,),
            total_capacity_minutes=60,
            review_selected_minutes=0,
            new_learning_active=False,
        )
        tasks = [
            task
            for task in plan.selected
            if task.kind == "discrimination"
        ]
        self.assertEqual(len(tasks), 1)
        self.assertEqual(
            tasks[0].skill_uids,
            ("S18_DFS", "S19_BFS"),
        )

    def test_capacity_protects_new_learning(self):
        env = envelope(
            day=1,
            problem="p1",
            skill="S18_DFS",
            outcome="FAIL",
            assistance=3,
            independent=False,
        )
        plan = CognitiveOrchestrator().plan(
            (env,),
            total_capacity_minutes=60,
            review_selected_minutes=18,
            new_learning_active=True,
        )

        self.assertEqual(
            plan.protected_new_learning_minutes,
            36,
        )
        self.assertLessEqual(
            plan.selected_minutes,
            6,
        )
        self.assertLessEqual(
            18
            + plan.selected_minutes
            + plan.protected_new_learning_minutes,
            60,
        )

    def test_guidance_fades_only_after_real_independent_pass(self):
        fail_state = skill_states(
            (
                envelope(
                    day=1,
                    problem="p1",
                    skill="S20_DP",
                    outcome="FAIL",
                    assistance=4,
                    independent=False,
                ),
            )
        )[("S20_DP", "Implementation")]
        self.assertEqual(
            guidance_for(fail_state),
            ("Guided Drill", "A3"),
        )

        pass_state = skill_states(
            (
                envelope(
                    day=1,
                    problem="p2",
                    skill="S20_DP",
                    outcome="PASS",
                    assistance=0,
                    independent=True,
                ),
            )
        )[("S20_DP", "Implementation")]
        self.assertEqual(
            guidance_for(pass_state),
            ("Core Independent", "A1"),
        )

    def test_repair_instruction_is_bottleneck_specific(self):
        self.assertIn(
            "constraints",
            repair_instruction("Complexity"),
        )
        self.assertIn(
            "最小失敗案例",
            repair_instruction("Debugging"),
        )


if __name__ == "__main__":
    unittest.main()
