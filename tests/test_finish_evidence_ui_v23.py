import datetime as dt
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.apcs_control import (
    attempt_envelope_for_record,
    independent_menu,
)
from tools.runtime_curriculum import (
    PlacementContext,
)


TZ = dt.timezone(dt.timedelta(hours=8))
FINISHED = dt.datetime(
    2026,
    10,
    1,
    18,
    30,
    tzinfo=TZ,
)


def problem():
    return {
        "id": "a693",
        "path": Path(
            "/tmp/a693.cpp"
        ),
    }


def placement():
    return PlacementContext(
        placement_uid="PL-001",
        pb_uid="PB-001",
        problem_id="a693",
        title="Prefix Sum",
        url="https://example.invalid/a693",
        difficulty="D2",
        primary_skill="S22_Prefix_Sum",
        supporting_skills=(
            "S05_Array",
            "S03_Loops",
        ),
        role="Core Independent",
        lesson_uid="L-PFX-01",
        lesson_order=1,
    )


class FinishEvidenceUiV23Test(unittest.TestCase):
    def test_finish_uses_primary_skill_only(self):
        envelope = attempt_envelope_for_record(
            action="finish",
            problem=problem(),
            result="AC",
            minutes=18,
            assistance=0,
            independent=True,
            novelty="new",
            timed=False,
            placement=placement(),
            finished_at=FINISHED,
        )

        self.assertEqual(
            envelope.attempt.pb_uid,
            "PB-001",
        )
        self.assertEqual(
            envelope.attempt.activity,
            "Core Independent",
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
            {
                item.skill_uid
                for item in envelope.evidence
            },
        )

    def test_review_uses_review_activity(self):
        envelope = attempt_envelope_for_record(
            action="review",
            problem=problem(),
            result="AC",
            minutes=9,
            assistance=1,
            independent=True,
            novelty="delayed_retest",
            timed=True,
            placement=placement(),
            finished_at=FINISHED,
        )

        self.assertEqual(
            envelope.attempt.activity,
            "Review",
        )
        self.assertTrue(
            envelope.attempt.timed
        )

    def test_failed_judge_maps_to_failed_implementation_evidence(self):
        envelope = attempt_envelope_for_record(
            action="review",
            problem=problem(),
            result="WA",
            minutes=10,
            assistance=0,
            independent=True,
            novelty="delayed_retest",
            timed=False,
            placement=placement(),
            finished_at=FINISHED,
        )

        self.assertEqual(
            envelope.evidence[0].outcome,
            "FAIL",
        )

    def test_missing_published_placement_keeps_attempt_without_evidence(self):
        envelope = attempt_envelope_for_record(
            action="finish",
            problem=problem(),
            result="AC",
            minutes=None,
            assistance=0,
            independent=True,
            novelty="new",
            timed=False,
            placement=None,
            finished_at=FINISHED,
        )

        self.assertIsNone(
            envelope.attempt.pb_uid
        )
        self.assertIsNone(
            envelope.attempt.activity
        )
        self.assertEqual(
            envelope.evidence,
            (),
        )

    def test_start_time_is_not_invented_from_minutes(self):
        envelope = attempt_envelope_for_record(
            action="finish",
            problem=problem(),
            result="AC",
            minutes=18,
            assistance=0,
            independent=True,
            novelty="new",
            timed=False,
            placement=placement(),
            finished_at=FINISHED,
        )

        self.assertIsNone(
            envelope.attempt.started_at
        )
        self.assertEqual(
            envelope.attempt.active_minutes,
            18,
        )

    def test_a2_plus_is_never_marked_independent(self):
        for assistance in (2, 3, 4, 5):
            self.assertFalse(
                independent_menu(
                    problem(),
                    assistance,
                )
            )

    def test_a0_a1_ask_instead_of_guessing_independence(self):
        with patch(
            "tools.apcs_control.yes_no_menu",
            return_value=False,
        ) as menu:
            value = independent_menu(
                problem(),
                1,
            )

        self.assertFalse(value)
        menu.assert_called_once()


if __name__ == "__main__":
    unittest.main()
