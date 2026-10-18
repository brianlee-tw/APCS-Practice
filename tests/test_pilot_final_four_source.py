from __future__ import annotations

import copy
import subprocess
import sys
import unittest

from tools import pilot_final_four_source as audit


class FinalFourOfficialSourceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = audit.load(audit.MANIFEST)
        cls.seed = audit.load(audit.SEED)
        cls.published = audit.load(audit.PUBLISHED)

    def verify(self, data):
        return audit.verify(data, self.seed, self.published)

    def test_source_review_three_official_one_quarantined(self):
        self.assertEqual(self.verify(self.data), [])
        by = {r["pb_uid"]: r for r in self.data["records"]}
        self.assertEqual(len(by), 4)
        self.assertEqual(
            sum(len(r["samples"]) for r in by.values()), 4
        )
        self.assertEqual(by["PB-10"]["samples"], [])
        self.assertFalse(by["PB-10"]["official_statement_verified"])
        self.assertFalse(by["PB-10"]["official_samples_verified"])
        self.assertEqual(by["PB-10"]["output_mode"], "NO_VERIFIED_SAMPLE")
        self.assertEqual(
            set(by["PB-32"]["qa_flags"]),
            {"SOURCE_POSITIVE_INTEGER_VS_ZERO_SAMPLE", "VALUE_RANGE_NOT_SPECIFIED"},
        )
        self.assertEqual(self.data["publication_authority"], "NONE")
        self.assertEqual(self.data["test_center_status"], "STAGED_DO_NOT_LOAD")

    def test_source_example_outputs(self):
        for row in self.data["records"]:
            for sample in row["samples"]:
                with self.subTest(problem=row["pb_uid"]):
                    self.assertEqual(
                        audit.expected_output(row["pb_uid"], sample["input"]).split(),
                        sample["output"].split(),
                    )

    def test_q836_both_traps_and_life_jump_order(self):
        self.assertEqual(audit.expected_output("PB-120", "1\n1 1\n1 1\n"), "1\n")
        self.assertEqual(audit.expected_output("PB-120", "7\n3 2\n2 3\n"), "18\n")

    def test_cf71a_exact_threshold_and_words(self):
        inp = "4\nabcdefghij\nabcdefghijk\nz\nbbbbbbbbbbbb\n"
        self.assertEqual(
            audit.expected_output("PB-97", inp),
            "abcdefghij\na9k\nz\nb10b\n",
        )

    def test_sort_zeros_and_duplicates_are_allowed_by_official_sample(self):
        self.assertEqual(
            audit.expected_output("PB-32", "5\n0 3 1 1 0\n"),
            "0 0 1 1 3\n",
        )
        self.assertIn(
            "SOURCE_POSITIVE_INTEGER_VS_ZERO_SAMPLE",
            next(r for r in self.data["records"] if r["pb_uid"] == "PB-32")["qa_flags"],
        )

    def test_unverified_q182_cannot_get_official_output_claim(self):
        fake = copy.deepcopy(self.data)
        p = next(r for r in fake["records"] if r["pb_uid"] == "PB-10")
        p["samples"] = [{"input": "abc\n", "output": "bac\n"}]
        p["official_samples_verified"] = True
        p["output_mode"] = "EXACT_OUTPUT_CANDIDATE"
        errors = self.verify(fake)
        self.assertGreaterEqual(len(errors), 2)
        self.assertTrue(any("PB-10" in e for e in errors), errors)
        with self.assertRaisesRegex(ValueError, "no official-verified"):
            audit.expected_output("PB-10", "abc\n")

    def test_change_official_sample_or_source_identity_fails(self):
        tampered = copy.deepcopy(self.data)
        p = next(r for r in tampered["records"] if r["pb_uid"] == "PB-120")
        p["samples"][1]["output"] = "999\n"
        self.assertTrue(
            any("independent reference" in e for e in self.verify(tampered))
        )
        wrong_source = copy.deepcopy(self.data)
        wrong_source["records"][0]["canonical_url"] = (
            "https://zerojudge.tw/ShowProblem?problemid=q182"
        )
        self.assertTrue(
            any("source identity" in e for e in self.verify(wrong_source))
        )

    def test_no_spurious_full_release_or_case_publication(self):
        fake = copy.deepcopy(self.data)
        fake["status"] = "ALL_OFFICIAL_SOURCE_VERIFIED"
        fake["test_center_status"] = "PUBLISHED"
        fake["publication_authority"] = "YES"
        errors = self.verify(fake)
        self.assertGreaterEqual(len(errors), 3)

    def test_cli_is_read_only(self):
        result = subprocess.run(
            [sys.executable, str(audit.ROOT / "tools" / "pilot_final_four_source.py")],
            cwd=audit.ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("FINAL FOUR SOURCE QA PASS", result.stdout)


if __name__ == "__main__":
    unittest.main()
