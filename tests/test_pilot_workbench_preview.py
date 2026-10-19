"""Source-pinned, official-only preview of four Published pilot Test Center tasks.

Tests the actual Published scratch -> Workbench Context -> Test Asset Store
route, not just a stand-alone read of tests.json. Synthetic scratch paths
are intentionally never created and never count as learner evidence.
"""
from __future__ import annotations

from dataclasses import replace
from unittest.mock import patch
import unittest

from tools import vscode_task
from tools.pilot_source_review import (
    load as load_batch2,
    SOURCE_REVIEWS,
    expected_exact_output,
)
from tools.pilot_final_four_source import (
    load as load_batch4,
    MANIFEST as BATCH4,
    expected_output as final_four_expected,
)
from tools.test_assets import SUITE_FAST, SUITE_FULL, TestAssetStore

# Exact Published PB identities and judge-local external IDs.
PREVIEW = {
    "PB-42": ("cses", "1069", 1),
    "PB-150": ("cses", "1094", 1),
    "PB-97": ("codeforces", "71A", 1),
    "PB-120": ("zerojudge", "q836", 2),
}
UNENROLLED = {"PB-40", "PB-103", "PB-109", "PB-10", "PB-32"}


class PilotPublishedWorkbenchPreviewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.placements = {
            p.pb_uid: p for p in vscode_task.CURRICULUM.all_placements()
        }
        cls.batch2 = {
            e["pb_uid"]: e
            for e in load_batch2(SOURCE_REVIEWS)["entries"]
        }
        cls.batch4 = {
            e["pb_uid"]: e
            for e in load_batch4(BATCH4)["records"]
        }

    @classmethod
    def context(cls, uid):
        placement = cls.placements[uid]
        scratch = (
            vscode_task.ROOT / ".apcs" / "runtime" / "learn"
            / "2099-01-01"
            / f"{placement.problem_id}__{placement.placement_uid}.cpp"
        )
        context = vscode_task.problem_context(str(scratch))
        assert context is not None
        return context, str(scratch), placement

    def test_four_published_scratch_contexts_load_exact_official_bundles(self):
        for uid, (source, external_id, n) in PREVIEW.items():
            with self.subTest(pb_uid=uid):
                context, filename, placement = self.context(uid)
                self.assertFalse(vscode_task.Path(filename).exists())
                self.assertEqual(context.identity_origin, "published_placement")
                self.assertEqual(context.pb_uid, uid)
                self.assertEqual(context.placement_uid, placement.placement_uid)
                self.assertEqual(context.problem_id, placement.problem_id.lower())
                self.assertEqual(context.canonical_url, placement.url)
                bundle = vscode_task._test_bundle(context)
                self.assertIsNotNone(bundle)
                assert bundle is not None
                self.assertEqual(bundle.source, source)
                self.assertEqual(bundle.external_id, external_id)
                self.assertEqual(bundle.canonical_url.rstrip("/"), placement.url.rstrip("/"))
                self.assertEqual(bundle.official_count, n)
                self.assertEqual(bundle.verified_count, n)
                self.assertEqual(len(bundle.cases), n)
                for case in bundle.cases:
                    self.assertEqual(case.provenance, "OFFICIAL")
                    self.assertEqual(case.trust, "OFFICIAL")
                    self.assertEqual(case.suite, SUITE_FAST)
                    self.assertEqual(case.visibility, "official")

                with (
                    patch.object(vscode_task.control, "selection_mode", return_value="practice"),
                    patch.object(vscode_task, "_post_attempt", return_value=False),
                ):
                    fast = vscode_task._visible_cases(
                        bundle, context, filename, suite=SUITE_FAST
                    )
                    full = vscode_task._visible_cases(
                        bundle, context, filename, suite=SUITE_FULL
                    )
                self.assertEqual(len(fast), n)
                self.assertEqual(len(full), n)
                with (
                    patch.object(vscode_task.control, "selection_mode", return_value="exam"),
                    patch.object(vscode_task, "_post_attempt", return_value=False),
                ):
                    strict = vscode_task._visible_cases(
                        bundle, context, filename, suite=SUITE_FULL
                    )
                self.assertEqual(len(strict), n)
                with (
                    patch.object(vscode_task.control, "selection_mode", return_value="practice"),
                    patch.object(vscode_task, "_post_attempt", return_value=False),
                ):
                    transfer = vscode_task._visible_cases(
                        bundle, replace(context, role="Transfer Challenge"),
                        filename, suite=SUITE_FULL,
                    )
                self.assertEqual(len(transfer), n)

    def test_every_preview_case_matches_staged_official_source_sample(self):
        for uid, (source, external_id, _) in PREVIEW.items():
            bundle = vscode_task._test_bundle(self.context(uid)[0])
            assert bundle is not None
            record = self.batch2.get(uid) or self.batch4.get(uid)
            source_cases = record.get("official_samples", record.get("samples"))
            self.assertEqual(len(source_cases), len(bundle.cases))
            for case, sample in zip(bundle.cases, source_cases):
                with self.subTest(pb_uid=uid, case=case.case_id):
                    self.assertEqual(case.input_text, sample["input"])
                    self.assertEqual(case.expected_output, (
                        sample.get("output") or sample.get("expected_output")
                    ))
                    oracle = (
                        expected_exact_output(uid, case.input_text)
                        if uid in self.batch2
                        else final_four_expected(uid, case.input_text)
                    )
                    self.assertEqual(oracle.split(), case.expected_output.split())

    def test_unreviewed_or_multianswer_records_do_not_autoload(self):
        for uid in UNENROLLED:
            with self.subTest(pb_uid=uid):
                context, _, _ = self.context(uid)
                self.assertIsNone(vscode_task._test_bundle(context))
        self.assertEqual(
            set(vscode_task.PILOT_PREVIEW_IDENTITIES),
            {
                ("cses", "cses-1069"),
                ("cses", "cses-1094"),
                ("codeforces", "cf-71a"),
                ("apcs", "apcs-zj-q836"),
            }
        )

    def test_trust_binding_rejects_wrong_url_source_pb_and_identity_origin(self):
        for uid in PREVIEW:
            with self.subTest(pb_uid=uid):
                context, _, _ = self.context(uid)
                other_uid = next(x for x in PREVIEW if x != uid)
                invalid = [
                    replace(context, canonical_url="https://example.invalid/fake"),
                    replace(context, canonical_url=None),
                    replace(context, pb_uid=other_uid),
                    replace(context, identity_origin="catalog_solution"),
                    replace(context, source="malicious"),
                ]
                for forged in invalid:
                    self.assertIsNone(vscode_task._test_bundle(forged))

    def test_no_cross_judge_collision_or_relabelled_published_identity(self):
        a, _, _ = self.context("PB-42")
        b, _, _ = self.context("PB-97")
        self.assertIsNone(
            vscode_task._test_bundle(replace(a, canonical_url=b.canonical_url))
        )
        self.assertIsNone(vscode_task._test_bundle(
            replace(a, problem_id="cses-1094")
        ))
        self.assertIsNone(vscode_task._test_bundle(
            replace(b, problem_id="cf-977c")
        ))
        c, _, _ = self.context("PB-120")
        self.assertIsNone(vscode_task._test_bundle(
            replace(c, problem_id="zj-q836")
        ))
        self.assertIsNone(vscode_task._test_bundle(
            replace(c, source="zerojudge")
        ))

    def test_durable_test_assets_validate_without_any_nonofficial_candidate(self):
        store = TestAssetStore(
            vscode_task.ROOT / "data" / "problem_enrichment"
        )
        self.assertEqual(store.validate_all(), [])


if __name__ == "__main__":
    unittest.main()
