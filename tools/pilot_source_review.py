#!/usr/bin/env python3
"""Read-only verifier for five source-reviewed, non-published APCS seed items.

This module does not import non-ZeroJudge data into L0, publish to Notion,
produce an OJ verdict, or add sample cases to the Test Center.
"""
from __future__ import annotations

import bisect
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE_REVIEWS = ROOT / "data" / "problem_pilot" / "source_reviews_batch2.v1.json"
SEED = ROOT / "data" / "problem_pilot" / "seed.v1.json"
PUBLISHED = ROOT / "curriculum" / "published.v23.json"
SAMPLE_MODE_EXACT = "EXACT_OUTPUT"
SAMPLE_MODE_ANY = "VALIDATE_ANY_CORRECT_X"
EXPECTED_ITEMS = {
    "PB-42": ("CSES", "1069", SAMPLE_MODE_EXACT),
    "PB-150": ("CSES", "1094", SAMPLE_MODE_EXACT),
    "PB-40": ("CSES", "1068", SAMPLE_MODE_EXACT),
    "PB-103": ("Codeforces", "706B", SAMPLE_MODE_EXACT),
    "PB-109": ("Codeforces", "977C", SAMPLE_MODE_ANY),
}


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: root must be an object")
    return data


def _numbers(source: str) -> list[int]:
    return list(map(int, source.split()))


def expected_exact_output(pb_uid: str, inp: str) -> str:
    """Independent small semantic procedures, only for fixed-output tasks."""
    if pb_uid == "PB-42":
        data = inp.strip()
        if not data or set(data) - set("ACGT"):
            raise ValueError("invalid DNA sample")
        streak = best = 1
        for i in range(1, len(data)):
            streak = streak + 1 if data[i] == data[i - 1] else 1
            best = max(best, streak)
        return str(best) + "\n"
    if pb_uid == "PB-150":
        values = _numbers(inp)
        n, arr = values[0], values[1:]
        if len(arr) != n or n < 1:
            raise ValueError("invalid Increasing Array sample")
        last, increments = arr[0], 0
        for v in arr[1:]:
            if v < last:
                increments += last - v
            else:
                last = v
        return str(increments) + "\n"
    if pb_uid == "PB-40":
        values = _numbers(inp)
        if len(values) != 1 or not 1 <= values[0] <= 1_000_000:
            raise ValueError("invalid Weird Algorithm sample")
        v = values[0]
        sequence = [v]
        while v != 1:
            v = v // 2 if v % 2 == 0 else 3 * v + 1
            sequence.append(v)
            if len(sequence) > 1_000_000:
                raise ValueError("unusually long sequence: sample cannot be verified")
        return " ".join(map(str, sequence)) + "\n"
    if pb_uid == "PB-103":
        values = _numbers(inp)
        if len(values) < 4:
            raise ValueError("invalid Interesting drink sample")
        n = values[0]
        prices = sorted(values[1:1 + n])
        q_pos = 1 + n
        q = values[q_pos]
        budgets = values[q_pos + 1:]
        if n < 1 or q < 1 or len(prices) != n or len(budgets) != q:
            raise ValueError("invalid Interesting drink sample")
        return "\n".join(
            str(bisect.bisect_right(prices, budget)) for budget in budgets
        ) + "\n"
    raise ValueError("non-EXACT task must use semantic checker")


def is_valid_977c(inp: str, candidate_output: str) -> bool:
    """CF 977C special checker: accept ANY legal x, not only sample's 6."""
    try:
        data = _numbers(inp)
        if len(data) < 3:
            return False
        n, k, *arr = data
        if not (1 <= n <= 200_000 and 0 <= k <= n and len(arr) == n):
            return False
        if any(not 1 <= x <= 10**9 for x in arr):
            return False
        fields = candidate_output.split()
        if len(fields) != 1:
            return False
        x = int(fields[0])
        if x != -1:
            return 1 <= x <= 10**9 and sum(v <= x for v in arr) == k
        values = sorted(arr)
        # Feasible iff there exists x in [1,1e9] between k-th and
        # (k+1)-th ranked values, accounting for k=0 and k=n.
        feasible = (
            (k == 0 and values[0] > 1)
            or k == n
            or (0 < k < n and values[k - 1] < values[k])
        )
        return not feasible
    except (ValueError, IndexError, TypeError):
        return False


