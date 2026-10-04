import io
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
    PROVENANCE_OFFICIAL,
    SUITE_FAST,
    TRUST_OFFICIAL,
    VISIBILITY_OFFICIAL,
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


if __name__ == "__main__":
    unittest.main()
