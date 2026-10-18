from __future__ import annotations

import copy
import subprocess
import sys
import unittest

from tools import pilot_source_review as review


class PilotSecondBatchSourceReviewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.batch = review.load(review.SOURCE_REVIEWS)
        cls.seed = review.load(review.SEED)
        cls.published = review.load(review.PUBLISHED)

    def validate(self, batch):
        return review.verify_batch(batch, self.seed, self.published)

    def test_all_five_official_sources_and_sample_semantics(self):
        self.assertEqual(self.validate(self.batch), [])
        self.assertEqual(len(self.batch["entries"]), 5)
        self.assertTrue(all(not row["ai_approved"] for row in self.batch["entries"]))
        self.assertTrue(all(not row["published_mutation"] for row in self.batch["entries"]))
        self.assertEqual(self.batch["test_center_status"], "STAGED_DO_NOT_LOAD")
        self.assertFalse(self.batch["l0_import_supported"])

    def test_nonunique_codeforces_sample_accepts_both_five_and_six(self):
        pb = next(x for x in self.batch["entries"] if x["pb_uid"] == "PB-109")
        sample = pb["official_samples"][0]
        self.assertEqual(sample["output"].strip(), "6")
        self.assertTrue(review.is_valid_977c(sample["input"], "6\n"))
        self.assertTrue(review.is_valid_977c(sample["input"], "5\n"))
        self.assertFalse(review.is_valid_977c(sample["input"], "7\n"))
        self.assertFalse(review.is_valid_977c(sample["input"], "-1\n"))
        impossible = pb["official_samples"][1]
        self.assertTrue(review.is_valid_977c(impossible["input"], "-1\n"))
        self.assertFalse(review.is_valid_977c(impossible["input"], "2\n"))

    def test_special_checker_k_zero_and_duplicates(self):
        self.assertTrue(review.is_valid_977c("3 0\n2 3 4\n", "1\n"))
        self.assertFalse(review.is_valid_977c("3 0\n1 3 4\n", "-2\n"))
        self.assertTrue(review.is_valid_977c("3 0\n1 3 4\n", "-1\n"))
        self.assertTrue(review.is_valid_977c("3 2\n2 2 3\n", "2\n"))
        self.assertFalse(review.is_valid_977c("3 1\n2 2 3\n", "2\n"))
        self.assertTrue(review.is_valid_977c("3 1\n2 2 3\n", "-1\n"))
        self.assertTrue(review.is_valid_977c("3 3\n2 2 3\n", "3\n"))

    def test_exact_sample_mutation_rejected(self):
        batch = copy.deepcopy(self.batch)
        cses = next(x for x in batch["entries"] if x["pb_uid"] == "PB-42")
        cses["official_samples"][0]["output"] = "999\n"
        errors = self.validate(batch)
        self.assertTrue(any("independent oracle" in x for x in errors), errors)

    def test_sample_cannot_auto_publish_or_claim_unsupported_l0(self):
        batch = copy.deepcopy(self.batch)
        batch["l0_import_supported"] = True
        batch["test_center_status"] = "VERIFIED_PUBLISHED"
        batch["entries"][0]["ai_approved"] = True
        errors = self.validate(batch)
        self.assertTrue(any("not implemented" in x for x in errors), errors)
        self.assertTrue(any("Test Center" in x for x in errors), errors)
        self.assertTrue(any("authority" in x for x in errors), errors)

    def test_cross_platform_identity_mismatch_is_detected(self):
        batch = copy.deepcopy(self.batch)
        e = next(x for x in batch["entries"] if x["pb_uid"] == "PB-103")
        e["url"] = "https://codeforces.com/problemset/problem/977/C"
        self.assertTrue(any("source/role/provenance" in x for x in self.validate(batch)))

    def test_batch_cli_is_read_only(self):
        result = subprocess.run(
            [sys.executable, str(review.ROOT / "tools" / "pilot_source_review.py")],
            cwd=review.ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("SOURCE REVIEW PASS", result.stdout)


if __name__ == "__main__":
    unittest.main()
