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


if __name__ == "__main__":
    unittest.main()
