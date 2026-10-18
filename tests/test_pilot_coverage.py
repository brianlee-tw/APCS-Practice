import copy
import subprocess
import sys
import unittest
from pathlib import Path

from tools.test_assets import TestAssetStore, SUITE_FAST, SUITE_FULL

from tools.pilot_coverage import (
    AUDIT,
    PUBLISHED,
    ROOT,
    SEED,
    build_coverage,
    load_json,
    validate_pilot,
)


class APCSProblemPilotAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.published = load_json(PUBLISHED)
        cls.audit = load_json(AUDIT)
        cls.seed = load_json(SEED)

    def test_published_contract_snapshot_is_reproduced(self):
        self.assertEqual(
            build_coverage(
                self.published,
                self.seed,
                as_of=self.audit["as_of"],
                main_sha=self.audit["snapshot"]["main_sha"],
            ),
            self.audit,
        )

    def test_candidate_roster_has_valid_published_authority(self):
        self.assertEqual(
            validate_pilot(
                self.published,
                self.audit,
                self.seed,
            ),
            [],
        )

    def test_no_new_runtime_published_claims(self):
        curated = []
        for entry in self.seed["entries"]:
            self.assertFalse(
                entry["runtime_published_by_pilot"]
            )
            self.assertEqual(
                entry["enrichment"],
                "NOT_CURATED",
            )
            if entry["testcases"] == "OFFICIAL_SAMPLE_CURATED":
                curated.append(entry)
            else:
                self.assertEqual(
                    entry["source_verification"],
                    "NOT_CHECKED_THIS_PILOT",
                )
                self.assertEqual(
                    entry["testcases"],
                    "NOT_CURATED",
                )
        self.assertEqual(len(curated), 4)
        self.assertEqual(
            sum(x["source_receipt"]["sample_count"] for x in curated),
            8,
        )

    def test_official_sample_receipt_cannot_be_faked(self):
        seed = copy.deepcopy(self.seed)
        curated = next(
            x for x in seed["entries"]
            if x["testcases"] == "OFFICIAL_SAMPLE_CURATED"
        )
        curated["source_receipt"]["sample_count"] = 999
        errors = validate_pilot(
            self.published, self.audit, seed
        )
        self.assertTrue(
            any("sample asset/receipt mismatch" in x for x in errors)
        )

    def test_official_case_sources_are_official_only(self):
        for entry in self.seed["entries"]:
            if entry["testcases"] != "OFFICIAL_SAMPLE_CURATED":
                continue
            asset = load_json(ROOT / entry["source_receipt"]["asset_path"])
            self.assertEqual(
                len(asset["cases"]),
                entry["source_receipt"]["sample_count"],
            )
            for case in asset["cases"]:
                self.assertEqual(case["provenance"], "OFFICIAL")
                self.assertEqual(case["trust"], "OFFICIAL")
                self.assertEqual(case["visibility"], "official")

    def test_official_samples_are_visible_in_practice_and_strict_exam(self):
        store = TestAssetStore(
            ROOT / "data" / "problem_enrichment",
            ROOT / ".apcs" / "runtime",
        )
        for entry in self.seed["entries"]:
            if entry["testcases"] != "OFFICIAL_SAMPLE_CURATED":
                continue
            source_id = entry["canonical_url"].split("problemid=", 1)[1]
            bundle = store.load(
                "zerojudge",
                source_id,
                include_candidates=False,
            )
            self.assertIsNotNone(bundle)
            assert bundle is not None
            self.assertEqual(
                bundle.official_count,
                entry["source_receipt"]["sample_count"],
            )
            for mode, suite in (
                ("practice", SUITE_FAST),
                ("exam", SUITE_FULL),
            ):
                visible = store.visible_cases(
                    bundle,
                    mode=mode,
                    activity="Core Independent",
                    post_attempt=False,
                    suite=suite,
                )
                self.assertEqual(
                    len(visible),
                    bundle.official_count,
                )

    def test_selected_problem_metadata_cannot_be_silently_changed(self):
        seed = copy.deepcopy(self.seed)
        seed["entries"][0]["canonical_url"] = (
            "https://example.invalid/wrong"
        )
        errors = validate_pilot(
            self.published,
            self.audit,
            seed,
        )
        self.assertTrue(
            any("canonical_url" in x for x in errors)
        )

    def test_duplicate_pilot_identity_is_rejected(self):
        seed = copy.deepcopy(self.seed)
        seed["entries"][1]["pb_uid"] = (
            seed["entries"][0]["pb_uid"]
        )
        errors = validate_pilot(
            self.published,
            self.audit,
            seed,
        )
        self.assertTrue(
            any("duplicate pilot" in x for x in errors)
        )

    def test_verified_testcase_claim_is_not_allowed_in_seed(self):
        seed = copy.deepcopy(self.seed)
        seed["entries"][0]["testcases"] = (
            "OFFICIAL_VERIFIED"
        )
        errors = validate_pilot(
            self.published,
            self.audit,
            seed,
        )
        self.assertTrue(
            any("testcases" in x for x in errors)
        )

    def test_cli_validation_is_read_only(self):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools" / "pilot_coverage.py"),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(
            result.returncode, 0, result.stdout + result.stderr
        )
        self.assertIn(
            "PILOT COVERAGE PASS", result.stdout
        )


if __name__ == "__main__":
    unittest.main()
