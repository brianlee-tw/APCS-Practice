from __future__ import annotations

import datetime as dt
import types
import unittest
from unittest import mock

from tools import apcs_control as control
from tools.adaptive_memory import MemoryPolicy, MemoryState


class LearningStatusV23Test(unittest.TestCase):
    def test_status_uses_durable_outbox_memory_and_capacity_without_readiness_claim(self):
        on_date = dt.date(2026, 10, 3)
        plan = types.SimpleNamespace(
            budget_minutes=18,
            selected=(object(), object()),
            deferred=(object(),),
            selected_minutes=14,
        )
        today = {
            "date": on_date,
            "capacity_minutes": 60,
            "target": "5+5",
            "plan": plan,
            "warning": None,
        }

        reading = types.SimpleNamespace(track="Reading")
        implementation = types.SimpleNamespace(track="Implementation")
        envelopes = (
            types.SimpleNamespace(evidence=(reading,)),
            types.SimpleNamespace(evidence=(implementation, reading)),
            types.SimpleNamespace(evidence=()),
        )
        pending = (envelopes[1],)

        state_a = MemoryState(
            skill_uid="S01_IO",
            track="Reading",
            stability_days=7.0,
            last_evidence_on=dt.date(2026, 9, 25),
            evidence_count=2,
            successful_retrievals=1,
        )
        state_b = MemoryState(
            skill_uid="S01_IO",
            track="Implementation",
            stability_days=30.0,
            last_evidence_on=dt.date(2026, 10, 1),
            evidence_count=4,
            successful_retrievals=2,
        )
        memory = types.SimpleNamespace(
            policy=MemoryPolicy(),
            load_states=lambda: {
                ("S01_IO", "Reading"): state_a,
                ("S01_IO", "Implementation"): state_b,
            },
        )
        outbox = types.SimpleNamespace(
            all_envelopes=lambda: envelopes,
            pending=lambda: pending,
        )

        with (
            mock.patch.object(
                control,
                "adaptive_today_snapshot",
                return_value=today,
            ),
            mock.patch.object(control, "OUTBOX", outbox),
            mock.patch.object(control, "MEMORY", memory),
        ):
            snapshot = control.learning_status_snapshot(
                on_date=on_date,
                total_capacity_minutes=60,
            )

        self.assertEqual(snapshot["attempts"], 3)
        self.assertEqual(snapshot["evidence"], 3)
        self.assertEqual(snapshot["evidence_by_track"]["Reading"], 2)
        self.assertEqual(snapshot["evidence_by_track"]["Implementation"], 1)
        self.assertEqual(snapshot["remote_pending"], 1)
        self.assertEqual(snapshot["remote_acknowledged"], 2)
        self.assertEqual(snapshot["memory_states"], 2)
        self.assertEqual(snapshot["review_budget_minutes"], 18)
        self.assertEqual(snapshot["review_selected_minutes"], 14)
        self.assertEqual(snapshot["review_selected"], 2)
        self.assertEqual(snapshot["review_deferred"], 1)
        self.assertEqual(snapshot["protected_new_learning_minutes"], 42)
        self.assertEqual(snapshot["learner_readiness"], "NOT ASSESSED")
        self.assertEqual(
            [item["track"] for item in snapshot["retention"]],
            ["Reading", "Implementation"],
        )

    def test_status_deduplicates_warnings_and_fails_closed(self):
        on_date = dt.date(2026, 10, 3)
        plan = types.SimpleNamespace(
            budget_minutes=0,
            selected=(),
            deferred=(),
            selected_minutes=0,
        )
        today = {
            "date": on_date,
            "capacity_minutes": 30,
            "target": "3+3",
            "plan": plan,
            "warning": "broken derived cache",
        }

        class BadOutbox:
            def all_envelopes(self):
                raise OSError("broken derived cache")

            def pending(self):
                return ()

        class BadMemory:
            policy = MemoryPolicy()

            def load_states(self):
                raise ValueError("bad memory")

        with (
            mock.patch.object(
                control,
                "adaptive_today_snapshot",
                return_value=today,
            ),
            mock.patch.object(control, "OUTBOX", BadOutbox()),
            mock.patch.object(control, "MEMORY", BadMemory()),
        ):
            snapshot = control.learning_status_snapshot(
                on_date=on_date
            )

        self.assertEqual(snapshot["attempts"], 0)
        self.assertEqual(snapshot["memory_states"], 0)
        self.assertEqual(
            snapshot["warnings"],
            ("broken derived cache", "bad memory"),
        )
        self.assertEqual(snapshot["learner_readiness"], "NOT ASSESSED")


if __name__ == "__main__":
    unittest.main()
