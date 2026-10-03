import datetime as dt
import io
import tempfile
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
        "title": "d050 妳那裡現在幾點了？",
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


    def test_problem_library_entry_is_choice_first_not_query_first(self):
        with (
            patch.object(
                control,
                "choose_grid",
                return_value=None,
            ) as menu,
            patch.object(
                control,
                "prompt_text",
                side_effect=AssertionError(
                    "entry must not force text search"
                ),
            ),
        ):
            control.problem_library_view()

        options = menu.call_args.args[1]
        self.assertEqual(
            [item["label"] for item in options],
            [
                "推薦給我",
                "分類找題",
                "題號／題名",
                "全部題目",
            ],
        )

    def test_skill_navigation_groups_all_skills_by_unit(self):
        groups = (
            control._problem_library_skill_groups()
        )

        self.assertEqual(
            sum(
                len(group["skills"])
                for group in groups
            ),
            39,
        )
        self.assertLessEqual(
            max(
                len(group["skills"])
                for group in groups
            ),
            7,
        )
        self.assertIn(
            "基礎語法與函式",
            {
                group["label"]
                for group in groups
            },
        )
        self.assertIn(
            "圖論與樹",
            {
                group["label"]
                for group in groups
            },
        )

    def test_practice_skill_filter_can_surface_transfer_and_mock(self):
        def item(
            *,
            problem_id,
            role,
            attempted,
        ):
            return types.SimpleNamespace(
                external_id=problem_id,
                source="zerojudge",
                difficulty="D2",
                primary_skill="S18_DFS",
                supporting_skills=(),
                role=role,
                attempted=attempted,
                has_l2=False,
            )

        items = [
            item(
                problem_id="guided",
                role="Guided Drill",
                attempted=False,
            ),
            item(
                problem_id="transfer",
                role="Transfer Challenge",
                attempted=False,
            ),
            item(
                problem_id="mock",
                role="Mock",
                attempted=False,
            ),
            item(
                problem_id="old-transfer",
                role="Transfer Challenge",
                attempted=True,
            ),
        ]

        filtered = (
            control._problem_library_filter_items(
                items,
                {
                    "skill_uids": (
                        "S18_DFS",
                    ),
                },
            )
        )

        self.assertEqual(
            [
                value.external_id
                for value in filtered
            ],
            [
                "guided",
                "transfer",
                "mock",
                "old-transfer",
            ],
        )

    def test_filter_summary_is_human_readable(self):
        summary = (
            control._problem_library_filter_summary(
                {
                    "skill_label": "DFS",
                    "difficulty": "D3",
                    "source": "zerojudge",
                    "attempted": False,
                    "role": "Core Independent",
                    "require_l2": True,
                }
            )
        )

        self.assertEqual(
            summary,
            "DFS · D3 · ZeroJudge · 未做 · 獨立練習 · 有教學資料",
        )


    def test_menu_footer_uses_context_action_instead_of_execute(self):
        output = io.StringIO()

        with (
            patch.object(
                control,
                "read_key",
                return_value="q",
            ),
            redirect_stdout(output),
        ):
            control.choose_menu(
                "測試",
                [
                    {
                        "label": "題目",
                        "detail": "查看詳細內容",
                        "enabled": True,
                        "action": "查看",
                    }
                ],
            )

        rendered = output.getvalue()
        self.assertIn(
            "Enter 查看",
            rendered,
        )
        self.assertNotIn(
            "Enter 執行",
            rendered,
        )

    def test_today_capacity_override_is_daily_and_15_minute_granularity(self):
        with tempfile.TemporaryDirectory() as temp:
            path = (
                Path(temp)
                / "today_capacity.json"
            )
            on_date = dt.date(
                2026,
                10,
                4,
            )

            with (
                patch.object(
                    control,
                    "TODAY_CAPACITY_PATH",
                    path,
                ),
                patch.dict(
                    "os.environ",
                    {
                        "APCS_SESSION_MINUTES": "60",
                    },
                    clear=False,
                ),
            ):
                control.set_today_capacity_minutes(
                    75,
                    on_date=on_date,
                )

                self.assertEqual(
                    control.session_capacity_minutes(
                        on_date
                    ),
                    75,
                )
                self.assertEqual(
                    control.session_capacity_minutes(
                        on_date
                        + dt.timedelta(days=1)
                    ),
                    60,
                )

                with self.assertRaises(
                    ValueError
                ):
                    control.set_today_capacity_minutes(
                        70,
                        on_date=on_date,
                    )

    def test_capacity_picker_uses_sparse_high_value_presets(self):
        with patch.object(
            control,
            "choose_grid",
            return_value=3,
        ) as menu:
            value = (
                control.today_capacity_menu(
                    60
                )
            )

        self.assertEqual(value, 60)
        options = menu.call_args.args[1]
        self.assertEqual(
            [
                int(
                    option["label"]
                    .split()[0]
                )
                for option in options
            ],
            [
                15,
                30,
                45,
                60,
                75,
                90,
                120,
                150,
                180,
                240,
            ],
        )
        self.assertEqual(
            options[3]["detail"],
            "目前設定",
        )
        self.assertEqual(
            menu.call_args.kwargs[
                "wide_columns"
            ],
            5,
        )

    def test_filter_view_has_explicit_live_result_action(self):
        def item(problem_id):
            return types.SimpleNamespace(
                external_id=problem_id,
                source="zerojudge",
                difficulty="D1",
                attempted=False,
                role="Guided Drill",
                has_l2=True,
                primary_skill="S01_IO",
                supporting_skills=(),
            )

        calls = []

        def choose(title, options, **kwargs):
            calls.append(
                (
                    title,
                    options,
                    kwargs,
                )
            )
            return None

        with (
            patch.object(
                control.PROBLEM_LIBRARY,
                "items",
                return_value=[
                    item("a001"),
                    item("a002"),
                ],
            ),
            patch.object(
                control,
                "choose_menu",
                side_effect=choose,
            ),
            patch(
                "tools.apcs_control.shutil.get_terminal_size",
                return_value=types.SimpleNamespace(
                    columns=80
                ),
            ),
        ):
            control._problem_library_filter_view(
                mode="practice",
            )

        options = calls[0][1]
        self.assertEqual(
            options[0]["label"],
            "查看 2 題",
        )
        self.assertEqual(
            options[0]["action"],
            "查看",
        )
        self.assertEqual(
            options[0]["section"],
            "目前結果",
        )

    def test_control_dashboard_is_responsive(self):
        plan = types.SimpleNamespace(
            budget_minutes=18,
            selected=(),
            selected_minutes=0,
        )
        route = types.SimpleNamespace(
            skill=types.SimpleNamespace(
                uid="S01_IO"
            )
        )
        snapshot = {
            "capacity_minutes": 60,
            "plan": plan,
            "new_learning": route,
            "curriculum_blocker": None,
            "warning": None,
        }

        wide = io.StringIO()
        with (
            patch(
                "tools.apcs_control.shutil.get_terminal_size",
                return_value=types.SimpleNamespace(
                    columns=100
                ),
            ),
            redirect_stdout(wide),
        ):
            control.print_control_dashboard(
                problem(),
                snapshot,
            )

        self.assertIn(
            "│",
            wide.getvalue(),
        )

        narrow = io.StringIO()
        with (
            patch(
                "tools.apcs_control.shutil.get_terminal_size",
                return_value=types.SimpleNamespace(
                    columns=50
                ),
            ),
            redirect_stdout(narrow),
        ):
            control.print_control_dashboard(
                problem(),
                snapshot,
            )

        self.assertNotIn(
            "│",
            narrow.getvalue(),
        )
        self.assertIn(
            "今日規劃",
            narrow.getvalue(),
        )


    def test_selection_mode_persists_without_becoming_a_new_ssot(self):
        with tempfile.TemporaryDirectory() as temp:
            path = (
                Path(temp)
                / "selection_mode.json"
            )
            with patch.object(
                control,
                "SELECTION_MODE_PATH",
                path,
            ):
                self.assertEqual(
                    control.selection_mode(),
                    "practice",
                )
                control.set_selection_mode(
                    "exam"
                )
                self.assertEqual(
                    control.selection_mode(),
                    "exam",
                )
                self.assertEqual(
                    control.toggle_selection_mode(),
                    "practice",
                )

    def test_choose_grid_supports_horizontal_navigation(self):
        keys = iter(
            [
                "RIGHT",
                "ENTER",
            ]
        )
        with (
            patch.object(
                control,
                "read_key",
                side_effect=lambda: next(keys),
            ),
            patch(
                "tools.apcs_control.shutil.get_terminal_size",
                return_value=types.SimpleNamespace(
                    columns=100
                ),
            ),
            redirect_stdout(io.StringIO()),
        ):
            selected = control.choose_grid(
                "測試",
                [
                    {
                        "label": "A",
                        "enabled": True,
                        "section": "主要",
                    },
                    {
                        "label": "B",
                        "enabled": True,
                        "section": "主要",
                    },
                    {
                        "label": "C",
                        "enabled": True,
                        "section": "主要",
                    },
                ],
            )

        self.assertEqual(
            selected,
            1,
        )

    def test_exam_filter_hides_method_classification_controls(self):
        options = (
            control._problem_library_filter_options(
                {
                    "skill_uids": (),
                    "skill_label": None,
                    "difficulty": None,
                    "source": None,
                    "attempted": None,
                    "role": None,
                    "require_l2": None,
                },
                [],
                mode="exam",
            )
        )
        labels = {
            option["label"]
            for option in options
        }
        self.assertNotIn(
            "學習主題",
            labels,
        )
        self.assertNotIn(
            "難度",
            labels,
        )
        self.assertNotIn(
            "練習用途",
            labels,
        )
        self.assertNotIn(
            "教學資料",
            labels,
        )
        self.assertIn(
            "來源",
            labels,
        )
        self.assertIn(
            "作答狀態",
            labels,
        )

    def test_exam_text_search_does_not_match_hidden_skill_metadata(self):
        item = types.SimpleNamespace(
            external_id="a001",
            title="一般題名",
            source="zerojudge",
            difficulty="D2",
            attempted=False,
            role="Transfer Challenge",
            has_l2=True,
            primary_skill="S18_DFS",
            supporting_skills=(),
            canonical_url="https://example.invalid/a001",
        )
        captured = {}

        def results(items, **kwargs):
            captured["items"] = list(items)

        with (
            patch.object(
                control,
                "prompt_text",
                return_value="DFS",
            ),
            patch.object(
                control.PROBLEM_LIBRARY,
                "items",
                return_value=[item],
            ),
            patch.object(
                control,
                "_problem_library_results_view",
                side_effect=results,
            ),
            redirect_stdout(io.StringIO()),
        ):
            control._problem_library_text_search(
                mode="exam",
            )

        self.assertEqual(
            captured["items"],
            [],
        )

    def test_transfer_implementation_scratch_hides_classification(self):
        p = placement(
            role="Transfer Challenge"
        )
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(
                control,
                "RUNTIME_DIR",
                Path(temp),
            ):
                path = (
                    control.create_learning_scratch(
                        p
                    )
                )
                text = path.read_text(
                    encoding="utf-8"
                )

        self.assertNotIn(
            "Skill:",
            text,
        )
        self.assertNotIn(
            "Lesson:",
            text,
        )
        self.assertNotIn(
            "Role:",
            text,
        )
        self.assertIn(
            "嚴格防劇透",
            text,
        )

    def test_exam_duration_uses_presets_instead_of_manual_input(self):
        with patch.object(
            control,
            "choose_grid",
            return_value=1,
        ) as menu:
            value = (
                control._exam_duration_menu(
                    60
                )
            )

        self.assertEqual(
            value,
            60,
        )
        self.assertEqual(
            [
                int(
                    option["label"]
                    .split()[0]
                )
                for option in menu.call_args.args[1]
            ],
            [
                30,
                60,
                90,
                120,
                180,
            ],
        )

    def test_learning_status_uses_wide_summary_when_space_allows(self):
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
            patch(
                "tools.apcs_control.shutil.get_terminal_size",
                return_value=types.SimpleNamespace(
                    columns=100
                ),
            ),
            redirect_stdout(output),
        ):
            control.learning_status_view()

        rendered = output.getvalue()
        self.assertIn(
            "目前進度",
            rendered,
        )
        self.assertIn(
            "今日容量",
            rendered,
        )
        self.assertIn(
            "LEARNER_READINESS = NOT ASSESSED",
            rendered,
        )


if __name__ == "__main__":
    unittest.main()
