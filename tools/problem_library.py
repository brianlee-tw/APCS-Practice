#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    from .evidence_outbox import EvidenceOutbox
    from .problem_enrichment import ProblemEnrichmentStore
    from .problem_intelligence import ProblemIntelligenceStore
except ImportError:
    from evidence_outbox import EvidenceOutbox
    from problem_enrichment import ProblemEnrichmentStore
    from problem_intelligence import ProblemIntelligenceStore

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE_DIR = ROOT / "data" / "problem_intelligence"
DEFAULT_ENRICHMENT_DIR = ROOT / "data" / "problem_enrichment"
DEFAULT_RUNTIME_DIR = ROOT / ".apcs" / "runtime"

HIDE_METHOD_ACTIVITIES = {
    "Core Independent",
    "Transfer Challenge",
    "Mock",
}
STRICT_SPOILER_ACTIVITIES = {
    "Transfer Challenge",
    "Mock",
}


@dataclass(frozen=True)
class LibraryItem:
    source: str
    external_id: str
    canonical_url: str
    title: str
    statement_summary: str
    lifecycle: str
    classification_status: str
    difficulty: str | None
    primary_skill: str | None
    supporting_skills: tuple[str, ...]
    role: str | None
    pb_uid: str | None
    attempted: bool
    has_l2: bool
    trust_status: str | None

    @property
    def key(self) -> str:
        return f"{self.source}:{self.external_id}"


