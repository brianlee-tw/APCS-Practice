import datetime as dt
import unittest

from tools.adaptive_memory import (
    Evidence,
    MemoryPolicy,
    MemoryState,
    ReviewCandidate,
    interval_for_retention,
    next_due_on,
    retrievability,
    review_budget_minutes,
    select_review_plan,
    update_memory,
)


DAY0 = dt.date(2026, 1, 1)


class AdaptiveMemoryV23Test(unittest.TestCase):
    def test_clean_independent_first_pass_starts_near_one_week(self):
        state = update_memory(
            None,
            Evidence(
                skill_uid="S22_Prefix_Sum",
                track="Implementation",
                occurred_on=DAY0,
                outcome="PASS",
                assistance=0,
                independent=True,
                novelty="delayed_retest",
            ),
        )

        self.assertAlmostEqual(
            state.stability_days,
            7.0,
            places=6,
        )

    def test_assisted_first_pass_has_lower_stability(self):
        clean = update_memory(
            None,
            Evidence(
                "S22_Prefix_Sum",
                "Implementation",
                DAY0,
                "PASS",
                assistance=0,
                independent=True,
                novelty="transfer",
            ),
        )

        assisted = update_memory(
            None,
            Evidence(
                "S22_Prefix_Sum",
                "Implementation",
                DAY0,
                "PASS",
                assistance=3,
                independent=False,
                novelty="seen",
            ),
        )

        self.assertLess(
            assisted.stability_days,
            clean.stability_days,
        )

    def test_retrievability_is_ninety_percent_at_stability(self):
        state = MemoryState(
            "S09_Sorting",
            "Reading",
            stability_days=10.0,
            last_evidence_on=DAY0,
        )

        value = retrievability(
            state,
            DAY0 + dt.timedelta(days=10),
        )

        self.assertAlmostEqual(
            value,
            0.9,
            places=7,
        )

    def test_delayed_success_earns_more_than_immediate_repeat(self):
        base = MemoryState(
            "S09_Sorting",
            "Implementation",
            stability_days=7.0,
            last_evidence_on=DAY0,
            evidence_count=1,
            successful_retrievals=1,
        )

        same_day = update_memory(
            base,
            Evidence(
                "S09_Sorting",
                "Implementation",
                DAY0,
                "PASS",
                assistance=0,
                independent=True,
                novelty="same_problem_repeat",
            ),
        )

        delayed = update_memory(
            base,
            Evidence(
                "S09_Sorting",
                "Implementation",
                DAY0 + dt.timedelta(days=21),
                "PASS",
                assistance=0,
                independent=True,
                novelty="transfer",
            ),
        )

        self.assertLessEqual(
            same_day.stability_days,
            base.stability_days * 1.05,
        )

        self.assertGreater(
            delayed.stability_days,
            same_day.stability_days,
        )

    def test_failure_reduces_but_does_not_erase_long_term_memory(self):
        base = MemoryState(
            "S10_Binary_Search",
            "Implementation",
            stability_days=90.0,
            last_evidence_on=DAY0,
            evidence_count=7,
            successful_retrievals=6,
        )

        failed = update_memory(
            base,
            Evidence(
                "S10_Binary_Search",
                "Implementation",
                DAY0 + dt.timedelta(days=100),
                "FAIL",
                assistance=0,
                independent=True,
                novelty="transfer",
            ),
        )

        self.assertLess(
            failed.stability_days,
            90.0,
        )
        self.assertGreater(
            failed.stability_days,
            1.0,
        )
        self.assertEqual(
            failed.lapses,
            1,
        )

    def test_evidence_cannot_move_backwards(self):
        state = MemoryState(
            "S03_Loops",
            "Reading",
            stability_days=5.0,
            last_evidence_on=DAY0 + dt.timedelta(days=5),
        )

        with self.assertRaisesRegex(
            ValueError,
            "backwards",
        ):
            update_memory(
                state,
                Evidence(
                    "S03_Loops",
                    "Reading",
                    DAY0,
                    "PASS",
                ),
            )

    def test_target_retention_changes_interval_without_fixed_sequence(self):
        stability = 30.0

        high = interval_for_retention(
            stability,
            0.92,
        )
        low = interval_for_retention(
            stability,
            0.82,
        )

        self.assertLess(
            high,
            low,
        )
        self.assertNotEqual(
            round(high),
            30,
        )
        self.assertNotEqual(
            round(low),
            30,
        )

    def test_next_due_comes_from_memory_state_not_review_count(self):
        policy = MemoryPolicy(
            target_retention=0.88,
        )

        state = MemoryState(
            "S20_DP",
            "Implementation",
            stability_days=40.0,
            last_evidence_on=DAY0,
            evidence_count=99,
            successful_retrievals=50,
        )

        due = next_due_on(
            state,
            policy=policy,
        )

        expected_days = int(
            __import__("math").ceil(
                interval_for_retention(
                    40.0,
                    0.88,
                )
            )
        )

        self.assertEqual(
            due,
            DAY0 + dt.timedelta(days=expected_days),
        )

    def test_sixty_minute_session_protects_new_learning(self):
        policy = MemoryPolicy()
        budget = review_budget_minutes(
            60,
            policy=policy,
        )

        self.assertEqual(
            budget,
            18,
        )
        self.assertLessEqual(
            budget,
            int(60 * policy.review_fraction_max),
        )
        self.assertGreaterEqual(
            60 - budget,
            int(60 * policy.min_new_learning_fraction),
        )

    def test_large_backlog_does_not_expand_daily_review_budget(self):
        today = DAY0 + dt.timedelta(days=200)

        candidates = [
            ReviewCandidate(
                skill_uid=f"S{i:04d}",
                track="Implementation",
                retrievability=0.5,
                due_on=DAY0,
                estimated_minutes=6,
                importance="required",
            )
            for i in range(1000)
        ]

        plan = select_review_plan(
            candidates,
            today=today,
            total_capacity_minutes=60,
        )

        self.assertEqual(
            plan.budget_minutes,
            18,
        )
        self.assertEqual(
            len(plan.selected),
            3,
        )
        self.assertEqual(
            plan.selected_minutes,
            18,
        )
        self.assertEqual(
            len(plan.deferred),
            997,
        )

    def test_priority_is_transparent(self):
        today = DAY0 + dt.timedelta(days=30)

        candidates = [
            ReviewCandidate(
                "S_ext",
                "Implementation",
                0.20,
                DAY0,
                6,
                importance="extension",
            ),
            ReviewCandidate(
                "S_current",
                "Implementation",
                0.75,
                DAY0 + dt.timedelta(days=20),
                6,
                importance="current_required",
            ),
            ReviewCandidate(
                "S_failed",
                "Implementation",
                0.80,
                DAY0 + dt.timedelta(days=25),
                6,
                importance="supporting",
                recent_failure=True,
            ),
        ]

        plan = select_review_plan(
            candidates,
            today=today,
            total_capacity_minutes=40,
        )

        self.assertEqual(
            [x.skill_uid for x in plan.selected],
            ["S_failed", "S_current"],
        )
        self.assertEqual(
            [x.skill_uid for x in plan.deferred],
            ["S_ext"],
        )


if __name__ == "__main__":
    unittest.main()
