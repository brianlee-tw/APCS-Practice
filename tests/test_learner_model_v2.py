from __future__ import annotations

import datetime as dt
import tempfile
import unittest
from pathlib import Path

from tools.evidence_outbox import build_envelope
from tools.learner_model_v2 import (
    LearnerModelError,
    LearnerSignalStore,
    derive_skill_track_models,
    learner_model_snapshot,
    repeated_bottlenecks,
)


TZ = dt.timezone(dt.timedelta(hours=8))


def make_envelope(
    *,
    day: int,
    problem: str,
    skill: str,
    outcome: str,
    assistance: int | None,
    independent: bool | None,
    novelty: str,
    track: str = "Implementation",
):
    when = dt.datetime(2026, 10, day, 20, 0, tzinfo=TZ)
    return build_envelope(
        problem_id=problem,
        started_at=when - dt.timedelta(minutes=8),
        finished_at=when,
        language="cpp",
        judge_result="AC" if outcome == "PASS" else "WA",
        evidence=[(skill, track, outcome, "test")],
        assistance=assistance,
        independent=independent,
        attempt_count=1,
        active_minutes=8,
        timed=False,
        novelty=novelty,
        activity="Core Independent",
        attempt_id=f"att_{problem}_{day}",
        writeback_id=f"wb_{problem}_{day}",
        created_at=when,
    )


class LearnerModelV2Test(unittest.TestCase):
    def test_hint_dependence_derived_from_real_assistance(self):
        envelopes = (
            make_envelope(
                day=1,
                problem="p1",
                skill="S20_DP",
                outcome="PASS",
                assistance=3,
                independent=False,
                novelty="new",
            ),
            make_envelope(
                day=2,
                problem="p2",
                skill="S20_DP",
                outcome="PASS",
                assistance=2,
                independent=False,
                novelty="seen",
            ),
        )
        model = derive_skill_track_models(envelopes)[0]
        self.assertEqual(model.hint_dependence, "HIGH")
        self.assertEqual(model.assisted_count, 2)

    def test_one_a0_pass_is_ready_for_transfer_not_mastery(self):
        model = derive_skill_track_models(
            (
                make_envelope(
                    day=1,
                    problem="p1",
                    skill="S10_Binary_Search",
                    outcome="PASS",
                    assistance=0,
                    independent=True,
                    novelty="new",
                ),
            )
        )[0]
        self.assertEqual(model.transfer_state, "READY_FOR_TRANSFER")
        self.assertEqual(model.transfer_passes, 0)

    def test_transfer_pass_marks_only_transfer_state_verified(self):
        model = derive_skill_track_models(
            (
                make_envelope(
                    day=1,
                    problem="p1",
                    skill="S10_Binary_Search",
                    outcome="PASS",
                    assistance=0,
                    independent=True,
                    novelty="transfer",
                ),
            )
        )[0]
        self.assertEqual(model.transfer_state, "VERIFIED")
        self.assertEqual(model.transfer_passes, 1)

    def test_single_bottleneck_never_becomes_durable_candidate(self):
        rows = (
            {
                "schema_version": "apcs-learner-signal-v1",
                "type": "bottleneck",
                "occurred_at": "2026-10-01T20:00:00+08:00",
                "skill_uid": "S20_DP",
                "problem_id": "p1",
                "category": "Representation",
                "root_cause": "state 定義混亂",
                "source": "explicit",
            },
        )
        self.assertEqual(repeated_bottlenecks(rows), ())

    def test_same_root_cause_must_repeat_on_distinct_problems(self):
        rows = (
            {
                "schema_version": "apcs-learner-signal-v1",
                "type": "bottleneck",
                "occurred_at": "2026-10-01T20:00:00+08:00",
                "skill_uid": "S20_DP",
                "problem_id": "p1",
                "category": "Representation",
                "root_cause": "state 定義混亂",
                "source": "explicit",
            },
            {
                "schema_version": "apcs-learner-signal-v1",
                "type": "bottleneck",
                "occurred_at": "2026-10-02T20:00:00+08:00",
                "skill_uid": "S20_DP",
                "problem_id": "p2",
                "category": "Representation",
                "root_cause": "state 定義混亂",
                "source": "explicit",
            },
        )
        result = repeated_bottlenecks(rows)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].distinct_problems, ("p1", "p2"))

    def test_repeating_same_problem_is_not_misconception_candidate(self):
        rows = (
            {
                "schema_version": "apcs-learner-signal-v1",
                "type": "bottleneck",
                "occurred_at": "2026-10-01T20:00:00+08:00",
                "skill_uid": "S20_DP",
                "problem_id": "p1",
                "category": "Implementation",
                "root_cause": "index 起點錯",
                "source": "explicit",
            },
            {
                "schema_version": "apcs-learner-signal-v1",
                "type": "bottleneck",
                "occurred_at": "2026-10-02T20:00:00+08:00",
                "skill_uid": "S20_DP",
                "problem_id": "p1",
                "category": "Implementation",
                "root_cause": "index 起點錯",
                "source": "explicit",
            },
        )
        self.assertEqual(repeated_bottlenecks(rows), ())

    def test_confidence_sampling_is_optional_and_not_readiness(self):
        with tempfile.TemporaryDirectory() as temp:
            store = LearnerSignalStore(Path(temp))
            store.record_confidence(
                skill_uid="S18_DFS",
                track="Implementation",
                confidence=60,
                activity="Transfer Challenge",
                problem_id="p1",
                occurred_at=dt.datetime(
                    2026, 10, 3, 20, 0, tzinfo=TZ
                ),
            )
            snapshot = learner_model_snapshot((), store.load())
            self.assertEqual(len(snapshot["confidence_samples"]), 1)
            self.assertEqual(snapshot["readiness"], "NOT_ASSESSED")

    def test_confidence_rejects_arbitrary_scale(self):
        with tempfile.TemporaryDirectory() as temp:
            store = LearnerSignalStore(Path(temp))
            with self.assertRaisesRegex(
                LearnerModelError,
                "30 / 60 / 90",
            ):
                store.record_confidence(
                    skill_uid="S18_DFS",
                    track="Implementation",
                    confidence=75,
                    activity="Mock",
                    problem_id="p1",
                )

    def test_snapshot_has_no_mastery_score(self):
        snapshot = learner_model_snapshot(())
        self.assertNotIn("mastery", snapshot)
        self.assertNotIn("score", snapshot)
        self.assertEqual(snapshot["readiness"], "NOT_ASSESSED")


if __name__ == "__main__":
    unittest.main()
