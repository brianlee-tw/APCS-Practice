import datetime as dt
import unittest

from tools.attempt_capture import (
    build_attempt_envelope,
    evidence_outcome_from_judge,
    language_from_path,
)
from tools.runtime_curriculum import (
    PlacementContext,
    SkillContext,
)


TZ = dt.timezone(dt.timedelta(hours=8))
DONE = dt.datetime(2026, 10, 1, 18, 30, tzinfo=TZ)


def placement(role="Core Independent"):
    return PlacementContext(
        placement_uid="PL-PFX-01-A693",
        pb_uid="PB-93",
        problem_id="a693",
        problem_title="吞食天地",
        problem_url="https://example.invalid/a693",
        difficulty="D2",
        primary_skill=SkillContext(
            uid="S22_Prefix_Sum",
            name="Prefix Sum",
            unit="U-PFX",
            path_stage="Bridge",
        ),
        supporting_skills=(
            SkillContext(
                uid="S05_Array",
                name="Array",
                unit="U-DAT",
                path_stage="Foundation",
            ),
        ),
        role=role,
        lesson_uid="L-PFX-01",
        lesson_order=3,
    )


class AttemptCaptureV23Test(unittest.TestCase):
    def test_language_from_path(self):
        self.assertEqual(
            language_from_path("x.cpp"),
            "cpp",
        )
        self.assertEqual(
            language_from_path("x.py"),
            "python",
        )

    def test_judge_result_maps_only_to_observed_implementation_outcome(self):
        self.assertEqual(
            evidence_outcome_from_judge("AC"),
            "PASS",
        )

        for result in [
            "WA",
            "TLE",
            "MLE",
            "RE",
            "CE",
        ]:
            self.assertEqual(
                evidence_outcome_from_judge(
                    result
                ),
                "FAIL",
            )

    def test_published_placement_creates_primary_skill_claim_only(self):
        envelope = build_attempt_envelope(
            action="finish",
            problem_id="a693",
            problem_path="solutions/a693.cpp",
            judge_result="AC",
            finished_at=DONE,
            minutes=18,
            assistance=0,
            independent=True,
            novelty="transfer",
            placement=placement(),
        )

        self.assertEqual(
            envelope.attempt.pb_uid,
            "PB-93",
        )
        self.assertEqual(
            envelope.attempt.placement_uid,
            "PL-PFX-01-A693",
        )
        self.assertEqual(
            envelope.attempt.activity,
            "Core Independent",
        )
        self.assertEqual(
            envelope.attempt.started_at,
            None,
        )
        self.assertEqual(
            len(envelope.evidence),
            1,
        )

        claim = envelope.evidence[0]

        self.assertEqual(
            claim.skill_uid,
            "S22_Prefix_Sum",
        )
        self.assertEqual(
            claim.track,
            "Implementation",
        )
        self.assertEqual(
            claim.outcome,
            "PASS",
        )

        self.assertNotIn(
            "S05_Array",
            [
                item.skill_uid
                for item in envelope.evidence
            ],
        )

    def test_review_uses_review_activity(self):
        envelope = build_attempt_envelope(
            action="review",
            problem_id="a693",
            problem_path="solutions/a693.cpp",
            judge_result="WA",
            finished_at=DONE,
            minutes=12,
            assistance=1,
            independent=False,
            novelty="delayed_retest",
            placement=placement(),
        )

        self.assertEqual(
            envelope.attempt.activity,
            "Review",
        )
        self.assertEqual(
            envelope.evidence[0].outcome,
            "FAIL",
        )

    def test_worked_example_does_not_auto_claim_skill_evidence(self):
        envelope = build_attempt_envelope(
            action="finish",
            problem_id="a693",
            problem_path="solutions/a693.cpp",
            judge_result="AC",
            finished_at=DONE,
            minutes=10,
            assistance=4,
            independent=False,
            novelty="seen",
            placement=placement(
                role="Worked Example"
            ),
        )

        self.assertEqual(
            envelope.evidence,
            (),
        )
        self.assertIsNone(
            envelope.attempt.activity
        )

    def test_missing_published_context_still_captures_attempt_without_evidence(self):
        envelope = build_attempt_envelope(
            action="finish",
            problem_id="a693",
            problem_path="solutions/a693.cpp",
            judge_result="AC",
            finished_at=DONE,
            minutes=18,
            assistance=0,
            independent=True,
            novelty="new",
            placement=None,
        )

        self.assertIsNone(
            envelope.attempt.pb_uid
        )
        self.assertIsNone(
            envelope.attempt.placement_uid
        )
        self.assertEqual(
            envelope.evidence,
            (),
        )


if __name__ == "__main__":
    unittest.main()
