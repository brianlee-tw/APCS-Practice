import io
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from tools import apcs_control as control
from tools import vscode_task
from tools import workbench_tui
from tools.local_test_runner import (
    PASS,
    CaseResult,
    CompileResult,
    SuiteResult,
)
from tools.test_assets import (
    PROVENANCE_AI,
    PROVENANCE_OFFICIAL,
    SUITE_FAST,
    SUITE_FULL,
    TRUST_CANDIDATE,
    TRUST_OFFICIAL,
    VISIBILITY_OFFICIAL,
    VISIBILITY_PRACTICE,
    TestBundle,
    TestCase,
)
from tools.workbench_context import ProblemContext


class WorkbenchAcceptanceV24Test(unittest.TestCase):
    def assert_frame_width(
        self,
        rendered: str,
        width: int,
    ) -> None:
        for line in rendered.splitlines():
            self.assertLessEqual(
                workbench_tui.display_width(
                    line
                ),
                width,
                msg=(
                    f"line exceeds {width} cols: "
                    f"{workbench_tui.display_width(line)} · {line!r}"
                ),
            )

    def test_ansi_width_and_fit_are_visual_not_escape_sequence_width(self):
        colored = (
            f"{workbench_tui.CYAN}"
            f"{workbench_tui.BOLD}"
            "測試中心"
            f"{workbench_tui.RESET}"
        )
        self.assertEqual(
            workbench_tui.display_width(
                colored
            ),
            workbench_tui.display_width(
                "測試中心"
            ),
        )
        clipped = workbench_tui.fit(
            colored + " · 很長的狀態文字",
            12,
        )
        self.assertLessEqual(
            workbench_tui.display_width(
                clipped
            ),
            12,
        )

    def test_pane_widths_never_overflow_even_when_requested_minimums_are_impossible(self):
        widths = workbench_tui.pane_widths(
            32,
            (42, 58),
            gap=3,
            min_width=28,
        )
        self.assertEqual(
            len(widths),
            2,
        )
        self.assertLessEqual(
            sum(widths) + 3,
            32,
        )
        self.assertTrue(
            all(width >= 1 for width in widths)
        )

    def test_command_bar_wraps_inside_narrow_terminal(self):
        output = io.StringIO()
        with (
            patch.object(
                workbench_tui,
                "terminal_width",
                return_value=32,
            ),
            redirect_stdout(output),
        ):
            workbench_tui.command_bar(
                [
                    ("↑↓", "選測資"),
                    ("R", "重跑"),
                    ("T", "完整測試"),
                    ("I", "手動輸入"),
                    ("C", "複製程式碼"),
                    ("O", "開啟 OJ"),
                    ("Esc", "關閉"),
                ]
            )

        self.assert_frame_width(
            output.getvalue(),
            32,
        )

    def test_test_center_has_real_narrow_stacked_fallback(self):
        case = TestCase(
            case_id="S1",
            name="sample",
            input_text="1\n",
            expected_output="1\n",
            provenance=PROVENANCE_OFFICIAL,
            trust=TRUST_OFFICIAL,
            suite=SUITE_FAST,
            visibility=VISIBILITY_OFFICIAL,
        )
        result = CaseResult(
            case=case,
            status=PASS,
            duration_ms=3,
            actual_output="1\n",
            stderr="",
            returncode=0,
        )
        compiled = CompileResult(
            success=True,
            executable=Path("/tmp/a.out"),
            duration_ms=40,
            stdout="",
            stderr="",
        )
        context = ProblemContext(
            problem_id="d050",
            title="妳那裡現在幾點了？",
            source="zerojudge",
            canonical_url="https://example.invalid/d050",
            solution_path=Path("/tmp/d050.cpp"),
            placement_uid="PL-TEST",
            role="Guided Drill",
            pb_uid="PB-TEST",
            identity_origin="published_placement",
        )
        bundle = TestBundle(
            source="zerojudge",
            external_id="d050",
            canonical_url="https://example.invalid/d050",
            cases=(case,),
        )
        output = io.StringIO()

        with (
            patch(
                "tools.workbench_tui.shutil.get_terminal_size",
                return_value=types.SimpleNamespace(
                    columns=50,
                    lines=26,
                ),
            ),
            patch.object(
                vscode_task.control,
                "selection_mode",
                return_value="practice",
            ),
            patch.object(
                vscode_task.control,
                "read_key",
                return_value="ESC",
            ),
            patch.object(
                vscode_task,
                "_post_attempt",
                return_value=False,
            ),
            redirect_stdout(output),
        ):
            code = vscode_task._test_center(
                "/tmp/d050.cpp",
                Path("/tmp/a.out"),
                context,
                bundle,
                SuiteResult((result,)),
                compiled,
            )

        self.assertEqual(code, 0)
        rendered = output.getvalue()
        self.assertIn(
            "選中測資",
            rendered,
        )
        self.assert_frame_width(
            rendered,
            48,
        )

    def test_choose_menu_keeps_context_inside_redrawn_frame(self):
        output = io.StringIO()
        with (
            patch.object(
                control,
                "read_key",
                return_value="ESC",
            ),
            redirect_stdout(output),
        ):
            result = control.choose_menu(
                "模擬考 · 下一步",
                [
                    {
                        "label": "d050",
                        "detail": "保持作答",
                        "enabled": True,
                    },
                ],
                context_lines=[
                    "時間      12/60 min · 剩餘約 48 min",
                    "目前題目  d050",
                ],
            )

        self.assertIsNone(result)
        rendered = output.getvalue()
        self.assertIn(
            "12/60 min",
            rendered,
        )
        self.assertIn(
            "目前題目  d050",
            rendered,
        )

    def test_exam_center_passes_live_runtime_status_into_menu_frame(self):
        session = {
            "duration_minutes": 60,
            "problem_ids": [
                "d050",
                "a001",
            ],
            "selected_problem_id": "d050",
        }
        summary = {
            "elapsed_minutes": 12,
            "compile_count": 3,
            "submit_count": 1,
            "switch_count": 2,
        }

        with (
            patch.object(
                control.EXAM,
                "active",
                return_value=session,
            ),
            patch.object(
                control.EXAM,
                "summary",
                return_value=summary,
            ),
            patch.object(
                control,
                "choose_menu",
                return_value=None,
            ) as menu,
        ):
            control.exam_center()

        context_lines = (
            menu.call_args.kwargs[
                "context_lines"
            ]
        )
        self.assertIn(
            control.aligned_field(
                "時間",
                "12 / 60 min",
            ),
            context_lines,
        )
        self.assertIn(
            control.aligned_field(
                "剩餘",
                "約 48 min",
            ),
            context_lines,
        )
        self.assertIn(
            control.aligned_field(
                "題目",
                "d050",
            ),
            context_lines,
        )
        self.assertIn(
            control.aligned_field(
                "編譯",
                "3 次",
            ),
            context_lines,
        )
        self.assertIn(
            control.aligned_field(
                "提交",
                "1 次",
            ),
            context_lines,
        )
        self.assertIn(
            control.aligned_field(
                "切題",
                "2 次",
            ),
            context_lines,
        )

    def test_test_center_no_case_path_stays_inside_narrow_terminal(self):
        compiled = CompileResult(
            success=True,
            executable=Path("/tmp/a.out"),
            duration_ms=40,
            stdout="",
            stderr="",
        )
        output = io.StringIO()

        with (
            patch(
                "tools.workbench_tui.shutil.get_terminal_size",
                return_value=types.SimpleNamespace(
                    columns=34,
                    lines=24,
                ),
            ),
            patch.object(
                vscode_task.control,
                "selection_mode",
                return_value="practice",
            ),
            patch.object(
                vscode_task.control,
                "read_key",
                return_value="ESC",
            ),
            patch.object(
                vscode_task,
                "_post_attempt",
                return_value=False,
            ),
            redirect_stdout(output),
        ):
            code = vscode_task._test_center(
                "/tmp/very_long_solution_name.cpp",
                Path("/tmp/a.out"),
                None,
                None,
                SuiteResult(()),
                compiled,
            )

        self.assertEqual(code, 0)
        rendered = output.getvalue()
        self.assertIn(
            "執行資訊",
            rendered,
        )
        self.assert_frame_width(
            rendered,
            32,
        )

    def test_low_density_grid_uses_available_vertical_space(self):
        output = io.StringIO()

        with (
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
            control.choose_grid(
                "今日學習 · 可用時間",
                [
                    {
                        "label": "15 分",
                        "detail": "",
                        "enabled": True,
                    },
                    {
                        "label": "30 分",
                        "detail": "",
                        "enabled": True,
                    },
                    {
                        "label": "45 分",
                        "detail": "",
                        "enabled": True,
                    },
                ],
                wide_columns=3,
            )

        lines = output.getvalue().splitlines()
        footer_index = next(
            index
            for index, line in enumerate(lines)
            if "←→ 選擇" in line
        )
        self.assertGreaterEqual(
            footer_index,
            30,
        )

    def test_git_center_fits_exact_86_column_boundary(self):
        output = io.StringIO()
        changes = [
            {
                "code": "M ",
                "path": "tools/apcs_control.py",
                "paths": [
                    "tools/apcs_control.py",
                ],
                "display": (
                    "tools/apcs_control.py"
                ),
            },
        ]

        with (
            patch(
                "tools.workbench_tui.shutil.get_terminal_size",
                return_value=types.SimpleNamespace(
                    columns=88,
                    lines=42,
                ),
            ),
            patch.object(
                control,
                "validate_summary",
                return_value=(0, 0, 0),
            ),
            patch.object(
                control,
                "git_changes",
                return_value=changes,
            ),
            patch.object(
                control,
                "staged_count",
                return_value=1,
            ),
            patch.object(
                control,
                "unstaged_count",
                return_value=0,
            ),
            patch.object(
                control,
                "branch_sync",
                return_value={
                    "branch": "feat/c8-workbench-test-center",
                    "upstream": (
                        "origin/feat/c8-workbench-test-center"
                    ),
                    "ahead": 2,
                    "behind": 0,
                },
            ),
            patch.object(
                control,
                "whitespace_ok",
                return_value=True,
            ),
            patch.object(
                control,
                "suggested_commit_message",
                return_value=(
                    "fix: validate Workbench acceptance"
                ),
            ),
            patch.object(
                control,
                "read_key",
                return_value="ESC",
            ),
            redirect_stdout(output),
        ):
            control.git_center()

        rendered = output.getvalue()
        self.assertIn(
            "Upstream",
            rendered,
        )
        self.assert_frame_width(
            rendered,
            86,
        )


    def test_control_center_wide_frame_prioritizes_mode_next_action_problem_and_capacity(self):
        plan = types.SimpleNamespace(
            budget_minutes=18,
            selected=(),
            selected_minutes=0,
            deferred=(),
        )
        route = types.SimpleNamespace(
            skill=types.SimpleNamespace(
                uid="S01_IO",
            ),
            placement=types.SimpleNamespace(
                lesson_uid="L-FND-01",
                problem_id="d050",
            ),
        )
        snapshot = {
            "capacity_minutes": 60,
            "plan": plan,
            "new_learning": route,
            "cognitive_plan": types.SimpleNamespace(
                selected=(),
            ),
            "curriculum_blocker": None,
            "warning": None,
        }
        problem = {
            "id": "r488",
            "title": "APCS 彗星撞擊",
            "path": Path("/tmp/r488.cpp"),
            "state": None,
            "due": None,
            "source": "zerojudge",
            "url": "https://zerojudge.tw/ShowProblem?problemid=r488",
        }
        options = [
            {
                "label": "今日學習",
                "detail": "依 Evidence 與容量安排下一步",
                "enabled": True,
                "section": "主要",
                "kind": "today",
                "action": "開啟",
            },
            {
                "label": "題目庫",
                "detail": "選題",
                "enabled": True,
                "section": "主要",
                "kind": "library",
                "action": "開啟",
            },
            {
                "label": "模擬考",
                "detail": "計時",
                "enabled": True,
                "section": "主要",
                "kind": "exam",
                "action": "開啟",
            },
        ]
        output = io.StringIO()

        with (
            patch(
                "tools.workbench_tui.shutil.get_terminal_size",
                return_value=types.SimpleNamespace(
                    columns=100,
                    lines=42,
                ),
            ),
            patch.object(
                control,
                "adaptive_today_snapshot",
                return_value=snapshot,
            ),
            patch.object(
                control,
                "selection_mode",
                return_value="practice",
            ),
            patch.object(
                control,
                "current_catalog_solution",
                return_value=None,
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
            redirect_stdout(output),
        ):
            selected = control.choose_grid(
                "控制中心",
                options,
                problem=problem,
                main=True,
                mode_toggle=True,
                back_text="關閉",
            )

        self.assertIsNone(selected)
        rendered = output.getvalue()
        self.assertIn(
            "[ 練習 ]",
            rendered,
        )
        self.assertIn(
            "現在可做",
            rendered,
        )
        self.assertIn(
            "目前題目",
            rendered,
        )
        self.assertIn(
            "今日容量",
            rendered,
        )
        self.assertIn(
            "S01_IO",
            rendered,
        )
        self.assertIn(
            "r488",
            rendered,
        )
        self.assertIn(
            "Ctrl+Shift+B",
            rendered,
        )
        self.assert_frame_width(
            rendered,
            96,
        )

        lines = rendered.splitlines()
        footer_index = next(
            index
            for index, line in enumerate(lines)
            if "M 切換選題模式" in line
        )
        self.assertGreaterEqual(
            footer_index,
            34,
        )

    def test_today_wide_frame_uses_88_column_boundary_without_overflow(self):
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
            "curriculum_blocker": None,
        }
        options = [
            {
                "label": "新學習 · S01_IO × Reading",
                "detail": "Guided Drill · L-FND-01 · d050",
                "enabled": True,
                "kind": "new",
                "track": "Reading",
                "route": types.SimpleNamespace(
                    skill=types.SimpleNamespace(
                        uid="S01_IO",
                    ),
                    placement=types.SimpleNamespace(
                        problem_id="d050",
                        title="妳那裡現在幾點了？",
                        role="Guided Drill",
                        lesson_uid="L-FND-01",
                    ),
                ),
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
                "tools.workbench_tui.shutil.get_terminal_size",
                return_value=types.SimpleNamespace(
                    columns=88,
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
            selected = control._today_action_menu(
                snapshot,
                options,
            )

        self.assertIsNone(selected)
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
            "Lesson    L-FND-01",
            rendered,
        )
        self.assert_frame_width(
            rendered,
            86,
        )

        lines = rendered.splitlines()
        footer_index = next(
            index
            for index, line in enumerate(lines)
            if "Esc / Q 返回控制中心" in line
        )
        self.assertGreaterEqual(
            footer_index,
            34,
        )


    def test_learning_status_fits_exact_86_column_boundary(self):
        snapshot = {
            "target": "3+3",
            "attempts": 12,
            "evidence": 8,
            "evidence_by_track": {
                "Reading": 3,
                "Implementation": 5,
            },
            "memory_states": 7,
            "capacity_minutes": 60,
            "review_selected_minutes": 18,
            "review_budget_minutes": 18,
            "review_selected": 2,
            "review_deferred": 1,
            "protected_new_learning_minutes": 42,
            "remote_acknowledged": 6,
            "remote_pending": 2,
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
                    columns=88,
                    lines=42,
                ),
            ),
            redirect_stdout(output),
        ):
            control.learning_status_view()

        rendered = output.getvalue()
        self.assertIn(
            "LEARNER_READINESS = NOT ASSESSED",
            rendered,
        )
        self.assertIn(
            "目前進度",
            rendered,
        )
        self.assertIn(
            "今日容量",
            rendered,
        )
        self.assert_frame_width(
            rendered,
            86,
        )

    def test_learning_status_narrow_summary_stays_inside_terminal(self):
        snapshot = {
            "target": "3+3",
            "attempts": 12,
            "evidence": 8,
            "evidence_by_track": {
                "Reading": 3,
                "Implementation": 5,
            },
            "memory_states": 7,
            "capacity_minutes": 60,
            "review_selected_minutes": 18,
            "review_budget_minutes": 18,
            "review_selected": 2,
            "review_deferred": 3,
            "protected_new_learning_minutes": 42,
            "remote_acknowledged": 6,
            "remote_pending": 2,
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
                    columns=62,
                    lines=30,
                ),
            ),
            redirect_stdout(output),
        ):
            control.learning_status_view()

        rendered = output.getvalue()
        self.assertIn(
            "安全延後",
            rendered,
        )
        self.assert_frame_width(
            rendered,
            60,
        )

    def test_solution_data_fits_exact_86_column_boundary(self):
        problem = {
            "id": "d050",
            "title": "妳那裡現在幾點了？",
            "path": Path("/tmp/d050.cpp"),
            "state": None,
        }
        solution = types.SimpleNamespace(
            language="cpp",
            path="solutions/d050.cpp",
            complexity="O(1)",
        )
        output = io.StringIO()

        with (
            patch.object(
                control,
                "solutions_for_problem",
                return_value=(solution,),
            ),
            patch.object(
                control,
                "read_key",
                return_value="ESC",
            ),
            patch(
                "tools.apcs_control.shutil.get_terminal_size",
                return_value=types.SimpleNamespace(
                    columns=88,
                    lines=42,
                ),
            ),
            redirect_stdout(output),
        ):
            result = control.solution_center_ui(
                problem,
                "/tmp/d050.cpp",
            )

        self.assertEqual(
            result,
            "/tmp/d050.cpp",
        )
        rendered = output.getvalue()
        self.assertIn(
            "已登錄解法 · 1",
            rendered,
        )
        self.assertIn(
            "選中解法資訊",
            rendered,
        )
        self.assertIn(
            "C++",
            rendered,
        )
        self.assert_frame_width(
            rendered,
            86,
        )

    def test_problem_library_narrow_width_uses_compact_fallback(self):
        with (
            patch.object(
                control,
                "selection_mode",
                return_value="practice",
            ),
            patch.object(
                control,
                "choose_grid",
                return_value=None,
            ) as compact,
            patch.object(
                control,
                "_problem_library_workbench",
            ) as workbench,
            patch(
                "tools.apcs_control.shutil.get_terminal_size",
                return_value=types.SimpleNamespace(
                    columns=80,
                    lines=30,
                ),
            ),
        ):
            control.problem_library_view()

        compact.assert_called_once()
        workbench.assert_not_called()

    def test_exam_test_center_hides_nonofficial_inventory_pre_attempt(self):
        official = TestCase(
            case_id="S1",
            name="official sample",
            input_text="1\n",
            expected_output="1\n",
            provenance=PROVENANCE_OFFICIAL,
            trust=TRUST_OFFICIAL,
            suite=SUITE_FAST,
            visibility=VISIBILITY_OFFICIAL,
        )
        hidden_candidate = TestCase(
            case_id="G1",
            name="hidden candidate",
            input_text="2\n",
            expected_output=None,
            provenance=PROVENANCE_AI,
            trust=TRUST_CANDIDATE,
            suite=SUITE_FULL,
            visibility=VISIBILITY_PRACTICE,
        )
        bundle = TestBundle(
            source="zerojudge",
            external_id="d050",
            canonical_url="https://example.invalid/d050",
            cases=(
                official,
                hidden_candidate,
            ),
        )
        result = CaseResult(
            case=official,
            status=PASS,
            duration_ms=3,
            actual_output="1\n",
            stderr="",
            returncode=0,
        )
        compiled = CompileResult(
            success=True,
            executable=Path("/tmp/a.out"),
            duration_ms=40,
            stdout="",
            stderr="",
        )
        context = ProblemContext(
            problem_id="d050",
            title="妳那裡現在幾點了？",
            source="zerojudge",
            canonical_url="https://example.invalid/d050",
            solution_path=Path("/tmp/d050.cpp"),
            placement_uid="PL-TEST",
            role="Guided Drill",
            pb_uid="PB-TEST",
            identity_origin="published_placement",
        )
        output = io.StringIO()

        with (
            patch.object(
                control,
                "selection_mode",
                return_value="exam",
            ),
            patch.object(
                vscode_task,
                "_post_attempt",
                return_value=False,
            ),
            patch.object(
                control,
                "read_key",
                return_value="ESC",
            ),
            patch.object(
                vscode_task,
                "terminal_width",
                return_value=100,
            ),
            patch.object(
                vscode_task,
                "terminal_height",
                return_value=42,
            ),
            redirect_stdout(output),
        ):
            code = vscode_task._test_center(
                "/tmp/d050.cpp",
                Path("/tmp/a.out"),
                context,
                bundle,
                SuiteResult((result,)),
                compiled,
            )

        self.assertEqual(
            code,
            0,
        )
        rendered = output.getvalue()
        self.assertIn(
            "防劇透",
            rendered,
        )
        self.assertIn(
            "目前可見 official 1",
            rendered,
        )
        self.assertNotIn(
            "Candidate",
            rendered,
        )
        self.assertNotIn(
            "hidden candidate",
            rendered,
        )
        self.assertNotIn(
            "已驗證",
            rendered,
        )
        self.assert_frame_width(
            rendered,
            100,
        )

    def test_test_center_refuses_copy_after_source_changes_since_build(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "d050.cpp"
            source.write_text(
                "int main(){return 0;}\n",
                encoding="utf-8",
            )
            built_digest = (
                vscode_task._source_digest(
                    str(source)
                )
            )
            source.write_text(
                "int main(){return 1;}\n",
                encoding="utf-8",
            )

            compiled = CompileResult(
                success=True,
                executable=Path(temp) / "a.out",
                duration_ms=40,
                stdout="",
                stderr="",
            )
            output = io.StringIO()
            keys = iter(
                [
                    "C",
                    "ESC",
                ]
            )

            with (
                patch.object(
                    control,
                    "selection_mode",
                    return_value="practice",
                ),
                patch.object(
                    vscode_task,
                    "_post_attempt",
                    return_value=False,
                ),
                patch.object(
                    control,
                    "read_key",
                    side_effect=lambda: next(keys),
                ),
                patch.object(
                    vscode_task,
                    "copy_current_code",
                ) as copy_code,
                patch.object(
                    vscode_task,
                    "terminal_width",
                    return_value=80,
                ),
                patch.object(
                    vscode_task,
                    "terminal_height",
                    return_value=30,
                ),
                redirect_stdout(output),
            ):
                code = vscode_task._test_center(
                    str(source),
                    Path(temp) / "a.out",
                    None,
                    None,
                    SuiteResult(()),
                    compiled,
                    compiled_source_digest=built_digest,
                )

        self.assertEqual(
            code,
            0,
        )
        copy_code.assert_not_called()
        self.assertIn(
            "本次 build 後變更",
            output.getvalue(),
        )

    def test_build_and_run_marks_copy_untrusted_if_source_changes_during_compile(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "d050.cpp"
            source.write_text(
                "int main(){return 0;}\n",
                encoding="utf-8",
            )
            compiled = CompileResult(
                success=True,
                executable=Path(temp) / "a.out",
                duration_ms=40,
                stdout="",
                stderr="",
            )

            def fake_compile(filename):
                Path(filename).write_text(
                    "int main(){return 1;}\n",
                    encoding="utf-8",
                )
                return None, compiled

            with (
                patch.object(
                    vscode_task,
                    "compile_current",
                    side_effect=fake_compile,
                ),
                patch.object(
                    vscode_task,
                    "_test_bundle",
                    return_value=None,
                ),
                patch.object(
                    vscode_task,
                    "_test_center",
                    return_value=0,
                ) as center,
            ):
                code = vscode_task.build_and_run(
                    str(source)
                )

        self.assertEqual(
            code,
            0,
        )
        self.assertIsNone(
            center.call_args.kwargs[
                "compiled_source_digest"
            ]
        )

    def test_oj_followup_routes_exam_and_practice_without_auto_submit(self):
        context = ProblemContext(
            problem_id="d050",
            title="妳那裡現在幾點了？",
            source="zerojudge",
            canonical_url="https://example.invalid/d050",
            solution_path=Path("/tmp/d050.cpp"),
            placement_uid="PL-TEST",
            role="Guided Drill",
            pb_uid="PB-TEST",
            identity_origin="published_placement",
        )

        with patch.object(
            vscode_task.EXAM,
            "active",
            return_value={
                "selected_problem_id": "d050",
            },
        ):
            exam_text = vscode_task._oj_followup(
                "/tmp/d050.cpp",
                context,
            )

        self.assertIn(
            "模擬考 → 記錄提交",
            exam_text,
        )
        self.assertIn(
            "不代表已 Submit",
            exam_text,
        )

        with (
            patch.object(
                vscode_task.EXAM,
                "active",
                return_value=None,
            ),
            patch.object(
                control,
                "current_problem",
                return_value={
                    "runtime_action": "finish",
                },
            ),
        ):
            finish_text = vscode_task._oj_followup(
                "/tmp/d050.cpp",
                context,
            )

        self.assertIn(
            "完成題目",
            finish_text,
        )
        self.assertIn(
            "不會自動寫入 Evidence",
            finish_text,
        )

    def test_exam_telemetry_failure_does_not_break_ordinary_compile_hook(self):
        context = ProblemContext(
            problem_id="d050",
            title="測試題",
            source="zerojudge",
            canonical_url="https://example.invalid/d050",
            solution_path=Path("/tmp/d050.cpp"),
            placement_uid="PL-TEST",
            role="Guided Drill",
            pb_uid="PB-TEST",
            identity_origin="published_placement",
        )

        with patch.object(
            vscode_task.EXAM,
            "mark_compile",
            side_effect=vscode_task.ExamRuntimeError(
                "corrupt exam state"
            ),
        ):
            vscode_task._mark_exam_compile(
                context,
                success=True,
            )

    def test_commit_quality_gate_does_not_auto_push(self):
        changes = [
            {
                "code": "M ",
                "path": "tools/apcs_control.py",
                "paths": [
                    "tools/apcs_control.py",
                ],
                "display": "tools/apcs_control.py",
            },
        ]

        def fake_git(*args):
            if args == (
                "diff",
                "--cached",
                "--stat",
            ):
                return types.SimpleNamespace(
                    returncode=0,
                    stdout=(
                        " tools/apcs_control.py | 2 +-\n"
                        " 1 file changed, 1 insertion(+), 1 deletion(-)"
                    ),
                    stderr="",
                )
            if args[:2] == (
                "commit",
                "-m",
            ):
                return types.SimpleNamespace(
                    returncode=0,
                    stdout="[branch abc1234] test",
                    stderr="",
                )
            if args == (
                "rev-parse",
                "--short",
                "HEAD",
            ):
                return types.SimpleNamespace(
                    returncode=0,
                    stdout="abc1234\n",
                    stderr="",
                )
            raise AssertionError(
                f"unexpected git call: {args!r}"
            )

        with (
            patch.object(
                control,
                "git_changes",
                return_value=changes,
            ),
            patch.object(
                control,
                "staged_count",
                return_value=1,
            ),
            patch.object(
                control,
                "whitespace_ok",
                return_value=True,
            ),
            patch.object(
                control,
                "local_quality_gate",
                return_value=types.SimpleNamespace(
                    returncode=0,
                    stdout="PASS",
                    stderr="",
                ),
            ),
            patch.object(
                control,
                "suggested_commit_message",
                return_value="fix: close evidence workflow",
            ),
            patch.object(
                control,
                "run_git",
                side_effect=fake_git,
            ) as run_git,
            patch(
                "builtins.input",
                return_value="",
            ),
            patch.object(
                control,
                "confirm",
                return_value=True,
            ),
            patch.object(
                control,
                "push_commit",
            ) as push,
            patch.object(
                control,
                "pause",
            ),
            redirect_stdout(
                io.StringIO()
            ),
        ):
            control.create_commit()

        self.assertTrue(
            any(
                call.args[:2] == (
                    "commit",
                    "-m",
                )
                for call in run_git.call_args_list
            )
        )
        push.assert_not_called()


if __name__ == "__main__":
    unittest.main()
