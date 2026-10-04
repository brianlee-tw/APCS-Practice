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

    def test_published_result_reuses_explicit_exam_submit_only(self):
        session = {
            "events": [
                {
                    "type": "SUBMIT",
                    "problem_id": "d050",
                    "result": "WA",
                },
            ],
        }
        with patch.object(
            control.EXAM,
            "active",
            return_value=session,
        ):
            self.assertEqual(
                control.inferred_published_result(
                    problem()
                ),
                "WA",
            )

        session["events"][0]["result"] = "N/A"
        with patch.object(
            control.EXAM,
            "active",
            return_value=session,
        ):
            self.assertIsNone(
                control.inferred_published_result(
                    problem()
                )
            )

    def test_published_result_does_not_infer_without_exam_submit(self):
        with patch.object(
            control.EXAM,
            "active",
            return_value={
                "events": [
                    {
                        "type": "COMPILE",
                        "problem_id": "d050",
                        "success": True,
                    },
                ],
            },
        ):
            self.assertIsNone(
                control.inferred_published_result(
                    problem()
                )
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

    def test_published_finish_requires_authoritative_oj_result_before_evidence(self):
        with (
            patch.object(
                control,
                "review_result_menu",
                return_value=None,
            ) as result_menu,
            patch.object(
                control,
                "published_evidence_context_menu",
            ) as evidence_menu,
        ):
            control.record_problem(
                "finish",
                problem(action="finish"),
            )

        result_menu.assert_called_once()
        self.assertEqual(
            result_menu.call_args.kwargs["action"],
            "finish",
        )
        evidence_menu.assert_not_called()

    def test_failure_bottleneck_menu_is_one_explicit_learner_choice(self):
        with patch.object(
            control,
            "choose_menu",
            return_value=7,
        ):
            value = control.failure_bottleneck_menu(
                problem()
            )

        self.assertEqual(
            value,
            "State / Index",
        )

    def test_attempt_note_can_keep_failure_bottleneck_without_promoting_it(self):
        envelope = control.attempt_envelope_for_record(
            action="finish",
            problem=problem(),
            result="WA",
            minutes=None,
            assistance=0,
            independent=True,
            novelty="new",
            timed=False,
            placement=placement(),
            bottleneck="Debugging",
        )

        self.assertEqual(
            envelope.attempt.judge_result,
            "WA",
        )
        self.assertIn(
            "Bottleneck: Debugging",
            envelope.attempt.note,
        )
        self.assertEqual(
            envelope.evidence[0].outcome,
            "FAIL",
        )

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


    def test_problem_library_compact_entry_is_choice_first_not_query_first(self):
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
            patch(
                "tools.workbench_tui.shutil.get_terminal_size",
                return_value=types.SimpleNamespace(
                    columns=80,
                    lines=30,
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

    def test_problem_library_wide_entry_opens_workbench_directly(self):
        with (
            patch.object(
                control,
                "_problem_library_workbench",
                return_value=None,
            ) as workbench,
            patch.object(
                control,
                "choose_grid",
            ) as menu,
            patch.object(
                control,
                "prompt_text",
                side_effect=AssertionError(
                    "wide entry must not force text search"
                ),
            ),
            patch(
                "tools.workbench_tui.shutil.get_terminal_size",
                return_value=types.SimpleNamespace(
                    columns=100,
                    lines=42,
                ),
            ),
        ):
            control.problem_library_view()

        workbench.assert_called_once_with(
            mode=control.selection_mode(),
        )
        menu.assert_not_called()

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
        self.assertIn(
            "目前",
            options[3]["label"],
        )
        self.assertEqual(
            options[3]["detail"],
            "",
        )
        self.assertEqual(
            menu.call_args.kwargs[
                "wide_columns"
            ],
            3,
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
                control,
                "_problem_library_items",
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

        rendered_wide = wide.getvalue()
        self.assertIn(
            "現在可做",
            rendered_wide,
        )
        self.assertIn(
            "目前題目",
            rendered_wide,
        )
        self.assertIn(
            "今日容量",
            rendered_wide,
        )
        self.assertIn(
            control.aligned_field(
                "可用",
                "60 分",
            ),
            rendered_wide,
        )
        self.assertIn(
            control.aligned_field(
                "複習",
                "0 / 18 分",
            ),
            rendered_wide,
        )
        self.assertNotIn(
            "可用 60 分 · 複習",
            rendered_wide,
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

        rendered_narrow = narrow.getvalue()
        self.assertIn(
            "現在可做",
            rendered_narrow,
        )
        self.assertIn(
            "目前題目",
            rendered_narrow,
        )
        self.assertIn(
            "今日容量",
            rendered_narrow,
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
        self.assertEqual(
            menu.call_args.kwargs[
                "wide_columns"
            ],
            3,
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
        self.assertIn(
            control.aligned_field(
                "Evidence",
                1,
            ),
            rendered,
        )
        self.assertNotIn(
            "真實作答 2 · Evidence 1",
            rendered,
        )


    def test_legacy_finish_initializes_runtime_flag_before_branching(self):
        legacy_problem = {
            "id": "r488",
            "title": "彗星撞擊",
            "path": Path("/tmp/r488.cpp"),
            "published_runtime": False,
            "runtime_track": "Implementation",
            "state": None,
        }

        with (
            patch.object(
                control,
                "missing_finish_complexity",
                return_value=None,
            ),
            patch.object(
                control,
                "recall_menu",
                return_value=None,
            ),
        ):
            control.record_problem(
                "finish",
                legacy_problem,
            )

    def test_problem_library_uses_published_curriculum_as_baseline_coverage(self):
        published = PlacementContext(
            placement_uid="PL-PB-1-L-FND-01",
            pb_uid="PB-1",
            problem_id="zj-d050",
            title="妳那裡現在幾點了？",
            url="https://example.invalid/d050",
            difficulty="D1",
            primary_skill="S01_IO",
            supporting_skills=(),
            role="Guided Drill",
            lesson_uid="L-FND-01",
            lesson_order=1,
            source_platform="zerojudge",
        )

        with (
            patch.object(
                control.PROBLEM_LIBRARY,
                "items",
                return_value=[],
            ),
            patch.object(
                control.PROBLEM_LIBRARY,
                "attempted_pb_uids",
                return_value=set(),
            ),
            patch.object(
                control.CURRICULUM,
                "all_placements",
                return_value=(published,),
            ),
        ):
            items = (
                control._problem_library_items()
            )

        self.assertEqual(
            len(items),
            1,
        )
        self.assertEqual(
            items[0].external_id,
            "zj-d050",
        )
        self.assertEqual(
            items[0].primary_skill,
            "S01_IO",
        )

    def test_selection_mode_badge_is_visually_distinct(self):
        practice = (
            control.selection_mode_badge(
                "practice"
            )
        )
        exam = (
            control.selection_mode_badge(
                "exam"
            )
        )

        self.assertIn(
            "[ 練習 ]",
            practice,
        )
        self.assertIn(
            "[ 考試 · 防劇透 ]",
            exam,
        )
        self.assertNotEqual(
            practice,
            exam,
        )

    def test_wide_problem_filter_shows_choices_and_live_count_together(self):
        def item(problem_id):
            return types.SimpleNamespace(
                external_id=problem_id,
                title=f"題目 {problem_id}",
                source="zerojudge",
                difficulty="D1",
                attempted=False,
                role="Guided Drill",
                has_l2=False,
                primary_skill="S01_IO",
                supporting_skills=(),
            )

        output = io.StringIO()
        with (
            patch(
                "tools.apcs_control.shutil.get_terminal_size",
                return_value=types.SimpleNamespace(
                    columns=100,
                    lines=42,
                ),
            ),
            patch.object(
                control,
                "read_key",
                return_value="ESC",
            ),
            redirect_stdout(output),
        ):
            result = (
                control._problem_library_filter_choice(
                    {
                        "skill_uids": (),
                        "skill_label": None,
                        "difficulty": None,
                        "source": None,
                        "attempted": None,
                        "role": None,
                        "require_l2": None,
                    },
                    [
                        item("a001"),
                        item("a002"),
                    ],
                    mode="practice",
                )
            )

        self.assertIsNone(result)
        rendered = output.getvalue()
        self.assertIn(
            "篩選條件",
            rendered,
        )
        self.assertIn(
            "可選值",
            rendered,
        )
        self.assertIn(
            "目前 2 題",
            rendered,
        )

    def test_solution_language_labels_are_learner_facing(self):
        self.assertEqual(
            control._solution_language_label(
                "cpp"
            ),
            "C++",
        )
        self.assertEqual(
            control._solution_language_label(
                "python"
            ),
            "Python",
        )

    def test_wide_today_view_keeps_plan_and_actions_on_one_screen(self):
        plan = types.SimpleNamespace(
            budget_minutes=18,
            selected=(),
            selected_minutes=0,
            deferred=(),
        )
        snapshot = {
            "target": "3+3",
            "capacity_minutes": 60,
            "plan": plan,
            "warning": None,
        }
        options = [
            {
                "label": "新學習 · S01_IO × Reading",
                "detail": "Guided Drill · d050",
                "enabled": True,
                "kind": "new",
            },
            {
                "label": "調整今日可用時間 · 60 min",
                "detail": "只影響今天",
                "enabled": True,
                "kind": "capacity",
                "action": "調整",
            },
        ]

        output = io.StringIO()
        with (
            patch(
                "tools.apcs_control.shutil.get_terminal_size",
                return_value=types.SimpleNamespace(
                    columns=100,
                    lines=42,
                ),
            ),
            patch.object(
                control,
                "read_key",
                return_value="ESC",
            ),
            redirect_stdout(output),
        ):
            result = (
                control._today_action_menu(
                    snapshot,
                    options,
                )
            )

        self.assertIsNone(result)
        rendered = output.getvalue()
        self.assertIn(
            "學習活動",
            rendered,
        )
        self.assertIn(
            "規劃與執行",
            rendered,
        )
        self.assertIn(
            "今日規劃",
            rendered,
        )
        self.assertIn(
            "可用時間  60 分",
            rendered,
        )


    def test_problem_library_workbench_renders_filter_results_and_sidebar_together(self):
        item = types.SimpleNamespace(
            external_id="a001",
            title="測試題目",
            source="zerojudge",
            difficulty="D2",
            attempted=False,
            role="Guided Drill",
            has_l2=False,
            primary_skill="S01_IO",
            supporting_skills=(),
            canonical_url="https://example.invalid/a001",
        )
        output = io.StringIO()

        state = {
            "library_result_index": 0,
            "library_filter_kind": "results",
            "library_focus": 0,
            "library_filters_practice": None,
            "library_filters_exam": None,
            "library_query_practice": "",
            "library_query_exam": "",
        }

        with (
            patch.dict(
                control.UI_STATE,
                state,
                clear=True,
            ),
            patch.object(
                control,
                "_problem_library_items",
                return_value=[item],
            ),
            patch.object(
                control.TEST_ASSETS,
                "load",
                return_value=None,
            ),
            patch.object(
                control,
                "read_key",
                return_value="ESC",
            ),
            patch(
                "tools.workbench_tui.shutil.get_terminal_size",
                return_value=types.SimpleNamespace(
                    columns=100,
                    lines=42,
                ),
            ),
            redirect_stdout(output),
        ):
            result = (
                control._problem_library_workbench(
                    mode="practice",
                )
            )

        self.assertIsNone(result)
        rendered = output.getvalue()
        self.assertIn(
            "篩選",
            rendered,
        )
        self.assertIn(
            "題目 · 1 題",
            rendered,
        )
        self.assertIn(
            "題目資訊",
            rendered,
        )
        self.assertIn(
            "測資",
            rendered,
        )

    def test_problem_library_tab_navigation_preserves_result_focus(self):
        items = [
            types.SimpleNamespace(
                external_id=pid,
                title=f"題目 {pid}",
                source="zerojudge",
                difficulty="D1",
                attempted=False,
                role="Guided Drill",
                has_l2=False,
                primary_skill="S01_IO",
                supporting_skills=(),
                canonical_url=f"https://example.invalid/{pid}",
            )
            for pid in ("a001", "a002")
        ]
        keys = iter(
            [
                "TAB",
                "DOWN",
                "ESC",
            ]
        )
        state = {
            "library_result_index": 0,
            "library_filter_kind": "results",
            "library_focus": 0,
            "library_filters_practice": None,
            "library_filters_exam": None,
            "library_query_practice": "",
            "library_query_exam": "",
        }

        with (
            patch.dict(
                control.UI_STATE,
                state,
                clear=True,
            ),
            patch.object(
                control,
                "_problem_library_items",
                return_value=items,
            ),
            patch.object(
                control.TEST_ASSETS,
                "load",
                return_value=None,
            ),
            patch.object(
                control,
                "read_key",
                side_effect=lambda: next(keys),
            ),
            patch(
                "tools.workbench_tui.shutil.get_terminal_size",
                return_value=types.SimpleNamespace(
                    columns=100,
                    lines=42,
                ),
            ),
            redirect_stdout(io.StringIO()),
        ):
            control._problem_library_workbench(
                mode="practice",
            )

            self.assertEqual(
                control.UI_STATE[
                    "library_result_index"
                ],
                1,
            )
            self.assertEqual(
                control.UI_STATE[
                    "library_focus"
                ],
                1,
            )

    def test_problem_library_right_arrow_moves_from_filters_to_results(self):
        items = [
            types.SimpleNamespace(
                external_id="a001",
                title="題目 a001",
                source="custom",
                difficulty="D1",
                attempted=False,
                role="Guided Drill",
                has_l2=False,
                primary_skill="S01_IO",
                supporting_skills=(),
                canonical_url="https://example.invalid/a001",
            ),
        ]
        keys = iter(
            [
                "RIGHT",
                "ESC",
            ]
        )
        state = {
            "library_result_index": 0,
            "library_filter_kind": "results",
            "library_focus": 0,
            "library_filters_practice": None,
            "library_filters_exam": None,
            "library_query_practice": "",
            "library_query_exam": "",
        }

        with (
            patch.dict(
                control.UI_STATE,
                state,
                clear=True,
            ),
            patch.object(
                control,
                "_problem_library_items",
                return_value=items,
            ),
            patch.object(
                control.TEST_ASSETS,
                "load",
                return_value=None,
            ),
            patch.object(
                control,
                "read_key",
                side_effect=lambda: next(keys),
            ),
            patch(
                "tools.workbench_tui.shutil.get_terminal_size",
                return_value=types.SimpleNamespace(
                    columns=100,
                    lines=42,
                ),
            ),
            redirect_stdout(io.StringIO()),
        ):
            control._problem_library_workbench(
                mode="practice",
            )
            final_focus = control.UI_STATE[
                "library_focus"
            ]

        self.assertEqual(
            final_focus,
            1,
        )

    def test_problem_library_master_list_does_not_duplicate_inspector_metadata(self):
        items = [
            types.SimpleNamespace(
                external_id=f"custom-{index}",
                title=f"題目 {index}",
                source="custom",
                difficulty="D1",
                attempted=False,
                role="Guided Drill",
                has_l2=False,
                primary_skill="S01_IO",
                supporting_skills=(),
                canonical_url=f"https://example.invalid/{index}",
            )
            for index in range(5)
        ]
        output = io.StringIO()
        state = {
            "library_result_index": 0,
            "library_filter_kind": "results",
            "library_focus": 1,
            "library_filters_practice": None,
            "library_filters_exam": None,
            "library_query_practice": "",
            "library_query_exam": "",
        }

        with (
            patch.dict(
                control.UI_STATE,
                state,
                clear=True,
            ),
            patch.object(
                control,
                "_problem_library_items",
                return_value=items,
            ),
            patch.object(
                control.TEST_ASSETS,
                "load",
                return_value=None,
            ),
            patch.object(
                control,
                "read_key",
                return_value="ESC",
            ),
            patch(
                "tools.workbench_tui.shutil.get_terminal_size",
                return_value=types.SimpleNamespace(
                    columns=100,
                    lines=42,
                ),
            ),
            redirect_stdout(output),
        ):
            control._problem_library_workbench(
                mode="practice",
            )

        rendered = output.getvalue()
        self.assertIn(
            "› 題目 · 5 題",
            rendered,
        )
        self.assertIn(
            "題目資訊",
            rendered,
        )
        self.assertEqual(
            rendered.count(
                "來源      custom"
            ),
            1,
        )
        self.assertNotIn(
            "custom · D1 · 未做",
            rendered,
        )

    def test_problem_library_filter_selection_persists_for_return_navigation(self):
        item = types.SimpleNamespace(
            external_id="a001",
            title="測試題",
            source="zerojudge",
            difficulty="D1",
            attempted=False,
            role="Guided Drill",
            has_l2=False,
            primary_skill="S01_IO",
            supporting_skills=(),
            canonical_url="https://example.invalid/a001",
        )
        keys = iter(
            [
                "DOWN",
                "DOWN",
                "ENTER",
                "DOWN",
                "DOWN",
                "ENTER",
                "ESC",
            ]
        )
        state = {
            "library_result_index": 0,
            "library_filter_kind": "results",
            "library_focus": 0,
            "library_filters_practice": None,
            "library_filters_exam": None,
            "library_query_practice": "",
            "library_query_exam": "",
        }

        with (
            patch.dict(
                control.UI_STATE,
                state,
                clear=True,
            ),
            patch.object(
                control,
                "_problem_library_items",
                return_value=[item],
            ),
            patch.object(
                control.TEST_ASSETS,
                "load",
                return_value=None,
            ),
            patch.object(
                control,
                "read_key",
                side_effect=lambda: next(keys),
            ),
            patch(
                "tools.workbench_tui.shutil.get_terminal_size",
                return_value=types.SimpleNamespace(
                    columns=100,
                    lines=42,
                ),
            ),
            redirect_stdout(io.StringIO()),
        ):
            control._problem_library_workbench(
                mode="practice",
            )

            saved = control.UI_STATE[
                "library_filters_practice"
            ]
            self.assertEqual(
                saved["difficulty"],
                "D2",
            )

    def test_problem_library_recommendation_is_clean_preset_not_old_filter_intersection(self):
        item = types.SimpleNamespace(
            external_id="a001",
            title="測試題",
            source="zerojudge",
            difficulty="D1",
            attempted=False,
            role="Guided Drill",
            has_l2=False,
            primary_skill="S01_IO",
            supporting_skills=(),
            canonical_url="https://example.invalid/a001",
        )
        keys = iter(
            [
                "ENTER",
                "ESC",
            ]
        )
        state = {
            "library_result_index": 0,
            "library_filter_kind": "results",
            "library_focus": 0,
            "library_filters_practice": {
                "skill_uids": (),
                "skill_label": None,
                "difficulty": "D5",
                "source": None,
                "attempted": None,
                "role": None,
                "require_l2": None,
            },
            "library_filters_exam": None,
            "library_query_practice": "old query",
            "library_query_exam": "",
        }

        with (
            patch.dict(
                control.UI_STATE,
                state,
                clear=True,
            ),
            patch.object(
                control,
                "_problem_library_items",
                return_value=[item],
            ),
            patch.object(
                control,
                "_recommended_problem_items",
                return_value=(
                    [item],
                    "依 Today 路徑",
                ),
            ),
            patch.object(
                control.TEST_ASSETS,
                "load",
                return_value=None,
            ),
            patch.object(
                control,
                "read_key",
                side_effect=lambda: next(keys),
            ),
            patch(
                "tools.workbench_tui.shutil.get_terminal_size",
                return_value=types.SimpleNamespace(
                    columns=100,
                    lines=42,
                ),
            ),
            redirect_stdout(io.StringIO()),
        ):
            control._problem_library_workbench(
                mode="practice",
            )

            saved = control.UI_STATE[
                "library_filters_practice"
            ]
            self.assertIsNone(
                saved["difficulty"]
            )
            self.assertEqual(
                control.UI_STATE[
                    "library_query_practice"
                ],
                "",
            )

    def test_problem_library_exam_workbench_never_renders_hidden_classification_values(self):
        item = types.SimpleNamespace(
            external_id="a001",
            title="一般題名",
            source="zerojudge",
            difficulty="D5",
            attempted=False,
            role="Transfer Challenge",
            has_l2=True,
            primary_skill="S18_DFS",
            supporting_skills=(
                "S30_COMPLEXITY",
            ),
            canonical_url="https://example.invalid/a001",
        )
        output = io.StringIO()
        state = {
            "library_result_index": 0,
            "library_filter_kind": "results",
            "library_focus": 0,
            "library_filters_practice": None,
            "library_filters_exam": None,
            "library_query_practice": "",
            "library_query_exam": "",
        }

        with (
            patch.dict(
                control.UI_STATE,
                state,
                clear=True,
            ),
            patch.object(
                control,
                "_problem_library_items",
                return_value=[item],
            ),
            patch.object(
                control.TEST_ASSETS,
                "load",
                return_value=None,
            ),
            patch.object(
                control,
                "read_key",
                return_value="ESC",
            ),
            patch(
                "tools.workbench_tui.shutil.get_terminal_size",
                return_value=types.SimpleNamespace(
                    columns=100,
                    lines=42,
                ),
            ),
            redirect_stdout(output),
        ):
            control._problem_library_workbench(
                mode="exam",
            )

        rendered = output.getvalue()
        self.assertIn(
            "[ 考試 · 防劇透 ]",
            rendered,
        )
        self.assertNotIn(
            "S18_DFS",
            rendered,
        )
        self.assertNotIn(
            "S30_COMPLEXITY",
            rendered,
        )
        self.assertNotIn(
            "Transfer Challenge",
            rendered,
        )
        self.assertNotIn(
            "D5",
            rendered,
        )

    def test_problem_library_exam_query_only_matches_public_id_or_title(self):
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
        )

        self.assertEqual(
            control._problem_library_query_filter(
                [item],
                "DFS",
                mode="exam",
            ),
            [],
        )
        self.assertEqual(
            control._problem_library_query_filter(
                [item],
                "a001",
                mode="exam",
            ),
            [item],
        )

    def test_problem_library_sidebar_groups_test_assets_without_input_output(self):
        item = types.SimpleNamespace(
            external_id="a001",
            title="測試題",
            source="zerojudge",
            difficulty="D1",
            attempted=False,
            role="Guided Drill",
            has_l2=False,
            primary_skill="S01_IO",
            supporting_skills=(),
            canonical_url="https://example.invalid/a001",
        )
        bundle = types.SimpleNamespace(
            cases=(
                types.SimpleNamespace(
                    case_id="S1",
                    name="官方範例 1",
                    provenance="OFFICIAL",
                    verified=True,
                ),
                types.SimpleNamespace(
                    case_id="E1",
                    name="最小邊界",
                    provenance="AI_GENERATED",
                    verified=True,
                ),
                types.SimpleNamespace(
                    case_id="G1",
                    name="AI candidate",
                    provenance="AI_GENERATED",
                    verified=False,
                ),
            )
        )

        with patch.object(
            control.TEST_ASSETS,
            "load",
            return_value=bundle,
        ):
            lines = (
                control._problem_library_inspector_lines(
                    item,
                    mode="practice",
                )
            )

        rendered = "\n".join(lines)
        self.assertIn(
            "官方 1",
            rendered,
        )
        self.assertIn(
            "S1 · 官方範例 1",
            rendered,
        )
        self.assertIn(
            "AI 生成已驗證 1",
            rendered,
        )
        self.assertIn(
            "E1 · 最小邊界",
            rendered,
        )
        self.assertIn(
            "Candidate 1",
            rendered,
        )
        self.assertIn(
            "未驗證，不影響 PASS / FAIL",
            rendered,
        )
        self.assertIn(
            "Ctrl+Shift+B 測試中心",
            rendered,
        )
        self.assertIn(
            "Input / Expected / Actual / Diff",
            rendered,
        )
        self.assertNotIn(
            "7 -3",
            rendered,
        )
        self.assertNotIn(
            "999",
            rendered,
        )

    def test_problem_library_sidebar_anonymizes_edge_case_names_for_unattempted_independent_work(self):
        item = types.SimpleNamespace(
            external_id="a001",
            title="獨立題",
            source="zerojudge",
            difficulty="D2",
            attempted=False,
            role="Core Independent",
            has_l2=False,
            primary_skill="S01_IO",
            supporting_skills=(),
            canonical_url="https://example.invalid/a001",
        )
        bundle = types.SimpleNamespace(
            cases=(
                types.SimpleNamespace(
                    case_id="E1",
                    name="Overflow Trap",
                    provenance="AI_GENERATED",
                    verified=True,
                ),
            )
        )

        with patch.object(
            control.TEST_ASSETS,
            "load",
            return_value=bundle,
        ):
            rendered = "\n".join(
                control._problem_library_inspector_lines(
                    item,
                    mode="practice",
                )
            )

        self.assertIn(
            "E1 · Local Case 1",
            rendered,
        )
        self.assertNotIn(
            "Overflow Trap",
            rendered,
        )

    def test_problem_library_exam_sidebar_hides_generated_test_inventory_before_attempt(self):
        item = types.SimpleNamespace(
            external_id="a001",
            title="考試題",
            source="zerojudge",
            difficulty="D5",
            attempted=False,
            role="Mock",
            has_l2=True,
            primary_skill="S18_DFS",
            supporting_skills=(),
            canonical_url="https://example.invalid/a001",
        )
        bundle = types.SimpleNamespace(
            cases=(
                types.SimpleNamespace(
                    case_id="S1",
                    name="官方範例 1",
                    provenance="OFFICIAL",
                    verified=True,
                ),
                types.SimpleNamespace(
                    case_id="E1",
                    name="DFS Trap",
                    provenance="AI_GENERATED",
                    verified=True,
                ),
                types.SimpleNamespace(
                    case_id="G1",
                    name="candidate",
                    provenance="AI_GENERATED",
                    verified=False,
                ),
            )
        )

        with patch.object(
            control.TEST_ASSETS,
            "load",
            return_value=bundle,
        ):
            rendered = "\n".join(
                control._problem_library_inspector_lines(
                    item,
                    mode="exam",
                )
            )

        self.assertIn(
            "官方 1",
            rendered,
        )
        self.assertIn(
            "延伸測資  作答後解鎖",
            rendered,
        )
        self.assertNotIn(
            "DFS Trap",
            rendered,
        )
        self.assertNotIn(
            "Candidate 1",
            rendered,
        )
        self.assertNotIn(
            "S18_DFS",
            rendered,
        )
        self.assertNotIn(
            "D5",
            rendered,
        )


    def test_problem_library_saved_filters_are_isolated_between_practice_and_exam(self):
        state = {
            "library_filters_practice": {
                "skill_uids": ("S18_DFS",),
                "skill_label": "DFS",
                "difficulty": "D4",
                "source": "zerojudge",
                "attempted": False,
                "role": "Core Independent",
                "require_l2": True,
            },
            "library_filters_exam": {
                "skill_uids": ("SHOULD_NOT_SURVIVE",),
                "skill_label": "hidden",
                "difficulty": "D5",
                "source": "zerojudge",
                "attempted": False,
                "role": "Mock",
                "require_l2": True,
            },
        }

        with patch.dict(
            control.UI_STATE,
            state,
            clear=False,
        ):
            practice = (
                control._problem_library_saved_filters(
                    "practice"
                )
            )
            exam = (
                control._problem_library_saved_filters(
                    "exam"
                )
            )

        self.assertEqual(
            practice["skill_uids"],
            ("S18_DFS",),
        )
        self.assertEqual(
            practice["difficulty"],
            "D4",
        )
        self.assertEqual(
            exam["skill_uids"],
            (),
        )
        self.assertIsNone(
            exam["difficulty"],
        )
        self.assertIsNone(
            exam["role"],
        )
        self.assertIsNone(
            exam["require_l2"],
        )
        self.assertEqual(
            exam["source"],
            "zerojudge",
        )
        self.assertFalse(
            exam["attempted"],
        )

    def test_problem_library_workbench_fits_compact_wide_width_without_fixed_96_column_overflow(self):
        item = types.SimpleNamespace(
            external_id="a001",
            title="測試題",
            source="zerojudge",
            difficulty="D1",
            attempted=False,
            role="Guided Drill",
            has_l2=False,
            primary_skill="S01_IO",
            supporting_skills=(),
            canonical_url="https://example.invalid/a001",
        )
        output = io.StringIO()
        state = {
            "library_result_index": 0,
            "library_filter_kind": "results",
            "library_focus": 0,
            "library_filters_practice": None,
            "library_filters_exam": None,
            "library_query_practice": "",
            "library_query_exam": "",
        }

        with (
            patch.dict(
                control.UI_STATE,
                state,
                clear=True,
            ),
            patch.object(
                control,
                "_problem_library_items",
                return_value=[item],
            ),
            patch.object(
                control.TEST_ASSETS,
                "load",
                return_value=None,
            ),
            patch.object(
                control,
                "read_key",
                return_value="ESC",
            ),
            patch(
                "tools.workbench_tui.shutil.get_terminal_size",
                return_value=types.SimpleNamespace(
                    columns=88,
                    lines=42,
                ),
            ),
            redirect_stdout(output),
        ):
            control._problem_library_workbench(
                mode="practice",
            )

        rendered = output.getvalue()
        self.assertIn(
            "題目 · 1 題",
            rendered,
        )
        self.assertIn(
            "題目資訊",
            rendered,
        )


    def test_problem_library_workbench_mode_toggle_returns_sentinel_and_preserves_state(self):
        item = types.SimpleNamespace(
            external_id="a001",
            title="測試題",
            source="zerojudge",
            difficulty="D1",
            attempted=False,
            role="Guided Drill",
            has_l2=False,
            primary_skill="S01_IO",
            supporting_skills=(),
            canonical_url="https://example.invalid/a001",
        )
        state = {
            "library_result_index": 0,
            "library_filter_kind": "results",
            "library_focus": 1,
            "library_filters_practice": {
                "skill_uids": (),
                "skill_label": None,
                "difficulty": "D1",
                "source": None,
                "attempted": None,
                "role": None,
                "require_l2": None,
            },
            "library_filters_exam": None,
            "library_query_practice": "a001",
            "library_query_exam": "",
        }

        with (
            patch.dict(
                control.UI_STATE,
                state,
                clear=True,
            ),
            patch.object(
                control,
                "_problem_library_items",
                return_value=[item],
            ),
            patch.object(
                control.TEST_ASSETS,
                "load",
                return_value=None,
            ),
            patch.object(
                control,
                "read_key",
                return_value="M",
            ),
            patch(
                "tools.workbench_tui.shutil.get_terminal_size",
                return_value=types.SimpleNamespace(
                    columns=100,
                    lines=42,
                ),
            ),
            redirect_stdout(io.StringIO()),
        ):
            result = (
                control._problem_library_workbench(
                    mode="practice",
                )
            )
            snapshot = dict(
                control.UI_STATE
            )

        self.assertIs(
            result,
            control.MODE_TOGGLE,
        )
        self.assertEqual(
            snapshot[
                "library_focus"
            ],
            1,
        )
        self.assertEqual(
            snapshot[
                "library_query_practice"
            ],
            "a001",
        )
        self.assertEqual(
            snapshot[
                "library_filters_practice"
            ]["difficulty"],
            "D1",
        )


    def test_today_reading_detail_routes_to_lesson_context_without_claiming_implementation_flow(self):
        route = types.SimpleNamespace(
            skill=types.SimpleNamespace(
                uid="S01_IO",
            ),
            placement=types.SimpleNamespace(
                problem_id="d050",
                title="妳那裡現在幾點了？",
                role="Guided Drill",
                lesson_uid="L-FND-01",
            ),
        )
        plan = types.SimpleNamespace(
            budget_minutes=18,
            selected=(),
            selected_minutes=0,
            deferred=(),
        )
        snapshot = {
            "target": "3+3",
            "capacity_minutes": 60,
            "plan": plan,
        }
        option = {
            "label": "新學習 · S01_IO × Reading",
            "kind": "new",
            "track": "Reading",
            "route": route,
        }

        rendered = "\n".join(
            control._today_option_detail_lines(
                snapshot,
                option,
            )
        )

        self.assertIn(
            "Track     Reading",
            rendered,
        )
        self.assertIn(
            "Lesson    L-FND-01",
            rendered,
        )
        self.assertIn(
            "Lesson context → Formal response",
            rendered,
        )
        self.assertNotIn(
            "Ctrl+Shift+B",
            rendered,
        )

    def test_today_implementation_detail_routes_to_test_center_then_oj(self):
        route = types.SimpleNamespace(
            skill=types.SimpleNamespace(
                uid="S01_IO",
            ),
            placement=types.SimpleNamespace(
                problem_id="d050",
                title="妳那裡現在幾點了？",
                role="Guided Drill",
                lesson_uid="L-FND-01",
            ),
        )
        plan = types.SimpleNamespace(
            budget_minutes=18,
            selected=(),
            selected_minutes=0,
            deferred=(),
        )
        snapshot = {
            "target": "3+3",
            "capacity_minutes": 60,
            "plan": plan,
        }
        option = {
            "label": "新學習 · S01_IO × Implementation",
            "kind": "new",
            "track": "Implementation",
            "route": route,
        }

        rendered = "\n".join(
            control._today_option_detail_lines(
                snapshot,
                option,
            )
        )

        self.assertIn(
            "Track     Implementation",
            rendered,
        )
        self.assertIn(
            "VS Code scratch → Ctrl+Shift+B → 正式 OJ → 完成題目",
            rendered,
        )

    def test_closed_screen_names_test_center_for_ctrl_shift_b(self):
        output = io.StringIO()
        with redirect_stdout(output):
            control.closed_screen()

        self.assertIn(
            "Ctrl+Shift+B",
            output.getvalue(),
        )
        self.assertIn(
            "測試中心",
            output.getvalue(),
        )


if __name__ == "__main__":
    unittest.main()
