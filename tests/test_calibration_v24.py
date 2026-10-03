from __future__ import annotations

import datetime as dt
import tempfile
import unittest
from pathlib import Path

from tools.adaptive_memory import MemoryPolicy
from tools.calibration import (
    BASELINE_POLICY,
    BASELINE_VERSION,
    CalibrationError,
    MemoryPolicyFlag,
    calibration_report,
    compare_policies,
    replay_policy,
)
from tools.evidence_outbox import build_envelope
from tools.skill_memory_store import SkillMemoryStore


TZ = dt.timezone(dt.timedelta(hours=8))


def env(
    *,
    day: int,
    skill: str,
    novelty: str,
    outcome: str = "PASS",
):
    when = dt.datetime(
        2026, 9, 1, 20, 0, tzinfo=TZ
    ) + dt.timedelta(days=day)
    problem = f"{skill}_{day}"
    return build_envelope(
        problem_id=problem,
        started_at=when - dt.timedelta(minutes=10),
        finished_at=when,
        language="cpp",
        judge_result="AC" if outcome == "PASS" else "WA",
        evidence=[
            (
                skill,
                "Implementation",
                outcome,
                "calibration-test",
            )
        ],
        assistance=0,
        independent=True,
        attempt_count=1,
        active_minutes=10,
        timed=False,
        novelty=novelty,
        activity="Transfer Challenge",
        attempt_id=f"att_{skill}_{day}",
        writeback_id=f"wb_{skill}_{day}",
        created_at=when,
    )


def sufficient_history():
    rows = []
    for index in range(5):
        skill = f"S{index + 1:02d}_TEST"
        rows.append(
            env(
                day=0,
                skill=skill,
                novelty="new",
            )
        )
        for day in (2, 4, 6, 8):
            rows.append(
                env(
                    day=day,
                    skill=skill,
                    novelty="delayed_retest",
                )
            )
    return tuple(rows)


class CalibrationV24Test(unittest.TestCase):
    def test_no_real_delayed_samples_is_insufficient(self):
        report = calibration_report(
            (
                env(
                    day=0,
                    skill="S01_TEST",
                    novelty="new",
                ),
            )
        )
        self.assertEqual(
            report.status,
            "INSUFFICIENT_DATA",
        )
        self.assertEqual(report.sample_count, 0)
        self.assertIsNone(report.brier_score)

    def test_replay_records_prediction_before_delayed_update(self):
        rows = (
            env(
                day=0,
                skill="S01_TEST",
                novelty="new",
            ),
            env(
                day=7,
                skill="S01_TEST",
                novelty="delayed_retest",
            ),
        )
        samples, skipped = replay_policy(rows)
        self.assertEqual(skipped, 0)
        self.assertEqual(len(samples), 1)
        self.assertGreater(
            samples[0].predicted_retrievability,
            0.0,
        )
        self.assertLessEqual(
            samples[0].predicted_retrievability,
            1.0,
        )
        self.assertEqual(samples[0].actual_score, 1.0)

    def test_sufficiency_requires_real_volume_and_coverage(self):
        report = calibration_report(
            sufficient_history()
        )
        self.assertEqual(
            report.status,
            "SUFFICIENT_FOR_C9_ANALYSIS",
        )
        self.assertEqual(report.sample_count, 20)
        self.assertEqual(report.skill_track_count, 5)
        self.assertGreaterEqual(report.date_count, 4)

    def test_policy_comparison_never_auto_selects_winner_in_c7(self):
        candidate = MemoryPolicy(
            version="apcs-memory-candidate-test",
            min_stability_days=0.75,
        )
        comparison = compare_policies(
            sufficient_history(),
            [BASELINE_POLICY, candidate],
        )
        self.assertTrue(comparison["all_sufficient"])
        self.assertEqual(
            comparison["decision"],
            "DEFER_TO_C9",
        )
        self.assertIsNone(
            comparison["selected_policy"]
        )

    def test_feature_flag_defaults_to_v01_and_can_rollback(self):
        with tempfile.TemporaryDirectory() as temp:
            candidate = MemoryPolicy(
                version="apcs-memory-candidate-test",
                min_stability_days=0.75,
            )
            registry = {
                BASELINE_VERSION: BASELINE_POLICY,
                candidate.version: candidate,
            }
            flag = MemoryPolicyFlag(
                Path(temp),
                registry=registry,
            )

            self.assertEqual(
                flag.resolve().version,
                BASELINE_VERSION,
            )
            self.assertEqual(
                flag.set_active(candidate.version).version,
                candidate.version,
            )
            self.assertEqual(
                flag.resolve().version,
                candidate.version,
            )
            self.assertEqual(
                flag.rollback().version,
                BASELINE_VERSION,
            )

    def test_unknown_policy_cannot_be_activated(self):
        with tempfile.TemporaryDirectory() as temp:
            flag = MemoryPolicyFlag(Path(temp))
            with self.assertRaisesRegex(
                CalibrationError,
                "未註冊",
            ):
                flag.set_active("mystery-policy")

    def test_policy_version_change_triggers_full_memory_rebuild(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "memory.json"
            rows = (
                env(
                    day=0,
                    skill="S01_TEST",
                    novelty="new",
                ),
                env(
                    day=2,
                    skill="S01_TEST",
                    novelty="delayed_retest",
                ),
            )

            baseline = SkillMemoryStore(
                path,
                policy=BASELINE_POLICY,
            )
            baseline.reconcile(rows)

            candidate = MemoryPolicy(
                version="apcs-memory-candidate-test",
                min_stability_days=0.75,
            )
            changed = SkillMemoryStore(
                path,
                policy=candidate,
            )
            report = changed.reconcile(rows)

            self.assertTrue(report.rebuilt)
            self.assertEqual(
                changed.load_raw()["policy_version"],
                candidate.version,
            )


if __name__ == "__main__":
    unittest.main()
