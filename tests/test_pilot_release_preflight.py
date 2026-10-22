from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import pilot_release_preflight as gate


class PilotReleasePreflightTest(unittest.TestCase):
    def test_real_pilot_gate_passes_engineering_but_never_authorizes_release(self):
        report = gate.preflight()
        self.assertEqual(report["engineering_checks"], "PASS", report["errors"])
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["release_gate"], "BLOCKED_MANUAL")
        self.assertFalse(report["auto_merge_permitted"])
        self.assertFalse(report["c8_closed"])
        self.assertEqual(report["learner_readiness"], "NOT_ASSESSED")
        self.assertEqual(report["ci_claim"], "NOT_CHECKED_BY_THIS_LOCAL_PREFLIGHT")
        self.assertEqual(report["counts"], {
            "published_problems": 127,
            "seed_candidates": 18,
            "ai_candidate_unreviewed": 3,
            "ai_needs_qa": 1,
            "official_samples": 8,
            "differential_edge_tests": 17,
            "source_review_staged": 5,
            "source_review_exact_output": 4,
            "source_review_special_checker_required": 1,
            "custom_lesson_contracts_reviewed": 5,
            "custom_task_packets_verified": 0,
            "custom_gate_candidates_conditional": 4,
            "final_four_reviewed_official": 3,
            "final_four_pending_official": 1,
            "final_four_official_samples_staged": 4,
            "workbench_official_preview_problems": 5,
            "workbench_official_preview_samples": 7,
            "workbench_differential_full_edges": 24,
            "all_pilot_differential_full_edges": 41,
            "workbench_total_official_samples": 15,
        })

    def test_staged_multisource_review_cannot_enable_exact_checker_for_977c(self):
        batch = gate.load_json(gate.SOURCE_REVIEWS)
        with tempfile.TemporaryDirectory() as td:
            local = Path(td) / "batch.json"
            wrong = copy.deepcopy(batch)
            row = next(x for x in wrong["entries"] if x["pb_uid"] == "PB-109")
            row["judge_mode"] = "EXACT_OUTPUT"
            local.write_text(json.dumps(wrong), encoding="utf-8")
            with patch.object(gate, "SOURCE_REVIEWS", local):
                report = gate.preflight()
        self.assertEqual(report["engineering_checks"], "FAIL")
        self.assertEqual(report["release_gate"], "BLOCKED_MANUAL")
        self.assertTrue(any("PB-109" in e for e in report["errors"]))

    def test_custom_gate_cannot_override_learner_evidence_or_task_verification(self):
        with tempfile.TemporaryDirectory() as td:
            local = Path(td) / "custom-contracts.json"
            forged = copy.deepcopy(gate.load_json(gate.CUSTOM_CONTRACTS))
            forged["entries"][0]["learner_evidence_written"] = True
            forged["entries"][0]["task_statement_retrieved"] = True
            local.write_text(json.dumps(forged), encoding="utf-8")
            with patch.object(gate, "CUSTOM_CONTRACTS", local):
                report = gate.preflight()
        self.assertEqual(report["engineering_checks"], "FAIL")
        self.assertEqual(report["release_gate"], "BLOCKED_MANUAL")
        self.assertFalse(report["auto_merge_permitted"])
        self.assertTrue(any("learner_evidence_written" in e for e in report["errors"]))
        self.assertTrue(any("task_statement_retrieved" in e for e in report["errors"]))

    def test_last_four_q182_cannot_claim_unverified_official_samples(self):
        with tempfile.TemporaryDirectory() as td:
            local = Path(td) / "last-four.json"
            tampered = copy.deepcopy(gate.load_json(gate.FINAL_FOUR))
            pending = next(x for x in tampered["records"] if x["pb_uid"] == "PB-10")
            pending["official_samples_verified"] = True
            pending["samples"] = [{"input": "fake", "output": "fake"}]
            local.write_text(json.dumps(tampered), encoding="utf-8")
            with patch.object(gate, "FINAL_FOUR", local):
                report = gate.preflight()
        self.assertEqual(report["engineering_checks"], "FAIL")
        self.assertEqual(report["release_gate"], "BLOCKED_MANUAL")
        self.assertTrue(any("PB-10" in x for x in report["errors"]))

    def test_unapproved_preview_or_main_publication_claim_fails(self):
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "preview.json"
            forged = copy.deepcopy(gate.load_json(gate.WORKBENCH_PREVIEW))
            forged["is_main_published"] = True
            forged["entries"][0]["unverified_candidates_allowed"] = True
            output.write_text(json.dumps(forged), encoding="utf-8")
            with patch.object(gate, "WORKBENCH_PREVIEW", output):
                report = gate.preflight()
        self.assertEqual(report["engineering_checks"], "FAIL")
        self.assertEqual(report["release_gate"], "BLOCKED_MANUAL")
        self.assertFalse(report["auto_merge_permitted"])
        self.assertTrue(
            any("publication" in msg for msg in report["errors"]),
            report["errors"],
        )
        self.assertTrue(
            any("unverified_candidates_allowed" in msg for msg in report["errors"]),
            report["errors"],
        )

    def test_publication_claim_or_authority_override_fails(self):
        original = gate.load_json(gate.POLICY)
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td) / "policy.json"
            invalid = copy.deepcopy(original)
            invalid["release_boundaries"]["allow_merge_without_explicit_user_approval"] = True
            invalid["decisions"][0]["reviewer_approval"] = "APPROVED"
            temp.write_text(json.dumps(invalid), encoding="utf-8")
            with patch.object(gate, "POLICY", temp):
                report = gate.preflight()
        self.assertEqual(report["engineering_checks"], "FAIL")
        self.assertEqual(report["release_gate"], "BLOCKED_MANUAL")
        self.assertFalse(report["auto_merge_permitted"])
        self.assertTrue(
            any("authority expansion" in x for x in report["errors"]),
            report["errors"],
        )
        self.assertTrue(
            any("decision/authority changed" in x for x in report["errors"]),
            report["errors"],
        )

    def test_published_blob_drift_is_explicit_error(self):
        with tempfile.TemporaryDirectory() as td:
            tampered = Path(td) / "published.v23.json"
            data = gate.load_json(gate.PUBLISHED)
            data["problems"][0]["title"] = "UNAUTHORIZED_TEST_CHANGE"
            tampered.write_text(
                json.dumps(data, ensure_ascii=False), encoding="utf-8"
            )
            with patch.object(gate, "PUBLISHED", tampered):
                report = gate.preflight()
        self.assertEqual(report["engineering_checks"], "FAIL")
        self.assertTrue(
            any("canonical main blob authority drift" in x for x in report["errors"]),
            report["errors"],
        )

    def test_local_cli_does_not_claim_manual_acceptance(self):
        completed = subprocess.run(
            [sys.executable, str(gate.ROOT / "tools" / "pilot_release_preflight.py")],
            cwd=gate.ROOT,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(
            completed.returncode, 0, completed.stdout + completed.stderr
        )
        self.assertIn("PILOT PREFLIGHT PASS / RELEASE BLOCKED_MANUAL", completed.stdout)

    def test_output_is_write_once_and_does_not_mutate_learning_system(self):
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "qa.json"
            command = [
                sys.executable,
                str(gate.ROOT / "tools" / "pilot_release_preflight.py"),
                "--output", str(output),
            ]
            r1 = subprocess.run(
                command, cwd=gate.ROOT, capture_output=True,
                text=True, timeout=20, check=False,
            )
            self.assertEqual(r1.returncode, 0, r1.stdout + r1.stderr)
            data = gate.load_json(output)
            self.assertEqual(data["release_gate"], "BLOCKED_MANUAL")
            r2 = subprocess.run(
                command, cwd=gate.ROOT, capture_output=True,
                text=True, timeout=20, check=False,
            )
            self.assertNotEqual(r2.returncode, 0)
            self.assertIn("refusing overwrite", r2.stdout)
            self.assertEqual(gate.load_json(output), data)

    def test_policy_reconciliation_cannot_silently_change_placement_role(self):
        with tempfile.TemporaryDirectory() as td:
            candidate = copy.deepcopy(gate.load_json(gate.POLICY))
            candidate["decisions"][1]["role"] = "Core Independent"
            local = Path(td) / "policy.json"
            local.write_text(json.dumps(candidate), encoding="utf-8")
            with patch.object(gate, "POLICY", local):
                outcome = gate.preflight()
        self.assertEqual(outcome["engineering_checks"], "FAIL")
        self.assertTrue(
            any("PB-27" in x and "policy drift" in x for x in outcome["errors"])
        )


if __name__ == "__main__":
    unittest.main()
