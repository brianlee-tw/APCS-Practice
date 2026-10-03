from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "cloudflare" / "worker"
RECOVERY = ROOT / "cloudflare" / "recovery" / "worker-51"
SCHEMA_RECEIPT = ROOT / "docs" / "REC_SCHEMA_COMPAT_PRODUCTION_RECEIPT_2026-10-03.json"
READING_RECEIPT = ROOT / "docs" / "READING_NA_PRODUCTION_RECEIPT_2026-10-03.json"

EXPECTED_BASELINE_SHA = (
    "c4f2271c73a928a4dd757aaa160be303"
    "d3e555b0cfee80f156b2ca6956c7ba67"
)
EXPECTED_PRODUCTION_VERSION_ID = "0eafa60d-6d4d-4edb-b1eb-ac6a9a3625b6"
EXPECTED_DEPLOYMENT_ID = "220994e0-549b-4143-800e-44c089c3ba4a"
EXPECTED_SOURCE_COMMIT = "0be65f2ab4ca44ea089aa48afc63ef09afd1778f"


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
        self.assertEqual(authority["production_version_number"], 58)
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
            "READING_NA_WRITEBACK_VERIFIED_ON_VERSION_58",
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
        receipt = json.loads(SCHEMA_RECEIPT.read_text(encoding="utf-8"))

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


    def test_reading_na_release_receipt(self) -> None:
        receipt = json.loads(READING_RECEIPT.read_text(encoding="utf-8"))

        self.assertEqual(
            receipt["schema_version"],
            "apcs-reading-na-production-receipt-1",
        )
        self.assertEqual(receipt["production_version_number"], 58)
        self.assertEqual(
            receipt["production_version_id"],
            EXPECTED_PRODUCTION_VERSION_ID,
        )
        self.assertEqual(receipt["deployment_id"], EXPECTED_DEPLOYMENT_ID)
        self.assertEqual(receipt["git_head"], EXPECTED_SOURCE_COMMIT)
        self.assertEqual(
            receipt["phase1"]["remote_rec_result"],
            "未提交/未知",
        )
        self.assertEqual(
            receipt["phase1"]["remote_ev_track"],
            "Reading",
        )
        self.assertEqual(
            receipt["phase1"]["remote_ev_judge_result"],
            "N/A",
        )
        self.assertEqual(
            receipt["phase1"]["remote_ev_outcome"],
            "PARTIAL",
        )
        self.assertIs(
            receipt["phase1"]["remote_ev_valid_for_gate"],
            False,
        )
        self.assertEqual(
            receipt["phase2"]["system_audit"],
            "PASS_CLEAN",
        )
        self.assertEqual(
            receipt["production_integrity"]["exceptions"],
            0,
        )
        self.assertEqual(
            receipt["production_integrity"]["warnings"],
            0,
        )
        self.assertEqual(receipt["learner_readiness"], "NOT_ASSESSED")


if __name__ == "__main__":
    unittest.main()
