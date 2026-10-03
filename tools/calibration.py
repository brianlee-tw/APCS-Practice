#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

try:
    from .adaptive_memory import (
        MemoryPolicy,
        MemoryState,
        retrievability,
        update_memory,
    )
    from .evidence_outbox import (
        EvidenceOutbox,
        EvidenceOutboxError,
        memory_evidence,
    )
except ImportError:
    from adaptive_memory import (
        MemoryPolicy,
        MemoryState,
        retrievability,
        update_memory,
    )
    from evidence_outbox import (
        EvidenceOutbox,
        EvidenceOutboxError,
        memory_evidence,
    )


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME_DIR = ROOT / ".apcs" / "runtime"

BASELINE_VERSION = "apcs-memory-v0.1"
FLAG_SCHEMA = "apcs-memory-policy-flag-v1"

CALIBRATION_NOVELTY = {
    "delayed_retest",
    "transfer",
}
OUTCOME_SCORE = {
    "PASS": 1.0,
    "PARTIAL": 0.5,
    "FAIL": 0.0,
}

MIN_SAMPLES = 20
MIN_SKILL_TRACKS = 5
MIN_DATES = 4

BASELINE_POLICY = MemoryPolicy()
POLICY_REGISTRY: dict[str, MemoryPolicy] = {
    BASELINE_VERSION: BASELINE_POLICY,
}


class CalibrationError(ValueError):
    pass


@dataclass(frozen=True)
class CalibrationSample:
    policy_version: str
    skill_uid: str
    track: str
    occurred_on: str
    novelty: str
    predicted_retrievability: float
    actual_score: float
    outcome: str


@dataclass(frozen=True)
class CalibrationReport:
    policy_version: str
    status: str
    sample_count: int
    skill_track_count: int
    date_count: int
    skipped_incomplete_envelopes: int
    brier_score: float | None
    mean_absolute_error: float | None


def _ordered_envelopes(envelopes: Iterable) -> list:
    return sorted(
        envelopes,
        key=lambda envelope: (
            envelope.attempt.finished_at,
            envelope.writeback_id,
        ),
    )


def replay_policy(
    envelopes: Iterable,
    *,
    policy: MemoryPolicy = BASELINE_POLICY,
) -> tuple[tuple[CalibrationSample, ...], int]:
    """用歷史 Evidence 從零重播，不改任何 production state。"""

    states: dict[tuple[str, str], MemoryState] = {}
    samples: list[CalibrationSample] = []
    skipped = 0

    for envelope in _ordered_envelopes(envelopes):
        try:
            evidence_rows = memory_evidence(envelope)
        except EvidenceOutboxError:
            skipped += 1
            continue

        for evidence in evidence_rows:
            key = (
                evidence.skill_uid,
                evidence.track,
            )
            before = states.get(key)

            if before is not None:
                elapsed_days = (
                    evidence.occurred_on
                    - before.last_evidence_on
                ).days

                if (
                    evidence.novelty in CALIBRATION_NOVELTY
                    and elapsed_days >= 1
                ):
                    samples.append(
                        CalibrationSample(
                            policy_version=policy.version,
                            skill_uid=evidence.skill_uid,
                            track=evidence.track,
                            occurred_on=evidence.occurred_on.isoformat(),
                            novelty=evidence.novelty,
                            predicted_retrievability=retrievability(
                                before,
                                evidence.occurred_on,
                            ),
                            actual_score=OUTCOME_SCORE[
                                evidence.outcome
                            ],
                            outcome=evidence.outcome,
                        )
                    )

            states[key] = update_memory(
                before,
                evidence,
                policy=policy,
            )

    return tuple(samples), skipped


def calibration_report(
    envelopes: Iterable,
    *,
    policy: MemoryPolicy = BASELINE_POLICY,
) -> CalibrationReport:
    samples, skipped = replay_policy(
        envelopes,
        policy=policy,
    )

    keys = {
        (sample.skill_uid, sample.track)
        for sample in samples
    }
    dates = {
        sample.occurred_on
        for sample in samples
    }

    enough = (
        len(samples) >= MIN_SAMPLES
        and len(keys) >= MIN_SKILL_TRACKS
        and len(dates) >= MIN_DATES
    )

    if samples:
        brier = sum(
            (
                sample.predicted_retrievability
                - sample.actual_score
            )
            ** 2
            for sample in samples
        ) / len(samples)
        mae = sum(
            abs(
                sample.predicted_retrievability
                - sample.actual_score
            )
            for sample in samples
        ) / len(samples)
    else:
        brier = None
        mae = None

    return CalibrationReport(
        policy_version=policy.version,
        status=(
            "SUFFICIENT_FOR_C9_ANALYSIS"
            if enough
            else "INSUFFICIENT_DATA"
        ),
        sample_count=len(samples),
        skill_track_count=len(keys),
        date_count=len(dates),
        skipped_incomplete_envelopes=skipped,
        brier_score=brier,
        mean_absolute_error=mae,
    )


