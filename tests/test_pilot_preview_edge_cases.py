"""Independent verification for four official-only-to-Full pilot previews.

Two structurally different reference methods/problem, 17 ChatGPT-designed
Full-only cases, fixed-seed fuzz, boundary-size tests, and spoiler policies.
This runs in CI and does NOT certify OJ AC, learner mastery or C8 acceptance.
"""
from __future__ import annotations

from itertools import accumulate
import random
import re
import unittest

from tools import vscode_task
from tools.test_assets import (
    PROVENANCE_OFFICIAL, PROVENANCE_AI,
    TRUST_OFFICIAL, TRUST_DIFFERENTIAL_VERIFIED,
    SUITE_FAST, SUITE_FULL, TestAssetStore, same_output,
)

ROOT = vscode_task.ROOT
ITEMS = {
    "PB-42": ("cses", "1069", 1, 4),
    "PB-150": ("cses", "1094", 1, 5),
    "PB-97": ("codeforces", "71A", 1, 3),
    "PB-120": ("zerojudge", "q836", 2, 5),
}
RNG_SEED = 20261020


def oracle_a(uid: str, text: str) -> str:
    """Streaming/stepwise control-flow reference."""
    if uid == "PB-42":
        sequence = text.strip()
        assert sequence and all(x in "ACGT" for x in sequence)
        previous = ""
        run = longest = 0
        for ch in sequence:
            run = run + 1 if ch == previous else 1
            longest = max(longest, run)
            previous = ch
        return f"{longest}\n"
    if uid == "PB-150":
        tokens = list(map(int, text.split()))
        n, nums = tokens[0], tokens[1:]
        assert 1 <= n <= 200000 and len(nums) == n
        assert all(1 <= num <= 10**9 for num in nums)
        maximum, moves = nums[0], 0
        for num in nums[1:]:
            if num < maximum:
                moves += maximum - num
            else:
                maximum = num
        return f"{moves}\n"
    if uid == "PB-97":
        lines = text.strip().splitlines()
        n, words = int(lines[0]), lines[1:]
        assert 1 <= n <= 100 and len(words) == n
        assert all(1 <= len(word) <= 100 and word.isascii()
                   and word.islower() and word.isalpha() for word in words)
        answers = []
        for word in words:
            if len(word) > 10:
                answers.append(word[0] + str(len(word) - 2) + word[-1])
            else:
                answers.append(word)
        return "\n".join(answers) + "\n"
    if uid == "PB-120":
        k, x1, y1, x2, y2 = map(int, text.split())
        assert 1 <= k <= 20
        assert 1 <= x1 <= 10 and 1 <= x2 <= 10
        assert 1 <= y1 <= 20 and 1 <= y2 <= 20
        p, health = 0, k
        for _ in range(1000):
            p += health
            if p % x1 == 0:
                health -= y1
            if p % x2 == 0:
                health -= y2
            if health <= 0:
                return f"{p}\n"
        raise ValueError("unexpected q836 nontermination")
    raise ValueError(f"unsupported {uid}")


def oracle_b(uid: str, text: str) -> str:
    """Regex/prefix-max/list-transform/next-event route, separate from A."""
    if uid == "PB-42":
        sequence = text.strip()
        assert sequence and set(sequence).issubset({"A", "C", "G", "T"})
        runs = re.findall(r"A+|C+|G+|T+", sequence)
        assert "".join(runs) == sequence
        return f"{max(map(len, runs))}\n"
    if uid == "PB-150":
        xs = list(map(int, text.split()))
        n, a = xs[0], xs[1:]
        assert n == len(a) and n >= 1
        prefix_peaks = accumulate(a, max)
        return f"{sum(peak - value for peak, value in zip(prefix_peaks, a))}\n"
    if uid == "PB-97":
        parts = text.split()
        n, words = int(parts[0]), parts[1:]
        assert n == len(words)
        transformed = [
            word if len(word) <= 10
            else "{}{}{}".format(word[:1], len(word[1:-1]), word[-1:])
            for word in words
        ]
        return "\n".join(transformed) + "\n"
    if uid == "PB-120":
        k, x1, y1, x2, y2 = map(int, text.split())
        p, hp = 0, k
        # Jump over all positions that trigger no trap, by searching the
        # next event under the current constant movement step hp.
        for _ in range(1000):
            first_hit = None
            for jump_count in range(1, max(x1, x2) + 1):
                target = p + jump_count * hp
                if target % x1 == 0 or target % x2 == 0:
                    first_hit = jump_count
                    break
            if first_hit is None:
                raise ValueError("no next trap within one modular period")
            p += first_hit * hp
            loss = y1 * (p % x1 == 0) + y2 * (p % x2 == 0)
            hp -= loss
            if hp <= 0:
                return f"{p}\n"
        raise ValueError("unexpected q836 nontermination")
    raise ValueError(f"unsupported {uid}")


def fuzz(uid: str, rng: random.Random):
    if uid == "PB-42":
        for _ in range(240):
            n = rng.randint(1, 500)
            yield "".join(rng.choice("ACGT") for __ in range(n)) + "\n"
    elif uid == "PB-150":
        for _ in range(240):
            n = rng.randint(1, 200)
            data = [rng.randint(1, 10**9) for __ in range(n)]
            yield f"{n}\n" + " ".join(map(str, data)) + "\n"
    elif uid == "PB-97":
        for _ in range(240):
            n = rng.randint(1, 25)
            lines = [
                "".join(rng.choice("abcdefghijklmnopqrstuvwxyz")
                        for ___ in range(rng.randint(1, 100)))
                for __ in range(n)
            ]
            yield f"{n}\n" + "\n".join(lines) + "\n"
    elif uid == "PB-120":
        for _ in range(240):
            k = rng.randint(1, 20)
            x1, x2 = rng.randint(1, 10), rng.randint(1, 10)
            y1, y2 = rng.randint(1, 20), rng.randint(1, 20)
            yield f"{k}\n{x1} {y1}\n{x2} {y2}\n"


class PilotPreviewEdgeCaseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = TestAssetStore(ROOT / "data/problem_enrichment")
        cls.placements = {
            p.pb_uid: p for p in vscode_task.CURRICULUM.all_placements()
        }

    def test_17_verified_edges_and_5_original_official_samples(self):
        for uid, (source, external, official, added) in ITEMS.items():
            with self.subTest(uid=uid):
                bundle = self.store.load(source, external, include_candidates=False)
                self.assertIsNotNone(bundle)
                assert bundle is not None
                self.assertEqual(bundle.official_count, official)
                self.assertEqual(len(bundle.cases), official + added)
                self.assertEqual(len({x.case_id for x in bundle.cases}), official + added)
                for case in bundle.cases:
                    with self.subTest(uid=uid, case=case.case_id):
                        left = oracle_a(uid, case.input_text)
                        right = oracle_b(uid, case.input_text)
                        self.assertEqual(left, right)
                        self.assertTrue(same_output(left, case.expected_output))
                        if case.provenance == PROVENANCE_OFFICIAL:
                            self.assertEqual(case.trust, TRUST_OFFICIAL)
                            self.assertEqual(case.suite, SUITE_FAST)
                            self.assertEqual(case.visibility, "official")
                        else:
                            self.assertEqual(case.provenance, PROVENANCE_AI)
                            self.assertEqual(
                                case.trust, TRUST_DIFFERENTIAL_VERIFIED
                            )
                            self.assertEqual(case.suite, SUITE_FULL)
                            self.assertEqual(case.visibility, "practice")
                            self.assertTrue(case.name.startswith("加強測資 "))
                            self.assertNotIn("邊界", case.name)
                            self.assertNotIn("溢位", case.name)

    def test_960_seeded_random_inputs_crosscheck_two_oracles(self):
        rng = random.Random(RNG_SEED)
        for uid in ITEMS:
            for index, case in enumerate(fuzz(uid, rng)):
                with self.subTest(uid=uid, index=index):
                    self.assertEqual(oracle_a(uid, case), oracle_b(uid, case))

    def test_maximum_source_sizes_without_checking_big_fixtures_into_git(self):
        sequence = "ACGT" * 250000
        self.assertEqual(
            oracle_a("PB-42", sequence), oracle_b("PB-42", sequence)
        )
        self.assertEqual(oracle_a("PB-42", sequence), "1\n")

        arr = [10**9] + [1] * (200000 - 1)
        input_data = "200000\n" + " ".join(map(str, arr)) + "\n"
        expected = 999999999 * 199999
        self.assertGreater(expected, 2**31 - 1)
        self.assertEqual(
            oracle_a("PB-150", input_data),
            f"{expected}\n",
        )
        self.assertEqual(oracle_a("PB-150", input_data), oracle_b("PB-150", input_data))

        n = 100
        long_words = "a" * 100
        input_data = f"{n}\n" + (long_words + "\n") * n
        self.assertEqual(
            oracle_a("PB-97", input_data), oracle_b("PB-97", input_data)
        )
        self.assertEqual(
            oracle_a("PB-97", input_data), ("a98a\n" * n)
        )

        for k in (1, 20):
            for x1 in range(1, 11):
                for x2 in range(1, 11):
                    s = f"{k}\n{x1} 1\n{x2} 20\n"
                    self.assertEqual(oracle_a("PB-120", s), oracle_b("PB-120", s))

    def test_published_context_fast_full_exam_transfer_spoiler_guards(self):
        for uid, (source, external, official, added) in ITEMS.items():
            placement = self.placements[uid]
            phantom = (
                ROOT / ".apcs/runtime/learn/2099-01-01"
                / f"{placement.problem_id}__{placement.placement_uid}.cpp"
            )
            ctx = vscode_task.problem_context(str(phantom))
            self.assertIsNotNone(ctx)
            assert ctx is not None
            bundle = vscode_task._test_bundle(ctx)
            self.assertIsNotNone(bundle)
            assert bundle is not None
            for mode, role, after, suite, count in (
                ("practice", ctx.role, False, SUITE_FAST, official),
                ("practice", ctx.role, False, SUITE_FULL, official + added),
                ("exam", ctx.role, False, SUITE_FULL, official),
                ("practice", "Transfer Challenge", False, SUITE_FULL, official),
                ("exam", ctx.role, True, SUITE_FULL, official + added),
            ):
                with (
                    unittest.mock.patch.object(
                        vscode_task.control, "selection_mode", return_value=mode
                    ),
                    unittest.mock.patch.object(
                        vscode_task, "_post_attempt", return_value=after
                    ),
                ):
                    result = vscode_task._visible_cases(
                        bundle,
                        ctx if role == ctx.role else __import__("dataclasses").replace(ctx, role=role),
                        str(phantom), suite=suite,
                    )
                self.assertEqual(len(result), count, (uid, mode, role, after))
            self.assertFalse(phantom.exists())

    def test_tampered_expected_output_cannot_agree_with_both_oracles(self):
        bundle = self.store.load("cses", "1094", include_candidates=False)
        assert bundle is not None
        edge = next(case for case in bundle.cases if case.case_id == "E4")
        actual = oracle_a("PB-150", edge.input_text)
        self.assertNotEqual(actual, "2147483647\n")
        self.assertFalse(same_output(actual, "2147483647\n"))


if __name__ == "__main__":
    unittest.main()
