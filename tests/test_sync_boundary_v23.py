import contextlib
import io
import unittest
from unittest.mock import patch

import tools.apcs as apcs


class FakeEngine:
    def __init__(self):
        self.finish_calls = []
        self.review_calls = []

    def finish(
        self,
        pid,
        score,
        *,
        minutes=None,
        note="",
    ):
        self.finish_calls.append(
            (pid, score, minutes, note)
        )

    def review(
        self,
        pid,
        score,
        *,
        result="AC",
        minutes=None,
        note="",
    ):
        self.review_calls.append(
            (
                pid,
                score,
                result,
                minutes,
                note,
            )
        )


class SyncBoundaryV23Test(unittest.TestCase):
    def setUp(self):
        self.engine = FakeEngine()

    def test_best_effort_sync_returns_warning_instead_of_raising(self):
        def broken_sync():
            raise RuntimeError(
                "simulated generated sync failure"
            )

        warning = (
            apcs.sync_generated_best_effort(
                sync_runner=broken_sync
            )
        )

        self.assertEqual(
            warning,
            "simulated generated sync failure",
        )

    def test_finish_success_survives_generated_sync_failure(self):
        output = io.StringIO()

        with (
            patch.object(
                apcs,
                "ENGINE",
                self.engine,
            ),
            patch.object(
                apcs,
                "known_problem_ids",
                return_value={"a001"},
            ),
            patch.object(
                apcs,
                "sync",
                side_effect=RuntimeError(
                    "generated write failed"
                ),
            ),
            contextlib.redirect_stdout(
                output
            ),
        ):
            result = apcs.finish_cmd(
                "a001",
                3,
                minutes=12,
            )

        self.assertEqual(
            result,
            0,
        )

        self.assertEqual(
            self.engine.finish_calls,
            [
                (
                    "a001",
                    3,
                    12,
                    "",
                )
            ],
        )

        rendered = output.getvalue()

        self.assertIn(
            "已完成 a001",
            rendered,
        )

        self.assertIn(
            "學習紀錄已寫入",
            rendered,
        )

        self.assertIn(
            "generated sync 失敗",
            rendered,
        )

    def test_review_success_survives_generated_sync_failure(self):
        output = io.StringIO()

        with (
            patch.object(
                apcs,
                "ENGINE",
                self.engine,
            ),
            patch.object(
                apcs,
                "known_problem_ids",
                return_value={"a001"},
            ),
            patch.object(
                apcs,
                "sync",
                side_effect=OSError(
                    "generated write failed"
                ),
            ),
            contextlib.redirect_stdout(
                output
            ),
        ):
            result = apcs.review_cmd(
                "a001",
                2,
                result="WA",
                minutes=9,
            )

        self.assertEqual(
            result,
            0,
        )

        self.assertEqual(
            self.engine.review_calls,
            [
                (
                    "a001",
                    2,
                    "WA",
                    9,
                    "",
                )
            ],
        )

        rendered = output.getvalue()

        self.assertIn(
            "已複習 a001",
            rendered,
        )

        self.assertIn(
            "generated sync 失敗",
            rendered,
        )

    def test_finish_can_defer_generated_sync_to_ui_boundary(self):
        with (
            patch.object(
                apcs,
                "ENGINE",
                self.engine,
            ),
            patch.object(
                apcs,
                "known_problem_ids",
                return_value={"a001"},
            ),
            patch.object(
                apcs,
                "sync",
            ) as sync_mock,
        ):
            result = apcs.finish_cmd(
                "a001",
                3,
                sync_after=False,
            )

        self.assertEqual(
            result,
            0,
        )

        sync_mock.assert_not_called()

    def test_review_can_defer_generated_sync_to_ui_boundary(self):
        with (
            patch.object(
                apcs,
                "ENGINE",
                self.engine,
            ),
            patch.object(
                apcs,
                "known_problem_ids",
                return_value={"a001"},
            ),
            patch.object(
                apcs,
                "sync",
            ) as sync_mock,
        ):
            result = apcs.review_cmd(
                "a001",
                3,
                sync_after=False,
            )

        self.assertEqual(
            result,
            0,
        )

        sync_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
