#!/usr/bin/env python3
"""Read-only v2.4 Published coverage + APCS seed-pilot consistency checks.

This module never writes a curriculum, Notion record, testcase or learner
Evidence. Coverage is an allocation count, not learner readiness or QA.
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PUBLISHED = ROOT / "curriculum" / "published.v23.json"
AUDIT = ROOT / "data" / "problem_pilot" / "coverage.v1.json"
SEED = ROOT / "data" / "problem_pilot" / "seed.v1.json"


def load_json(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: JSON root must be an object")
    return raw


def frequencies(values: list[str]) -> dict[str, int]:
    counts = collections.Counter(values)
    return dict(sorted(counts.items()))


def build_coverage(
    published: dict[str, Any],
    seed: dict[str, Any],
    *,
    as_of: str,
    main_sha: str,
) -> dict[str, Any]:
    skills = published["skills"]
    problems = published["problems"]
    placements = published["placements"]
    entries = seed["entries"]
    skill_count = collections.Counter(
        row["primary_skill"] for row in placements
    )
    rows = []
    for skill in skills:
        uid = skill["uid"]
        n = skill_count[uid]
        rows.append(
            {
                "skill_uid": uid,
                "name": skill["name"],
                "published_placements": n,
                "coverage_band": (
                    "ZERO" if n == 0 else "THIN" if n < 3 else "PRESENT"
                ),
            }
        )
    return {
        "schema_version": "apcs-published-coverage-v1",
        "as_of": as_of,
        "snapshot": {
            "path": "curriculum/published.v23.json",
            "main_sha": main_sha,
        },
        "scope_note": (
            "Counts are published allocation references, not tested OJ correctness, "
            "learner attempts, source-statement QA, or actual mastery."
        ),
        "counts": {
            "published_skills": len(skills),
            "published_problems": len(problems),
            "published_placements": len(placements),
            "zero_primary_skill_placements": sum(
                row["coverage_band"] == "ZERO" for row in rows
            ),
            "thin_primary_skill_placements": sum(
                row["coverage_band"] == "THIN" for row in rows
            ),
        },
        "source_distribution": frequencies(
            [row.get("source_platform") or "UNKNOWN" for row in problems]
        ),
        "difficulty_distribution": frequencies(
            [row.get("difficulty") or "UNKNOWN" for row in problems]
        ),
        "role_distribution": frequencies(
            [row.get("role") or "UNKNOWN" for row in placements]
        ),
        "primary_skill_coverage": rows,
        "pilot_selection": {
            "size": len(entries),
            "by_primary_skill": frequencies(
                [row["primary_skill"] for row in entries]
            ),
            "by_source": frequencies(
                [row["source_platform"] for row in entries]
            ),
            "by_role": frequencies(
                [row["role"] for row in entries]
            ),
            "external_oj_count": sum(
                row["source_platform"] != "Custom" for row in entries
            ),
            "custom_count": sum(
                row["source_platform"] == "Custom" for row in entries
            ),
        },
    }


def validate_pilot(
    published: dict[str, Any],
    audit: dict[str, Any],
    seed: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if audit.get("schema_version") != "apcs-published-coverage-v1":
        errors.append("unexpected coverage schema")
    if seed.get("schema_version") != "apcs-problem-pilot-v1":
        errors.append("unexpected pilot schema")
    if seed.get("status") != "SEED_SELECTION_CANDIDATE":
        errors.append("seed may not claim published / verified status")
    if seed.get("snapshot") != audit.get("snapshot"):
        errors.append("pilot and audit must use same source snapshot")
    if seed.get("as_of") != audit.get("as_of"):
        errors.append("pilot and audit dates must match")

    entries = seed.get("entries")
    if not isinstance(entries, list) or not 15 <= len(entries) <= 20:
        return errors + ["pilot must contain 15-20 candidates"]

    pb_rows = published.get("problems", [])
    placement_rows = published.get("placements", [])
    known_skills = {row["uid"] for row in published.get("skills", [])}
    by_uid = {row["pb_uid"]: row for row in pb_rows}
    by_placement = {row["pb_uid"]: row for row in placement_rows}
    if len(by_uid) != len(pb_rows):
        errors.append("published PB UID is ambiguous")
    if len(by_placement) != len(placement_rows):
        errors.append("published placement PB UID is ambiguous")

    seen: set[str] = set()
    for rank, row in enumerate(entries, start=1):
        if not isinstance(row, dict):
            errors.append(f"pilot #{rank}: entry must be object")
            continue
        uid = row.get("pb_uid")
        if uid in seen:
            errors.append(f"{uid}: duplicate pilot PB UID")
        seen.add(uid)
        p = by_uid.get(uid)
        placement = by_placement.get(uid)
        if p is None or placement is None:
            errors.append(f"{uid}: no published identity + placement")
            continue
        expected = {
            "rank": rank,
            "problem_id": p["problem_id"],
            "title": p["title"],
            "source_platform": p["source_platform"],
            "canonical_url": p["url"],
            "primary_skill": placement["primary_skill"],
            "role": placement["role"],
            "difficulty": p["difficulty"],
            "suitability_3p3": p.get("suitability", {}).get("3+3", ""),
            "assessment_only": p.get("assessment_only") is True,
            "enrichment": "NOT_CURATED",
            "runtime_published_by_pilot": False,
        }
        for field, actual in expected.items():
            if row.get(field) != actual:
                errors.append(f"{uid}: {field} does not match safe baseline")
        receipt = row.get("source_receipt")
        if receipt is None:
            if (
                row.get("source_verification") != "NOT_CHECKED_THIS_PILOT"
                or row.get("testcases") != "NOT_CURATED"
            ):
                errors.append(f"{uid}: no source receipt for curated claim")
        else:
            if (
                row.get("source_verification")
                != "OFFICIAL_PAGE_SNAPSHOT_REVIEWED"
                or row.get("testcases") != "OFFICIAL_SAMPLE_CURATED"
            ):
                errors.append(f"{uid}: receipt/status mismatch")
            if not isinstance(receipt, dict):
                errors.append(f"{uid}: source receipt must be object")
                continue
            expected_asset_path = (
                "data/problem_enrichment/zerojudge/"
                + str(p["url"]).rsplit("problemid=", 1)[-1]
                + "/tests.json"
            )
            if (
                p["source_platform"] != "ZeroJudge"
                or receipt.get("asset_path") != expected_asset_path
                or receipt.get("url") != p["url"]
                or not receipt.get("reviewed_on")
                or receipt.get("source") != "public-indexed-official-page"
            ):
                errors.append(f"{uid}: source receipt identity is not verified")
            else:
                asset_file = ROOT / expected_asset_path
                try:
                    asset = load_json(asset_file)
                    cases = asset.get("cases", [])
                    identity = asset.get("identity", {})
                    if (
                        asset.get("schema_version") != "apcs-test-bundle-v1"
                        or identity.get("source") != "zerojudge"
                        or identity.get("external_id")
                        != str(p["url"]).rsplit("problemid=", 1)[-1]
                        or identity.get("canonical_url") != p["url"]
                        or len(cases) != receipt.get("sample_count")
                        or not cases
                        or any(
                            case.get("provenance") != "OFFICIAL"
                            or case.get("trust") != "OFFICIAL"
                            or case.get("suite") != "fast"
                            or case.get("visibility") != "official"
                            or not isinstance(case.get("input"), str)
                            or not isinstance(case.get("expected_output"), str)
                            for case in cases
                        )
                    ):
                        errors.append(f"{uid}: official sample asset/receipt mismatch")
                except (OSError, ValueError, TypeError) as exc:
                    errors.append(f"{uid}: official sample asset invalid: {exc}")
        if placement["primary_skill"] not in known_skills:
            errors.append(f"{uid}: unknown primary skill")
        if not str(row.get("priority_reason") or "").strip():
            errors.append(f"{uid}: missing selection rationale")
    try:
        expected_report = build_coverage(
            published,
            seed,
            as_of=str(audit["as_of"]),
            main_sha=str(audit["snapshot"]["main_sha"]),
        )
        if expected_report != audit:
            errors.append("coverage snapshot differs from reproducible counts")
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(f"coverage cannot be reconstructed: {exc}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate source-backed APCS coverage and 18-pilot seed"
    )
    parser.add_argument("--published", type=Path, default=PUBLISHED)
    parser.add_argument("--coverage", type=Path, default=AUDIT)
    parser.add_argument("--seed", type=Path, default=SEED)
    args = parser.parse_args()
    try:
        published = load_json(args.published)
        audit = load_json(args.coverage)
        seed = load_json(args.seed)
        errors = validate_pilot(published, audit, seed)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors = [str(exc)]
    if errors:
        for message in errors:
            print("FAIL:", message)
        return 1
    stats = audit["counts"]
    print(
        f"PILOT COVERAGE PASS | {stats['published_problems']} published | "
        f"{len(seed['entries'])} candidates | "
        f"{stats['zero_primary_skill_placements']} zero-placement skills"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
