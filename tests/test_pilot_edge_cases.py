"""Independent regression proof for ChatGPT edge-case candidates.

Two differently structured reference procedures per problem must agree on every
curated case and on deterministic generated inputs. All verified edges remain
FULL-only / non-official; strict preattempt can show official examples only.
"""
from __future__ import annotations

import bisect
import random
import unittest
from pathlib import Path

from tools.test_assets import (
    PROVENANCE_AI,
    PROVENANCE_OFFICIAL,
    SUITE_FAST,
    SUITE_FULL,
    TRUST_DIFFERENTIAL_VERIFIED,
    TRUST_OFFICIAL,
    TestAssetStore,
    same_output,
)

ROOT = Path(__file__).resolve().parents[1]
TEST_DATA = ROOT / "data" / "problem_enrichment"
IDS = ("d067", "d097", "d732", "j606")
OFFICIAL_COUNTS = {"d067": 4, "d097": 1, "d732": 1, "j606": 2}
EDGE_COUNTS = {"d067": 6, "d097": 4, "d732": 3, "j606": 4}


def oracle_direct(problem: str, source: str) -> str:
    """Reference A: direct semantics (membership/set/scatter)."""
    if problem == "d067":
        year = int(source.strip())
        leap = year % 400 == 0 or (year % 4 == 0 and year % 100 != 0)
        return ("a leap year" if leap else "a normal year") + "\n"

    if problem == "d097":
        lines = []
        for line in source.strip().splitlines():
            parts = list(map(int, line.split()))
            n, values = parts[0], parts[1:]
            assert n == len(values) and 1 <= n < 3000
            diffs = {abs(values[i] - values[i - 1]) for i in range(1, n)}
            lines.append("Jolly" if diffs == set(range(1, n)) else "Not jolly")
        return "\n".join(lines) + "\n"

    if problem == "d732":
        lines = source.strip().splitlines()
        n, k = map(int, lines[0].split())
        values = list(map(int, lines[1].split()))
        queries = list(map(int, lines[2].split()))
        assert len(values) == n and len(queries) == k
        assert values == sorted(set(values))
        positions = {value: index for index, value in enumerate(values, start=1)}
        return "\n".join(str(positions.get(query, 0)) for query in queries) + "\n"

    if problem == "j606":
        lines = source.strip().splitlines()
        k, q, r = map(int, lines[0].split())
        current = lines[1]
        steps = lines[2:]
        assert len(current) == k and len(steps) == q and 1 <= r <= k
        snapshots = []
        for raw in steps:
            permutation = list(map(int, raw.split()))
            assert sorted(permutation) == list(range(1, k + 1))
            next_chars = [""] * k
            for old_index, new_position in enumerate(permutation):
                next_chars[new_position - 1] = current[old_index]
            current = "".join(next_chars)
            snapshots.append(current)
        return "\n".join(
            "".join(value[index] for value in snapshots)
            for index in range(r)
        ) + "\n"

    raise AssertionError("unsupported problem " + problem)


