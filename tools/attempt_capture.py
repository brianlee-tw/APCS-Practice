"""Pure attempt -> durable outbox conversion for APCS v2.3."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

try:
    from .evidence_outbox import (
        OutboxEnvelope,
        build_envelope,
    )
    from .runtime_curriculum import (
        PlacementContext,
        evidence_activity,
    )
except ImportError:
    from evidence_outbox import (
        OutboxEnvelope,
        build_envelope,
    )
    from runtime_curriculum import (
        PlacementContext,
        evidence_activity,
    )


def language_from_path(path: str | Path) -> str:
    suffix = Path(path).suffix.lower()

    if suffix == ".cpp":
        return "cpp"

    if suffix == ".py":
        return "python"

    return suffix.lstrip(".") or "unknown"


def evidence_outcome_from_judge(
    judge_result: str,
) -> str:
    return (
        "PASS"
        if str(judge_result).upper() == "AC"
        else "FAIL"
    )


def build_attempt_envelope(
    *,
    action: str,
    problem_id: str,
    problem_path: str | Path,
    judge_result: str,
    finished_at: dt.datetime,
    minutes: int | None,
    assistance: int | None,
    independent: bool | None,
    novelty: str | None,
    placement: PlacementContext | None,
    note: str = "",
) -> OutboxEnvelope:
    activity = None
    evidence = []
    pb_uid = None
    placement_uid = None

    if placement is not None:
        pb_uid = placement.pb_uid
        placement_uid = (
            placement.placement_uid
        )
        activity = evidence_activity(
            action=action,
            placement=placement,
        )

        # Published Placement gives an explicit primary Skill.  Supporting
        # Skills are not automatically promoted to Evidence.
        if activity is not None:
            evidence.append(
                (
                    placement.primary_skill.uid,
                    "Implementation",
                    evidence_outcome_from_judge(
                        judge_result
                    ),
                    (
                        f"placement={placement.placement_uid}; "
                        f"role={placement.role}"
                    ),
                )
            )

    return build_envelope(
        problem_id=problem_id,
        pb_uid=pb_uid,
        placement_uid=placement_uid,
        started_at=None,
        finished_at=finished_at,
        language=language_from_path(
            problem_path
        ),
        judge_result=str(
            judge_result
        ).upper(),
        assistance=assistance,
        independent=independent,
        attempt_count=None,
        active_minutes=minutes,
        novelty=novelty,
        activity=activity,
        note=note,
        evidence=evidence,
    )
