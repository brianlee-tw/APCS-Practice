import copy
import subprocess
import sys
import unittest
from pathlib import Path

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
        for entry in self.seed["entries"]:
            self.assertFalse(
                entry["runtime_published_by_pilot"]
            )
            self.assertEqual(
                entry["source_verification"],
                "NOT_CHECKED_THIS_PILOT",
            )
            self.assertEqual(
                entry["testcases"],
                "NOT_CURATED",
            )
            self.assertEqual(
                entry["enrichment"],
                "NOT_CURATED",
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