def compare_policies(
    envelopes: Iterable,
    policies: Iterable[MemoryPolicy],
) -> dict[str, Any]:
    reports = tuple(
        calibration_report(
            envelopes,
            policy=policy,
        )
        for policy in policies
    )

    # C7 只提供 comparison infrastructure。即使資料量足夠，
    # 也不在這裡自動選 winner 或切換 production policy。
    return {
        "reports": reports,
        "all_sufficient": bool(reports)
        and all(
            report.status
            == "SUFFICIENT_FOR_C9_ANALYSIS"
            for report in reports
        ),
        "decision": "DEFER_TO_C9",
        "selected_policy": None,
    }


class MemoryPolicyFlag:
    """版本化 memory policy feature flag；baseline 可隨時回退。"""

    def __init__(
        self,
        runtime_dir: Path = DEFAULT_RUNTIME_DIR,
        *,
        registry: Mapping[str, MemoryPolicy] | None = None,
    ):
        self.path = (
            Path(runtime_dir)
            / "memory_policy_flag.json"
        )
        self.registry = dict(
            registry
            if registry is not None
            else POLICY_REGISTRY
        )

    def _default(self) -> dict[str, Any]:
        return {
            "schema_version": FLAG_SCHEMA,
            "active_policy": BASELINE_VERSION,
        }

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._default()

        try:
            data = json.loads(
                self.path.read_text(
                    encoding="utf-8"
                )
            )
        except (
            OSError,
            json.JSONDecodeError,
        ) as exc:
            raise CalibrationError(
                f"memory policy flag 無法讀取：{exc}"
            ) from exc

        if (
            not isinstance(data, dict)
            or set(data)
            != {
                "schema_version",
                "active_policy",
            }
            or data.get("schema_version")
            != FLAG_SCHEMA
        ):
            raise CalibrationError(
                "memory policy flag schema 不一致"
            )

        version = str(
            data.get("active_policy") or ""
        ).strip()
        if version not in self.registry:
            raise CalibrationError(
                f"未知 memory policy：{version}"
            )

        return data

    def resolve(self) -> MemoryPolicy:
        version = self.load()["active_policy"]
        return self.registry[version]

    def set_active(
        self,
        version: str,
    ) -> MemoryPolicy:
        version = str(version or "").strip()
        if version not in self.registry:
            raise CalibrationError(
                f"不能啟用未註冊 policy：{version}"
            )

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        payload = {
            "schema_version": FLAG_SCHEMA,
            "active_policy": version,
        }
        temp = self.path.with_name(
            self.path.name + ".tmp"
        )
        try:
            temp.write_text(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            temp.replace(self.path)
        finally:
            temp.unlink(missing_ok=True)

        return self.registry[version]

    def rollback(self) -> MemoryPolicy:
        return self.set_active(
            BASELINE_VERSION
        )


def resolve_memory_policy(
    runtime_dir: Path = DEFAULT_RUNTIME_DIR,
) -> MemoryPolicy:
    return MemoryPolicyFlag(
        runtime_dir
    ).resolve()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="APCS v2.4 記憶校準基礎設施"
    )
    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )
    sub.add_parser("report")
    sub.add_parser("flag")
    sub.add_parser("rollback")
    args = parser.parse_args(argv)

    if args.command == "report":
        outbox = EvidenceOutbox(
            DEFAULT_RUNTIME_DIR
        )
        report = calibration_report(
            outbox.all_envelopes()
        )
        print(
            json.dumps(
                asdict(report),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    flag = MemoryPolicyFlag()
    if args.command == "rollback":
        policy = flag.rollback()
        print(
            f"Memory policy 已回退：{policy.version}"
        )
        return 0

    policy = flag.resolve()
    print(
        f"Active memory policy：{policy.version}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