def oracle_independent(problem: str, source: str) -> str:
    """Reference B: a different algorithmic route from Reference A."""
    if problem == "d067":
        y = int(source.strip())
        def prior_days(year: int) -> int:
            z = year - 1
            return 365 * z + z // 4 - z // 100 + z // 400
        leap = prior_days(y + 1) - prior_days(y) == 366
        return ("a leap year" if leap else "a normal year") + "\n"

    if problem == "d097":
        outputs = []
        for row in source.splitlines():
            if not row.strip():
                continue
            nums = list(map(int, row.split()))
            n = nums[0]
            assert len(nums) == n + 1
            differences = sorted(abs(b - a) for a, b in zip(nums[1:-1], nums[2:]))
            outputs.append(
                "Jolly" if differences == list(range(1, n)) else "Not jolly"
            )
        return "\n".join(outputs) + "\n"

    if problem == "d732":
        toks = list(map(int, source.split()))
        n, k = toks[:2]
        values = toks[2:2 + n]
        queries = toks[2 + n:]
        assert len(queries) == k and values == sorted(set(values))
        result = []
        for query in queries:
            offset = bisect.bisect_left(values, query)
            result.append(
                str(offset + 1 if offset < n and values[offset] == query else 0)
            )
        return "\n".join(result) + "\n"

    if problem == "j606":
        toks = source.strip().splitlines()
        k, q, r = [int(s) for s in toks[0].split()]
        current = list(toks[1])
        assert len(current) == k and len(toks) == q + 2
        stored_columns: list[list[str]] = [[] for _ in range(r)]
        for row in toks[2:]:
            perm = list(map(int, row.split()))
            assert sorted(perm) == list(range(1, k + 1))
            inverse = [perm.index(i + 1) for i in range(k)]
            current = [current[inverse[j]] for j in range(k)]
            for j in range(r):
                stored_columns[j].append(current[j])
        return "\n".join(map("".join, stored_columns)) + "\n"

    raise AssertionError("unsupported problem " + problem)


def fuzz_cases(problem: str, rng: random.Random):
    if problem == "d067":
        for _ in range(220):
            yield f"{rng.randint(1, 1000000)}\n"
    elif problem == "d097":
        for _ in range(220):
            parts = []
            for __ in range(rng.randint(1, 4)):
                n = rng.randint(1, 60)
                values = [rng.randint(-1000, 1000) for ___ in range(n)]
                parts.append(f"{n} " + " ".join(map(str, values)))
            yield "\n".join(parts) + "\n"
    elif problem == "d732":
        for _ in range(220):
            n, k = rng.randint(1, 80), rng.randint(1, 80)
            nums = sorted(rng.sample(range(-500, 501), n))
            queries = [
                rng.choice(nums) if rng.randrange(2) else rng.randint(-600, 600)
                for __ in range(k)
            ]
            yield f"{n} {k}\n" + " ".join(map(str, nums)) + "\n" + " ".join(map(str, queries)) + "\n"
    elif problem == "j606":
        for _ in range(220):
            k, q = rng.randint(1, 12), rng.randint(1, 12)
            r = rng.randint(1, k)
            initial = "".join(rng.choice("abca") for __ in range(k))
            ops = []
            for __ in range(q):
                order = list(range(1, k + 1))
                rng.shuffle(order)
                ops.append(" ".join(map(str, order)))
            yield f"{k} {q} {r}\n{initial}\n" + "\n".join(ops) + "\n"
    else:
        raise AssertionError(problem)


class PilotEdgeCaseVerificationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = TestAssetStore(TEST_DATA)

    def test_all_official_examples_and_verified_edges_match_two_oracles(self):
        for problem in IDS:
            with self.subTest(problem=problem):
                bundle = self.store.load("zerojudge", problem, include_candidates=False)
                self.assertIsNotNone(bundle)
                assert bundle is not None
                self.assertEqual(bundle.official_count, OFFICIAL_COUNTS[problem])
                self.assertEqual(
                    len(bundle.cases) - bundle.official_count, EDGE_COUNTS[problem]
                )
                self.assertEqual(len({c.case_id for c in bundle.cases}), len(bundle.cases))
                for case in bundle.cases:
                    with self.subTest(problem=problem, case=case.case_id):
                        self.assertEqual(
                            oracle_direct(problem, case.input_text),
                            oracle_independent(problem, case.input_text),
                        )
                        self.assertTrue(
                            same_output(
                                oracle_independent(problem, case.input_text),
                                case.expected_output,
                            )
                        )
                        if case.provenance == PROVENANCE_OFFICIAL:
                            self.assertEqual(case.trust, TRUST_OFFICIAL)
                            self.assertEqual(case.suite, SUITE_FAST)
                            self.assertEqual(case.visibility, "official")
                        else:
                            self.assertEqual(case.provenance, PROVENANCE_AI)
                            self.assertEqual(case.trust, TRUST_DIFFERENTIAL_VERIFIED)
                            self.assertEqual(case.suite, SUITE_FULL)
                            self.assertEqual(case.visibility, "practice")
                            self.assertTrue(case.name.startswith("加強測資 "))
                            # Do not place method/edge identity in visible case names.
                            self.assertNotIn("邊界", case.name)
                            self.assertNotIn("排序", case.name)

    def test_fuzz_880_independently_generated_valid_inputs(self):
        rng = random.Random(20261018)
        for problem in IDS:
            for index, source in enumerate(fuzz_cases(problem, rng)):
                with self.subTest(problem=problem, fuzz=index):
                    self.assertEqual(
                        oracle_direct(problem, source),
                        oracle_independent(problem, source),
                    )

    def test_source_constraint_maximum_sizes_with_independent_references(self):
        # Large valid inputs are synthesized at test time to avoid checking
        # megabytes of deterministic fixtures into Git.
        n, k = 100000, 100000
        values = list(range(-50000, 50000))
        queries = list(range(-50001, 49999))
        search_input = (
            f"{n} {k}\n"
            + " ".join(map(str, values)) + "\n"
            + " ".join(map(str, queries)) + "\n"
        )
        self.assertEqual(
            oracle_direct("d732", search_input),
            oracle_independent("d732", search_input),
        )

        nums = list(range(2999))
        jolly = "2999 " + " ".join(map(str, nums)) + "\n"
        self.assertEqual(
            oracle_direct("d097", jolly),
            oracle_independent("d097", jolly),
        )
        self.assertEqual(oracle_direct("d097", jolly), "Not jolly\n")

        permutation = list(range(20, 0, -1))
        matrix_input = (
            "20 20 20\n"
            + "abcdefghijklmnopqrst\n"
            + (" ".join(map(str, permutation)) + "\n") * 20
        )
        self.assertEqual(
            oracle_direct("j606", matrix_input),
            oracle_independent("j606", matrix_input),
        )
        self.assertEqual(len(oracle_direct("j606", matrix_input).splitlines()), 20)

    def test_fast_full_and_strict_spoiler_visibility(self):
        self.assertEqual(self.store.validate_all(), [])
        for problem in IDS:
            with self.subTest(problem=problem):
                bundle = self.store.load("zerojudge", problem, include_candidates=False)
                assert bundle is not None
                def visible(mode, activity, post, suite=SUITE_FULL):
                    return self.store.visible_cases(
                        bundle, mode=mode, activity=activity,
                        post_attempt=post, suite=suite,
                    )
                self.assertEqual(
                    len(visible("practice", "Core Independent", False, SUITE_FAST)),
                    OFFICIAL_COUNTS[problem],
                )
                self.assertEqual(
                    len(visible("practice", "Core Independent", False)),
                    OFFICIAL_COUNTS[problem] + EDGE_COUNTS[problem],
                )
                for mode, activity in (
                    ("exam", "Mock"),
                    ("practice", "Transfer Challenge"),
                ):
                    only_official = visible(mode, activity, False)
                    self.assertEqual(len(only_official), OFFICIAL_COUNTS[problem])
                    self.assertTrue(
                        all(x.trust == TRUST_OFFICIAL for x in only_official)
                    )
                    after_attempt = visible(mode, activity, True)
                    self.assertEqual(
                        len(after_attempt),
                        OFFICIAL_COUNTS[problem] + EDGE_COUNTS[problem],
                    )

    def test_expected_output_tampering_is_detected(self):
        bundle = self.store.load("zerojudge", "j606", include_candidates=False)
        assert bundle is not None
        edge = next(x for x in bundle.cases if x.case_id == "E2")
        self.assertFalse(
            same_output(oracle_direct("j606", edge.input_text), "incorrect\n")
        )


if __name__ == "__main__":
    unittest.main()
