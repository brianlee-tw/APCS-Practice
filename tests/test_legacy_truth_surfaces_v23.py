import io
import json
import unittest
from pathlib import Path
from contextlib import redirect_stdout
from unittest.mock import patch

from tools import apcs


ROOT = Path(__file__).resolve().parents[1]


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

    def test_static_diagnostic_skill_model_is_not_v23_authority(self):
        model = json.loads(
            (
                ROOT
                / "site"
                / "data"
                / "skill-model.v1.json"
            ).read_text(encoding="utf-8")
        )

        self.assertEqual(
            model["scope"],
            "diagnostic-only",
        )
        self.assertIs(
            model["readinessAuthority"],
            False,
        )

    def test_static_diagnostic_page_exposes_authority_boundary(self):
        html = (
            ROOT
            / "site"
            / "index.html"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "diagnostic-only surface",
            html,
        )
        self.assertIn(
            "不是 v2.3 Learning Runtime",
            html,
        )
        self.assertIn(
            "不代表 Skill × Track mastery",
            html,
        )
        self.assertIn(
            "不會寫入 REC / EV",
            html,
        )

    def test_static_site_contract_rejects_skill_map_role(self):
        contract = (
            ROOT
            / "site"
            / "README.md"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "DIAGNOSTIC ONLY",
            contract,
        )
        self.assertIn(
            "not a stale alternate copy of Skill Map v3",
            contract,
        )
        self.assertIn(
            "readinessAuthority",
            contract,
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
