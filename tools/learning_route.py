"""Curriculum route planner for APCS v2.3.

This module decides the *next learning action* without pretending that route
progress equals RM/IM mastery.

A Skill becomes route-unlocked only after a strong implementation attempt:
PASS, A0-A1, independent, and Core/Transfer/Review/Mock context.  This is a
navigation signal, not a mastery award.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

try:
    from .evidence_outbox import OutboxEnvelope
    from .runtime_curriculum import PlacementContext, RuntimeCurriculum
except ImportError:
    from evidence_outbox import OutboxEnvelope
    from runtime_curriculum import PlacementContext, RuntimeCurriculum


QUALIFYING_UNLOCK_ACTIVITIES = {
    "Core Independent",
    "Transfer Challenge",
    "Review",
    "Mock",
}


@dataclass(frozen=True)
class RouteSkillState:
    skill_uid: str
    name: str
    unit: str
    path_stage: str
    path_order: int | float
    relevance: str
    prerequisites: tuple[str, ...]
    status: str
    missing_prerequisites: tuple[str, ...]


@dataclass(frozen=True)
class LearningAction:
    skill: RouteSkillState
    placement: PlacementContext | None
    reason: str


def _normalize_relevance(
    value: str,
) -> str:
    raw = str(value or "").strip().lower()

    if raw in {
        "required",
        "required-core",
        "core",
    }:
        return "required"

    if raw == "bridge":
        return "bridge"

    if raw == "supporting":
        return "supporting"

    if raw in {
        "extension",
        "optional",
        "not required",
        "not for 3+3",
    }:
        return "excluded"

    return "supporting"


def target_priority(
    relevance: str,
    *,
    target: str,
) -> int | None:
    relevance = _normalize_relevance(
        relevance
    )

    if target == "3+3":
        return {
            "required": 0,
            "supporting": 1,
        }.get(relevance)

    return {
        "required": 0,
        "bridge": 1,
        "supporting": 2,
    }.get(relevance)


def route_unlocks(
    envelopes: Iterable[
        OutboxEnvelope
    ],
) -> set[str]:
    """Return Skills with strong enough evidence to unlock downstream study.

    This deliberately does not claim IM3.  Complexity/correctness explanation
    and the full MEAS gate remain separate mastery concerns.
    """

    result: set[str] = set()

    for envelope in envelopes:
        attempt = envelope.attempt

        if (
            attempt.assistance is None
            or attempt.assistance > 1
            or attempt.independent is not True
            or attempt.activity
            not in QUALIFYING_UNLOCK_ACTIVITIES
            or attempt.novelty
            == "same_problem_repeat"
        ):
            continue

        for claim in envelope.evidence:
            if (
                claim.track
                != "Implementation"
                or claim.outcome
                != "PASS"
            ):
                continue

            result.add(
                claim.skill_uid
            )

    return result


def evidenced_skills(
    envelopes: Iterable[
        OutboxEnvelope
    ],
) -> set[str]:
    return {
        claim.skill_uid
        for envelope in envelopes
        for claim in envelope.evidence
        if claim.track
        == "Implementation"
    }


def attempted_problem_ids(
    envelopes: Iterable[
        OutboxEnvelope
    ],
    *,
    skill_uid: str,
) -> set[str]:
    result: set[str] = set()

    for envelope in envelopes:
        if not any(
            claim.skill_uid
            == skill_uid
            and claim.track
            == "Implementation"
            for claim in envelope.evidence
        ):
            continue

        result.add(
            envelope.attempt
            .problem_id
            .strip()
            .lower()
        )

    return result


def route_states(
    curriculum: RuntimeCurriculum,
    envelopes: Iterable[
        OutboxEnvelope
    ],
    *,
    target: str,
) -> tuple[
    RouteSkillState,
    ...,
]:
    data = curriculum.load()
    envelopes = tuple(
        envelopes
    )

    unlocked = route_unlocks(
        envelopes
    )
    evidenced = evidenced_skills(
        envelopes
    )

    result = []

    for row in sorted(
        data.get("skills") or [],
        key=lambda item: (
            item.get(
                "path_order",
                10**9,
            ),
            item.get(
                "uid",
                "",
            ),
        ),
    ):
        uid = str(
            row.get(
                "uid",
                "",
            )
        ).strip()

        if not uid:
            continue

        relevance_map = (
            row.get("relevance")
            or {}
        )
        relevance = str(
            relevance_map.get(
                target,
                "",
            )
        ).strip()

        prereqs = tuple(
            str(item).strip()
            for item in (
                row.get(
                    "prerequisites"
                )
                or []
            )
            if str(item).strip()
        )

        missing = tuple(
            item
            for item in prereqs
            if item not in unlocked
        )

        if uid in unlocked:
            status = "ROUTE_UNLOCKED"
        elif missing:
            status = "LOCKED"
        elif uid in evidenced:
            status = "PRACTICE"
        else:
            status = "READY"

        result.append(
            RouteSkillState(
                skill_uid=uid,
                name=str(
                    row.get(
                        "name",
                        "",
                    )
                ).strip(),
                unit=str(
                    row.get(
                        "unit",
                        "",
                    )
                ).strip(),
                path_stage=str(
                    row.get(
                        "path_stage",
                        "",
                    )
                ).strip(),
                path_order=row.get(
                    "path_order",
                    10**9,
                ),
                relevance=relevance,
                prerequisites=prereqs,
                status=status,
                missing_prerequisites=missing,
            )
        )

    return tuple(result)


def _placement_for_action(
    curriculum: RuntimeCurriculum,
    envelopes: tuple[
        OutboxEnvelope,
        ...,
    ],
    skill: RouteSkillState,
) -> PlacementContext | None:
    placements = list(
        curriculum.placements_for_skill(
            skill.skill_uid
        )
    )

    if not placements:
        return None

    attempted = attempted_problem_ids(
        envelopes,
        skill_uid=skill.skill_uid,
    )

    if skill.status == "READY":
        role_rank = {
            "Worked Example": 0,
            "Guided Drill": 1,
            "Core Independent": 2,
            "Transfer Challenge": 3,
            "Mock": 4,
        }
    else:
        role_rank = {
            "Core Independent": 0,
            "Transfer Challenge": 1,
            "Guided Drill": 2,
            "Worked Example": 3,
            "Mock": 4,
        }

    return min(
        placements,
        key=lambda item: (
            1
            if item.problem_id.lower()
            in attempted
            else 0,
            role_rank.get(
                item.role,
                9,
            ),
            (
                float("inf")
                if item.lesson_order
                is None
                else item.lesson_order
            ),
            item.placement_uid,
        ),
    )


def next_learning_action(
    curriculum: RuntimeCurriculum,
    envelopes: Iterable[
        OutboxEnvelope
    ],
    *,
    target: str = "3+3",
) -> LearningAction | None:
    """Choose one learner-facing new-learning/practice action.

    Continue an already-started PRACTICE Skill before opening another READY
    Skill at the same/higher route priority.
    """

    envelopes = tuple(
        envelopes
    )
    states = route_states(
        curriculum,
        envelopes,
        target=target,
    )

    candidates = []

    for state in states:
        priority = target_priority(
            state.relevance,
            target=target,
        )

        if (
            priority is None
            or state.status
            not in {
                "PRACTICE",
                "READY",
            }
        ):
            continue

        phase_rank = (
            0
            if state.status
            == "PRACTICE"
            else 1
        )

        candidates.append(
            (
                priority,
                phase_rank,
                state.path_order,
                state.skill_uid,
                state,
            )
        )

    if not candidates:
        return None

    _, _, _, _, skill = min(
        candidates
    )

    placement = _placement_for_action(
        curriculum,
        envelopes,
        skill,
    )

    reason = (
        "已有練習證據，但尚未形成 route-unlock 強證據；"
        "先完成獨立 Core / Transfer，再開下一個 Skill。"
        if skill.status
        == "PRACTICE"
        else
        "前置 route-unlock 條件已成立；開始下一個 curriculum Skill。"
    )

    return LearningAction(
        skill=skill,
        placement=placement,
        reason=reason,
    )
