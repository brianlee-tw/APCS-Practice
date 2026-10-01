import contextlib
import io
import unittest
from unittest.mock import patch

import tools.apcs as apcs


class V23CliBoundaryTest(unittest.TestCase):
    def test_today_cli_points_to_control_center(self):
        output = io.StringIO()

        with contextlib.redirect_stdout(
            output
        ):
            result = apcs.main(
                ["today"]
            )

        self.assertEqual(
            result,
            0,
        )
        self.assertIn(
            "Control Center",
            output.getvalue(),
        )

    def test_finish_cli_cannot_bypass_evidence_capture(self):
        error = io.StringIO()

        with (
            patch.object(
                apcs,
                "finish_cmd",
            ) as finish,
            contextlib.redirect_stderr(
                error
            ),
        ):
            result = apcs.main(
                [
                    "finish",
                    "a001",
                    "3",
                ]
            )

        self.assertEqual(
            result,
            2,
        )
        finish.assert_not_called()
        self.assertIn(
            "已停用 CLI 直接 Finish / Review",
            error.getvalue(),
        )

    def test_review_cli_cannot_bypass_evidence_capture(self):
        error = io.StringIO()

        with (
            patch.object(
                apcs,
                "review_cmd",
            ) as review,
            contextlib.redirect_stderr(
                error
            ),
        ):
            result = apcs.main(
                [
                    "review",
                    "a001",
                    "3",
                    "--result",
                    "AC",
                ]
            )

        self.assertEqual(
            result,
            2,
        )
        review.assert_not_called()


if __name__ == "__main__":
    unittest.main()
