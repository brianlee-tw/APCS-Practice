"""Adaptive Skill x Track memory model for APCS v2.3.

This module is intentionally:
- deterministic;
- interpretable;
- calibration-friendly;
- workload-aware.

It is inspired by stability/retrievability models used in modern spaced
repetition, but does not copy flashcard-trained parameters into programming
practice.  The defaults are priors and are expected to be calibrated from the
learner's own evidence history after sufficient real use.
"""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass, replace
from typing import Iterable


VALID_OUTCOMES = {"PASS", "PARTIAL", "FAIL"}
VALID_NOVELTY = {
    "new",
    "seen",
    "delayed_retest",
    "transfer",
    "mixed",
    "same_problem_repeat",
}
VALID_IMPORTANCE = {
    "current_required",
    "required",
    "supporting",
    "extension",
}


@dataclass(frozen=True)
class MemoryPolicy:
    """Versioned prior for Skill x Track memory maintenance."""

    version: str = "apcs-memory-v0.1"
    target_retention: float = 0.88
    min_stability_days: float = 0.5
    max_stability_days: float = 1095.0
    review_fraction: float = 0.30
    review_fraction_max: float = 0.35
    min_new_learning_fraction: float = 0.60

    def __post_init__(self) -> None:
        if not 0.5 < self.target_retention < 0.99:
            raise ValueError("target_retention must be between 0.5 and 0.99")
        if not 0 < self.min_stability_days <= self.max_stability_days:
            raise ValueError("invalid stability bounds")
        if not 0 < self.review_fraction <= self.review_fraction_max < 1:
            raise ValueError("invalid review fractions")
        if not 0 < self.min_new_learning_fraction < 1:
            raise ValueError("invalid new-learning fraction")
        if self.review_fraction_max + self.min_new_learning_fraction > 1:
            raise ValueError(
                "review max + protected new-learning fraction cannot exceed 1"
            )


@dataclass(frozen=True)
class Evidence:
    skill_uid: str
    track: str
    occurred_on: dt.date
    outcome: str
    assistance: int = 0
    independent: bool = True
    novelty: str = "new"
    timed: bool = False
    problem_id: str | None = None

    def __post_init__(self) -> None:
        if self.outcome not in VALID_OUTCOMES:
            raise ValueError(f"invalid outcome={self.outcome}")
        if self.novelty not in VALID_NOVELTY:
            raise ValueError(f"invalid novelty={self.novelty}")
        if not 0 <= self.assistance <= 5:
            raise ValueError("assistance must be A0-A5 / integer 0-5")
        if not self.skill_uid.strip():
            raise ValueError("skill_uid is required")
        if not self.track.strip():
            raise ValueError("track is required")


@dataclass(frozen=True)
class MemoryState:
    skill_uid: str
    track: str
    stability_days: float
    last_evidence_on: dt.date
    evidence_count: int = 0
    successful_retrievals: int = 0
    lapses: int = 0
    last_outcome: str = "PASS"
    policy_version: str = "apcs-memory-v0.1"


@dataclass(frozen=True)
class ReviewCandidate:
    skill_uid: str
    track: str
    retrievability: float
    due_on: dt.date
    estimated_minutes: int
    importance: str = "supporting"
    recent_failure: bool = False

    def __post_init__(self) -> None:
        if self.importance not in VALID_IMPORTANCE:
            raise ValueError(f"invalid importance={self.importance}")
        if not 0 <= self.retrievability <= 1:
            raise ValueError("retrievability must be in [0, 1]")
        if self.estimated_minutes <= 0:
            raise ValueError("estimated_minutes must be positive")


@dataclass(frozen=True)
class ReviewPlan:
    budget_minutes: int
    selected: tuple[ReviewCandidate, ...]
    deferred: tuple[ReviewCandidate, ...]

    @property
    def selected_minutes(self) -> int:
        return sum(item.estimated_minutes for item in self.selected)


