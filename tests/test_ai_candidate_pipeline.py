from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.ai_candidate_pipeline import (
    API_URL,
    CandidateError,
    PROFILE_DIR,
    PUBLISHED,
    ROOT,
    SEED,
    _api_candidate,
    build_jobs,
    canonical_hash,
    evaluate,
    generate,
    load_json,
    convert_chatgpt_proposals,
)
from tools.problem_intelligence import ProblemIntelligenceStore


class CandidatePipelineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pub = load_json(PUBLISHED)
        cls.seed = load_json(SEED)
        cls.jobs = build_jobs(
            cls.pub, cls.seed, ProblemIntelligenceStore(PROFILE_DIR)
        )
        cls.problems = {p["pb_uid"]: p for p in cls.pub["problems"]}
        cls.placements = {p["pb_uid"]: p for p in cls.pub["placements"]}

    def make_candidate(self, job):
        uid = job["pb_uid"]
        problem = self.problems[uid]
        placement = self.placements[uid]
        return {
            "confidence": 0.94,
            "primary_skill_candidate": placement["primary_skill"],
            "supporting_skill_candidates": [],
            "difficulty_candidate": problem["difficulty"],
            "prerequisite_candidates": [],
            "expected_complexity_candidate": "O(n)",
            "role_candidate": placement["role"],
            "alternate_solution_risk_candidate": "Low",
            "evidence_suitability_candidate": "Both",
            "rationale": "Based on the supplied source summary and constraints.",
            "ambiguity_notes": [],
            "classification_source": "AI_CANDIDATE",
        }

    def fake_generate(self):
        return generate(
            self.jobs,
            model="mock-model",
            api_key="TEST-ONLY",
            limit=4,
            generator=lambda job, skills, **kw: (
                self.make_candidate(job), "mock-response"
            ),
        )

    def test_prepare_uses_only_four_reviewed_l0_source_records(self):
        self.assertEqual(self.jobs["schema_version"], "apcs-ai-classification-jobs-v1")
        self.assertEqual(len(self.jobs["jobs"]), 4)
        self.assertEqual(len(self.jobs["skills"]), 39)
        for job in self.jobs["jobs"]:
            self.assertEqual(len(job["source_sha256"]), 64)
            self.assertEqual(job["source"], "zerojudge")
            self.assertNotIn("published_skill", job)
            self.assertNotIn("learner_evidence", job)

    def test_generator_produces_provenance_not_source_writes(self):
        generated = self.fake_generate()
        self.assertEqual(generated["schema_version"], "apcs-ai-classification-responses-v1")
        self.assertEqual(generated["model"], "mock-model")
        self.assertEqual(len(generated["responses"]), 4)
        report = evaluate(
            self.jobs, generated, self.pub, ProblemIntelligenceStore(PROFILE_DIR)
        )
        self.assertFalse(report["reviewed"])
        self.assertEqual(report["summary"]["candidate_unreviewed"], 4)
        self.assertEqual(report["summary"]["needs_qa"], 0)
        self.assertTrue(
            all(not x["approved_for_publish"] and not x["runtime_eligible"]
                for x in report["rows"])
        )

    def test_conflicting_published_classification_goes_to_qa(self):
        generated = self.fake_generate()
        generated["responses"][0]["candidate"]["difficulty_candidate"] = "D5"
        report = evaluate(
            self.jobs, generated, self.pub, ProblemIntelligenceStore(PROFILE_DIR)
        )
        modified_uid = generated["responses"][0]["pb_uid"]
        flagged = next(
            row for row in report["rows"] if row["pb_uid"] == modified_uid
        )
        self.assertEqual(flagged["review_status"], "NEEDS_QA")
        self.assertTrue(
            any("Published difficulty" in s for s in flagged["qa_reasons"])
        )

    def test_low_confidence_or_ambiguity_goes_to_qa(self):
        generated = self.fake_generate()
        generated["responses"][0]["candidate"]["confidence"] = 0.7
        generated["responses"][1]["candidate"]["ambiguity_notes"] = [
            "Statement does not establish uniqueness."
        ]
        report = evaluate(
            self.jobs, generated, self.pub, ProblemIntelligenceStore(PROFILE_DIR)
        )
        self.assertEqual(report["summary"]["needs_qa"], 2)

    def test_unknown_skill_and_published_smuggling_fail_closed(self):
        generated = self.fake_generate()
        generated["responses"][0]["candidate"]["primary_skill_candidate"] = "S999_FAKE"
        with self.assertRaisesRegex(CandidateError, "unknown skill"):
            evaluate(self.jobs, generated, self.pub, ProblemIntelligenceStore(PROFILE_DIR))
        generated = self.fake_generate()
        generated["responses"][0]["candidate"]["published"] = True
        with self.assertRaisesRegex(CandidateError, "schema"):
            evaluate(self.jobs, generated, self.pub, ProblemIntelligenceStore(PROFILE_DIR))

    def test_forged_identity_and_duplicate_response_rejected(self):
        generated = self.fake_generate()
        generated["responses"][0]["source_sha256"] = "f" * 64
        with self.assertRaisesRegex(CandidateError, "fingerprint"):
            evaluate(self.jobs, generated, self.pub, ProblemIntelligenceStore(PROFILE_DIR))
        generated = self.fake_generate()
        generated["responses"].append(copy.deepcopy(generated["responses"][0]))
        with self.assertRaisesRegex(CandidateError, "duplicate|more model responses"):
            evaluate(self.jobs, generated, self.pub, ProblemIntelligenceStore(PROFILE_DIR))

    def test_source_metadata_change_invalidates_old_ai_response(self):
        generated = self.fake_generate()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for job in self.jobs["jobs"]:
                source = PROFILE_DIR / job["source"] / f"{job['external_id']}.json"
                target = root / job["source"] / source.name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            target = root / "zerojudge" / f"{self.jobs['jobs'][0]['external_id']}.json"
            payload = load_json(target)
            payload["source_metadata"]["statement_summary"] += " UPDATED"
            target.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(CandidateError, "source metadata changed"):
                evaluate(
                    self.jobs, generated, self.pub,
                    ProblemIntelligenceStore(root),
                )

    def test_missing_responses_never_count_as_candidates(self):
        generated = self.fake_generate()
        generated["responses"] = generated["responses"][:1]
        report = evaluate(
            self.jobs, generated, self.pub, ProblemIntelligenceStore(PROFILE_DIR)
        )
        self.assertEqual(report["summary"]["not_generated"], 3)
        self.assertEqual(report["summary"]["candidate_unreviewed"], 1)
        self.assertTrue(
            all(x["review_status"] == "NOT_GENERATED"
                for x in report["rows"] if "candidate" not in x)
        )

    def test_cli_prepare_writes_no_runtime_authority(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "jobs.json"
            run = subprocess.run(
                [
                    sys.executable, str(ROOT / "tools" / "ai_candidate_pipeline.py"),
                    "prepare", "--output", str(target),
                ],
                cwd=ROOT, text=True, capture_output=True, timeout=15,
                check=False,
            )
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertEqual(load_json(target), self.jobs)
            self.assertEqual(
                load_json(target)["jobs"][0]["source_sha256"],
                self.jobs["jobs"][0]["source_sha256"],
            )

    def test_generate_requires_explicit_cost_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out.json"
            job_path = Path(tmp) / "jobs.json"
            job_path.write_text(json.dumps(self.jobs), encoding="utf-8")
            with patch.dict(os.environ, {"OPENAI_API_KEY": "SENSITIVE-DO-NOT-SHOW"}):
                run = subprocess.run(
                    [
                        sys.executable, str(ROOT / "tools" / "ai_candidate_pipeline.py"),
                        "generate", "--jobs", str(job_path), "--output",
                        str(output), "--model", "gpt-4.1-mini",
                    ],
                    cwd=ROOT, text=True, capture_output=True, timeout=15,
                    check=False,
                )
            self.assertNotEqual(run.returncode, 0)
            self.assertIn("--confirm-api-cost", run.stdout)
            self.assertNotIn("SENSITIVE-DO-NOT-SHOW", run.stdout + run.stderr)
            self.assertFalse(output.exists())

    def test_four_real_chatgpt_candidates_use_existing_job_fingerprints(self):
        proposals = load_json(
            ROOT / "data" / "problem_pilot" / "chatgpt_proposals.v1.json"
        )
        generated = convert_chatgpt_proposals(self.jobs, proposals)
        self.assertEqual(
            generated["model"], "chatgpt-gpt-6-conversation"
        )
        self.assertEqual(len(generated["responses"]), 4)
        by_uid = {
            job["pb_uid"]: job for job in self.jobs["jobs"]
        }
        for row in generated["responses"]:
            self.assertEqual(
                row["source_sha256"],
                by_uid[row["pb_uid"]]["source_sha256"],
            )
            self.assertEqual(row["provider_response_id"], "")
            self.assertNotIn("approved_for_publish", row)

        report = evaluate(
            self.jobs, generated, self.pub,
            ProblemIntelligenceStore(PROFILE_DIR),
        )
        self.assertEqual(report["summary"], {
            "prepared": 4,
            "generated": 4,
            "candidate_unreviewed": 3,
            "needs_qa": 1,
            "not_generated": 0,
        })
        rows = {row["pb_uid"]: row for row in report["rows"]}
        self.assertEqual(rows["PB-9"]["review_status"], "NEEDS_QA")
        self.assertTrue(
            any("ambiguity" in note for note in rows["PB-9"]["qa_reasons"])
        )
        for uid in ("PB-27", "PB-183", "PB-182"):
            self.assertEqual(
                rows[uid]["review_status"], "CANDIDATE_UNREVIEWED"
            )
        self.assertTrue(
            all(not row["runtime_eligible"] and
                not row["approved_for_publish"] for row in report["rows"])
        )

    def test_chatgpt_schema_rejects_fake_api_receipt_or_duplicate_uid(self):
        proposals = load_json(
            ROOT / "data" / "problem_pilot" / "chatgpt_proposals.v1.json"
        )
        forged = copy.deepcopy(proposals)
        forged["proposals"][0]["source_sha256"] = "fake"
        with self.assertRaisesRegex(CandidateError, "only pb_uid"):
            convert_chatgpt_proposals(self.jobs, forged)

        dup = copy.deepcopy(proposals)
        dup["proposals"][1]["pb_uid"] = dup["proposals"][0]["pb_uid"]
        with self.assertRaisesRegex(CandidateError, "duplicate"):
            convert_chatgpt_proposals(self.jobs, dup)

        forged_model = copy.deepcopy(proposals)
        forged_model["model"] = "provider-api-response"
        with self.assertRaisesRegex(CandidateError, "model/date"):
            convert_chatgpt_proposals(self.jobs, forged_model)

    def test_chatgpt_unknown_prerequisite_does_not_pass_taxonomy(self):
        proposals = load_json(
            ROOT / "data" / "problem_pilot" / "chatgpt_proposals.v1.json"
        )
        bad = copy.deepcopy(proposals)
        bad["proposals"][0]["candidate"]["prerequisite_candidates"] = [
            "S999_FORGED"
        ]
        with self.assertRaisesRegex(CandidateError, "unknown skill"):
            evaluate(
                self.jobs,
                convert_chatgpt_proposals(self.jobs, bad),
                self.pub,
                ProblemIntelligenceStore(PROFILE_DIR),
            )

    def test_chatgpt_review_cli_requires_no_api_credentials_or_cost_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "qa.json"
            source = ROOT / "data" / "problem_pilot" / "chatgpt_proposals.v1.json"
            env = os.environ.copy()
            env.pop("OPENAI_API_KEY", None)
            run = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "ai_candidate_pipeline.py"),
                    "review-chatgpt",
                    "--proposals", str(source),
                    "--output", str(path),
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                timeout=15,
                check=False,
            )
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            report = load_json(path)
            self.assertEqual(report["summary"]["needs_qa"], 1)
            self.assertEqual(report["summary"]["candidate_unreviewed"], 3)
            self.assertFalse(report["reviewed"])
            self.assertEqual(report["model"], "chatgpt-gpt-6-conversation")

    def test_api_payload_fixed_endpoint_and_store_disabled(self):
        class FakeHTTP:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self):
                return json.dumps({
                    "status": "completed",
                    "id": "resp_test",
                    "output": [
                        {"type": "message", "content": [
                            {"type": "output_text", "text": json.dumps(
                                self_candidate
                            )}
                        ]}
                    ],
                }).encode("utf-8")

        self_candidate = self.make_candidate(self.jobs["jobs"][0])
        requests = []
        def fake_urlopen(request, timeout):
            requests.append(request)
            return FakeHTTP()
        with patch("tools.ai_candidate_pipeline.urllib.request.urlopen", fake_urlopen):
            candidate, provider_id = _api_candidate(
                self.jobs["jobs"][0],
                self.jobs["skills"],
                model="gpt-4.1-mini",
                api_key="TEST-KEY",
            )
        self.assertEqual(candidate, self_candidate)
        self.assertEqual(provider_id, "resp_test")
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].full_url, API_URL)
        sent = json.loads(requests[0].data)
        self.assertIs(sent["store"], False)
        self.assertEqual(sent["text"]["format"]["type"], "json_schema")
        self.assertIs(sent["text"]["format"]["strict"], True)
        self.assertNotIn("published_skill", sent["input"])


if __name__ == "__main__":
    unittest.main()
