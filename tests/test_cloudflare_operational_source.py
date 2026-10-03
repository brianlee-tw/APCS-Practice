from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "cloudflare" / "worker"
RECOVERY = ROOT / "cloudflare" / "recovery" / "worker-51"
RECEIPT = ROOT / "docs" / "REC_SCHEMA_COMPAT_PRODUCTION_RECEIPT_2026-10-03.json"

EXPECTED_BASELINE_SHA = (
    "c4f2271c73a928a4dd757aaa160be303"
    "d3e555b0cfee80f156b2ca6956c7ba67"
)
EXPECTED_PRODUCTION_VERSION_ID = "a8a3e533-70a3-4b95-a34b-5ba22b6d75b3"
EXPECTED_DEPLOYMENT_ID = "cfdc07b8-6a2b-45b4-8ec0-9812a4e9db78"
EXPECTED_SOURCE_COMMIT = "4ce453b55cd61e54495d36edf1156753aac0d6b2"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CloudflareOperationalSourceTests(unittest.TestCase):
    def test_immutable_recovery_snapshot_is_exact_worker51_baseline(self) -> None:
        recovered = RECOVERY / "index.mjs"
        self.assertEqual(_sha256(recovered), EXPECTED_BASELINE_SHA)

    def test_operational_source_authority_contract(self) -> None:
        authority = json.loads(
            (WORKER / "source-authority.json").read_text(encoding="utf-8")
        )

        self.assertEqual(authority["status"], "PRODUCTION_ACTIVE")
        self.assertEqual(authority["production_version_number"], 55)
        self.assertEqual(
            authority["production_version_id"],
            EXPECTED_PRODUCTION_VERSION_ID,
        )
        self.assertEqual(authority["deployment_id"], EXPECTED_DEPLOYMENT_ID)
        self.assertEqual(
            authority["production_source_git_commit"],
            EXPECTED_SOURCE_COMMIT,
        )
        self.assertEqual(
            authority["production_runtime_status"],
            "SCHEMA_COMPAT_VERIFIED_ON_VERSION_55",
        )
        self.assertEqual(
            authority["pending_patch"]["deployment_status"],
            "DEPLOYED_AND_VERIFIED",
        )
        self.assertEqual(
            authority["baseline_source_sha256"],
            EXPECTED_BASELINE_SHA,
        )
        self.assertEqual(
            authority["original_typescript_status"],
            "NOT_RECOVERED",
        )

        config = (WORKER / "wrangler.jsonc").read_text(encoding="utf-8")
        self.assertIn('"name": "apcs-rec-writeback"', config)
        self.assertIn('"main": "src/index.mjs"', config)
        self.assertIn('"compatibility_date": "2026-08-25"', config)
        self.assertIn('"nodejs_compat"', config)
        self.assertIn(
            '"directory": "../recovery/assets-51/public"',
            config,
        )
        self.assertIn('"binding": "ASSETS"', config)

    def test_operational_source_does_not_write_removed_rec_fields(self) -> None:
        source = (WORKER / "src" / "index.mjs").read_text(encoding="utf-8")

        self.assertNotIn('"進度狀態":', source)
        self.assertNotIn('"\\u9032\\u5EA6\\u72C0\\u614B":', source)
        self.assertNotIn(
            'properties["\\u8907\\u7FD2\\u65E5\\u671F"]',
            source,
        )

        self.assertIn(
            'REMOTE_WRITEBACK_SCHEMA = "v2.3-remote-writeback-1"',
            source,
        )
        self.assertIn(
            'REMOTE_RECEIPT_SCHEMA = "v2.3-remote-receipt-1"',
            source,
        )
        self.assertIn(
            "makePageBody(p, { result, assistance, independent, "
            "attempts, timeMin, stage, errors, takeaway, reviewDate })",
            source,
        )

    def test_schema_compat_release_receipt(self) -> None:
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))

        self.assertEqual(
            receipt["schema_version"],
            "apcs-rec-schema-compat-production-receipt-1",
        )
        self.assertEqual(receipt["production_version_number"], 55)
        self.assertEqual(
            receipt["production_version_id"],
            EXPECTED_PRODUCTION_VERSION_ID,
        )
        self.assertEqual(receipt["deployment_id"], EXPECTED_DEPLOYMENT_ID)
        self.assertEqual(receipt["git_head"], EXPECTED_SOURCE_COMMIT)
        self.assertEqual(
            receipt["cleanup"]["status"],
            "PASS_0_LIVE_TEST_ROWS",
        )
        self.assertEqual(receipt["cleanup"]["rec_total_after_cleanup"], 137)
        self.assertEqual(receipt["cleanup"]["evidence_total_after_cleanup"], 0)
        self.assertEqual(
            receipt["phase2"]["system_audit"],
            "PASS_KNOWN_PB_BACKLOG_ONLY",
        )
        self.assertEqual(receipt["learner_readiness"], "NOT_ASSESSED")


if __name__ == "__main__":
    unittest.main()
