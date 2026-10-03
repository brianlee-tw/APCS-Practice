import datetime as dt
import unittest

from tools.evidence_outbox import (
    build_envelope,
)
from tools.remote_writeback import (
    RemoteWritebackError,
    build_remote_writeback_bundle,
    derive_rec_stage,
    notion_projection,
    validate_remote_receipt,
)


TZ = dt.timezone(dt.timedelta(hours=8))
END = dt.datetime(
    2026,
    10,
    2,
    6,
    0,
    tzinfo=TZ,
)


def sample_envelope(
    **overrides,
):
    values = {
        "problem_id": "CF-4A",
        "pb_uid": "PB-145",
        "started_at": None,
        "finished_at": END,
        "language": "cpp",
        "judge_result": "AC",
        "assistance": 1,
        "independent": True,
        "attempt_count": 1,
        "active_minutes": 11,
        "timed": False,
        "novelty": "transfer",
        "activity": "Core Independent",
        "evidence": [
            (
                "S02_Conditionals",
                "Implementation",
                "PASS",
                "clean condition model",
            )
        ],
        "attempt_id": "att_remote_001",
        "writeback_id": "wb_remote_001",
        "created_at": END,
    }
    values.update(
        overrides
    )
    return build_envelope(
        **values
    )


class RemoteWritebackV23Test(
    unittest.TestCase
):
    def test_bundle_preserves_stable_transaction_and_event_ids(self):
        bundle = (
            build_remote_writeback_bundle(
                sample_envelope()
            )
        )

        self.assertEqual(
            bundle.writeback_id,
            "wb_remote_001",
        )
        self.assertEqual(
            bundle.attempt.writeback_id,
            "wb_remote_001",
        )
        self.assertEqual(
            bundle.evidence[0].event_id,
            "wb_remote_001.ev1",
        )

    def test_bundle_preserves_exact_finished_at_for_offline_retry(self):
        bundle = (
            build_remote_writeback_bundle(
                sample_envelope()
            )
        )

        self.assertEqual(
            bundle.attempt.finished_at,
            END.isoformat(
                timespec="seconds"
            ),
        )
        self.assertEqual(
            bundle.evidence[0].occurred_at,
            END.isoformat(
                timespec="seconds"
            ),
        )

        projection = (
            notion_projection(
                bundle
            )
        )

        self.assertEqual(
            projection[
                "rec"
            ][
                "properties"
            ][
                "Attempt Finished At"
            ],
            END.isoformat(
                timespec="seconds"
            ),
        )

    def test_projection_uses_vscode_direct_and_lossless_novelty(self):
        projection = notion_projection(
            build_remote_writeback_bundle(
                sample_envelope()
            )
        )

        rec = projection[
            "rec"
        ][
            "properties"
        ]
        ev = projection[
            "evidence"
        ][0][
            "properties"
        ]

        self.assertEqual(
            rec["紀錄來源"],
            "VS Code Direct",
        )
        self.assertEqual(
            ev["Novelty"],
            "Transfer",
        )
        self.assertEqual(
            ev["Activity"],
            "Core Independent",
        )
        self.assertEqual(
            ev["Assistance"],
            "A1",
        )

    def test_mle_is_preserved_for_rec_and_evidence(self):
        projection = notion_projection(
            build_remote_writeback_bundle(
                sample_envelope(
                    judge_result="MLE",
                    evidence=[
                        (
                            "S02_Conditionals",
                            "Implementation",
                            "FAIL",
                            "memory limit",
                        )
                    ],
                )
            )
        )

        self.assertEqual(
            projection[
                "rec"
            ][
                "properties"
            ][
                "最新提交結果"
            ],
            "MLE",
        )
        self.assertEqual(
            projection[
                "evidence"
            ][0][
                "properties"
            ][
                "Judge Result"
            ],
            "MLE",
        )

    def test_projection_preserves_attempt_start_and_known_flags(self):
        started = END - dt.timedelta(
            minutes=11
        )
        projection = notion_projection(
            build_remote_writeback_bundle(
                sample_envelope(
                    started_at=started,
                    independent=False,
                    timed=False,
                )
            )
        )

        rec = projection[
            "rec"
        ][
            "properties"
        ]
        ev = projection[
            "evidence"
        ][0][
            "properties"
        ]

        self.assertEqual(
            rec["Attempt Started At"],
            started.isoformat(
                timespec="seconds"
            ),
        )
        self.assertTrue(
            rec["Independent Known"]
        )
        self.assertFalse(
            rec["獨立完成"]
        )
        self.assertTrue(
            ev["Independent Known"]
        )
        self.assertFalse(
            ev["Independent"]
        )
        self.assertTrue(
            ev["Timed Known"]
        )
        self.assertFalse(
            ev["Timed"]
        )

    def test_unknown_facts_remain_unknown_not_defaulted(self):
        projection = notion_projection(
            build_remote_writeback_bundle(
                sample_envelope(
                    assistance=None,
                    independent=None,
                    timed=None,
                    novelty=None,
                    activity=None,
                )
            )
        )

        rec = projection[
            "rec"
        ][
            "properties"
        ]
        ev = projection[
            "evidence"
        ][0][
            "properties"
        ]

        self.assertNotIn(
            "Assistance",
            rec,
        )
        self.assertNotIn(
            "獨立完成",
            rec,
        )
        self.assertFalse(
            rec["Independent Known"]
        )
        self.assertNotIn(
            "Attempt Started At",
            rec,
        )
        self.assertNotIn(
            "學習階段",
            rec,
        )
        self.assertNotIn(
            "Novelty",
            ev,
        )
        self.assertNotIn(
            "Independent",
            ev,
        )
        self.assertFalse(
            ev["Independent Known"]
        )
        self.assertNotIn(
            "Timed",
            ev,
        )
        self.assertFalse(
            ev["Timed Known"]
        )

    def test_valid_for_gate_is_never_client_supplied(self):
        projection = notion_projection(
            build_remote_writeback_bundle(
                sample_envelope()
            )
        )

        self.assertNotIn(
            "Valid for Gate",
            projection[
                "evidence"
            ][0][
                "properties"
            ],
        )

    def test_relations_are_canonical_ids_not_guessed_notion_pages(self):
        projection = notion_projection(
            build_remote_writeback_bundle(
                sample_envelope()
            )
        )

        self.assertEqual(
            projection[
                "rec"
            ][
                "relations"
            ],
            {
                "problem_pb_uid": "PB-145",
                "skill_uids": [
                    "S02_Conditionals",
                ],
            },
        )
        self.assertEqual(
            projection[
                "evidence"
            ][0][
                "relations"
            ],
            {
                "problem_pb_uid": "PB-145",
                "skill_uid": "S02_Conditionals",
                "solve_writeback_id": "wb_remote_001",
            },
        )

    def test_missing_published_pb_uid_fails_closed(self):
        envelope = sample_envelope(
            pb_uid=None,
            evidence=[],
        )

        with self.assertRaisesRegex(
            RemoteWritebackError,
            "requires Published PB UID",
        ):
            build_remote_writeback_bundle(
                envelope
            )

    def test_zero_evidence_attempt_projects_rec_only_and_accepts_empty_receipt_set(self):
        bundle = build_remote_writeback_bundle(
            sample_envelope(
                evidence=[],
            )
        )

        self.assertEqual(
            bundle.evidence,
            (),
        )

        projection = notion_projection(
            bundle
        )
        self.assertEqual(
            projection["evidence"],
            [],
        )
        self.assertEqual(
            projection["rec"]["relations"]["skill_uids"],
            [],
        )

        receipt = {
            "schema_version": "v2.3-remote-receipt-1",
            "writeback_id": bundle.writeback_id,
            "complete": True,
            "rec": {
                "page_id": "rec-page-zero-ev",
                "duplicate": False,
            },
            "evidence": [],
        }

        self.assertEqual(
            validate_remote_receipt(
                bundle,
                receipt,
            ),
            receipt,
        )

    def test_projection_is_deterministic_for_same_envelope(self):
        envelope = sample_envelope()

        first = notion_projection(
            build_remote_writeback_bundle(
                envelope
            )
        )
        second = notion_projection(
            build_remote_writeback_bundle(
                envelope
            )
        )

        self.assertEqual(
            first,
            second,
        )

    def test_complete_receipt_accepts_exact_event_set(self):
        bundle = (
            build_remote_writeback_bundle(
                sample_envelope()
            )
        )
        receipt = {
            "schema_version": "v2.3-remote-receipt-1",
            "writeback_id": bundle.writeback_id,
            "complete": True,
            "rec": {
                "page_id": "rec-page-1",
                "duplicate": False,
            },
            "evidence": [
                {
                    "event_id": (
                        bundle.evidence[0].event_id
                    ),
                    "page_id": "ev-page-1",
                    "duplicate": False,
                }
            ],
        }

        self.assertEqual(
            validate_remote_receipt(
                bundle,
                receipt,
            ),
            receipt,
        )

    def test_partial_receipt_is_rejected(self):
        bundle = (
            build_remote_writeback_bundle(
                sample_envelope()
            )
        )

        with self.assertRaisesRegex(
            RemoteWritebackError,
            "not complete",
        ):
            validate_remote_receipt(
                bundle,
                {
                    "schema_version": "v2.3-remote-receipt-1",
                    "writeback_id": bundle.writeback_id,
                    "complete": False,
                    "rec": {
                        "page_id": "rec-page-1",
                    },
                    "evidence": [],
                },
            )

    def test_receipt_missing_expected_event_is_rejected(self):
        bundle = (
            build_remote_writeback_bundle(
                sample_envelope()
            )
        )

        with self.assertRaisesRegex(
            RemoteWritebackError,
            "Evidence identity mismatch",
        ):
            validate_remote_receipt(
                bundle,
                {
                    "schema_version": "v2.3-remote-receipt-1",
                    "writeback_id": bundle.writeback_id,
                    "complete": True,
                    "rec": {
                        "page_id": "rec-page-1",
                    },
                    "evidence": [],
                },
            )

    def test_receipt_wrong_writeback_id_is_rejected(self):
        bundle = (
            build_remote_writeback_bundle(
                sample_envelope()
            )
        )

        with self.assertRaisesRegex(
            RemoteWritebackError,
            "writeback_id mismatch",
        ):
            validate_remote_receipt(
                bundle,
                {
                    "schema_version": "v2.3-remote-receipt-1",
                    "writeback_id": "wb_wrong",
                    "complete": True,
                    "rec": {
                        "page_id": "rec-page-1",
                    },
                    "evidence": [
                        {
                            "event_id": (
                                bundle.evidence[0].event_id
                            ),
                            "page_id": "ev-page-1",
                        }
                    ],
                },
            )

    def test_stage_is_derived_from_attempt_context_not_capability(self):
        self.assertEqual(
            derive_rec_stage(
                activity="Review",
                independent=True,
                timed=False,
            ),
            "複習驗證",
        )
        self.assertEqual(
            derive_rec_stage(
                activity="Core Independent",
                independent=True,
                timed=False,
            ),
            "獨立解題",
        )
        self.assertEqual(
            derive_rec_stage(
                activity="Guided Drill",
                independent=False,
                timed=False,
            ),
            "理解觀念",
        )
        self.assertEqual(
            derive_rec_stage(
                activity="Core Independent",
                independent=True,
                timed=True,
            ),
            "限時實戰",
        )
        self.assertIsNone(
            derive_rec_stage(
                activity=None,
                independent=None,
                timed=None,
            )
        )


if __name__ == "__main__":
    unittest.main()
