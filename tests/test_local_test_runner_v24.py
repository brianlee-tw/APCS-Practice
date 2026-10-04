import shutil
import tempfile
import unittest
from pathlib import Path

from tools.local_test_runner import (
    PASS,
    TIMEOUT,
    WRONG_OUTPUT,
    compile_cpp,
    run_case,
    unified_diff,
)
from tools.test_assets import (
    PROVENANCE_OFFICIAL,
    SUITE_FAST,
    TRUST_OFFICIAL,
    VISIBILITY_OFFICIAL,
    TestCase,
    same_output,
)


class LocalTestRunnerV24Test(unittest.TestCase):
    def test_output_policy_ignores_final_newline_and_line_tail_space(self):
        self.assertTrue(
            same_output(
                "3   \n",
                "3\n",
            )
        )
        self.assertFalse(
            same_output(
                "3 4\n",
                "34\n",
            )
        )

    def test_diff_is_bounded(self):
        diff = unified_diff(
            "1\n2\n3\n",
            "1\n9\n3\n",
            max_lines=6,
        )
        self.assertTrue(diff)
        self.assertLessEqual(
            len(diff),
            7,
        )

    @unittest.skipUnless(
        shutil.which("g++"),
        "需要 g++",
    )
    def test_compile_and_case_runner_distinguish_pass_and_wrong_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "a001.cpp"
            source.write_text(
                "#include <iostream>\n"
                "int main(){ long long a,b; std::cin>>a>>b; "
                "std::cout<<a+b<<'\\n'; }\n",
                encoding="utf-8",
            )
            executable = root / "build" / "a001"
            compiled = compile_cpp(
                source,
                executable,
                root=root,
            )
            self.assertTrue(
                compiled.success
            )

            case = TestCase(
                case_id="S1",
                name="官方範例",
                input_text="1 2\n",
                expected_output="3\n",
                provenance=PROVENANCE_OFFICIAL,
                trust=TRUST_OFFICIAL,
                suite=SUITE_FAST,
                visibility=VISIBILITY_OFFICIAL,
            )
            passed = run_case(
                executable,
                case,
                root=root,
            )
            self.assertEqual(
                passed.status,
                PASS,
            )

            wrong = TestCase(
                case_id="S2",
                name="錯誤期待值",
                input_text="1 2\n",
                expected_output="4\n",
                provenance=PROVENANCE_OFFICIAL,
                trust=TRUST_OFFICIAL,
                suite=SUITE_FAST,
                visibility=VISIBILITY_OFFICIAL,
            )
            failed = run_case(
                executable,
                wrong,
                root=root,
            )
            self.assertEqual(
                failed.status,
                WRONG_OUTPUT,
            )

    @unittest.skipUnless(
        shutil.which("g++"),
        "需要 g++",
    )
    def test_timeout_cannot_block_workflow(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "loop.cpp"
            source.write_text(
                "int main(){ for(;;){} }\n",
                encoding="utf-8",
            )
            executable = root / "build" / "loop"
            compiled = compile_cpp(
                source,
                executable,
                root=root,
            )
            self.assertTrue(
                compiled.success
            )

            case = TestCase(
                case_id="E1",
                name="timeout",
                input_text="",
                expected_output="",
                provenance=PROVENANCE_OFFICIAL,
                trust=TRUST_OFFICIAL,
                suite=SUITE_FAST,
                visibility=VISIBILITY_OFFICIAL,
            )
            result = run_case(
                executable,
                case,
                root=root,
                timeout_seconds=0.1,
            )
            self.assertEqual(
                result.status,
                TIMEOUT,
            )


if __name__ == "__main__":
    unittest.main()
