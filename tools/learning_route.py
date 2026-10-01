"""Evidence-driven new-learning route for APCS v2.3 Gate B4.

This module deliberately separates three concepts:

1. durable Evidence facts;
2. a conservative MEAS-v1 lower bound for each Skill x Track;
3. the B4 *start threshold* used only to decide whether a dependent Skill may
   begin.

The start threshold is not RR/IR readiness and is not a replacement mastery
system.  Full readiness remains governed by MEAS-v1 required gates,
benchmarks, and critical-gap rules.

B4 policy v1:
- a prerequisite Skill is start-ready when at least one applicable Track has
  evidence supporting Level 2 or higher;
- direct target route contains Required Skills plus their transitive
  prerequisites;
- Supporting / Bridge / Extension Skills never become blockers unless they are
  actual prerequisites of a Required Skill;
- current Learning work (Level 1) is completed before opening another Ready
  Skill;
- new Skills use Guided practice first when available; Level-1 Skills prefer
  Core Independent practice;
- relation order, legacy tags, adaptive-memory retrievability, and manual
  Notion Skill Status are never used as mastery evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

try:
    from .evidence_outbox import OutboxEnvelope
    from .runtime_curriculum import (
        PlacementContext,
        RuntimeCurriculum,
        SkillContext,
    )
except ImportError:
    from evidence_outbox import OutboxEnvelope
    from runtime_curriculum import (
        PlacementContext,
        RuntimeCurriculum,
        SkillContext,
    )


POLICY_VERSION = "b4-start-v1"
START_LEVEL = 2


@dataclass(frozen=True)
class SkillEvidenceLowerBound:
    skill_uid: str
    reading_level: int = 0
    implementation_level: int = 0
    evidence_count: int = 0

    @property
    def start_level(self) -> int:
        return max(
            self.reading_level,
            self.implementation_level,
        )

    @property
    def start_ready(self) -> bool:
        return self.start_level >= START_LEVEL

    def label(self) -> str:
        parts = []

        if self.reading_level:
            parts.append(
                f"RM≥{self.reading_level}"
            )

        if self.implementation_level:
            parts.append(
                f"IM≥{self.implementation_level}"
            )

        return " / ".join(parts) if parts else "尚無 Gate Evidence"


@dataclass(frozen=True)
class PrerequisiteState:
    skill_uid: str
    name: str
    reading_level: int
    implementation_level: int
    satisfied: bool

    @property
    def evidence_label(self) -> str:
        parts = []

        if self.reading_level:
            parts.append(
                f"RM≥{self.reading_level}"
            )

        if self.implementation_level:
            parts.append(
                f"IM≥{self.implementation_level}"
            )

        return " / ".join(parts) if parts else "無有效 Evidence"


@dataclass(frozen=True)
class NewLearningPlan:
    target: str
    policy_version: str
    start_level: int
    route_skill_uids: tuple[str, ...]
    skill: SkillContext | None
    skill_evidence: SkillEvidenceLowerBound | None
    prerequisites: tuple[PrerequisiteState, ...]
    placement: PlacementContext | None
    status: str
    why_now: str
    blocked_skill: SkillContext | None
    blocked_by: tuple[PrerequisiteState, ...]
    route_complete: bool


def _novelty_allows_standard(
    novelty: str | None,
) -> bool:
    return novelty != "same_problem_repeat"


def _claim_lower_bound(
    envelope: OutboxEnvelope,
    *,
    track: str,
    outcome: str,
) -> int:
    """Return the strongest MEAS level this one event can safely support.

    This is a lower-bound projection, not a complete RM/IM evaluator.  B4 only
    needs the Level-2 start threshold.  Level 3/4 are retained where the
    outbox contains all observable facts needed by the corresponding MEAS
    pattern; Level 5 is intentionally not inferred here because it requires
    cross-date portfolio composition.
    """

    if outcome != "PASS":
        return 0

    attempt = envelope.attempt
    assistance = attempt.assistance
    activity = attempt.activity
    novelty = attempt.novelty

    if assistance is None or activity is None:
        return 0

    # Worked examples are learning material, not independent Gate evidence.
    if activity == "Worked Example":
        return 0

    if track == "Reading":
        level = 0

        if (
            assistance <= 3
            and activity
            in {
                "Concept Check",
                "Guided Drill",
                "Core Independent",
                "Transfer Challenge",
                "Review",
                "Diagnostic",
                "Mock",
            }
        ):
            level = 1

        if (
            assistance <= 2
            and _novelty_allows_standard(
                novelty
            )
            and activity
            in {
                "Guided Drill",
                "Core Independent",
                "Transfer Challenge",
                "Review",
                "Mock",
            }
        ):
            level = max(level, 2)

        if (
            assistance <= 1
            and attempt.independent is True
            and novelty
            not in {
                "seen",
                "same_problem_repeat",
            }
            and activity
            == "Core Independent"
        ):
            level = max(level, 3)

        if (
            assistance <= 1
            and attempt.independent is True
            and novelty == "transfer"
            and activity
            == "Transfer Challenge"
        ):
            level = max(level, 4)

        return level

    if track == "Implementation":
        level = 0

        if (
            assistance <= 3
            and activity
            in {
                "Guided Drill",
                "Core Independent",
                "Transfer Challenge",
                "Review",
                "Diagnostic",
                "Mock",
            }
        ):
            level = 1

        # Standard Implementation evidence must correspond to a successful
        # executable / judge outcome, not only a self-report.
        if (
            assistance <= 2
            and envelope.attempt.judge_result
            == "AC"
            and _novelty_allows_standard(
                novelty
            )
            and activity
            in {
                "Guided Drill",
                "Core Independent",
                "Transfer Challenge",
                "Review",
                "Mock",
            }
        ):
            level = max(level, 2)

        if (
            assistance <= 1
            and envelope.attempt.judge_result
            == "AC"
            and attempt.independent is True
            and novelty
            not in {
                "seen",
                "same_problem_repeat",
            }
            and activity
            == "Core Independent"
        ):
            level = max(level, 3)

        if (
            assistance <= 1
            and envelope.attempt.judge_result
            == "AC"
            and attempt.independent is True
            and novelty == "transfer"
            and activity
            == "Transfer Challenge"
        ):
            level = max(level, 4)

        return level

    return 0


def derive_evidence_lower_bounds(
    envelopes: Iterable[OutboxEnvelope],
) -> dict[str, SkillEvidenceLowerBound]:
    levels: dict[str, dict[str, int]] = {}
    counts: dict[str, int] = {}

    for envelope in envelopes:
        for claim in envelope.evidence:
            skill_uid = str(
                claim.skill_uid or ""
            ).strip()

            if not skill_uid:
                continue

            counts[skill_uid] = (
                counts.get(skill_uid, 0)
                + 1
            )

            row = levels.setdefault(
                skill_uid,
                {
                    "Reading": 0,
                    "Implementation": 0,
                },
            )

            candidate = _claim_lower_bound(
                envelope,
                track=claim.track,
                outcome=claim.outcome,
            )

            row[claim.track] = max(
                row.get(claim.track, 0),
                candidate,
            )

    return {
        skill_uid: SkillEvidenceLowerBound(
            skill_uid=skill_uid,
            reading_level=row.get(
                "Reading",
                0,
            ),
            implementation_level=row.get(
                "Implementation",
                0,
            ),
            evidence_count=counts.get(
                skill_uid,
                0,
            ),
        )
        for skill_uid, row
        in levels.items()
    }


def _empty_evidence(
    skill_uid: str,
) -> SkillEvidenceLowerBound:
    return SkillEvidenceLowerBound(
        skill_uid=skill_uid
    )


def _is_required(
    context: SkillContext,
    *,
    target: str,
) -> bool:
    raw = (
        context.relevance_55
        if target == "5+5"
        else context.relevance_33
    )

    value = str(
        raw or ""
    ).strip().lower()

    return value in {
        "required",
        "required-core",
        "critical",
        "core",
    }


def _route_closure(
    contexts: tuple[SkillContext, ...],
    *,
    target: str,
) -> tuple[str, ...]:
    by_uid = {
        item.uid: item
        for item in contexts
    }

    included = {
        item.uid
        for item in contexts
        if _is_required(
            item,
            target=target,
        )
    }

    pending = list(included)

    while pending:
        uid = pending.pop()
        item = by_uid[uid]

        for prerequisite in item.prerequisites:
            if prerequisite in included:
                continue

            if prerequisite not in by_uid:
                # The compiler normally prevents this.  Keep route selection
                # fail-closed if a malformed runtime snapshot is injected.
                raise ValueError(
                    f"unknown prerequisite {prerequisite} for {uid}"
                )

            included.add(
                prerequisite
            )
            pending.append(
                prerequisite
            )

    return tuple(
        item.uid
        for item in contexts
        if item.uid in included
    )


def _prerequisite_states(
    context: SkillContext,
    *,
    contexts_by_uid: dict[str, SkillContext],
    evidence: dict[
        str,
        SkillEvidenceLowerBound,
    ],
) -> tuple[PrerequisiteState, ...]:
    result = []

    for uid in context.prerequisites:
        prereq = contexts_by_uid[uid]
        state = evidence.get(
            uid,
            _empty_evidence(uid),
        )

        result.append(
            PrerequisiteState(
                skill_uid=uid,
                name=prereq.name,
                reading_level=(
                    state.reading_level
                ),
                implementation_level=(
                    state.implementation_level
                ),
                satisfied=(
                    state.start_ready
                ),
            )
        )

    return tuple(result)


def _attempted_pb_uids(
    envelopes: Iterable[OutboxEnvelope],
) -> set[str]:
    return {
        str(
            envelope.attempt.pb_uid
            or ""
        ).strip()
        for envelope in envelopes
        if str(
            envelope.attempt.pb_uid
            or ""
        ).strip()
    }


def _new_learning_placement(
    curriculum: RuntimeCurriculum,
    *,
    skill_uid: str,
    current_level: int,
    attempted_pb_uids: set[str],
) -> PlacementContext | None:
    placements = list(
        curriculum
        .placements_for_skill(
            skill_uid
        )
    )

    if not placements:
        return None

    role_rank = (
        {
            "Core Independent": 0,
            "Guided Drill": 1,
            "Worked Example": 2,
            "Transfer Challenge": 3,
            "Mock": 4,
        }
        if current_level >= 1
        else {
            "Guided Drill": 0,
            "Worked Example": 1,
            "Core Independent": 2,
            "Transfer Challenge": 3,
            "Mock": 4,
        }
    )

    placements.sort(
        key=lambda item: (
            item.pb_uid
            in attempted_pb_uids,
            role_rank.get(
                item.role,
                99,
            ),
            (
                float("inf")
                if item.lesson_order
                is None
                else item.lesson_order
            ),
            item.placement_uid,
        )
    )

    return placements[0]


def select_new_learning_plan(
    curriculum: RuntimeCurriculum,
    envelopes: Iterable[OutboxEnvelope],
    *,
    target: str,
) -> NewLearningPlan:
    envelopes = tuple(
        envelopes
    )
    contexts = (
        curriculum.skill_contexts()
    )
    contexts_by_uid = {
        item.uid: item
        for item in contexts
    }

    route_skill_uids = (
        _route_closure(
            contexts,
            target=target,
        )
    )

    evidence = (
        derive_evidence_lower_bounds(
            envelopes
        )
    )

    def state_for(
        uid: str,
    ) -> SkillEvidenceLowerBound:
        return evidence.get(
            uid,
            _empty_evidence(uid),
        )

    ready = []
    blocked = []

    for uid in route_skill_uids:
        context = contexts_by_uid[
            uid
        ]
        current = state_for(uid)

        if current.start_ready:
            continue

        prereqs = (
            _prerequisite_states(
                context,
                contexts_by_uid=(
                    contexts_by_uid
                ),
                evidence=evidence,
            )
        )
        missing = tuple(
            item
            for item in prereqs
            if not item.satisfied
        )

        if missing:
            blocked.append(
                (
                    context,
                    current,
                    prereqs,
                    missing,
                )
            )
        else:
            ready.append(
                (
                    context,
                    current,
                    prereqs,
                )
            )

    if ready:
        # Current Learning / Practice work comes before opening a fresh Ready
        # node.  Within the same status, Path Order is deterministic.
        ready.sort(
            key=lambda item: (
                (
                    0
                    if item[1].start_level
                    > 0
                    else 1
                ),
                item[0].path_order,
                item[0].uid,
            )
        )

        context, current, prereqs = (
            ready[0]
        )

        placement = (
            _new_learning_placement(
                curriculum,
                skill_uid=context.uid,
                current_level=(
                    current.start_level
                ),
                attempted_pb_uids=(
                    _attempted_pb_uids(
                        envelopes
                    )
                ),
            )
        )

        if current.start_level > 0:
            status = "Learning"
            why_now = (
                f"已有 {current.label()}，"
                f"但尚未達 B4 Level-{START_LEVEL} start threshold；"
                "先完成目前 Skill，再開下一個 prerequisite node。"
            )
        elif prereqs:
            status = "Ready"
            why_now = (
                f"{target} Required 路線中目前最前的 Ready Skill；"
                "所有 prerequisite 都已有 Level-2+ Evidence。"
            )
        else:
            status = "Ready"
            why_now = (
                f"{target} Required 路線起點；"
                "此 Skill 沒有 prerequisite。"
            )

        return NewLearningPlan(
            target=target,
            policy_version=(
                POLICY_VERSION
            ),
            start_level=START_LEVEL,
            route_skill_uids=(
                route_skill_uids
            ),
            skill=context,
            skill_evidence=current,
            prerequisites=prereqs,
            placement=placement,
            status=status,
            why_now=why_now,
            blocked_skill=None,
            blocked_by=(),
            route_complete=False,
        )

    if blocked:
        blocked.sort(
            key=lambda item: (
                item[0].path_order,
                item[0].uid,
            )
        )

        context, _, prereqs, missing = (
            blocked[0]
        )

        details = "; ".join(
            (
                f"{item.skill_uid} "
                f"({item.evidence_label})"
            )
            for item in missing
        )

        return NewLearningPlan(
            target=target,
            policy_version=(
                POLICY_VERSION
            ),
            start_level=START_LEVEL,
            route_skill_uids=(
                route_skill_uids
            ),
            skill=None,
            skill_evidence=None,
            prerequisites=(),
            placement=None,
            status="Blocked",
            why_now=(
                f"{context.uid} 尚未可開始；"
                f"prerequisite evidence 不足：{details}"
            ),
            blocked_skill=context,
            blocked_by=missing,
            route_complete=False,
        )

    return NewLearningPlan(
        target=target,
        policy_version=POLICY_VERSION,
        start_level=START_LEVEL,
        route_skill_uids=(
            route_skill_uids
        ),
        skill=None,
        skill_evidence=None,
        prerequisites=(),
        placement=None,
        status="Route Start Complete",
        why_now=(
            f"{target} Required route 的所有 Skill "
            f"都已達 B4 Level-{START_LEVEL} start threshold；"
            "這不代表 RR/IR readiness PASS。"
        ),
        blocked_skill=None,
        blocked_by=(),
        route_complete=True,
    )
