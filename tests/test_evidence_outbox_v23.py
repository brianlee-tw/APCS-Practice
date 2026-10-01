import datetime as dt
import tempfile
import unittest
from pathlib import Path

from tools.evidence_outbox import (
    EvidenceClaim,
    EvidenceOutbox,
    EvidenceOutboxError,
    OutboxEnvelope,
    build_envelope,
    memory_evidence,
)


TZ = dt.timezone(dt.timedelta(hours=8))
START = dt.datetime(2026, 10, 1, 18, 0, tzinfo=TZ)
END = dt.datetime(2026, 10, 1, 18, 18, tzinfo=TZ)


def sample_envelope(**overrides):
    values = {
        "problem_id": "a693",
        "pb_uid": "93",
        "started_at": START,
        "finished_at": END,
        "language": "cpp",
        "judge_result": "AC",
        "assistance": 0,
        "independent": True,
        "attempt_count": 1,
        "active_minutes": 18,
        "timed": False,
        "novelty": "transfer",
        "activity": "Core Independent",
        "evidence": [
            (
                "S22_Prefix_Sum",
                "Implementation",
                "PASS",
                "clean independent transfer",
            )
        ],
        "attempt_id": "att_test_001",
        "writeback_id": "wb_test_001",
        "created_at": END,
    }
    values.update(overrides)
    return build_envelope(**values)


