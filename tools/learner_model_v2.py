#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME_DIR = ROOT / ".apcs" / "runtime"
SIGNAL_SCHEMA = "apcs-learner-signal-v1"

VALID_BOTTLENECKS = {
    "Concept",
    "Condition",
    "Representation",
    "Strategy",
    "Complexity",
    "Implementation",
    "Syntax / API",
    "State / Index",
    "Debugging",
    "Exam Interface",
}
VALID_CONFIDENCE = {30, 60, 90}


class LearnerModelError(ValueError):
    pass


@dataclass(frozen=True)
class SkillTrackModel:
    skill_uid: str
    track: str
    evidence_count: int
    known_assistance_count: int
    assisted_count: int
    independent_a0_passes: int
    transfer_passes: int
    hint_dependence: str
    transfer_state: str


@dataclass(frozen=True)
class RepeatedBottleneck:
    skill_uid: str
    category: str
    root_cause: str
    distinct_problems: tuple[str, ...]
    occurrences: int


class LearnerSignalStore:
    """非 Evidence 的輕量操作訊號。

    只保存無法從 Attempt/Evidence 自動重建、但會改善下一步學習決策的
    少量資料。這些資料不得用來授予 mastery / readiness。
    """

    def __init__(self, runtime_dir: Path = DEFAULT_RUNTIME_DIR):
        self.path = Path(runtime_dir) / "learner_signals.jsonl"

    @staticmethod
    def _iso(value: dt.datetime | None = None) -> str:
        value = value or dt.datetime.now().astimezone()
        if value.tzinfo is None or value.utcoffset() is None:
            raise LearnerModelError("occurred_at 必須包含時區")
        return value.isoformat(timespec="seconds")

    def _append(self, row: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
            )

    def record_bottleneck(
        self,
        *,
        skill_uid: str,
        problem_id: str,
        category: str,
        root_cause: str,
        occurred_at: dt.datetime | None = None,
        source: str = "explicit",
    ) -> None:
        skill_uid = str(skill_uid or "").strip()
        problem_id = str(problem_id or "").strip()
        category = str(category or "").strip()
        root_cause = " ".join(str(root_cause or "").split())

        if not skill_uid or not problem_id or not root_cause:
            raise LearnerModelError(
                "bottleneck 需要 skill_uid、problem_id、root_cause"
            )
        if category not in VALID_BOTTLENECKS:
            raise LearnerModelError(f"未知 bottleneck category：{category}")

        self._append(
            {
                "schema_version": SIGNAL_SCHEMA,
                "type": "bottleneck",
                "occurred_at": self._iso(occurred_at),
                "skill_uid": skill_uid,
                "problem_id": problem_id,
                "category": category,
                "root_cause": root_cause,
                "source": str(source or "explicit").strip(),
            }
        )

    def record_confidence(
        self,
        *,
        skill_uid: str,
        track: str,
        confidence: int,
        activity: str,
        problem_id: str,
        occurred_at: dt.datetime | None = None,
    ) -> None:
        if confidence not in VALID_CONFIDENCE:
            raise LearnerModelError(
                "confidence 只允許 30 / 60 / 90"
            )
        if track not in {"Reading", "Implementation"}:
            raise LearnerModelError("track 不合法")

        self._append(
            {
                "schema_version": SIGNAL_SCHEMA,
                "type": "confidence",
                "occurred_at": self._iso(occurred_at),
                "skill_uid": str(skill_uid or "").strip(),
                "track": track,
                "confidence": confidence,
                "activity": str(activity or "").strip(),
                "problem_id": str(problem_id or "").strip(),
            }
        )

    def load(self) -> tuple[dict[str, Any], ...]:
        if not self.path.exists():
            return ()

        rows: list[dict[str, Any]] = []
        for number, line in enumerate(
            self.path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise LearnerModelError(
                    f"learner_signals.jsonl 第 {number} 行損壞"
                ) from exc
            self.validate_signal(row)
            rows.append(row)
        return tuple(rows)

    @staticmethod
    def validate_signal(row: dict[str, Any]) -> None:
        if not isinstance(row, dict):
            raise LearnerModelError("signal 必須是 object")
        if row.get("schema_version") != SIGNAL_SCHEMA:
            raise LearnerModelError("signal schema_version 不正確")

        kind = row.get("type")
        if kind == "bottleneck":
            required = {
                "schema_version",
                "type",
                "occurred_at",
                "skill_uid",
                "problem_id",
                "category",
                "root_cause",
                "source",
            }
            if set(row) != required:
                raise LearnerModelError("bottleneck signal schema 不一致")
            if row["category"] not in VALID_BOTTLENECKS:
                raise LearnerModelError("bottleneck category 不合法")
            if not all(
                str(row[field] or "").strip()
                for field in ("skill_uid", "problem_id", "root_cause")
            ):
                raise LearnerModelError("bottleneck signal 缺必要內容")

        elif kind == "confidence":
            required = {
                "schema_version",
                "type",
                "occurred_at",
                "skill_uid",
                "track",
                "confidence",
                "activity",
                "problem_id",
            }
            if set(row) != required:
                raise LearnerModelError("confidence signal schema 不一致")
            if row["confidence"] not in VALID_CONFIDENCE:
                raise LearnerModelError("confidence 值不合法")
            if row["track"] not in {"Reading", "Implementation"}:
                raise LearnerModelError("confidence track 不合法")
        else:
            raise LearnerModelError(f"未知 signal type：{kind!r}")

        try:
            occurred = dt.datetime.fromisoformat(row["occurred_at"])
        except (TypeError, ValueError) as exc:
            raise LearnerModelError("occurred_at 格式不合法") from exc
        if occurred.tzinfo is None or occurred.utcoffset() is None:
            raise LearnerModelError("occurred_at 必須包含時區")


def _hint_dependence(known: int, assisted: int) -> str:
    if known == 0:
        return "UNKNOWN"
    ratio = assisted / known
    if known >= 2 and ratio >= 0.60:
        return "HIGH"
    if ratio >= 0.30:
        return "MODERATE"
    return "LOW"


def derive_skill_track_models(
    envelopes: Iterable,
) -> tuple[SkillTrackModel, ...]:
    grouped: dict[tuple[str, str], dict[str, int]] = {}

    for envelope in envelopes:
        attempt = getattr(envelope, "attempt", None)
        evidence = getattr(envelope, "evidence", ())
        if attempt is None:
            # Read-only status callers may provide reduced test/dummy envelopes.
            # Such rows cannot contribute Assistance / transfer facts, so skip
            # them rather than inventing operational learner state.
            continue
        for claim in evidence:
            key = (claim.skill_uid, claim.track)
            state = grouped.setdefault(
                key,
                {
                    "evidence_count": 0,
                    "known_assistance_count": 0,
                    "assisted_count": 0,
                    "independent_a0_passes": 0,
                    "transfer_passes": 0,
                },
            )
            state["evidence_count"] += 1

            if attempt.assistance is not None:
                state["known_assistance_count"] += 1
                if attempt.assistance > 0:
                    state["assisted_count"] += 1

            strong = (
                claim.outcome == "PASS"
                and attempt.assistance == 0
                and attempt.independent is True
            )
            if strong:
                state["independent_a0_passes"] += 1
                if attempt.novelty in {"transfer", "delayed_retest"}:
                    state["transfer_passes"] += 1

    result = []
    for (skill_uid, track), state in sorted(grouped.items()):
        if state["transfer_passes"] > 0:
            transfer_state = "VERIFIED"
        elif state["independent_a0_passes"] > 0:
            transfer_state = "READY_FOR_TRANSFER"
        else:
            transfer_state = "NOT_VERIFIED"

        result.append(
            SkillTrackModel(
                skill_uid=skill_uid,
                track=track,
                evidence_count=state["evidence_count"],
                known_assistance_count=state["known_assistance_count"],
                assisted_count=state["assisted_count"],
                independent_a0_passes=state["independent_a0_passes"],
                transfer_passes=state["transfer_passes"],
                hint_dependence=_hint_dependence(
                    state["known_assistance_count"],
                    state["assisted_count"],
                ),
                transfer_state=transfer_state,
            )
        )

    return tuple(result)


def repeated_bottlenecks(
    signals: Iterable[dict[str, Any]],
) -> tuple[RepeatedBottleneck, ...]:
    groups: dict[tuple[str, str, str], dict[str, Any]] = {}

    for row in signals:
        if row.get("type") != "bottleneck":
            continue

        root = " ".join(
            str(row.get("root_cause") or "").casefold().split()
        )
        key = (
            str(row.get("skill_uid") or "").strip(),
            str(row.get("category") or "").strip(),
            root,
        )
        state = groups.setdefault(
            key,
            {"problems": set(), "occurrences": 0, "display_root": row["root_cause"]},
        )
        state["problems"].add(str(row["problem_id"]).strip())
        state["occurrences"] += 1

    result = []
    for (skill_uid, category, _), state in groups.items():
        problems = tuple(sorted(state["problems"]))
        # 同一題重複失敗不升級；至少兩個不同題目才是 durable candidate。
        if len(problems) < 2:
            continue
        result.append(
            RepeatedBottleneck(
                skill_uid=skill_uid,
                category=category,
                root_cause=state["display_root"],
                distinct_problems=problems,
                occurrences=state["occurrences"],
            )
        )

    return tuple(
        sorted(
            result,
            key=lambda item: (
                -len(item.distinct_problems),
                item.skill_uid,
                item.category,
                item.root_cause.casefold(),
            ),
        )
    )


def confidence_samples(
    signals: Iterable[dict[str, Any]],
) -> tuple[dict[str, Any], ...]:
    return tuple(
        row
        for row in signals
        if row.get("type") == "confidence"
    )


def learner_model_snapshot(
    envelopes: Iterable,
    signals: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    models = derive_skill_track_models(envelopes)
    bottlenecks = repeated_bottlenecks(signals)
    confidence = confidence_samples(signals)

    return {
        "skill_track": models,
        "hint_dependence_high": tuple(
            item
            for item in models
            if item.hint_dependence == "HIGH"
        ),
        "transfer_ready": tuple(
            item
            for item in models
            if item.transfer_state == "READY_FOR_TRANSFER"
        ),
        "transfer_verified": tuple(
            item
            for item in models
            if item.transfer_state == "VERIFIED"
        ),
        "repeated_bottlenecks": bottlenecks,
        "misconception_candidates": bottlenecks,
        "confidence_samples": confidence,
        "readiness": "NOT_ASSESSED",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="APCS v2.4 learner operational signals"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    b = sub.add_parser("bottleneck")
    b.add_argument("skill_uid")
    b.add_argument("problem_id")
    b.add_argument("category", choices=sorted(VALID_BOTTLENECKS))
    b.add_argument("root_cause")

    c = sub.add_parser("confidence")
    c.add_argument("skill_uid")
    c.add_argument("track", choices=["Reading", "Implementation"])
    c.add_argument("confidence", type=int, choices=sorted(VALID_CONFIDENCE))
    c.add_argument("activity")
    c.add_argument("problem_id")

    args = parser.parse_args(argv)
    store = LearnerSignalStore()

    if args.command == "bottleneck":
        store.record_bottleneck(
            skill_uid=args.skill_uid,
            problem_id=args.problem_id,
            category=args.category,
            root_cause=args.root_cause,
        )
        print("已記錄 bottleneck operational signal。")
    else:
        store.record_confidence(
            skill_uid=args.skill_uid,
            track=args.track,
            confidence=args.confidence,
            activity=args.activity,
            problem_id=args.problem_id,
        )
        print("已記錄 confidence sample；不影響 mastery / readiness。")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
