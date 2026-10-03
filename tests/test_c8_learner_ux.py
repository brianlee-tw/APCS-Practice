import io
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from tools import apcs_control as control
from tools.runtime_curriculum import PlacementContext


def problem(*, action="finish"):
    return {
        "id": "d050",
        "path": Path("/tmp/d050.cpp"),
        "published_runtime": True,
        "runtime_action": action,
        "runtime_track": "Implementation",
    }


def placement(*, role="Guided Drill"):
    return PlacementContext(
        placement_uid="PL-TEST",
        pb_uid="PB-TEST",
        problem_id="d050",
        title="測試題",
        url="https://example.invalid/d050",
        difficulty="D1",
        primary_skill="S01_IO",
        supporting_skills=(),
        role=role,
        lesson_uid="L-FND-01",
        lesson_order=1,
    )


class C8LearnerUxTest(unittest.TestCase):
    def test_menu_renders_visual_sections_without_extra_options(self):
        keys = iter(["q"])
        output = io.StringIO()

        with (
            patch.object(control, "read_key", side_effect=lambda: next(keys)),
            redirect_stdout(output),
        ):
            result = control.choose_menu(
                "測試",
                [
                    {
                        "label": "今日學習",
                        "detail": "主要",
                        "enabled": True,
                        "section": "主要入口",
                    },
                    {
                        "label": "完成題目",
                        "detail": "情境",
                        "enabled": True,
                        "section": "目前題目",
                    },
                ],
            )

        self.assertIsNone(result)
        rendered = output.getvalue()
        self.assertIn("主要入口", rendered)
        self.assertIn("目前題目", rendered)

    def test_compact_support_menu_captures_assistance_and_independence_once(self):
        with patch.object(
            control,
            "choose_menu",
            return_value=4,
        ):
            value = control.compact_support_menu(
                problem()
            )

        self.assertEqual(
            value,
            {
                "assistance": 2,
                "independent": False,
            },
        )

    def test_published_new_learning_infers_novelty_without_asking(self):
        self.assertEqual(
            control.inferred_published_novelty(
                "finish",
                problem(action="finish"),
                placement(role="Guided Drill"),
            ),
            "new",
        )
        self.assertEqual(
            control.inferred_published_novelty(
                "finish",
                problem(action="finish"),
                placement(role="Transfer Challenge"),
            ),
            "transfer",
        )
        self.assertEqual(
            control.inferred_published_novelty(
                "review",
                problem(action="review"),
                placement(),
            ),
            "delayed_retest",
        )

    def test_published_context_skips_novelty_and_timed_prompts_when_known(self):
        with (
            patch.object(
                control,
                "placement_for_record",
                return_value=(placement(), None),
            ),
            patch.object(
                control,
                "compact_support_menu",
                return_value={
                    "assistance": 0,
                    "independent": True,
                },
            ),
            patch.object(
                control,
                "novelty_menu",
            ) as novelty,
            patch.object(
                control,
                "timed_menu",
            ) as timed,
            patch.object(
                control.EXAM,
                "active",
                return_value=None,
            ),
        ):
            value = control.published_evidence_context_menu(
                "finish",
                problem(action="finish"),
            )

        self.assertEqual(value["novelty"], "new")
        self.assertFalse(value["timed"])
        novelty.assert_not_called()
        timed.assert_not_called()

    def test_learning_status_defaults_to_decision_summary(self):
        snapshot = {
            "target": "3+3",
            "attempts": 2,
            "evidence": 1,
            "evidence_by_track": {
                "Reading": 0,
                "Implementation": 1,
            },
            "memory_states": 1,
            "capacity_minutes": 60,
            "review_selected_minutes": 8,
            "review_budget_minutes": 18,
            "review_selected": 1,
            "review_deferred": 0,
            "protected_new_learning_minutes": 42,
            "remote_acknowledged": 1,
            "remote_pending": 1,
            "warnings": (),
        }
        output = io.StringIO()

        with (
            patch.object(
                control,
                "learning_status_snapshot",
                return_value=snapshot,
            ),
            patch.object(
                control,
                "read_key",
                return_value="ENTER",
            ),
            redirect_stdout(output),
        ):
            control.learning_status_view()

        rendered = output.getvalue()
        self.assertIn("目前進度", rendered)
        self.assertIn("今日容量", rendered)
        self.assertIn("同步狀態", rendered)
        self.assertIn("D 查看詳細技術狀態", rendered)
        self.assertNotIn("最低 R 優先", rendered)


if __name__ == "__main__":
    unittest.main()
