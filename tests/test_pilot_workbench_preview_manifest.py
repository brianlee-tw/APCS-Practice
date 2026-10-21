from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools import pilot_workbench_preview as q
from tools.test_assets import TestAssetStore


class PilotWorkbenchManifestTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = q.load(q.MANIFEST)
        cls.pub = q.load(q.PUBLISHED)
        cls.b2 = q.load(q.BATCH2)
        cls.b4 = q.load(q.BATCH4)
        cls.store = TestAssetStore(q.TESTS)

    def check(self, manifest, batch2=None, batch4=None):
        return q.validate(
            manifest, self.pub,
            batch2 if batch2 is not None else self.b2,
            batch4 if batch4 is not None else self.b4,
            self.store,
        )

    def test_all_four_official_only_assets_and_staged_authority(self):
        self.assertEqual(self.check(self.manifest), [])
        self.assertEqual(len(self.manifest["entries"]), 5)
        self.assertFalse(self.manifest["is_main_published"])
        self.assertFalse(self.manifest["automated_evidence_writeback"])
        self.assertEqual(self.manifest["release_gate"], "BLOCKED_MANUAL")
        self.assertEqual(
            sum(e["official_count"] for e in self.manifest["entries"]), 7,
        )
        self.assertEqual(
            sum(e["verified_edge_count"] for e in self.manifest["entries"]), 24,
        )

    def test_extra_problem_or_changed_published_identity_rejected(self):
        copy_manifest = copy.deepcopy(self.manifest)
        copy_manifest["entries"].append({
            **copy_manifest["entries"][0],
            "pb_uid": "PB-103",
        })
        self.assertTrue(
            any("allowlist" in x for x in self.check(copy_manifest))
        )
        copy_manifest = copy.deepcopy(self.manifest)
        copy_manifest["entries"][0]["canonical_url"] = (
            "https://cses.fi/problemset/task/1094"
        )
        self.assertTrue(
            any("canonical_url" in x for x in self.check(copy_manifest))
        )

    def test_staged_official_sample_cannot_change_without_qa(self):
        b2 = copy.deepcopy(self.b2)
        row = next(e for e in b2["entries"] if e["pb_uid"] == "PB-42")
        row["official_samples"][0]["output"] = "99\n"
        self.assertTrue(
            any("source sample" in x for x in self.check(self.manifest, batch2=b2))
        )

    def test_no_unverified_or_official_relabelled_edges_in_preview_manifest(self):
        bad = copy.deepcopy(self.manifest)
        row = next(e for e in bad["entries"] if e["pb_uid"] == "PB-120")
        row["unverified_candidates_allowed"] = True
        row["verified_edge_count"] = 999
        row["verified_edge_trust"] = "OFFICIAL"
        errors = self.check(bad)
        self.assertGreaterEqual(len(errors), 3)

    def test_cli_checks_real_repo_without_mutating_learner_data(self):
        result = subprocess.run(
            [sys.executable, str(q.ROOT / "tools/pilot_workbench_preview.py")],
            cwd=q.ROOT, text=True, capture_output=True,
            check=False, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("WORKBENCH PREVIEW PASS", result.stdout)


if __name__ == "__main__":
    unittest.main()
