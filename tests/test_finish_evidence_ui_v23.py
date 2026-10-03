import datetime as dt
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.apcs_control import (
    RECORD_BACK,
    attempt_envelope_for_record,
    display_width,
    evidence_context_menu,
    independent_menu,
    ui_width,
    wrap_display,
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


def confirmation_placement():
    return PlacementContext(
        placement_uid="PL-002",
        pb_uid="PB-002",
        problem_id="a693",
        title="Prefix Sum Alternate",
        url="https://example.invalid/a693",
        difficulty="D2",
        primary_skill="S22_Prefix_Sum",
        supporting_skills=(),
        role="Core Independent",
        lesson_uid="L-PFX-01",
        lesson_order=2,
        evidence_level_cap=3,
        method_confirmation_required=True,
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

    def test_unconfirmed_target_method_keeps_attempt_without_skill_evidence(self):
        envelope = attempt_envelope_for_record(
            action="finish",
            problem=problem(),
            result="AC",
            minutes=12,
            assistance=0,
            independent=True,
            novelty="new",
            timed=False,
            placement=confirmation_placement(),
            method_confirmed=False,
            finished_at=FINISHED,
        )

        self.assertEqual(
            envelope.attempt.pb_uid,
            "PB-002",
        )
        self.assertEqual(
            envelope.evidence,
            (),
        )
        self.assertIn(
            "target method not confirmed",
            envelope.attempt.note,
        )

    def test_confirmed_target_method_emits_primary_skill_evidence(self):
        envelope = attempt_envelope_for_record(
            action="finish",
            problem=problem(),
            result="AC",
            minutes=12,
            assistance=0,
            independent=True,
            novelty="new",
            timed=False,
            placement=confirmation_placement(),
            method_confirmed=True,
            finished_at=FINISHED,
        )

        self.assertEqual(
            len(envelope.evidence),
            1,
        )
        self.assertEqual(
            envelope.evidence[0].skill_uid,
            "S22_Prefix_Sum",
        )
        self.assertIn(
            "target method confirmed",
            envelope.evidence[0].note,
        )

    def test_required_confirmation_does_not_guess_true_when_omitted(self):
        envelope = attempt_envelope_for_record(
            action="finish",
            problem=problem(),
            result="AC",
            minutes=12,
            assistance=0,
            independent=True,
            novelty="new",
            timed=False,
            placement=confirmation_placement(),
            finished_at=FINISHED,
        )

        self.assertEqual(
            envelope.evidence,
            (),
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

    def test_ui_width_uses_available_terminal_width(self):
        with patch(
            "tools.apcs_control.shutil.get_terminal_size",
            return_value=os.terminal_size((96, 24)),
        ):
            self.assertEqual(
                ui_width(),
                94,
            )

    def test_wrap_display_preserves_all_text(self):
        text = (
            "方法與實作主要由你自行完成；"
            "A0/A1 可成立"
        )

        lines = wrap_display(
            text,
            12,
        )

        self.assertGreater(
            len(lines),
            1,
        )
        self.assertEqual(
            "".join(lines),
            text,
        )
        self.assertNotIn(
            "…",
            "".join(lines),
        )
        self.assertTrue(
            all(
                display_width(line) <= 12
                for line in lines
            )
        )

    def test_evidence_context_back_keeps_attempt_local(self):
        with (
            patch(
                "tools.apcs_control.placement_for_record",
                return_value=(
                    placement(),
                    None,
                ),
            ),
            patch(
                "tools.apcs_control.assistance_menu",
                return_value=None,
            ),
        ):
            value = evidence_context_menu(
                "finish",
                problem(),
            )

        self.assertIs(
            value,
            RECORD_BACK,
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
