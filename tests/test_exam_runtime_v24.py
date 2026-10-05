from __future__ import annotations

import datetime as dt
import tempfile
import unittest
from pathlib import Path

from tools.exam_runtime import (
    ExamRuntimeError,
    ExamSessionStore,
)


TZ = dt.timezone(dt.timedelta(hours=8))


class ExamRuntimeV24Test(unittest.TestCase):
    def make_store(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return ExamSessionStore(Path(temp.name))

    def t(self, minute: int) -> dt.datetime:
        return dt.datetime(
            2026, 10, 3, 20, minute, tzinfo=TZ
        )

    def test_start_records_scan_automatically(self):
        store = self.make_store()
        session = store.start(
            ["a001", "b130"],
            duration_minutes=60,
            started_at=self.t(0),
        )
        self.assertEqual(session["status"], "ACTIVE")
        self.assertEqual(
            [event["type"] for event in session["events"]],
            ["START", "SCAN_START"],
        )

    def test_select_and_switch_are_automatic_events(self):
        store = self.make_store()
        store.start(
            ["a001", "b130"],
            duration_minutes=60,
            started_at=self.t(0),
        )
        store.select("a001", at=self.t(3))
        session = store.select("b130", at=self.t(12))

        self.assertEqual(
            [event["type"] for event in session["events"][-2:]],
            ["SELECT", "SWITCH"],
        )
        self.assertEqual(
            session["events"][-1]["from_problem_id"],
            "a001",
        )

    def test_compile_hook_is_noop_without_active_exam(self):
        store = self.make_store()
        self.assertFalse(
            store.mark_compile(
                "a001",
                success=True,
                at=self.t(5),
            )
        )

    def test_compile_hook_records_only_selected_exam_problem(self):
        store = self.make_store()
        store.start(
            ["a001", "b130"],
            duration_minutes=30,
            started_at=self.t(0),
        )
        self.assertFalse(
            store.mark_compile(
                "a001",
                success=True,
                at=self.t(4),
            )
        )

        store.select(
            "a001",
            at=self.t(5),
        )

        self.assertFalse(
            store.mark_compile(
                "b130",
                success=True,
                at=self.t(6),
            )
        )
        self.assertTrue(
            store.mark_compile(
                "a001",
                success=False,
                at=self.t(7),
            )
        )
        active = store.active()
        compile_events = [
            event
            for event in active["events"]
            if event["type"] == "COMPILE"
        ]
        self.assertEqual(len(compile_events), 1)
        self.assertFalse(compile_events[0]["success"])

    def test_submit_is_one_explicit_event_for_selected_problem(self):
        store = self.make_store()
        store.start(
            ["a001", "b130"],
            duration_minutes=30,
            started_at=self.t(0),
        )

        with self.assertRaisesRegex(
            ExamRuntimeError,
            "目前選中",
        ):
            store.mark_submit(
                "a001",
                result="WA",
                at=self.t(8),
            )

        store.select(
            "a001",
            at=self.t(9),
        )

        with self.assertRaisesRegex(
            ExamRuntimeError,
            "目前選中",
        ):
            store.mark_submit(
                "b130",
                result="WA",
                at=self.t(9),
            )

        session = store.mark_submit(
            "a001",
            result="WA",
            at=self.t(10),
        )
        self.assertEqual(
            session["events"][-1],
            {
                "type": "SUBMIT",
                "at": self.t(10).isoformat(timespec="seconds"),
                "problem_id": "a001",
                "result": "WA",
            },
        )

    def test_end_requires_specific_postmortem_reason(self):
        store = self.make_store()
        store.start(
            ["a001"],
            duration_minutes=30,
            started_at=self.t(0),
        )

        with self.assertRaisesRegex(
            ExamRuntimeError,
            "postmortem",
        ):
            store.end(
                postmortem_reason="粗心",
                ended_at=self.t(20),
            )

        session = store.end(
            postmortem_reason="BUG",
            ended_at=self.t(20),
        )
        self.assertEqual(session["status"], "ENDED")
        self.assertEqual(
            session["postmortem_reason"],
            "BUG",
        )
        self.assertIsNone(store.active())

    def test_abort_closes_active_session_without_postmortem(self):
        store = self.make_store()
        started = store.start(
            ["a001", "b130"],
            duration_minutes=60,
            started_at=self.t(0),
        )
        session = store.abort(
            aborted_at=self.t(2),
        )

        self.assertEqual(
            session["status"],
            "ABORTED",
        )
        self.assertIsNone(
            session["postmortem_reason"]
        )
        self.assertEqual(
            session["events"][-1]["type"],
            "ABORT",
        )
        self.assertIsNone(
            store.active()
        )
        archived = (
            store.sessions_dir
            / f"{started['session_id']}.json"
        )
        self.assertTrue(
            archived.is_file()
        )

    def test_summary_separates_scan_compile_submit_switch(self):
        store = self.make_store()
        store.start(
            ["a001", "b130"],
            duration_minutes=60,
            started_at=self.t(0),
        )
        store.select("a001", at=self.t(4))
        store.mark_compile(
            "a001",
            success=True,
            at=self.t(9),
        )
        store.mark_submit(
            "a001",
            result="WA",
            at=self.t(15),
        )
        store.select("b130", at=self.t(18))
        session = store.end(
            postmortem_reason="TIME_ALLOCATION",
            ended_at=self.t(40),
        )
        summary = store.summary(session)

        self.assertEqual(summary["scan_minutes"], 4)
        self.assertEqual(summary["first_compile_minutes"], 9)
        self.assertEqual(summary["compile_count"], 1)
        self.assertEqual(summary["submit_count"], 1)
        self.assertEqual(summary["switch_count"], 1)
        self.assertEqual(
            summary["postmortem_reason"],
            "TIME_ALLOCATION",
        )

    def test_problem_list_is_deduplicated(self):
        store = self.make_store()
        session = store.start(
            ["A001", "a001", "b130"],
            duration_minutes=30,
            started_at=self.t(0),
        )
        self.assertEqual(
            session["problem_ids"],
            ["a001", "b130"],
        )


if __name__ == "__main__":
    unittest.main()