def retrievability(
    state: MemoryState,
    on_date: dt.date,
) -> float:
    """Estimate recall probability using an interpretable decay curve.

    Stability is defined as the elapsed time at which estimated recall is 90%.
    This mirrors the common DSR/FSRS interpretation while keeping the model
    intentionally simple until enough APCS-specific learner data exists.
    """

    elapsed = max(
        0.0,
        float((on_date - state.last_evidence_on).days),
    )
    stability = max(1e-9, state.stability_days)
    return float(0.9 ** (elapsed / stability))


def interval_for_retention(
    stability_days: float,
    target_retention: float,
) -> float:
    if not 0 < target_retention < 1:
        raise ValueError("target_retention must be in (0, 1)")
    if stability_days <= 0:
        raise ValueError("stability_days must be positive")

    return stability_days * (
        math.log(target_retention) / math.log(0.9)
    )


def next_due_on(
    state: MemoryState,
    *,
    policy: MemoryPolicy = MemoryPolicy(),
) -> dt.date:
    interval = interval_for_retention(
        state.stability_days,
        policy.target_retention,
    )
    days = max(1, int(math.ceil(interval)))
    return state.last_evidence_on + dt.timedelta(days=days)


def _evidence_strength(evidence: Evidence, elapsed_days: float) -> float:
    """Return an interpretable 0..1 evidence-quality weight."""

    outcome_factor = {
        "PASS": 1.0,
        "PARTIAL": 0.45,
        "FAIL": 0.0,
    }[evidence.outcome]

    assistance_factor = {
        0: 1.00,
        1: 0.90,
        2: 0.75,
        3: 0.55,
        4: 0.35,
        5: 0.15,
    }[evidence.assistance]

    independence_factor = 1.0 if evidence.independent else 0.55

    novelty_factor = {
        "transfer": 1.00,
        "delayed_retest": 1.00,
        "mixed": 0.95,
        "new": 0.85,
        "seen": 0.70,
        "same_problem_repeat": 0.35,
    }[evidence.novelty]

    strength = (
        outcome_factor
        * assistance_factor
        * independence_factor
        * novelty_factor
    )

    # Same-day re-exposure provides limited long-term retention evidence.
    if elapsed_days < 1.0:
        strength = min(strength, 0.30)

    return max(0.0, min(1.0, strength))


def _initial_stability(
    evidence: Evidence,
    *,
    policy: MemoryPolicy,
) -> float:
    """Conservative prior before learner-specific calibration exists."""

    strength = _evidence_strength(evidence, elapsed_days=7.0)

    if evidence.outcome == "PASS":
        # An independent clean first success starts near one week; weak or
        # assisted evidence starts shorter.  This is a prior, not a fixed
        # mandatory review interval.
        value = 1.0 + 6.0 * strength
    elif evidence.outcome == "PARTIAL":
        value = 1.0 + 1.5 * strength
    else:
        value = policy.min_stability_days

    return max(
        policy.min_stability_days,
        min(policy.max_stability_days, value),
    )


