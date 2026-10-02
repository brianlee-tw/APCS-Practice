import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from tools import apcs


class LegacyTruthSurfaceV23Test(unittest.TestCase):
    def test_dashboard_is_explicitly_compatibility_only(self):
        with patch.object(
            apcs.ENGINE,
            "due_queue",
            return_value=[],
        ):
            rendered = apcs.render_dashboard([])

        self.assertIn(
            "v2.2 Compatibility Dashboard",
            rendered,
        )
        self.assertIn(
            "不代表 v2.3 Skill × Track mastery",
            rendered,
        )
        self.assertIn(
            "v2.2 Mastered",
            rendered,
        )

    def test_problem_index_labels_legacy_state(self):
        rendered = apcs.render_index([])

        self.assertIn(
            "v2.2 State",
            rendered,
        )
        self.assertIn(
            "不是 v2.3 mastery/readiness",
            rendered,
        )

    def test_review_queue_is_not_learner_today(self):
        rendered = apcs.render_queue([])

        self.assertIn(
            "Compatibility Review Queue (v2.2)",
            rendered,
        )
        self.assertIn(
            "Control Center → 今日學習",
            rendered,
        )

    def test_low_level_today_warns_before_compatibility_queue(self):
        output = io.StringIO()

        with (
            patch.object(
                apcs,
                "build",
                return_value=([], []),
            ),
            patch.object(
                apcs.ENGINE,
                "due_queue",
                return_value=[],
            ),
            redirect_stdout(output),
        ):
            result = apcs.today_cmd()

        self.assertEqual(result, 0)
        text = output.getvalue()
        self.assertIn(
            "COMPATIBILITY ONLY",
            text,
        )
        self.assertIn(
            "Control Center → 今日學習",
            text,
        )


if __name__ == "__main__":
    unittest.main()