def verify_batch(
    review: dict[str, Any],
    seed: dict[str, Any],
    published: dict[str, Any],
) -> list[str]:
    errors = []
    if review.get("schema_version") != "apcs-pilot-source-review-v1":
        errors.append("source review schema mismatch")
    if review.get("outcome") != "SOURCE_REVIEW_STAGED_NOT_PUBLISHED":
        errors.append("source review cannot assert publishing")
    if review.get("test_center_status") != "STAGED_DO_NOT_LOAD":
        errors.append("source review cannot auto-expose Test Center cases")
    if review.get("l0_import_supported") is not False:
        errors.append("non-ZeroJudge L0 importer is not implemented")
    entries = review.get("entries")
    if not isinstance(entries, list):
        return errors + ["source review entries must be a list"]
    if len(entries) != len(EXPECTED_ITEMS):
        errors.append("source review must include exactly five records")
    keys = [e.get("pb_uid") for e in entries if isinstance(e, dict)]
    if len(keys) != len(entries) or len(set(keys)) != len(keys) or set(keys) != set(EXPECTED_ITEMS):
        errors.append("source review PB UID identity/uniqueness mismatch")
    seed_by = {x["pb_uid"]: x for x in seed["entries"]}
    published_by = {x["pb_uid"]: x for x in published["problems"]}
    placements_by = {x["pb_uid"]: x for x in published["placements"]}
    known_skills = {x["uid"] for x in published["skills"]}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        uid = entry.get("pb_uid")
        expected = EXPECTED_ITEMS.get(uid)
        s, p, pl = seed_by.get(uid), published_by.get(uid), placements_by.get(uid)
        if expected is None or s is None or p is None or pl is None:
            errors.append(f"{uid}: not in Published/Pilot authority")
            continue
        source, external_id, mode = expected
        if any([
            entry.get("source") != source,
            entry.get("external_id") != external_id,
            entry.get("url") != p["url"],
            entry.get("url") != s["canonical_url"],
            entry.get("title") != p["title"],
            entry.get("expected_problem_id") != p["problem_id"],
            entry.get("judge_mode") != mode,
            entry.get("source_review_status") != "OFFICIAL_PAGE_REVIEWED",
            entry.get("sample_type") != "ILLUSTRATIVE_OFFICIAL_OUTPUT",
            entry.get("classification_source") != "AI_CANDIDATE",
            entry.get("ai_approved") is not False,
            entry.get("published_mutation") is not False,
            entry.get("source_page_fingerprint") != "NOT_CAPTURED",
        ]):
            errors.append(f"{uid}: source/role/provenance/authority mismatch")
        if not isinstance(entry.get("summary"), str) or not entry["summary"].strip():
            errors.append(f"{uid}: missing source-backed summary")
        if not isinstance(entry.get("constraints"), list) or not entry["constraints"]:
            errors.append(f"{uid}: missing source-backed constraints")
        c = entry.get("candidate")
        if not isinstance(c, dict):
            errors.append(f"{uid}: classification candidate missing")
        else:
            if c.get("primary_skill") != pl["primary_skill"]:
                errors.append(f"{uid}: Published primary skill disagreement needs separate QA")
            if c.get("difficulty") != p["difficulty"] or c.get("role") != pl["role"]:
                errors.append(f"{uid}: Published difficulty/role disagreement")
            if not isinstance(c.get("confidence"), (float, int)) or isinstance(c.get("confidence"), bool) or not 0 <= c["confidence"] <= 1:
                errors.append(f"{uid}: invalid AI confidence")
            supporting = c.get("supporting_skills")
            if not isinstance(supporting, list) or any(x not in known_skills for x in supporting):
                errors.append(f"{uid}: unknown supporting skill")
            if c.get("primary_skill") not in known_skills:
                errors.append(f"{uid}: unknown primary skill")
            if not isinstance(c.get("qa_reasons"), list):
                errors.append(f"{uid}: QA reasons must be list")
        cases = entry.get("official_samples")
        expected_count = 2 if uid == "PB-109" else 1
        if not isinstance(cases, list) or len(cases) != expected_count:
            errors.append(f"{uid}: official sample count mismatch")
            continue
        for sample in cases:
            if not isinstance(sample, dict) or set(sample) != {"input", "output"} or any(
                not isinstance(sample.get(k), str) for k in ("input", "output")
            ):
                errors.append(f"{uid}: invalid official sample record")
                continue
            if mode == SAMPLE_MODE_ANY:
                if not is_valid_977c(sample["input"], sample["output"]):
                    errors.append(f"{uid}: source example is not semantically valid")
            elif expected_exact_output(uid, sample["input"]).split() != sample["output"].split():
                errors.append(f"{uid}: official example inconsistent with independent oracle")
    return errors


def main() -> int:
    report = verify_batch(load(SOURCE_REVIEWS), load(SEED), load(PUBLISHED))
    if report:
        for err in report:
            print("FAIL:", err)
        return 1
    print("SOURCE REVIEW PASS | 5 source-backed staged | 4 exact-only | 1 semantic checker required | 0 published")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
