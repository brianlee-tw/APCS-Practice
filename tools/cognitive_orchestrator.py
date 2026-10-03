#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

CONFUSABLE_SKILL_PAIRS = (
    ("S22_Prefix_Sum", "S13_Two_Pointers"),
    ("S13_Two_Pointers", "S10_Binary_Search"),
    ("S18_DFS", "S19_BFS"),
    ("S11_Greedy", "S20_DP"),
    ("S12_Brute_Force", "S32_Backtracking"),
    ("S09_Sorting", "S24_Map_Set"),
)

REPAIR_MINUTES = 8
DISCRIMINATION_MINUTES = 6
TRANSFER_MINUTES = 12
MIN_TASK_MINUTES = 6


@dataclass(frozen=True)
class CognitiveTask:
    kind: str
    estimated_minutes: int
    reason: str
    skill_uids: tuple[str, ...] = ()
    track: str | None = None
    activity: str | None = None
    guidance: str | None = None
    source_problem_id: str | None = None


@dataclass(frozen=True)
class CognitivePlan:
    selected: tuple[CognitiveTask, ...]
    deferred: tuple[CognitiveTask, ...]
    available_minutes: int
    selected_minutes: int
    protected_new_learning_minutes: int


@dataclass(frozen=True)
class SkillEvidenceState:
    skill_uid: str
    track: str
    latest_outcome: str
    latest_problem_id: str
    latest_assistance: int | None
    latest_independent: bool | None
    latest_novelty: str | None
    latest_order: int
    strong_passes: int
    transfer_passes: int


def _sort_envelopes(envelopes):
    return sorted(
        envelopes,
        key=lambda env: (
            env.attempt.finished_at,
            env.writeback_id,
        ),
    )


def skill_states(envelopes: Iterable) -> dict[tuple[str, str], SkillEvidenceState]:
    raw: dict[tuple[str, str], dict] = {}

    for order, envelope in enumerate(
        _sort_envelopes(envelopes),
        start=1,
    ):
        attempt = envelope.attempt
        for claim in envelope.evidence:
            key = (claim.skill_uid, claim.track)
            state = raw.setdefault(
                key,
                {
                    "skill_uid": claim.skill_uid,
                    "track": claim.track,
                    "latest_outcome": claim.outcome,
                    "latest_problem_id": attempt.problem_id,
                    "latest_assistance": attempt.assistance,
                    "latest_independent": attempt.independent,
                    "latest_novelty": attempt.novelty,
                    "latest_order": order,
                    "strong_passes": 0,
                    "transfer_passes": 0,
                },
            )

            state.update(
                {
                    "latest_outcome": claim.outcome,
                    "latest_problem_id": attempt.problem_id,
                    "latest_assistance": attempt.assistance,
                    "latest_independent": attempt.independent,
                    "latest_novelty": attempt.novelty,
                    "latest_order": order,
                }
            )

            strong = (
                claim.outcome == "PASS"
                and attempt.assistance == 0
                and attempt.independent is True
            )
            if strong:
                state["strong_passes"] += 1
                if attempt.novelty in {
                    "transfer",
                    "delayed_retest",
                }:
                    state["transfer_passes"] += 1

    return {
        key: SkillEvidenceState(**value)
        for key, value in raw.items()
    }


def guidance_for(state: SkillEvidenceState | None) -> tuple[str, str]:
    """回傳建議活動與最高提示起點。

    這不是 mastery 判定，只決定下一次應該給多少支援。
    """

    if state is None:
        return "Worked Example", "A3"

    if state.latest_outcome == "FAIL":
        return "Guided Drill", "A3"

    if state.latest_outcome == "PARTIAL":
        return "Guided Drill", "A2"

    if state.transfer_passes >= 1 and state.strong_passes >= 2:
        return "Transfer Challenge", "A1"

    if state.strong_passes >= 1:
        return "Core Independent", "A1"

    return "Guided Drill", "A2"


def _latest_failed_state(
    states: dict[tuple[str, str], SkillEvidenceState],
) -> SkillEvidenceState | None:
    failed = [
        state
        for state in states.values()
        if state.latest_outcome in {"FAIL", "PARTIAL"}
    ]
    if not failed:
        return None

    return sorted(
        failed,
        key=lambda state: (
            -state.latest_order,
            0 if state.latest_outcome == "FAIL" else 1,
            state.skill_uid,
            state.track,
        ),
    )[0]


def _discrimination_candidate(
    states: dict[tuple[str, str], SkillEvidenceState],
) -> CognitiveTask | None:
    known_skills = {
        state.skill_uid
        for state in states.values()
    }

    for left, right in CONFUSABLE_SKILL_PAIRS:
        if left in known_skills or right in known_skills:
            return CognitiveTask(
                kind="discrimination",
                estimated_minutes=DISCRIMINATION_MINUTES,
                reason=(
                    "近期 Evidence 涉及容易混淆的方法；"
                    "用短時間先判斷成立條件，可降低看到題型就套模板的風險。"
                ),
                skill_uids=(left, right),
                activity="Strategy Discrimination",
                guidance="A1",
            )

    return None