class ProblemLibrary:
    """只讀 learner-facing 題目庫。

    題目 identity 仍來自 Problem Intelligence / Problem Bank；
    本層只做搜尋與防劇透呈現，不建立新的 truth。
    """

    def __init__(
        self,
        profiles: ProblemIntelligenceStore | None = None,
        enrichment: ProblemEnrichmentStore | None = None,
        outbox: EvidenceOutbox | None = None,
    ):
        self.profiles = profiles or ProblemIntelligenceStore(
            DEFAULT_PROFILE_DIR
        )
        self.enrichment = enrichment or ProblemEnrichmentStore(
            self.profiles,
            DEFAULT_ENRICHMENT_DIR,
        )
        self.outbox = outbox or EvidenceOutbox(
            DEFAULT_RUNTIME_DIR
        )

    def attempted_pb_uids(self) -> set[str]:
        result: set[str] = set()
        try:
            envelopes = self.outbox.all_envelopes()
        except Exception:
            return result

        for envelope in envelopes:
            pb_uid = envelope.attempt.pb_uid
            if pb_uid:
                result.add(pb_uid)
        return result

    def _profile_rows(self) -> Iterable[dict[str, Any]]:
        for path in self.profiles.all_paths():
            try:
                profile = self.profiles._read(path)
                self.profiles.validate_record(profile, path)
            except Exception:
                continue
            yield profile

    def items(self) -> list[LibraryItem]:
        attempted = self.attempted_pb_uids()
        result: list[LibraryItem] = []

        for profile in self._profile_rows():
            identity = profile["identity"]
            metadata = profile["source_metadata"]
            classification = profile["classification"]
            integration = profile["integration"]

            source = identity["source"]
            external_id = identity["external_id"]
            package_path = self.enrichment.package_path(
                source,
                external_id,
            )
            trust = None

            if package_path.is_file():
                try:
                    package = self.enrichment.load(
                        source,
                        external_id,
                    )
                    trust = package["verification"]["trust_status"]
                except Exception:
                    # Invalid L2 is not learner-visible; metadata validation
                    # catches the corruption separately.
                    package_path = Path("")

            pb_uid = integration.get("pb_uid")

            result.append(
                LibraryItem(
                    source=source,
                    external_id=external_id,
                    canonical_url=identity["canonical_url"],
                    title=metadata.get("title") or external_id,
                    statement_summary=metadata.get("statement_summary") or "",
                    lifecycle=profile["lifecycle"],
                    classification_status=classification["status"],
                    difficulty=classification.get("difficulty_candidate"),
                    primary_skill=classification.get(
                        "primary_skill_candidate"
                    ),
                    supporting_skills=tuple(
                        classification.get(
                            "supporting_skill_candidates",
                            [],
                        )
                    ),
                    role=classification.get("role_candidate"),
                    pb_uid=pb_uid,
                    attempted=bool(pb_uid and pb_uid in attempted),
                    has_l2=package_path.is_file(),
                    trust_status=trust,
                )
            )

        return sorted(
            result,
            key=lambda item: (
                item.source,
                item.external_id,
            ),
        )

    def search(
        self,
        query: str = "",
        *,
        source: str | None = None,
        difficulty: str | None = None,
        skill: str | None = None,
        role: str | None = None,
        attempted: bool | None = None,
        require_l2: bool | None = None,
        limit: int = 50,
    ) -> list[LibraryItem]:
        q = str(query or "").strip().casefold()
        source_q = str(source or "").strip().casefold()
        difficulty_q = str(difficulty or "").strip()
        skill_q = str(skill or "").strip().casefold()
        role_q = str(role or "").strip().casefold()

        result = []
        for item in self.items():
            if source_q and item.source.casefold() != source_q:
                continue
            if difficulty_q and item.difficulty != difficulty_q:
                continue
            if attempted is not None and item.attempted is not attempted:
                continue
            if require_l2 is not None and item.has_l2 is not require_l2:
                continue
            if role_q and (item.role or "").casefold() != role_q:
                continue
            if skill_q:
                skills = [
                    item.primary_skill or "",
                    *item.supporting_skills,
                ]
                if not any(skill_q == value.casefold() for value in skills):
                    continue
            if q:
                haystack = " ".join(
                    [
                        item.external_id,
                        item.title,
                        item.statement_summary,
                        item.source,
                    ]
                ).casefold()
                if q not in haystack:
                    continue

            result.append(item)
            if len(result) >= max(1, int(limit)):
                break

        return result

    def learner_view(
        self,
        item: LibraryItem,
        *,
        activity: str | None = None,
        post_attempt: bool = False,
    ) -> dict[str, Any]:
        """回傳符合防劇透規則的 learner-facing 資料。"""

        effective_activity = activity or item.role or "Core Independent"
        strict = effective_activity in STRICT_SPOILER_ACTIVITIES
        hide_method = effective_activity in HIDE_METHOD_ACTIVITIES

        result: dict[str, Any] = {
            "key": item.key,
            "title": item.title,
            "source": item.source,
            "external_id": item.external_id,
            "canonical_url": item.canonical_url,
            "attempted": item.attempted,
            "has_l2": item.has_l2,
            "activity": effective_activity,
            "difficulty": item.difficulty,
            "classification_status": item.classification_status,
        }

        if not strict:
            result["statement_summary"] = item.statement_summary

        if post_attempt or not hide_method:
            result["primary_skill"] = item.primary_skill
            result["supporting_skills"] = list(item.supporting_skills)

        if post_attempt and item.has_l2:
            package = self.enrichment.load(
                item.source,
                item.external_id,
            )
            teaching = package["teaching"]
            result.update(
                {
                    "problem_model": teaching["problem_model"],
                    "key_observation": teaching["key_observation"],
                    "correctness_reasoning": teaching[
                        "correctness_reasoning"
                    ],
                    "invariant": teaching["invariant"],
                    "time_complexity": teaching["time_complexity"],
                    "space_complexity": teaching["space_complexity"],
                    "common_pitfalls": list(
                        teaching["common_pitfalls"]
                    ),
                    "edge_cases": list(teaching["edge_cases"]),
                    "hints": dict(teaching["hints"]),
                    "alternate_approaches": list(
                        teaching["alternate_approaches"]
                    ),
                    "transfer_signals": list(
                        teaching["transfer_signals"]
                    ),
                    "trust_status": package["verification"][
                        "trust_status"
                    ],
                }
            )

        # 任何 pre-attempt view 都不暴露解答路徑或 key observation。
        if not post_attempt:
            for key in (
                "problem_model",
                "key_observation",
                "correctness_reasoning",
                "invariant",
                "hints",
                "alternate_approaches",
                "transfer_signals",
                "trust_status",
            ):
                result.pop(key, None)

        if strict and not post_attempt:
            result.pop("primary_skill", None)
            result.pop("supporting_skills", None)
            result.pop("statement_summary", None)

        return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="APCS v2.4 題目庫搜尋工具"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    search = sub.add_parser("search")
    search.add_argument("query", nargs="?", default="")
    search.add_argument("--source")
    search.add_argument("--difficulty")
    search.add_argument("--skill")
    search.add_argument("--role")
    search.add_argument(
        "--attempted",
        choices=["yes", "no"],
    )
    search.add_argument("--require-l2", action="store_true")
    search.add_argument("--limit", type=int, default=20)
    search.add_argument(
        "--activity",
        default="Core Independent",
    )
    search.add_argument("--post-attempt", action="store_true")
    search.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    library = ProblemLibrary()

    attempted = None
    if args.attempted == "yes":
        attempted = True
    elif args.attempted == "no":
        attempted = False

    items = library.search(
        args.query,
        source=args.source,
        difficulty=args.difficulty,
        skill=args.skill,
        role=args.role,
        attempted=attempted,
        require_l2=True if args.require_l2 else None,
        limit=args.limit,
    )

    rows = [
        library.learner_view(
            item,
            activity=args.activity,
            post_attempt=args.post_attempt,
        )
        for item in items
    ]

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

    if not rows:
        print("沒有符合條件的題目。")
        return 0

    for row in rows:
        difficulty = row.get("difficulty") or "—"
        attempted_text = "做過" if row["attempted"] else "未做"
        print(
            f"{row['external_id']} · {row['title']} · "
            f"{difficulty} · {attempted_text}"
        )
        print(f"  {row['canonical_url']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
