#!/usr/bin/env python3
"""Fail-closed Pilot QA for five Custom lesson contracts.

Custom tasks are NOT ordinary OJ exact-output exercises. This program validates
a conservative Notion-lesson-derived content/rubric snapshot only. It does not
read or generate private hosted task packets or learner Evidence.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "problem_pilot" / "custom_contracts_batch3.v1.json"
SEED = ROOT / "data" / "problem_pilot" / "seed.v1.json"
PUBLISHED = ROOT / "curriculum" / "published.v23.json"

# Fixed contracts are manually reconciled against the canonical Notion
# L-PSV-02, L-PSV-03, and L-ORD-02 lessons. If a contract changes, review the
# source and change the validator consciously, not by hiding a failed test.
CONTRACTS = {
    "PB-160": {
        "lesson": "L-PSV-02", "track": "Reading",
        "judge": "SEMANTIC_HUMAN_REVIEW",
        "task_type": "REASONING_GUIDED", "gate": False,
        "timebox": 12, "minutes": [5, 8],
        "artifacts": (
            "repeated_operation", "iteration_bounds",
            "time_complexity", "extra_space", "constraint_feasibility",
        ),
    },
    "PB-161": {
        "lesson": "L-PSV-02", "track": "Reading",
        "judge": "SEMANTIC_HUMAN_REVIEW",
        "task_type": "REASONING_CORE", "gate": True,
        "timebox": 15, "minutes": [8, 12],
        "artifacts": (
            "repeated_operation", "operation_count_rationale",
            "time_complexity", "extra_space",
            "constraint_feasibility", "bottleneck_identification",
        ),
    },
    "PB-164": {
        "lesson": "L-PSV-03", "track": "Reading",
        "judge": "RESPONSE_FIRST_READING_RUBRIC",
        "task_type": "TRACE_COMPLETION_CORE", "gate": True,
        "timebox": 15, "minutes": [8, 12],
        "artifacts": (
            "trace", "output_prediction",
            "minimal_completion", "completion_rationale",
            "second_testcase_validation",
        ),
    },
    "PB-165": {
        "lesson": "L-PSV-03", "track": "Implementation",
        "judge": "BUG_REPAIR_RUBRIC",
        "task_type": "DEBUG_TESTING_CORE", "gate": True,
        "timebox": 15, "minutes": [8, 12],
        "artifacts": (
            "minimal_counterexample", "expected_trace",
            "actual_trace", "first_divergence", "single_root_cause",
            "minimal_patch", "regression_tests_at_least_3",
        ),
    },
    "PB-169": {
        "lesson": "L-ORD-02", "track": "Implementation",
        "judge": "HOSTED_CUSTOM_OJ_PLUS_METHOD_REVIEW",
        "task_type": "MULTIKEY_RECORD_SORT_CORE", "gate": True,
        "timebox": 15, "minutes": [8, 12],
        "artifacts": (
            "record_representation", "score_descending",
            "penalty_ascending", "exact_tie_input_order",
            "comparator_reasoning", "time_complexity_nlogn",
            "original_field_identity",
        ),
    },
}
LESSON_URLS = {
    "L-PSV-02": (
        "https://app.notion.com/p/3c743be958cd8136b049f1ca91269687",
        "https://app.notion.com/p/3c943be958cd810fa1effe30cbe5570a",
    ),
    "L-PSV-03": (
        "https://app.notion.com/p/3c743be958cd81a8a0bbdc932ae7dd13",
        "https://app.notion.com/p/3c943be958cd81379cc1cd578e272344",
    ),
    "L-ORD-02": (
        "https://app.notion.com/p/3c743be958cd81ad903ff74ea4899a61",
        None,
    ),
}
PRE_ATTEMPT_BANS = {
    "PB-160": {"final_big_o", "iteration_space_solution", "feasibility_conclusion"},
    "PB-161": {"complexity_table", "dominant_term_answer", "final_big_o"},
    "PB-164": {
        "trace_table_scaffold", "invariant_conclusion",
        "missing_line_pattern", "reference_solution",
    },
    "PB-165": {
        "bug_category", "bug_location", "failing_dimension",
        "full_rewrite", "reference_solution",
    },
    "PB-169": {
        "comparator_code", "stable_sort_choice", "original_index_strategy",
        "complete_tiebreak_case_split", "reference_solution",
    },
}
FORBIDDEN_FIELDS = {
    "expected_output", "official_sample", "testcases", "reference_solution",
    "solution_code", "learner_answer", "learner_evidence", "judge_verdict",
    "approved_for_publish",
}


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("contract JSON root must be object")
    return data


def validate(
    manifest: dict[str, Any],
    seed: dict[str, Any],
    published: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if manifest.get("schema_version") != "apcs-pilot-custom-contracts-v1":
        errors.append("invalid Custom contract schema")
    if manifest.get("status") != "LESSON_CONTRACT_REVIEWED_TASK_INSTANCE_PENDING":
        errors.append("Custom source cannot claim full task-level verification")
    if manifest.get("provenance") != "CANONICAL_NOTION_LESSON_AND_COACH_CONTRACT":
        errors.append("missing Notion lesson provenance")
    if manifest.get("publication_authority") != "NONE":
        errors.append("Custom cannot claim publication authority")
    if manifest.get("learner_visibility") != "STAGING_ONLY_NOT_IN_TEST_CENTER":
        errors.append("Custom cannot be exposed in local Test Center")
    rows = manifest.get("entries")
    if not isinstance(rows, list):
        return errors + ["Custom entries not array"]
    ids = [r.get("pb_uid") if isinstance(r, dict) else None for r in rows]
    if len(rows) != 5 or set(ids) != set(CONTRACTS) or len(ids) != len(set(ids)):
        errors.append("Custom contract must contain exactly the five expected PB UIDs")
    seed_by = {x["pb_uid"]: x for x in seed["entries"]}
    problem_by = {x["pb_uid"]: x for x in published["problems"]}
    placement_by = {x["pb_uid"]: x for x in published["placements"]}
    for row in rows:
        if not isinstance(row, dict):
            errors.append("Custom entry must be object")
            continue
        uid = row.get("pb_uid")
        base = CONTRACTS.get(uid)
        original = problem_by.get(uid)
        placement = placement_by.get(uid)
        selected = seed_by.get(uid)
        if any(x is None for x in (base, original, placement, selected)):
            errors.append(f"{uid}: missing Published/Seed identity")
            continue
        if FORBIDDEN_FIELDS.intersection(row):
            errors.append(f"{uid}: forbidden answer/evidence/testcase fields")
        identity = {
            "source": "Custom",
            "problem_id": original["problem_id"],
            "canonical_url": original["url"],
            "lesson_uid": placement["lesson_uid"],
            "placement_uid": placement["placement_uid"],
            "primary_skill": placement["primary_skill"],
            "role": placement["role"],
        }
        for key, actual in identity.items():
            if key == "source":
                if selected["source_platform"] != actual:
                    errors.append(f"{uid}: Published Custom source mismatch")
            elif key == "problem_id":
                if selected["problem_id"] != actual:
                    errors.append(f"{uid}: seed/PB ID mismatch")
            elif key == "canonical_url":
                if selected["canonical_url"] != actual:
                    errors.append(f"{uid}: seed/Published official route mismatch")
            elif row.get(key) != actual:
                errors.append(f"{uid}: {key} must equal canonical Published")
        if row.get("lesson_uid") != base["lesson"]:
            errors.append(f"{uid}: lesson contract mismatch")
        if (row.get("lesson_url"), row.get("coach_url")) != LESSON_URLS[base["lesson"]]:
            errors.append(f"{uid}: unverified Notion lesson/coach URL")
        required = {
            "task_type": base["task_type"],
            "track": base["track"],
            "grade_route": base["judge"],
            "gate_candidate": base["gate"],
            "timebox_minutes": base["timebox"],
            "a0_cold_minutes": base["minutes"],
            "required_artifacts": list(base["artifacts"]),
        }
        for field, expected in required.items():
            if row.get(field) != expected:
                errors.append(f"{uid}: {field} diverges from Notion lesson rubric")
        if row.get("gate_candidate") != (placement["role"] == "Core Independent"):
            errors.append(f"{uid}: Guided cannot claim Core Gate")
        if row.get("source_review_status") != "LESSON_CONTRACT_REVIEWED_TASK_INSTANCE_PENDING":
            errors.append(f"{uid}: false full source verification claim")
        locked = {
            "task_statement_retrieved": False,
            "local_test_center_eligible": False,
            "ai_approved": False,
            "learner_attempt_observed": False,
            "learner_evidence_written": False,
            "testcases_status": "NOT_CURATED",
        }
        for field, expected in locked.items():
            if row.get(field) != expected:
                errors.append(f"{uid}: {field} unauthorized adoption/publish")
        forbidden = row.get("pre_attempt_forbidden")
        disclosed = row.get("pre_attempt_disclosure")
        if (
            not isinstance(forbidden, list)
            or not PRE_ATTEMPT_BANS[uid].issubset(set(forbidden))
            or not isinstance(disclosed, list)
            or bool(set(disclosed).intersection(set(forbidden)))
        ):
            errors.append(f"{uid}: preattempt spoiler policy violated")
        if not isinstance(row.get("a1_policy"), str) or not row["a1_policy"]:
            errors.append(f"{uid}: missing A1-only safety guidance")
        if not isinstance(row.get("independent_rule"), str):
            errors.append(f"{uid}: missing assistance restriction")
        if row.get("assessment") != (
            "GATE_CANDIDATE_CONDITIONAL" if base["gate"] else "LEARNING_ONLY"
        ):
            errors.append(f"{uid}: Gate-grade claim overreaches")
    return errors


def main() -> int:
    errors = validate(load(MANIFEST), load(SEED), load(PUBLISHED))
    for err in errors:
        print("FAIL:", err)
    if errors:
        return 1
    print(
        "CUSTOM CONTRACT PASS | 5 source-backed lesson contracts | "
        "1 Guided learning-only / 4 Core Gate candidates | "
        "2 Reading Core / 2 Implementation Core | "
        "0 task packets verified | 0 Test Center cases"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