class EvidenceOutboxV23Test(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.runtime_dir = (
            Path(self.temp.name)
            / ".apcs"
            / "runtime"
        )
        self.store = EvidenceOutbox(
            self.runtime_dir
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_round_trip_preserves_attempt_facts(self):
        envelope = sample_envelope()

        self.assertTrue(
            self.store.enqueue(envelope)
        )

        loaded = self.store.load(
            envelope.writeback_id
        )

        self.assertEqual(
            loaded,
            envelope,
        )
        self.assertEqual(
            loaded.attempt.assistance,
            0,
        )
        self.assertTrue(
            loaded.attempt.independent
        )
        self.assertEqual(
            loaded.attempt.novelty,
            "transfer",
        )

    def test_enqueue_same_payload_is_idempotent(self):
        envelope = sample_envelope()

        self.assertTrue(
            self.store.enqueue(envelope)
        )
        self.assertFalse(
            self.store.enqueue(envelope)
        )

        self.assertEqual(
            len(self.store.pending()),
            1,
        )

    def test_conflicting_writeback_id_is_rejected(self):
        first = sample_envelope()
        second = sample_envelope(
            judge_result="WA",
        )

        self.store.enqueue(first)

        with self.assertRaisesRegex(
            EvidenceOutboxError,
            "different payload",
        ):
            self.store.enqueue(second)

    def test_receipt_removes_item_from_pending_without_deleting_event(self):
        envelope = sample_envelope()

        self.store.enqueue(envelope)

        self.assertEqual(
            len(self.store.pending()),
            1,
        )

        self.assertTrue(
            self.store.mark_sent(
                envelope.writeback_id,
                {
                    "rec_page_id": "rec-123",
                    "evidence_page_ids": [
                        "ev-456",
                    ],
                },
            )
        )

        self.assertEqual(
            self.store.pending(),
            (),
        )

        # Immutable local envelope remains available for audit/reconciliation.
        self.assertEqual(
            self.store.load(
                envelope.writeback_id
            ),
            envelope,
        )

    def test_same_receipt_is_idempotent(self):
        envelope = sample_envelope()
        receipt = {
            "rec_page_id": "rec-123",
        }

        self.store.enqueue(envelope)

        self.assertTrue(
            self.store.mark_sent(
                envelope.writeback_id,
                receipt,
            )
        )
        self.assertFalse(
            self.store.mark_sent(
                envelope.writeback_id,
                receipt,
            )
        )

    def test_conflicting_receipt_is_rejected(self):
        envelope = sample_envelope()

        self.store.enqueue(envelope)
        self.store.mark_sent(
            envelope.writeback_id,
            {
                "rec_page_id": "rec-123",
            },
        )

        with self.assertRaisesRegex(
            EvidenceOutboxError,
            "different payload",
        ):
            self.store.mark_sent(
                envelope.writeback_id,
                {
                    "rec_page_id": "rec-999",
                },
            )

    def test_unknown_facts_remain_unknown_in_durable_attempt(self):
        envelope = sample_envelope(
            assistance=None,
            independent=None,
            novelty=None,
        )

        self.store.enqueue(envelope)
        loaded = self.store.load(
            envelope.writeback_id
        )

        self.assertIsNone(
            loaded.attempt.assistance
        )
        self.assertIsNone(
            loaded.attempt.independent
        )
        self.assertIsNone(
            loaded.attempt.novelty
        )

    def test_unknown_facts_cannot_update_adaptive_memory(self):
        envelope = sample_envelope(
            assistance=None,
            independent=None,
            novelty=None,
        )

        with self.assertRaisesRegex(
            EvidenceOutboxError,
            "requires explicit assistance, independent, novelty",
        ):
            memory_evidence(envelope)

    def test_explicit_claim_converts_to_skill_track_memory_evidence(self):
        envelope = sample_envelope()

        converted = memory_evidence(
            envelope
        )

        self.assertEqual(
            len(converted),
            1,
        )

        event = converted[0]

        self.assertEqual(
            event.skill_uid,
            "S22_Prefix_Sum",
        )
        self.assertEqual(
            event.track,
            "Implementation",
        )
        self.assertEqual(
            event.outcome,
            "PASS",
        )
        self.assertEqual(
            event.occurred_on,
            END.date(),
        )
        self.assertEqual(
            event.problem_id,
            "a693",
        )

    def test_one_attempt_can_observe_multiple_distinct_skill_tracks(self):
        envelope = sample_envelope(
            evidence=[
                (
                    "S22_Prefix_Sum",
                    "Implementation",
                    "PASS",
                    "",
                ),
                (
                    "S30_Complexity",
                    "Reading",
                    "PASS",
                    "",
                ),
            ]
        )

        converted = memory_evidence(
            envelope
        )

        self.assertEqual(
            {
                (
                    item.skill_uid,
                    item.track,
                )
                for item in converted
            },
            {
                (
                    "S22_Prefix_Sum",
                    "Implementation",
                ),
                (
                    "S30_Complexity",
                    "Reading",
                ),
            },
        )

    def test_duplicate_skill_track_claim_is_rejected(self):
        with self.assertRaisesRegex(
            EvidenceOutboxError,
            "at most one evidence claim",
        ):
            sample_envelope(
                evidence=[
                    (
                        "S22_Prefix_Sum",
                        "Implementation",
                        "PASS",
                        "",
                    ),
                    (
                        "S22_Prefix_Sum",
                        "Implementation",
                        "PASS",
                        "duplicate",
                    ),
                ]
            )

    def test_unknown_start_time_is_preserved(self):
        envelope = sample_envelope(
            started_at=None,
        )

        self.store.enqueue(envelope)

        loaded = self.store.load(
            envelope.writeback_id
        )

        self.assertIsNone(
            loaded.attempt.started_at
        )

    def test_naive_known_timestamp_is_rejected(self):
        with self.assertRaisesRegex(
            EvidenceOutboxError,
            "timezone-aware",
        ):
            sample_envelope(
                started_at=dt.datetime(
                    2026,
                    10,
                    1,
                    18,
                    0,
                )
            )

    def test_active_minutes_does_not_imply_timed_condition(self):
        envelope = sample_envelope(
            active_minutes=18,
            timed=False,
        )

        converted = memory_evidence(
            envelope
        )

        self.assertFalse(
            converted[0].timed
        )

    def test_finish_cannot_precede_start(self):
        with self.assertRaisesRegex(
            EvidenceOutboxError,
            "finished_at cannot be earlier",
        ):
            sample_envelope(
                started_at=END,
                finished_at=START,
            )

    def test_envelope_deserialization_validates_claims(self):
        envelope = sample_envelope()
        raw = envelope.to_dict()
        raw["evidence"][0][
            "outcome"
        ] = "MAYBE"

        with self.assertRaisesRegex(
            EvidenceOutboxError,
            "invalid evidence outcome",
        ):
            OutboxEnvelope.from_dict(raw)

    def test_claims_are_explicit_not_inferred_from_problem_tags(self):
        envelope = sample_envelope(
            evidence=[],
        )

        self.assertEqual(
            envelope.evidence,
            (),
        )
        self.assertEqual(
            memory_evidence(envelope),
            (),
        )


if __name__ == "__main__":
    unittest.main()
