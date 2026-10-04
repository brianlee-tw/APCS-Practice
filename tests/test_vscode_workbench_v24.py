import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import vscode_task
from tools.test_assets import (
    PROVENANCE_OFFICIAL,
    SUITE_FAST,
    TRUST_OFFICIAL,
    VISIBILITY_OFFICIAL,
    TestBundle,
    TestCase,
)


class VscodeTaskWorkbenchTest(unittest.TestCase):
    def test_copy_current_code_reads_saved_source_only(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "a001.cpp"
            source.write_text(
                "int main(){}\n",
                encoding="utf-8",
            )

            with patch.object(
                vscode_task,
                "_copy_text",
                return_value=(
                    True,
                    "fake clipboard",
                ),
            ) as copy:
                ok, detail = (
                    vscode_task
                    .copy_current_code(
                        str(source)
                    )
                )

        self.assertTrue(ok)
        self.assertIn(
            "a001.cpp",
            detail,
        )
        copy.assert_called_once_with(
            "int main(){}\n"
        )

    def test_oj_url_never_invents_missing_authority(self):
        self.assertIsNone(
            vscode_task._oj_url(
                None,
                None,
            )
        )

    def test_test_center_fast_visibility_uses_policy_store(self):
        bundle = TestBundle(
            source="zerojudge",
            external_id="d050",
            canonical_url="https://example.invalid",
            cases=(
                TestCase(
                    case_id="S1",
                    name="sample",
                    input_text="",
                    expected_output="",
                    provenance=PROVENANCE_OFFICIAL,
                    trust=TRUST_OFFICIAL,
                    suite=SUITE_FAST,
                    visibility=VISIBILITY_OFFICIAL,
                ),
            ),
        )

        with (
            patch.object(
                vscode_task,
                "_post_attempt",
                return_value=False,
            ),
            patch.object(
                vscode_task.control,
                "selection_mode",
                return_value="exam",
            ),
        ):
            cases = (
                vscode_task
                ._visible_cases(
                    bundle,
                    None,
                    "d050.cpp",
                    suite=SUITE_FAST,
                )
            )

        self.assertEqual(
            [case.case_id for case in cases],
            ["S1"],
        )

    def test_workspace_forces_save_before_task_run(self):
        settings = json.loads(
            (
                vscode_task.ROOT
                / ".vscode"
                / "settings.json"
            ).read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            settings.get(
                "task.saveBeforeRun"
            ),
            "always",
        )


    def test_zerojudge_catalog_identity_can_open_canonical_oj_without_intelligence_file(self):
        context = vscode_task.ProblemContext(
            problem_id="r488",
            title="APCS 彗星撞擊",
            source="ZeroJudge",
            canonical_url=None,
            solution_path=Path("/tmp/r488.cpp"),
            placement_uid=None,
            role=None,
            pb_uid=None,
            identity_origin="catalog_solution",
        )

        self.assertEqual(
            vscode_task._oj_url(
                context,
                None,
            ),
            "https://zerojudge.tw/ShowProblem?problemid=r488",
        )

    def test_core_independent_hides_generated_case_name_before_attempt(self):
        context = vscode_task.ProblemContext(
            problem_id="a001",
            title="Independent",
            source="zerojudge",
            canonical_url=None,
            solution_path=Path("/tmp/a001.cpp"),
            placement_uid=None,
            role="Core Independent",
            pb_uid=None,
            identity_origin="published_placement",
        )
        case = TestCase(
            case_id="E1",
            name="Overflow Trap",
            input_text="",
            expected_output="",
            provenance="AI_GENERATED",
            trust="DIFFERENTIAL_VERIFIED",
            suite="full",
            visibility="practice",
        )
        result = vscode_task.CaseResult(
            case=case,
            status=vscode_task.PASS,
            duration_ms=1,
            actual_output="",
            stderr="",
            returncode=0,
        )

        self.assertEqual(
            vscode_task._case_display_name(
                result,
                index=0,
                context=context,
                post_attempt=False,
            ),
            "Local Case 1",
        )
        self.assertEqual(
            vscode_task._case_display_name(
                result,
                index=0,
                context=context,
                post_attempt=True,
            ),
            "Overflow Trap",
        )

    def test_candidate_expected_output_is_never_rendered_as_truth(self):
        case = TestCase(
            case_id="G1",
            name="AI candidate",
            input_text="7 -3\n",
            expected_output="999\n",
            provenance="AI_GENERATED",
            trust="CANDIDATE",
            suite="full",
            visibility="practice",
        )
        result = vscode_task.CaseResult(
            case=case,
            status=vscode_task.UNVERIFIED,
            duration_ms=0,
            actual_output="",
            stderr="",
            returncode=None,
        )

        rendered = "\n".join(
            vscode_task._case_detail_lines(
                result,
                40,
                strict_pre_attempt=False,
            )
        )
        self.assertIn(
            "尚未驗證",
            rendered,
        )
        self.assertNotIn(
            "999",
            rendered,
        )

    def test_compile_warning_count_is_explicit(self):
        result = vscode_task.CompileResult(
            success=True,
            executable=Path("/tmp/a.out"),
            duration_ms=100,
            stdout="",
            stderr=(
                "a.cpp:1: warning: one\n"
                "a.cpp:2: warning: two\n"
            ),
        )
        self.assertEqual(
            vscode_task._compile_warning_count(
                result
            ),
            2,
        )

    def test_successful_build_without_test_assets_opens_test_center_instead_of_raw_stdin(self):
        compiled = vscode_task.CompileResult(
            success=True,
            executable=Path("/tmp/a.out"),
            duration_ms=50,
            stdout="",
            stderr="",
        )

        with (
            patch.object(
                vscode_task,
                "compile_current",
                return_value=(None, compiled),
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
            patch.object(
                vscode_task,
                "_interactive_run",
            ) as interactive,
        ):
            code = vscode_task.build_and_run(
                "/tmp/a001.cpp"
            )

        self.assertEqual(code, 0)
        interactive.assert_not_called()
        center.assert_called_once()
        self.assertIsNone(
            center.call_args.args[3]
        )
        self.assertEqual(
            center.call_args.args[4].cases,
            (),
        )


if __name__ == "__main__":
    unittest.main()
