#!/usr/bin/env python3
"""Non-publishing gate for PR #89 source-backed Problem Bank Pilot.

PASS here means a reproducible *engineering preflight only*. It never
certifies human learner acceptance, OJ AC, manual L1 approval or merge readiness.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from .ai_candidate_pipeline import (
        PROFILE_DIR,
        PUBLISHED,
        SEED,
        build_jobs,
        convert_chatgpt_proposals,
        evaluate,
        load_json,
    )
    from .pilot_coverage import (
        AUDIT,
        validate_pilot,
    )
    from .pilot_source_review import (
        SOURCE_REVIEWS,
        verify_batch,
    )
    from .pilot_custom_contracts import (
        MANIFEST as CUSTOM_CONTRACTS,
        validate as validate_custom_contracts,
    )
    from .pilot_final_four_source import (
        MANIFEST as FINAL_FOUR,
        verify as verify_final_four,
    )
    from .problem_intelligence import ProblemIntelligenceStore
    from .test_assets import TestAssetStore
except ImportError:
    from ai_candidate_pipeline import (
        PROFILE_DIR,
        PUBLISHED,
        SEED,
        build_jobs,
        convert_chatgpt_proposals,
        evaluate,
        load_json,
    )
    from pilot_coverage import (
        AUDIT,
        validate_pilot,
    )
    from pilot_source_review import (
        SOURCE_REVIEWS,
        verify_batch,
    )
    from pilot_custom_contracts import (
        MANIFEST as CUSTOM_CONTRACTS,
        validate as validate_custom_contracts,
    )
    from pilot_final_four_source import (
        MANIFEST as FINAL_FOUR,
        verify as verify_final_four,
    )
    from problem_intelligence import ProblemIntelligenceStore
    from test_assets import TestAssetStore

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = ROOT / "docs" / "CURRENT_AUTHORITY.json"
POLICY = ROOT / "data" / "problem_pilot" / "policy_review.v1.json"
PROPOSALS = ROOT / "data" / "problem_pilot" / "chatgpt_proposals.v1.json"
EXPECTED_CASES = {
    "PB-182": ("d067", 4, 6),
    "PB-183": ("d097", 1, 4),
    "PB-27": ("d732", 1, 3),
    "PB-9": ("j606", 2, 4),
}
EXPECTED_POLICY = {
    "PB-9": {
        "primary_skill": "S34_Matrix_2D",
        "supporting_skills": ["S07_String", "S23_Simulation"],
        "role": "Core Independent",
        "evidence_level_cap": 3,
        "method_confirmation_required": False,
        "ai_classification_status": "NEEDS_QA",
    },
    "PB-27": {
        "primary_skill": "S10_Binary_Search",
        "supporting_skills": ["S30_Complexity"],
        "role": "Guided Drill",
        "evidence_level_cap": 2,
        "method_confirmation_required": False,
        "ai_classification_status": "CANDIDATE_UNREVIEWED",
    },
}


def github_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    git_object = b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    return hashlib.sha1(git_object).hexdigest()


def preflight(root: Path = ROOT) -> dict[str, Any]:
    """Read-only; never mutates a workspace, learning state or Git index."""
    # The existing code-backed validators operate on repository-root globals;
    # reject foreign roots rather than silently mixing data authorities.
    if root.resolve() != ROOT.resolve():
        raise ValueError("preflight must use this repository root")
    errors: list[str] = []
    published = load_json(PUBLISHED)
    seed = load_json(SEED)
    audit = load_json(AUDIT)
    policy = load_json(POLICY)
    authority = load_json(AUTHORITY)
    proposals = load_json(PROPOSALS)
    profiles = ProblemIntelligenceStore(PROFILE_DIR)

    if policy.get("schema_version") != "apcs-problem-pilot-policy-review-v1":
        errors.append("policy review schema mismatch")
    if policy.get("approval_scope") != "POLICY_CONSISTENCY_ONLY_NOT_CLASSIFICATION_APPROVAL":
        errors.append("policy source review cannot act as formal L1 approval")
    if policy.get("review_type") != "CHATGPT_SOURCE_RECONCILIATION":
        errors.append("policy review provenance mismatch")
    for path, field in (
        (PUBLISHED, "canonical_published_blob_sha"),
        (AUTHORITY, "canonical_authority_blob_sha"),
    ):
        if github_blob_sha(path) != policy.get(field):
            errors.append(f"{path.name}: canonical main blob authority drift")

    product = authority.get("product") or {}
    if product.get("next_version_status") != "C8_GENUINE_LEARNER_PILOT":
        errors.append("cannot change version gate status")
    if product.get("learner_readiness") != "NOT_ASSESSED":
        errors.append("learner readiness must remain NOT_ASSESSED")
    if authority.get("current_work", {}).get("gate") != "C8":
        errors.append("active gate must remain C8")
    errors.extend(validate_pilot(published, audit, seed))
    staged_source_batch = load_json(SOURCE_REVIEWS)
    errors.extend(verify_batch(staged_source_batch, seed, published))
    staged_custom = load_json(CUSTOM_CONTRACTS)
    errors.extend(validate_custom_contracts(staged_custom, seed, published))
    staged_last_four = load_json(FINAL_FOUR)
    errors.extend(verify_final_four(staged_last_four, seed, published))

    by_uid = {p["pb_uid"]: p for p in published["placements"]}
    problems = {p["pb_uid"]: p for p in published["problems"]}
    if len(by_uid) != len(published["placements"]):
        errors.append("ambiguous Published PB UID placements")
    if len(problems) != len(published["problems"]):
        errors.append("ambiguous Published PB UID problems")

    decisions = policy.get("decisions")
    if not isinstance(decisions, list):
        decisions = []
        errors.append("policy decisions must be array")
    ids = [d.get("pb_uid") for d in decisions if isinstance(d, dict)]
    if len(ids) != len(decisions) or set(ids) != set(EXPECTED_POLICY) or len(ids) != len(set(ids)):
        errors.append("policy decisions must cover exactly PB-9 / PB-27")
    for entry in decisions:
        if not isinstance(entry, dict):
            continue
        uid = entry.get("pb_uid")
        expected = EXPECTED_POLICY.get(uid)
        pl = by_uid.get(uid)
        p = problems.get(uid)
        if expected is None or pl is None or p is None:
            errors.append(f"{uid}: missing canonical policy/placement")
            continue
        if (
            entry.get("decision") != "KEEP_PUBLISHED_PLACEMENT_UNCHANGED"
            or entry.get("reviewer_approval") != "PENDING"
            or entry.get("lesson_uid") != pl.get("lesson_uid")
            or entry.get("source_problem") != p.get("url")
            or not str(entry.get("canonical_lesson") or "").startswith(
                "https://app.notion.com/p/"
            )
        ):
            errors.append(f"{uid}: policy decision/authority changed")
        for key, value in expected.items():
            if key != "ai_classification_status" and (
                entry.get("published_" + key if key == "primary_skill" else key)
                != value
                or pl.get(key) != value
            ):
                errors.append(f"{uid}: Published {key} policy drift")
        if entry.get("ai_classification_status") != expected["ai_classification_status"]:
            errors.append(f"{uid}: AI classification is not source-approved")
    boundaries = policy.get("release_boundaries") or {}
    required_closed = (
        "can_change_published_curriculum",
        "can_change_notion_formal_content",
        "can_autoadopt_l1",
        "can_count_oj_or_local_as_mastery",
        "allow_merge_without_explicit_user_approval",
    )
    if any(boundaries.get(key) is not False for key in required_closed):
        errors.append("policy has unauthorized authority expansion")
    for field, value in {
        "genuine_learner_acceptance": "PENDING",
        "ai_candidate_approval": "PENDING",
        "c8_status": "OPEN",
        "learner_readiness": "NOT_ASSESSED",
    }.items():
        if boundaries.get(field) != value:
            errors.append(f"release {field} must remain {value}")

    jobs = build_jobs(published, seed, profiles)
    responses = convert_chatgpt_proposals(jobs, proposals)
    qa = evaluate(jobs, responses, published, profiles)
    by_result = {x["pb_uid"]: x for x in qa["rows"]}
    if qa["summary"] != {
        "prepared": 4,
        "generated": 4,
        "candidate_unreviewed": 3,
        "needs_qa": 1,
        "not_generated": 0,
    }:
        errors.append("unexpected AI QA candidate lifecycle counts")
    for uid, expected in EXPECTED_POLICY.items():
        if (by_result.get(uid) or {}).get("review_status") != expected["ai_classification_status"]:
            errors.append(f"{uid}: AI QA result is no longer conservative")
    if qa["reviewed"] is not False or any(
        x.get("approved_for_publish") is not False
        or x.get("runtime_eligible") is not False
        for x in qa["rows"]
    ):
        errors.append("AI Candidate cannot assert formal approval or runtime eligibility")

    store = TestAssetStore(ROOT / "data" / "problem_enrichment")
    errors.extend(store.validate_all())
    total_official = total_edge = 0
    for uid, (external_id, expected_official, expected_edges) in EXPECTED_CASES.items():
        bundle = store.load("zerojudge", external_id, include_candidates=False)
        if bundle is None or bundle.canonical_url != problems[uid]["url"]:
            errors.append(f"{uid}: Test Center source identity mismatch")
            continue
        official = [x for x in bundle.cases if x.provenance == "OFFICIAL"]
        edge = [x for x in bundle.cases if x.provenance == "AI_GENERATED"]
        total_official += len(official)
        total_edge += len(edge)
        if (
            len(official) != expected_official
            or len(edge) != expected_edges
            or len(bundle.cases) != expected_official + expected_edges
        ):
            errors.append(f"{uid}: unexpected official / edge inventory")
        if any(
            x.trust != "OFFICIAL" or x.suite != "fast"
            or x.visibility != "official"
            for x in official
        ):
            errors.append(f"{uid}: OFFICIAL evidence tampered")
        if any(
            x.trust != "DIFFERENTIAL_VERIFIED" or x.suite != "full"
            or x.visibility != "practice"
            for x in edge
        ):
            errors.append(f"{uid}: AI edge trust/suite/visibility tampered")
        strict = store.visible_cases(
            bundle, mode="exam", activity="Mock",
            post_attempt=False, suite="full",
        )
        if len(strict) != expected_official or any(
            c.provenance != "OFFICIAL" for c in strict
        ):
            errors.append(f"{uid}: preattempt Exam spoiler leak")

    # This gate deliberately remains BLOCKED_MANUAL even when every automated
    # check passes. A CLI/CI cannot impersonate a real learner acceptance.
    return {
        "schema_version": "apcs-pilot-release-preflight-v1",
        "engineering_checks": "PASS" if not errors else "FAIL",
        "release_gate": "BLOCKED_MANUAL",
        "open_requirements": [
            "genuine Windows/WSL VS Code learner manual acceptance",
            "formal user authorization to merge PR #89",
            "L1 candidate adoption only after reviewer approval",
        ],
        "auto_merge_permitted": False,
        "c8_closed": False,
        "learner_readiness": "NOT_ASSESSED",
        "counts": {
            "published_problems": len(published["problems"]),
            "seed_candidates": len(seed["entries"]),
            "ai_candidate_unreviewed": qa["summary"]["candidate_unreviewed"],
            "ai_needs_qa": qa["summary"]["needs_qa"],
            "official_samples": total_official,
            "differential_edge_tests": total_edge,
            "source_review_staged": len(staged_source_batch["entries"]),
            "source_review_exact_output": sum(
                row["judge_mode"] == "EXACT_OUTPUT"
                for row in staged_source_batch["entries"]
            ),
            "source_review_special_checker_required": sum(
                row["judge_mode"] == "VALIDATE_ANY_CORRECT_X"
                for row in staged_source_batch["entries"]
            ),
            "custom_lesson_contracts_reviewed": len(staged_custom["entries"]),
            "custom_task_packets_verified": sum(
                row["task_statement_retrieved"]
                for row in staged_custom["entries"]
            ),
            "custom_gate_candidates_conditional": sum(
                row["gate_candidate"]
                for row in staged_custom["entries"]
            ),
            "final_four_reviewed_official": sum(
                row["official_statement_verified"]
                for row in staged_last_four["records"]
            ),
            "final_four_pending_official": sum(
                not row["official_statement_verified"]
                for row in staged_last_four["records"]
            ),
            "final_four_official_samples_staged": sum(
                len(row["samples"]) for row in staged_last_four["records"]
            ),
        },
        "errors": errors,
        "ci_claim": "NOT_CHECKED_BY_THIS_LOCAL_PREFLIGHT",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="APCS Pilot non-publishing release QA")
    parser.add_argument("--output", type=Path, help="optional JSON report (write-once)")
    args = parser.parse_args()
    try:
        report = preflight()
        if args.output is not None:
            if args.output.exists():
                raise ValueError(f"refusing overwrite: {args.output}")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"PILOT PREFLIGHT FAIL: {exc}")
        return 1
    for issue in report["errors"]:
        print("FAIL:", issue)
    print(
        f"PILOT PREFLIGHT {report['engineering_checks']} / "
        f"RELEASE {report['release_gate']} | "
        f"{report['counts']['official_samples']} official / "
        f"{report['counts']['differential_edge_tests']} edges"
    )
    return 0 if report["engineering_checks"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
