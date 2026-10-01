import datetime as dt
import tempfile
import unittest
from pathlib import Path

from tools.adaptive_memory import MemoryPolicy
from tools.evidence_outbox import build_envelope
from tools.skill_memory_store import (
    SCHEMA_VERSION,
    SkillMemoryStore,
)


TZ = dt.timezone(dt.timedelta(hours=8))
DAY0 = dt.datetime(2026, 10, 1, 18, 0, tzinfo=TZ)


def envelope(
    *,
    writeback_id,
    finished_at,
    outcome="PASS",
    assistance=0,
    independent=True,
    novelty="transfer",
    skill_uid="S22_Prefix_Sum",
    track="Implementation",
):
    return build_envelope(
        problem_id="a693",
        pb_uid="PB-001",
        started_at=None,
        finished_at=finished_at,
        language="cpp",
        judge_result="AC" if outcome == "PASS" else "WA",
        assistance=assistance,
        independent=independent,
        attempt_count=1,
        active_minutes=12,
        timed=False,
        novelty=novelty,
        activity="Review",
        evidence=[
            (
                skill_uid,
                track,
                outcome,
                "",
            )
        ],
        attempt_id=f"att_{writeback_id}",
        writeback_id=writeback_id,
        created_at=finished_at,
    )


class SkillMemoryStoreV23Test(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = (
            Path(self.temp.name)
            / "skill_memory.json"
        )
        self.store = SkillMemoryStore(
            self.path
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_reconcile_persists_state(self):
        report = self.store.reconcile(
            [
                envelope(
                    writeback_id="wb1",
                    finished_at=DAY0,
                )
            ]
        )

        self.assertEqual(
            report.applied_events,
            1,
        )
        self.assertEqual(
            report.states,
            1,
        )

        states = self.store.load_states()

        state = states[
            (
                "S22_Prefix_Sum",
                "Implementation",
            )
        ]

        self.assertEqual(
            state.evidence_count,
            1,
        )
        self.assertEqual(
            state.last_evidence_on,
            DAY0.date(),
        )

        raw = self.store.load_raw()
        self.assertEqual(
            raw["schema_version"],
            SCHEMA_VERSION,
        )

    def test_reconcile_is_idempotent(self):
        item = envelope(
            writeback_id="wb1",
            finished_at=DAY0,
        )

        first = self.store.reconcile(
            [item]
        )
        second = self.store.reconcile(
            [item]
        )

        self.assertEqual(
            first.applied_events,
            1,
        )
        self.assertEqual(
            second.applied_events,
            0,
        )

        state = self.store.load_states()[
            (
                "S22_Prefix_Sum",
                "Implementation",
            )
        ]

        self.assertEqual(
            state.evidence_count,
            1,
        )

    def test_incomplete_evidence_is_skipped_not_guessed(self):
        incomplete = build_envelope(
            problem_id="a693",
            pb_uid="PB-001",
            started_at=None,
            finished_at=DAY0,
            language="cpp",
            judge_result="AC",
            assistance=None,
            independent=None,
            attempt_count=1,
            active_minutes=12,
            timed=False,
            novelty=None,
            activity="Review",
            evidence=[
                (
                    "S22_Prefix_Sum",
                    "Implementation",
                    "PASS",
                    "",
                )
            ],
            attempt_id="att_incomplete",
            writeback_id="wb_incomplete",
            created_at=DAY0,
        )

        report = self.store.reconcile(
            [incomplete]
        )

        self.assertEqual(
            report.applied_events,
            0,
        )
        self.assertEqual(
            report.skipped_envelopes,
            1,
        )
        self.assertEqual(
            self.store.load_states(),
            {},
        )

    def test_late_evidence_triggers_rebuild(self):
        later = envelope(
            writeback_id="wb_later",
            finished_at=(
                DAY0
                + dt.timedelta(days=20)
            ),
        )

        earlier = envelope(
            writeback_id="wb_earlier",
            finished_at=(
                DAY0
                + dt.timedelta(days=10)
            ),
        )

        self.store.reconcile(
            [later]
        )

        report = self.store.reconcile(
            [
                later,
                earlier,
            ]
        )

        self.assertTrue(
            report.rebuilt
        )

        state = self.store.load_states()[
            (
                "S22_Prefix_Sum",
                "Implementation",
            )
        ]

        self.assertEqual(
            state.evidence_count,
            2,
        )
        self.assertEqual(
            state.last_evidence_on,
            (
                DAY0
                + dt.timedelta(days=20)
            ).date(),
        )

    def test_policy_change_rebuilds_cache(self):
        item = envelope(
            writeback_id="wb1",
            finished_at=DAY0,
        )

        self.store.reconcile(
            [item]
        )

        new_store = SkillMemoryStore(
            self.path,
            policy=MemoryPolicy(
                version="apcs-memory-v0.2",
            ),
        )

        report = new_store.reconcile(
            [item]
        )

        self.assertTrue(
            report.rebuilt
        )

        state = new_store.load_states()[
            (
                "S22_Prefix_Sum",
                "Implementation",
            )
        ]

        self.assertEqual(
            state.policy_version,
            "apcs-memory-v0.2",
        )

    def test_due_states_only_return_due_memory(self):
        item = envelope(
            writeback_id="wb1",
            finished_at=DAY0,
        )

        self.store.reconcile(
            [item]
        )

        early = self.store.due_states(
            on_date=(
                DAY0
                + dt.timedelta(days=1)
            ).date(),
        )

        late = self.store.due_states(
            on_date=(
                DAY0
                + dt.timedelta(days=30)
            ).date(),
        )

        self.assertEqual(
            early,
            (),
        )
        self.assertEqual(
            len(late),
            1,
        )
        state, value, due_on = late[0]
        self.assertEqual(
            state.skill_uid,
            "S22_Prefix_Sum",
        )
        self.assertLess(
            value,
            1.0,
        )
        self.assertLessEqual(
            due_on,
            (
                DAY0
                + dt.timedelta(days=30)
            ).date(),
        )


if __name__ == "__main__":
    unittest.main()
