"""Pilot integration acceptance without learner attempts or filesystem writes.

Exercise the same Published Placement -> Workbench context -> TestAssetStore
path used by Ctrl+Shift+B. Unit-only bundle tests cannot catch namespaced
Published problem IDs being passed as judge-local external IDs.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
import unittest

from tools import vscode_task
from tools.test_assets import SUITE_FAST, SUITE_FULL

PILOT = {
    "PB-182": ("d067", 4, 6),
    "PB-183": ("d097", 1, 4),
    "PB-27": ("d732", 1, 3),
    "PB-9": ("j606", 2, 4),
}


class PilotIntegrationAcceptanceTest(unittest.TestCase):
    def test_published_scratch_resolves_exact_official_and_verified_assets(self):
        curriculum = vscode_task.CURRICULUM
        placements = {p.pb_uid: p for p in curriculum.all_placements()}
        for uid, (external_id, official_count, edge_count) in PILOT.items():
            with self.subTest(pb_uid=uid):
                placement = placements[uid]
                # Control Center creates these exact suffixes (and hyphens).
                nonexistent = (
                    vscode_task.ROOT / ".apcs" / "runtime" / "learn"
                    / "2099-01-01"
                    / f"{placement.problem_id}__{placement.placement_uid}.cpp"
                )
                context = vscode_task.problem_context(str(nonexistent))
                self.assertIsNotNone(context)
                assert context is not None
                self.assertEqual(context.identity_origin, "published_placement")
                self.assertEqual(context.pb_uid, uid)
                self.assertEqual(context.placement_uid, placement.placement_uid)
                self.assertEqual(context.problem_id, placement.problem_id.lower())
                self.assertEqual(context.source.casefold(), "zerojudge")
                self.assertEqual(context.canonical_url, placement.url)

                bundle = vscode_task._test_bundle(context)
                self.assertIsNotNone(bundle)
                assert bundle is not None
                self.assertEqual(bundle.source, "zerojudge")
                self.assertEqual(bundle.external_id, external_id)
                self.assertEqual(bundle.canonical_url, placement.url)
                self.assertEqual(bundle.official_count, official_count)
                self.assertEqual(bundle.verified_count, official_count + edge_count)

                with (
                    patch.object(vscode_task.control, "selection_mode", return_value="practice"),
                    patch.object(vscode_task, "_post_attempt", return_value=False),
                ):
                    fast = vscode_task._visible_cases(
                        bundle, context, str(nonexistent), suite=SUITE_FAST
                    )
                    full = vscode_task._visible_cases(
                        bundle, context, str(nonexistent), suite=SUITE_FULL
                    )
                self.assertEqual(len(fast), official_count)
                self.assertEqual(len(full), official_count + edge_count)

                with (
                    patch.object(vscode_task.control, "selection_mode", return_value="exam"),
                    patch.object(vscode_task, "_post_attempt", return_value=False),
                ):
                    pre_exam = vscode_task._visible_cases(
                        bundle, context, str(nonexistent), suite=SUITE_FULL
                    )
                self.assertEqual(len(pre_exam), official_count)
                self.assertTrue(
                    all(item.provenance == "OFFICIAL" for item in pre_exam)
                )

                with (
                    patch.object(vscode_task.control, "selection_mode", return_value="practice"),
                    patch.object(vscode_task, "_post_attempt", return_value=False),
                ):
                    strict = replace(context, role="Transfer Challenge")
                    pre_transfer = vscode_task._visible_cases(
                        bundle, strict, str(nonexistent), suite=SUITE_FULL
                    )
                self.assertEqual(len(pre_transfer), official_count)

                with (
                    patch.object(vscode_task.control, "selection_mode", return_value="exam"),
                    patch.object(vscode_task, "_post_attempt", return_value=True),
                ):
                    after = vscode_task._visible_cases(
                        bundle, context, str(nonexistent), suite=SUITE_FULL
                    )
                self.assertEqual(len(after), official_count + edge_count)
                self.assertFalse(nonexistent.exists())

    def test_alias_requires_matching_canonical_url_and_judge(self):
        placement = next(
            p for p in vscode_task.CURRICULUM.all_placements()
            if p.pb_uid == "PB-27"
        )
        phantom = (
            vscode_task.ROOT / ".apcs" / "runtime" / "learn"
            / "2099-01-01"
            / f"{placement.problem_id}__{placement.placement_uid}.cpp"
        )
        context = vscode_task.problem_context(str(phantom))
        self.assertIsNotNone(context)
        assert context is not None
        self.assertIsNone(
            vscode_task._test_bundle(
                replace(context, canonical_url="https://example.invalid/fake")
            )
        )
        self.assertIsNone(
            vscode_task._test_bundle(
                replace(context, canonical_url="https://zerojudge.tw/ShowProblem?problemid=d097")
            )
        )
        self.assertIsNone(
            vscode_task._test_bundle(replace(context, canonical_url=None))
        )
        self.assertIsNone(
            vscode_task._test_bundle(replace(context, source="Codeforces"))
        )

    def test_judge_local_identity_still_supports_source_authoritative_catalog(self):
        existing = vscode_task.ProblemContext(
            problem_id="d732",
            title="Search",
            source="ZeroJudge",
            canonical_url="https://zerojudge.tw/ShowProblem?problemid=d732",
            solution_path=Path("/tmp/d732.cpp"),
            placement_uid=None,
            role=None,
            pb_uid=None,
            identity_origin="catalog_solution",
        )
        bundle = vscode_task._test_bundle(existing)
        self.assertIsNotNone(bundle)
        assert bundle is not None
        self.assertEqual(bundle.external_id, "d732")


if __name__ == "__main__":
    unittest.main()
