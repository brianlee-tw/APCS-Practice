"""End-to-end source-pinned semantic judging for CF 977C.

Use the official problem's multiple-answer semantics. Never claim OJ AC,
learner Evidence or readiness from the local verdict.
"""
from __future__ import annotations

import copy
import json
import random
import shutil
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from tools import vscode_task
from tools.local_test_runner import (
    PASS, WRONG_OUTPUT, CaseResult, compile_cpp, run_case, run_suite,
)
from tools.semantic_checkers import (
    CHECKER_EXACT, CHECKER_CF_977C, check_cf_977c,
)
from tools.test_assets import TestAssetError, TestAssetStore

ROOT = Path(__file__).resolve().parents[1]


def exhaustive_small_oracle(inp: str, output: str) -> bool:
    """Independent brute force, only for random small-range inputs."""
    n, k, *arr = map(int, inp.split())
    assert n == len(arr) and all(1 <= v <= 12 for v in arr)
    legal = {
        x for x in range(1, 13)
        if sum(v <= x for v in arr) == k
    }
    token = output.strip()
    if token == "-1":
        return not legal
    try:
        v = int(token)
    except ValueError:
        return False
    return v in legal


class CF977CSemanticJudgeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = TestAssetStore(ROOT / "data/problem_enrichment")
        cls.bundle = cls.store.load(
            "codeforces", "977C", include_candidates=False
        )
        assert cls.bundle is not None
        cls.placement = next(
            p for p in vscode_task.CURRICULUM.all_placements()
            if p.pb_uid == "PB-109"
        )

    def test_official_two_examples_are_multiple_answer_semantics(self):
        bundle = self.bundle
        self.assertEqual(bundle.official_count, 2)
        self.assertEqual(bundle.verified_count, 9)
        self.assertEqual(len(bundle.cases), 9)
        s1, s2 = bundle.cases[:2]
        self.assertEqual(s1.expected_output, "6\n")
        self.assertEqual(s2.expected_output, "-1\n")
        self.assertTrue(all(c.checker == CHECKER_CF_977C for c in bundle.cases))
        self.assertTrue(check_cf_977c(s1.input_text, "5\n"))
        self.assertTrue(check_cf_977c(s1.input_text, "6\n"))
        self.assertFalse(check_cf_977c(s1.input_text, "7\n"))
        self.assertFalse(check_cf_977c(s1.input_text, "-1\n"))
        self.assertTrue(check_cf_977c(s2.input_text, "-1\n"))
        self.assertFalse(check_cf_977c(s2.input_text, "2\n"))

    def test_k_zero_k_n_boundary_duplicates_and_x_limits(self):
        examples = [
            ("3 0\n2 3 4\n", "1\n", True),
            ("3 0\n1 3 4\n", "-1\n", True),
            ("3 0\n1 3 4\n", "0\n", False),
            ("4 4\n1 4 4 1000000000\n", "1000000000\n", True),
            ("4 4\n1 4 4 1000000000\n", "1000000001\n", False),
            ("5 2\n2 2 2 7 8\n", "-1\n", True),
            ("5 2\n2 2 2 7 8\n", "2\n", False),
            ("6 3\n1 2 2 9 9 10\n", "5\n", True),
            ("6 3\n1 2 2 9 9 10\n", "8\n", True),
            ("6 3\n1 2 2 9 9 10\n", "9\n", False),
            ("3 1\n1 1 2\n", "-1\n", True),
        ]
        for inp, out, truth in examples:
            with self.subTest(inp=inp, out=out):
                self.assertIs(check_cf_977c(inp, out), truth)

    def test_reject_malformed_output_and_input_fail_closed(self):
        source = self.bundle.cases[0].input_text
        for bad in (
            "", " ", "5 6\n", "5\n6\n", "5.0\n", "abc\n",
            "+5\n", "0005\n", "-2\n", "1000000001\n",
        ):
            self.assertFalse(check_cf_977c(source, bad), bad)
        for bad in (
            "", "3 2\n1 2\n", "0 0\n", "3 4\n1 2 3\n",
            "3 1\n0 2 3\n", "3 1\n1 2 1000000001\n",
        ):
            self.assertFalse(check_cf_977c(bad, "2\n"), bad)

    def test_400_small_random_inputs_against_brute_force_all_x(self):
        rng = random.Random(20261022)
        for repeat in range(400):
            n = rng.randint(1, 15)
            k = rng.randint(0, n)
            arr = [rng.randint(1, 12) for _ in range(n)]
            inp = f"{n} {k}\n" + " ".join(map(str, arr)) + "\n"
            candidates = ["-1\n", *(f"{x}\n" for x in range(1, 13))]
            for output in candidates:
                self.assertEqual(
                    check_cf_977c(inp, output),
                    exhaustive_small_oracle(inp, output),
                    (repeat, inp, output),
                )

    def test_max_n_200000_and_duplicate_threshold(self):
        n = 200000
        values = [1] * 100000 + [10**9] * 100000
        inp = f"{n} 100000\n" + " ".join(map(str, values)) + "\n"
        self.assertTrue(check_cf_977c(inp, "1\n"))
        self.assertTrue(check_cf_977c(inp, "500000000\n"))
        self.assertFalse(check_cf_977c(inp, "1000000000\n"))
        inp_impossible = inp.replace("200000 100000", "200000 99999", 1)
        self.assertTrue(check_cf_977c(inp_impossible, "-1\n"))

    def test_exact_fallback_is_still_exact_and_other_sources_cannot_claim_checker(self):
        normal = self.store.load("codeforces", "71A", include_candidates=False)
        assert normal is not None
        self.assertTrue(all(c.checker == CHECKER_EXACT for c in normal.cases))

        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            for source, external_id, canonical in [
                ("codeforces", "71A", "https://codeforces.com/problemset/problem/71/A"),
                ("codeforces", "977C", "https://example.invalid/fake"),
                ("zerojudge", "977C", "https://codeforces.com/problemset/problem/977/C"),
            ]:
                with self.subTest(source=source, external_id=external_id):
                    target = data / source / external_id / "tests.json"
                    target.parent.mkdir(parents=True)
                    target.write_text(json.dumps({
                        "schema_version": "apcs-test-bundle-v1",
                        "checker": CHECKER_CF_977C,
                        "identity": {
                            "source": source,
                            "external_id": external_id,
                            "canonical_url": canonical,
                        },
                        "cases": [{
                            "id": "S1", "name": "sample",
                            "input": "7 4\n3 7 5 1 10 3 20\n",
                            "expected_output": "6\n",
                            "provenance": "OFFICIAL", "trust": "OFFICIAL",
                            "suite": "fast", "visibility": "official",
                        }],
                    }), encoding="utf-8")
                    with self.assertRaises(TestAssetError):
                        TestAssetStore(data).load(source, external_id)
            # Even the real identity must not silently fall back to EXACT.
            source, external_id = "codeforces", "977C"
            target = data / source / external_id / "tests.json"
            target.write_text(json.dumps({
                "schema_version": "apcs-test-bundle-v1",
                "identity": {
                    "source": source, "external_id": external_id,
                    "canonical_url": "https://codeforces.com/problemset/problem/977/C",
                },
                "cases": [],
            }), encoding="utf-8")
            with self.assertRaises(TestAssetError):
                TestAssetStore(data).load(source, external_id)

    def test_published_workbench_identity_and_fast_full_spoiler(self):
        p = self.placement
        phantom = ROOT / ".apcs/runtime/learn/2099-01-01" / f"{p.problem_id}__{p.placement_uid}.cpp"
        context = vscode_task.problem_context(str(phantom))
        self.assertIsNotNone(context)
        assert context is not None
        self.assertEqual(context.pb_uid, "PB-109")
        self.assertEqual(vscode_task._test_bundle(context), self.bundle)
        self.assertIsNone(vscode_task._test_bundle(
            replace(context, pb_uid="PB-97")
        ))
        self.assertIsNone(vscode_task._test_bundle(
            replace(context, canonical_url="https://codeforces.com/problemset/problem/71/A")
        ))
        from unittest.mock import patch
        with (
            patch.object(vscode_task.control, "selection_mode", return_value="practice"),
            patch.object(vscode_task, "_post_attempt", return_value=False),
        ):
            fast = vscode_task._visible_cases(self.bundle, context, str(phantom), suite="fast")
            full = vscode_task._visible_cases(self.bundle, context, str(phantom), suite="full")
        self.assertEqual(len(fast), 2)
        self.assertEqual(len(full), 9)
        with (
            patch.object(vscode_task.control, "selection_mode", return_value="exam"),
            patch.object(vscode_task, "_post_attempt", return_value=False),
        ):
            pre = vscode_task._visible_cases(self.bundle, context, str(phantom), suite="full")
        self.assertEqual(len(pre), 2)
        self.assertTrue(all(c.provenance == "OFFICIAL" for c in pre))
        self.assertFalse(phantom.exists())

    def test_ui_explains_valid_answer_and_suppresses_misleading_diff(self):
        case = self.bundle.cases[0]
        result = CaseResult(
            case=case, status=WRONG_OUTPUT, duration_ms=1,
            actual_output="7\n", stderr="", returncode=0,
        )
        text = "\n".join(vscode_task._case_detail_lines(
            result, 70, strict_pre_attempt=False,
        ))
        self.assertIn("官方範例答案非唯一", text)
        self.assertNotIn("Difference", text)
        self.assertNotIn("--- Expected", text)

    @unittest.skipUnless(shutil.which("g++"), "g++ required for live C++ runner")
    def test_compile_run_semantic_multiple_answers_and_bad_output(self):
        code = """#include <algorithm>
#include <iostream>
#include <vector>
using namespace std;
int main() {
 int n,k; if (!(cin>>n>>k)) return 1;
 vector<int> a(n); for (auto &v:a) cin>>v;
 sort(a.begin(),a.end());
 if(k==0) cout << (a[0]==1 ? -1 : 1);
 else if(k==n) cout<<a[n-1];
 else cout<<(a[k-1]==a[k] ? -1 : a[k-1]);
 cout<<"\\n";
}
"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cpp = root / "solution.cpp"
            cpp.write_text(code, encoding="utf-8")
            compiled = compile_cpp(cpp, root / "program", root=root)
            self.assertTrue(compiled.success, compiled.stderr)
            assert compiled.executable is not None
            results = run_suite(compiled.executable, self.bundle.cases, root=root)
            self.assertTrue(results.all_passed)
            self.assertEqual(results.passed_count, 9)

            # A program that outputs the *other* valid sample x=5 must pass.
            alternative = root / "alternative.cpp"
            alternative.write_text(
                '#include <iostream>\nint main(){std::cout<<5<<"\\n";}\n',
                encoding="utf-8",
            )
            exe2 = compile_cpp(alternative, root / "alternative", root=root)
            self.assertTrue(exe2.success, exe2.stderr)
            assert exe2.executable is not None
            accepted = run_case(exe2.executable, self.bundle.cases[0], root=root)
            self.assertEqual(accepted.status, PASS)
            rejected = run_case(exe2.executable, self.bundle.cases[1], root=root)
            self.assertEqual(rejected.status, WRONG_OUTPUT)


if __name__ == "__main__":
    unittest.main()
