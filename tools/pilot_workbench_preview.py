#!/usr/bin/env python3
"""Fail-closed four-problem official Fast and verified Full Test Center branch preview QA.

Checks Published identifiers and source-reviewed official samples against the
actual TestAssetStore artifacts. It NEVER publishes into Notion/Curriculum,
writes learner Evidence, or treats CI as genuine manual acceptance.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from .test_assets import TestAssetStore
except ImportError:
    from test_assets import TestAssetStore

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/problem_pilot/workbench_preview.v1.json"
PUBLISHED = ROOT / "curriculum/published.v23.json"
BATCH2 = ROOT / "data/problem_pilot/source_reviews_batch2.v1.json"
BATCH4 = ROOT / "data/problem_pilot/source_reviews_batch4.v1.json"
TESTS = ROOT / "data/problem_enrichment"
EXPECTED = {
    "PB-42": ("CSES", "CSES-1069", "cses", "1069", 1, 4, "Core Independent"),
    "PB-150": ("CSES", "CSES-1094", "cses", "1094", 1, 5, "Core Independent"),
    "PB-97": ("Codeforces", "CF-71A", "codeforces", "71A", 1, 3, "Worked Example"),
    "PB-120": ("APCS", "APCS-ZJ-q836", "zerojudge", "q836", 2, 5, "Core Independent"),
}


def load(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"{path}: expected JSON object")
    return obj


def validate(
    manifest: dict[str, Any],
    published: dict[str, Any],
    batch2: dict[str, Any],
    batch4: dict[str, Any],
    store: TestAssetStore,
) -> list[str]:
    errors = []
    if manifest.get("schema_version") != "apcs-pilot-workbench-preview-v1":
        errors.append("preview schema mismatch")
    if manifest.get("stage") != "SOURCE_BACKED_VERIFIED_FULL_PREVIEW":
        errors.append("preview scope enlarged without review")
    if (
        manifest.get("is_main_published") is not False
        or manifest.get("is_notion_approved") is not False
        or manifest.get("automated_evidence_writeback") is not False
        or manifest.get("requires_genuine_learner_acceptance") is not True
        or manifest.get("release_gate") != "BLOCKED_MANUAL"
    ):
        errors.append("preview cannot claim publication, Evidence or manual acceptance")

    entries = manifest.get("entries")
    if not isinstance(entries, list):
        return errors + ["preview entries must be array"]
    uids = [r.get("pb_uid") if isinstance(r, dict) else None for r in entries]
    if (
        len(entries) != len(EXPECTED)
        or len(set(uids)) != len(uids)
        or set(uids) != set(EXPECTED)
    ):
        errors.append("preview allowlist must contain exactly four unique Published PB UIDs")

    source2 = {r["pb_uid"]: r for r in batch2["entries"]}
    source4 = {r["pb_uid"]: r for r in batch4["records"]}
    problems = {p["pb_uid"]: p for p in published["problems"]}
    placements = {p["pb_uid"]: p for p in published["placements"]}
    for item in entries:
        if not isinstance(item, dict):
            errors.append("preview row must be object")
            continue
        uid = item.get("pb_uid")
        known = EXPECTED.get(uid)
        if known is None:
            errors.append(f"{uid}: not enrolled for official preview")
            continue
        published_source, pid, source, external_id, case_count, edge_count, role = known
        p, pl = problems.get(uid), placements.get(uid)
        review = source2.get(uid) or source4.get(uid)
        if p is None or pl is None or review is None:
            errors.append(f"{uid}: missing Published source or official review")
            continue

        expected = {
            "problem_id": pid,
            "published_source": published_source,
            "source": source,
            "external_id": external_id,
            "canonical_url": p["url"],
            "role": role,
            "official_count": case_count,
            "test_asset": (
                f"data/problem_enrichment/{source}/{external_id}/tests.json"
            ),
            "provenance": "OFFICIAL",
            "trust": "OFFICIAL",
            "suite": "fast",
            "visibility": "official",
            "source_status": "OFFICIAL_PAGE_REVIEWED",
            "task_qa_status": "PREVIEW_OFFICIAL_PLUS_DIFFERENTIAL",
            "unverified_candidates_allowed": False,
            "differential_verified_full_edges_allowed": True,
            "verified_edge_count": edge_count,
            "verified_edge_provenance": "AI_GENERATED",
            "verified_edge_trust": "DIFFERENTIAL_VERIFIED",
            "verified_edge_suite": "full",
            "verified_edge_visibility": "practice",
            "candidate_classification_adopted": False,
            "official_page_bytes_sha256": "NOT_CAPTURED",
            "source_review": (
                "data/problem_pilot/source_reviews_batch2.v1.json"
                if uid in source2
                else "data/problem_pilot/source_reviews_batch4.v1.json"
            ),
        }
        if p["problem_id"] != pid or p["source_platform"] != published_source:
            errors.append(f"{uid}: Published source/identity changed")
        if pl["role"] != role:
            errors.append(f"{uid}: Published role changed")
        for key, value in expected.items():
            if item.get(key) != value:
                errors.append(f"{uid}: preview {key} does not match signed-off selection")
        status = (
            review.get("source_review_status")
            if uid in source2 else review.get("review_status")
        )
        review_url = (
            review.get("url") if uid in source2 else review.get("canonical_url")
        )
        review_source = (
            review.get("source") if uid in source2 else review.get("source_platform")
        )
        sample_list = (
            review.get("official_samples") if uid in source2
            else review.get("samples")
        )
        if (
            status != "OFFICIAL_PAGE_REVIEWED"
            or review_url != p["url"]
            or review_source != published_source
            or not isinstance(sample_list, list)
            or len(sample_list) != case_count
        ):
            errors.append(f"{uid}: source-review official sample trust mismatch")
            continue

        bundle = store.load(source, external_id, include_candidates=False)
        if (
            bundle is None
            or bundle.source != source
            or bundle.external_id != external_id
            or bundle.canonical_url.rstrip("/") != p["url"].rstrip("/")
            or len(bundle.cases) != case_count + edge_count
        ):
            errors.append(f"{uid}: Test Center preview bundle missing/identity mismatch")
            continue
        for index, (case, sample) in enumerate(zip(bundle.cases, sample_list), start=1):
            if (
                case.case_id != f"S{index}"
                or case.provenance != "OFFICIAL"
                or case.trust != "OFFICIAL"
                or case.suite != "fast"
                or case.visibility != "official"
                or not isinstance(sample, dict)
                or case.input_text != sample.get("input")
                or case.expected_output != sample.get("output")
            ):
                errors.append(f"{uid}: preview source sample {index} mismatch/unsafe trust")
        before_exam = store.visible_cases(
            bundle, mode="exam", activity="Mock",
            post_attempt=False, suite="full",
        )
        if (
            len(before_exam) != case_count
            or any(c.provenance != "OFFICIAL" for c in before_exam)
        ):
            errors.append(f"{uid}: Exam spoiler firewall failed")
    return errors


def main() -> int:
    errors = validate(
        load(MANIFEST), load(PUBLISHED), load(BATCH2), load(BATCH4),
        TestAssetStore(TESTS),
    )
    for error in errors:
        print("FAIL:", error)
    if errors:
        return 1
    print("WORKBENCH PREVIEW PASS | 4 Published PB identities | "
          "5 official Fast samples | 0 non-official | release BLOCKED_MANUAL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
