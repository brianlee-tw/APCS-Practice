"""Read-only evidence trust-boundary regression for APCS Test Center Pilot.

Covers local verdicts, Exam Runtime event epochs, user-recorded OJ results,
assistance and Skill x Track adaptive memory. Uses only synthetic events and
temporary paths; does not touch learner runtime files or Notion.
"""
from __future__ import annotations

import datetime as dt
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import apcs_control as control
from tools.evidence_outbox import (
    EvidenceOutboxError, build_envelope, memory_evidence,
)
from tools.local_test_runner import PASS, WRONG_OUTPUT, run_suite
from tools.test_assets import TestCase

TZ = dt.timezone(dt.timedelta(hours=8))
FINISHED = dt.datetime(2026, 10, 22, 19, 30, tzinfo=TZ)
PID = "cf-977c"


def exam_session(events, *, selected=PID):
    return {
        "selected_problem_id": selected,
        "events": events,
    }


def selection(pid=PID, action="SELECT"):
    return {"type": action, "problem_id": pid}


def submit(verdict="AC", pid=PID):
    return {"type": "SUBMIT", "problem_id": pid, "result": verdict}


def fresh_envelope(*, result="AC", assistance=0, independent=True, claims=None):
    if claims is None:
        claims = [("S09_Sorting", "Implementation", "PASS", "test")]
    return build_envelope(
        problem_id="CF-977C",
        pb_uid="PB-109",
        started_at=None,
        finished_at=FINISHED,
        language="cpp",
        judge_result=result,
        assistance=assistance,
        independent=independent,
        novelty="new",
        timed=False,
        activity="Core Independent",
        evidence=claims,
    )


class PilotEvidenceTrustBoundaryTest(unittest.TestCase):
    def test_explicit_current_exam_submit_can_be_reused(self):
        data = exam_session([
            {"type": "START"}, selection(),
            {"type": "COMPILE", "problem_id": PID, "success": True},
            submit("AC"),
        ])
        self.assertEqual(
            control.exam_verdict_for_current_selection(data, PID), "AC",
        )
        with patch.object(control.EXAM, "active", return_value=data):
            self.assertEqual(
                control.inferred_published_result({"id": "CF-977C"}),
                "AC",
            )
        failed = exam_session([selection(), submit("WA")])
        self.assertEqual(
            control.exam_verdict_for_current_selection(failed, PID), "WA",
        )

    def test_stale_ac_after_switch_away_and_back_is_not_inferred(self):
        data = exam_session([
            selection(), submit("AC"),
            selection("cf-71a", action="SWITCH"),
            selection(action="SWITCH"),
            {"type": "COMPILE", "problem_id": PID, "success": True},
        ])
        self.assertIsNone(
            control.exam_verdict_for_current_selection(data, PID)
        )
        with patch.object(control.EXAM, "active", return_value=data):
            self.assertIsNone(
                control.inferred_published_result({"id": "CF-977C"})
            )
        data["events"].append(submit("WA"))
        self.assertEqual(
            control.exam_verdict_for_current_selection(data, PID), "WA",
        )

    def test_unknown_newer_submit_cannot_resurrect_old_ac(self):
        data = exam_session([
            selection(), submit("AC"), submit("N/A"),
        ])
        self.assertIsNone(
            control.exam_verdict_for_current_selection(data, PID)
        )
        self.assertIsNone(
            control.exam_verdict_for_current_selection(
                exam_session([selection(), submit("AC")], selected="cf-71a"),
                PID,
            )
        )
        self.assertIsNone(
            control.exam_verdict_for_current_selection(
                exam_session([submit("AC")]), PID
            ),
            "Without SELECT/SWITCH epoch, no inherited authority",
        )

    def test_local_pass_does_not_record_any_attempt_or_skill_evidence(self):
        # An actual local subprocess outcome is not an OJ AC.
        case = TestCase(
            case_id="T1", name="synthetic", input_text="3\n",
            expected_output="3\n", provenance="OFFICIAL",
            trust="OFFICIAL", suite="fast", visibility="official",
        )
        bad = TestCase(
            case_id="T2", name="synthetic wrong expected",
            input_text="3\n", expected_output="4\n",
            provenance="OFFICIAL", trust="OFFICIAL",
            suite="fast", visibility="official",
        )
        with tempfile.TemporaryDirectory() as td:
            with (
                patch.object(control.OUTBOX, "enqueue") as enqueue,
                patch.object(control.MEMORY, "reconcile") as reconcile,
            ):
                report = run_suite(
                    Path("/bin/cat"), (case, bad), root=Path(td)
                )
                self.assertEqual(
                    [x.status for x in report.cases], [PASS, WRONG_OUTPUT]
                )
                enqueue.assert_not_called()
                reconcile.assert_not_called()

    def test_local_pass_cannot_be_used_as_an_oj_result(self):
        with self.assertRaisesRegex(
            EvidenceOutboxError, "invalid judge_result",
        ):
            fresh_envelope(result="PASS")

    def test_a2_to_a5_can_never_be_independent_even_via_raw_envelope(self):
        for tier in range(2, 6):
            with self.subTest(tier=tier):
                with self.assertRaisesRegex(
                    EvidenceOutboxError, "A2\\+ assistance",
                ):
                    fresh_envelope(assistance=tier, independent=True)
        allowed = fresh_envelope(assistance=3, independent=False)
        self.assertFalse(allowed.attempt.independent)
        self.assertEqual(memory_evidence(allowed)[0].assistance, 3)

    def test_local_or_unknown_result_cannot_create_implementation_pass_memory(self):
        envelope = fresh_envelope(result="WA")
        with self.assertRaisesRegex(
            EvidenceOutboxError, "contradicts recorded OJ",
        ):
            memory_evidence(envelope)
        missing = fresh_envelope(result="N/A")
        with self.assertRaisesRegex(
            EvidenceOutboxError, "contradicts recorded OJ",
        ):
            memory_evidence(missing)

    def test_raw_ac_cannot_back_an_implementation_fail_claim(self):
        attempt = fresh_envelope(
            result="AC",
            claims=[("S09_Sorting", "Implementation", "FAIL", "mismatch")],
        )
        with self.assertRaisesRegex(
            EvidenceOutboxError, "contradicts recorded OJ",
        ):
            memory_evidence(attempt)

    def test_mixed_reading_claim_remains_allowed_with_explicit_oj_ac(self):
        attempt = fresh_envelope(
            claims=[
                ("S09_Sorting", "Implementation", "PASS", "AC"),
                ("S30_Complexity", "Reading", "PASS", "response first"),
            ],
        )
        self.assertEqual(len(memory_evidence(attempt)), 2)

    def test_review_with_a2_plus_is_not_independent_skill_mastery(self):
        # Assistance and independence should not be inferred from PASS.
        for assistance in (2, 4, 5):
            attempt = fresh_envelope(assistance=assistance, independent=False)
            evidence = memory_evidence(attempt)
            self.assertFalse(evidence[0].independent)
            self.assertEqual(evidence[0].assistance, assistance)

    def test_tampered_replayed_data_rejected_during_deserialization(self):
        from tools.evidence_outbox import OutboxEnvelope
        good = fresh_envelope()
        tampered = good.to_dict()
        tampered["attempt"]["assistance"] = 4
        tampered["attempt"]["independent"] = True
        with self.assertRaisesRegex(EvidenceOutboxError, "A2\\+ assistance"):
            OutboxEnvelope.from_dict(tampered)


if __name__ == "__main__":
    unittest.main()