def update_memory(
    state: MemoryState | None,
    evidence: Evidence,
    *,
    policy: MemoryPolicy = MemoryPolicy(),
) -> MemoryState:
    """Update Skill x Track memory from one observable evidence event."""

    if state is None:
        return MemoryState(
            skill_uid=evidence.skill_uid,
            track=evidence.track,
            stability_days=_initial_stability(
                evidence,
                policy=policy,
            ),
            last_evidence_on=evidence.occurred_on,
            evidence_count=1,
            successful_retrievals=(
                1 if evidence.outcome == "PASS" else 0
            ),
            lapses=1 if evidence.outcome == "FAIL" else 0,
            last_outcome=evidence.outcome,
            policy_version=policy.version,
        )

    if (
        state.skill_uid != evidence.skill_uid
        or state.track != evidence.track
    ):
        raise ValueError("evidence does not match memory state")

    if evidence.occurred_on < state.last_evidence_on:
        raise ValueError("evidence cannot move backwards in time")

    elapsed_days = float(
        (evidence.occurred_on - state.last_evidence_on).days
    )
    before_r = retrievability(
        state,
        evidence.occurred_on,
    )
    strength = _evidence_strength(
        evidence,
        elapsed_days,
    )

    stability = state.stability_days
    successes = state.successful_retrievals
    lapses = state.lapses

    if evidence.outcome == "PASS":
        # Successful retrieval after genuine forgetting risk earns more
        # stability than an immediate/easy repeat.  Existing high stability
        # dampens the gain.
        forgetting_credit = max(0.0, 1.0 - before_r)
        diminishing = 4.0 + 2.0 / math.sqrt(max(1.0, stability))
        growth = 1.0 + strength * forgetting_credit * diminishing

        # A real delayed success should never reduce stability, while a
        # same-day repeat is deliberately capped to a tiny increase.
        if elapsed_days < 1.0:
            growth = min(growth, 1.05)

        stability *= growth
        successes += 1

    elif evidence.outcome == "PARTIAL":
        # Partial performance is evidence of an unstable memory, not a full
        # lapse. Preserve some prior stability but do not reward it.
        stability *= 0.75 + 0.20 * strength

    else:
        # A lapse lowers stability but does not erase all long-term evidence.
        # Long-standing skills retain more residual stability than a new one.
        residual = max(
            policy.min_stability_days,
            min(
                stability * 0.45,
                max(
                    policy.min_stability_days,
                    elapsed_days * 0.35,
                ),
            ),
        )
        stability = residual
        lapses += 1

    stability = max(
        policy.min_stability_days,
        min(policy.max_stability_days, stability),
    )

    return replace(
        state,
        stability_days=stability,
        last_evidence_on=evidence.occurred_on,
        evidence_count=state.evidence_count + 1,
        successful_retrievals=successes,
        lapses=lapses,
        last_outcome=evidence.outcome,
        policy_version=policy.version,
    )


def review_budget_minutes(
    total_capacity_minutes: int,
    *,
    policy: MemoryPolicy = MemoryPolicy(),
) -> int:
    if total_capacity_minutes <= 0:
        return 0

    nominal = int(
        math.floor(
            total_capacity_minutes
            * policy.review_fraction
        )
    )

    absolute_max = int(
        math.floor(
            total_capacity_minutes
            * policy.review_fraction_max
        )
    )

    protected_new = int(
        math.ceil(
            total_capacity_minutes
            * policy.min_new_learning_fraction
        )
    )

    capacity_after_protection = max(
        0,
        total_capacity_minutes - protected_new,
    )

    return max(
        0,
        min(
            nominal,
            absolute_max,
            capacity_after_protection,
        ),
    )


def _candidate_priority(
    candidate: ReviewCandidate,
    *,
    today: dt.date,
) -> tuple:
    importance_rank = {
        "current_required": 0,
        "required": 1,
        "supporting": 2,
        "extension": 3,
    }[candidate.importance]

    overdue_days = max(
        0,
        (today - candidate.due_on).days,
    )

    return (
        0 if candidate.recent_failure else 1,
        importance_rank,
        candidate.retrievability,
        -overdue_days,
        candidate.estimated_minutes,
        candidate.skill_uid,
        candidate.track,
    )


def select_review_plan(
    candidates: Iterable[ReviewCandidate],
    *,
    today: dt.date,
    total_capacity_minutes: int,
    policy: MemoryPolicy = MemoryPolicy(),
) -> ReviewPlan:
    """Select reviews without turning deferred work into debt.

    Selection is transparent and lexicographic:
    recent failure -> curriculum importance -> lower retrievability ->
    greater overdueness -> cheaper task.
    """

    budget = review_budget_minutes(
        total_capacity_minutes,
        policy=policy,
    )

    ordered = sorted(
        candidates,
        key=lambda item: _candidate_priority(
            item,
            today=today,
        ),
    )

    selected: list[ReviewCandidate] = []
    deferred: list[ReviewCandidate] = []
    used = 0

    for candidate in ordered:
        if used + candidate.estimated_minutes <= budget:
            selected.append(candidate)
            used += candidate.estimated_minutes
        else:
            deferred.append(candidate)

    return ReviewPlan(
        budget_minutes=budget,
        selected=tuple(selected),
        deferred=tuple(deferred),
    )
