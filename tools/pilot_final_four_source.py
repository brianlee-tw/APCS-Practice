#!/usr/bin/env python3
"""Last-four Pilot source audit: conservative official/secondary provenance.

No L0/Published/Notion mutation, no Test Center bundles and no learner Evidence.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/problem_pilot/source_reviews_batch4.v1.json"
SEED = ROOT / "data/problem_pilot/seed.v1.json"
PUBLISHED = ROOT / "curriculum/published.v23.json"
IDENTITIES = {
    "PB-120": ("APCS", "ZeroJudge", "q836", "OFFICIAL_PAGE_REVIEWED", 2),
    "PB-97": ("Codeforces", "Codeforces", "71A", "OFFICIAL_PAGE_REVIEWED", 1),
    "PB-32": ("ZeroJudge", "ZeroJudge", "a233", "OFFICIAL_PAGE_REVIEWED_WITH_QA_FLAG", 1),
    "PB-10": ("ZeroJudge", "ZeroJudge", "q182", "SECONDARY_DESCRIPTION_OFFICIAL_SAMPLE_PENDING", 0),
}
QA_FLAGS = {
    "PB-120": set(),
    "PB-97": set(),
    "PB-32": {"SOURCE_POSITIVE_INTEGER_VS_ZERO_SAMPLE", "VALUE_RANGE_NOT_SPECIFIED"},
    "PB-10": {"OFFICIAL_STATEMENT_UNAVAILABLE", "OFFICIAL_SAMPLE_UNAVAILABLE", "SECONDARY_SOURCE_ONLY"},
}


def load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: not an object")
    return data


def expected_output(uid: str, source: str) -> str:
    if uid == "PB-120":
        parts = list(map(int, source.split()))
        if len(parts) != 5:
            raise ValueError("q836 needs five integers")
        life, x1, y1, x2, y2 = parts
        if not (1 <= life <= 20 and 1 <= x1 <= 10 and 1 <= x2 <= 10
                and 1 <= y1 <= 20 and 1 <= y2 <= 20):
            raise ValueError("q836 input out of constraints")
        position = 0
        for _ in range(200000):
            position += life
            if position % x1 == 0:
                life -= y1
            if position % x2 == 0:
                life -= y2
            if life <= 0:
                return f"{position}\n"
        raise ValueError("q836 reference did not terminate")
    if uid == "PB-97":
        lines = source.strip().splitlines()
        n = int(lines[0])
        words = lines[1:]
        if len(words) != n or not 1 <= n <= 100:
            raise ValueError("invalid CF 71A count")
        if any(not 1 <= len(w) <= 100 or not w.isalpha() or not w.islower() for w in words):
            raise ValueError("invalid CF 71A word")
        return "\n".join(
            (w[0] + str(len(w) - 2) + w[-1]) if len(w) > 10 else w
            for w in words
        ) + "\n"
    if uid == "PB-32":
        arr = list(map(int, source.split()))
        if not arr or not 1 <= arr[0] <= 1000000 or len(arr) != arr[0] + 1:
            raise ValueError("invalid a233 count")
        return " ".join(map(str, sorted(arr[1:]))) + "\n"
    raise ValueError("no official-verified q182 task or sample oracle")


def verify(manifest: dict, seed: dict, published: dict) -> list[str]:
    errors = []
    if manifest.get("schema_version") != "apcs-pilot-source-review-batch4-v1":
        errors.append("unexpected batch 4 schema")
    if manifest.get("status") != "MIXED_OFFICIAL_AND_PENDING":
        errors.append("must not claim all four are fully source-verified")
    if manifest.get("publication_authority") != "NONE":
        errors.append("unapproved publication claim")
    if manifest.get("test_center_status") != "STAGED_DO_NOT_LOAD":
        errors.append("Test Center publication forbidden for batch 4")
    if manifest.get("official_page_bytes_sha256") != "NOT_CAPTURED":
        errors.append("official raw page hash cannot be fabricated")
    rows = manifest.get("records")
    if not isinstance(rows, list):
        return errors + ["records must be list"]
    ids = [row.get("pb_uid") for row in rows if isinstance(row, dict)]
    if len(ids) != 4 or len(set(ids)) != 4 or set(ids) != set(IDENTITIES):
        errors.append("records must contain exactly four unique expected PB UIDs")
    published_by = {r["pb_uid"]: r for r in published["problems"]}
    placements_by = {r["pb_uid"]: r for r in published["placements"]}
    seed_by = {r["pb_uid"]: r for r in seed["entries"]}
    known_skills = {s["uid"] for s in published["skills"]}
    for r in rows:
        if not isinstance(r, dict):
            errors.append("record not object")
            continue
        uid = r.get("pb_uid")
        if uid not in IDENTITIES:
            continue
        p, pl, sd = published_by[uid], placements_by[uid], seed_by[uid]
        source, judge, external, status, count = IDENTITIES[uid]
        if any([
            r.get("source_platform") != source,
            r.get("judge_platform") != judge,
            r.get("external_id") != external,
            r.get("problem_id") != p["problem_id"],
            r.get("canonical_url") != p["url"],
            r.get("canonical_url") != sd["canonical_url"],
            r.get("title") != p["title"],
            r.get("review_status") != status,
        ]):
            errors.append(f"{uid}: source identity/authority mismatch")
        if set(r.get("qa_flags", [])) != QA_FLAGS[uid]:
            errors.append(f"{uid}: source QA flags drift")
        if r.get("official_statement_verified") is not (uid != "PB-10"):
            errors.append(f"{uid}: statement status overclaimed")
        if r.get("official_samples_verified") is not (uid != "PB-10"):
            errors.append(f"{uid}: sample status overclaimed")
        evidence = r.get("source_evidence")
        if not isinstance(evidence, list) or not evidence or not all(
            isinstance(x, dict) and x.get("url", "").startswith("https://")
            and x.get("type") in {
                "OFFICIAL_PROBLEM_PAGE", "OFFICIAL_SOURCE_INDEXED_PAGE",
                "OFFICIAL_INDEX_IDENTITY_ONLY", "SECONDARY_WRITEUP_NOT_OFFICIAL",
            }
            for x in evidence
        ):
            errors.append(f"{uid}: missing source provenance")
        if uid == "PB-10":
            if not any(x.get("type") == "SECONDARY_WRITEUP_NOT_OFFICIAL" for x in evidence):
                errors.append("PB-10: secondary source provenance missing")
        elif not any(
            x.get("type") in {"OFFICIAL_PROBLEM_PAGE", "OFFICIAL_SOURCE_INDEXED_PAGE"}
            for x in evidence
        ):
            errors.append(f"{uid}: authoritative source page missing")
        candidate = r.get("candidate")
        if not isinstance(candidate, dict) or (
            candidate.get("primary_skill") != pl["primary_skill"]
            or candidate.get("difficulty") != p["difficulty"]
            or candidate.get("role") != pl["role"]
            or candidate.get("classification_source") != "AI_CANDIDATE"
            or not isinstance(candidate.get("supporting_skills"), list)
            or any(s not in known_skills for s in candidate.get("supporting_skills", []))
            or type(candidate.get("confidence")) not in (int, float)
            or not 0 <= candidate.get("confidence", -1) <= 1
        ):
            errors.append(f"{uid}: AI classification cannot override Published")
        samples = r.get("samples")
        if not isinstance(samples, list) or len(samples) != count:
            errors.append(f"{uid}: sample count wrong (pending official has zero)")
            continue
        if uid == "PB-10" and r.get("output_mode") != "NO_VERIFIED_SAMPLE":
            errors.append("PB-10: unverified samples cannot be judged")
        if uid != "PB-10" and r.get("output_mode") != "EXACT_OUTPUT_CANDIDATE":
            errors.append(f"{uid}: unexpected output checker candidate")
        for sample in samples:
            if not isinstance(sample, dict) or set(sample) != {"input", "output"}:
                errors.append(f"{uid}: malformed sample")
                continue
            try:
                output = expected_output(uid, sample["input"])
                if output.split() != sample["output"].split():
                    errors.append(f"{uid}: official example disagrees with independent reference")
            except (KeyError, ValueError, TypeError, IndexError) as exc:
                errors.append(f"{uid}: sample verification invalid: {exc}")
    return errors


def main() -> int:
    errors = verify(load(MANIFEST), load(SEED), load(PUBLISHED))
    for e in errors:
        print("FAIL:", e)
    if errors:
        return 1
    print("FINAL FOUR SOURCE QA PASS | 3 official reviewed, 1 secondary-only pending | 4 official sample pairs staged | 0 published")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