def _transfer_candidate(
    states: dict[tuple[str, str], SkillEvidenceState],
) -> CognitiveTask | None:
    candidates = [
        state
        for state in states.values()
        if (
            state.strong_passes >= 1
            and state.transfer_passes == 0
            and state.latest_outcome == "PASS"
        )
    ]
    if not candidates:
        return None

    state = sorted(
        candidates,
        key=lambda item: (
            -item.strong_passes,
            item.skill_uid,
            item.track,
        ),
    )[0]

    return CognitiveTask(
        kind="transfer",
        estimated_minutes=TRANSFER_MINUTES,
        reason=(
            "已有 A0 independent PASS，但尚無 delayed / transfer PASS；"
            "下一步應驗證能否在新題辨認並獨立使用。"
        ),
        skill_uids=(state.skill_uid,),
        track=state.track,
        activity="Transfer Challenge",
        guidance="A1",
    )


def _repair_candidate(
    states: dict[tuple[str, str], SkillEvidenceState],
) -> CognitiveTask | None:
    state = _latest_failed_state(states)
    if state is None:
        return None

    activity, guidance = guidance_for(state)
    return CognitiveTask(
        kind="repair",
        estimated_minutes=REPAIR_MINUTES,
        reason=(
            f"最近 {state.skill_uid} × {state.track} "
            f"為 {state.latest_outcome}；先做最小診斷與修復，"
            "不要直接重刷原題。"
        ),
        skill_uids=(state.skill_uid,),
        track=state.track,
        activity=activity,
        guidance=guidance,
        source_problem_id=state.latest_problem_id,
    )


class CognitiveOrchestrator:
    def plan(
        self,
        envelopes: Iterable,
        *,
        total_capacity_minutes: int,
        review_selected_minutes: int,
        new_learning_active: bool,
    ) -> CognitivePlan:
        capacity = max(0, int(total_capacity_minutes))
        review_minutes = max(0, int(review_selected_minutes))

        protected_new = (
            int(round(capacity * 0.60))
            if new_learning_active
            else 0
        )
        cognitive_budget = max(
            0,
            capacity - protected_new - review_minutes,
        )

        states = skill_states(envelopes)
        candidates = [
            task
            for task in (
                _repair_candidate(states),
                _discrimination_candidate(states),
                _transfer_candidate(states),
            )
            if task is not None
        ]

        selected: list[CognitiveTask] = []
        deferred: list[CognitiveTask] = []
        remaining = cognitive_budget

        for task in candidates:
            if remaining < MIN_TASK_MINUTES:
                deferred.append(task)
                continue

            minutes = min(task.estimated_minutes, remaining)
            if minutes < MIN_TASK_MINUTES:
                deferred.append(task)
                continue

            selected.append(
                CognitiveTask(
                    kind=task.kind,
                    estimated_minutes=minutes,
                    reason=task.reason,
                    skill_uids=task.skill_uids,
                    track=task.track,
                    activity=task.activity,
                    guidance=task.guidance,
                    source_problem_id=task.source_problem_id,
                )
            )
            remaining -= minutes

        return CognitivePlan(
            selected=tuple(selected),
            deferred=tuple(deferred),
            available_minutes=cognitive_budget,
            selected_minutes=sum(
                task.estimated_minutes
                for task in selected
            ),
            protected_new_learning_minutes=protected_new,
        )


def repair_instruction(
    bottleneck: str | None = None,
) -> str:
    generic = (
        "先寫 Expected / Observed，建立最小失敗案例，"
        "縮小範圍後提出一個 hypothesis，再只改一件事並做 regression test。"
    )

    mapping = {
        "Concept": "先補最小概念，再做一個新的 concept check。",
        "Condition": "列出方法成立與不成立的條件，各找一個反例。",
        "Representation": "先把題意轉成 state / array / graph 等可操作模型。",
        "Strategy": "先比較至少兩種候選方法的成立條件與複雜度。",
        "Complexity": "從 constraints 反推可接受的最壞時間與空間複雜度。",
        "Implementation": "保留原方法，只縮小到第一個 implementation root cause。",
        "Syntax / API": "只修正最小語法或 API 使用，再重新編譯。",
        "State / Index": "手動 trace 最小邊界案例，檢查初始化與 off-by-one。",
        "Debugging": generic,
        "Exam Interface": "記錄卡住時間與 stop-loss 決策，先修正作答流程。",
    }

    return mapping.get(bottleneck or "", generic)
