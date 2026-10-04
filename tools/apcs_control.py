#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import datetime as dt
import io
import json
import os
import re
import select
import shutil
import subprocess
import sys
import termios
import tty
import unicodedata
import webbrowser
from pathlib import Path

try:
    from . import apcs as core
    from .catalog_store import CatalogError, ProblemMeta, SolutionMeta
    from .evidence_outbox import (
        EvidenceOutbox,
        EvidenceOutboxError,
        build_envelope,
    )
    from .runtime_curriculum import (
        RuntimeCurriculum,
        RuntimeCurriculumError,
    )
    from .adaptive_memory import (
        next_due_on,
        retrievability,
    )
    from .calibration import (
        resolve_memory_policy,
    )
    from .cognitive_orchestrator import (
        CognitiveOrchestrator,
        repair_instruction,
    )
    from .learning_route import (
        select_new_learning_plan,
    )
    from .reading_runtime import (
        create_reading_scratch,
        formal_response_ready,
    )
    from .problem_library import ProblemLibrary, LibraryItem
    from .test_assets import TestAssetStore
    from .workbench_context import resolve_problem_context
    from .workbench_tui import (
        terminal_width as workbench_width,
        terminal_height as workbench_height,
        pane_widths as workbench_pane_widths,
    )
    from .learner_model_v2 import (
        LearnerSignalStore,
        learner_model_snapshot,
    )
    from .exam_runtime import (
        ExamRuntimeError,
        ExamSessionStore,
        POSTMORTEM_REASONS,
    )
    from .skill_memory_store import (
        SkillMemoryStore,
    )
    from .tag_taxonomy import TAG_GROUPS, serialize_selection, split_tags
except ImportError:
    import apcs as core
    from catalog_store import CatalogError, ProblemMeta, SolutionMeta
    from evidence_outbox import (
        EvidenceOutbox,
        EvidenceOutboxError,
        build_envelope,
    )
    from runtime_curriculum import (
        RuntimeCurriculum,
        RuntimeCurriculumError,
    )
    from adaptive_memory import (
        next_due_on,
        retrievability,
    )
    from calibration import (
        resolve_memory_policy,
    )
    from cognitive_orchestrator import (
        CognitiveOrchestrator,
        repair_instruction,
    )
    from learning_route import (
        select_new_learning_plan,
    )
    from reading_runtime import (
        create_reading_scratch,
        formal_response_ready,
    )
    from problem_library import ProblemLibrary, LibraryItem
    from test_assets import TestAssetStore
    from workbench_context import resolve_problem_context
    from workbench_tui import (
        terminal_width as workbench_width,
        terminal_height as workbench_height,
        pane_widths as workbench_pane_widths,
    )
    from learner_model_v2 import (
        LearnerSignalStore,
        learner_model_snapshot,
    )
    from exam_runtime import (
        ExamRuntimeError,
        ExamSessionStore,
        POSTMORTEM_REASONS,
    )
    from skill_memory_store import (
        SkillMemoryStore,
    )
    from tag_taxonomy import TAG_GROUPS, serialize_selection, split_tags


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = ROOT / ".apcs" / "runtime"
PUBLISHED_CURRICULUM = ROOT / "curriculum" / "published.v23.json"

OUTBOX = EvidenceOutbox(RUNTIME_DIR)
CURRICULUM = RuntimeCurriculum(PUBLISHED_CURRICULUM)
MEMORY = SkillMemoryStore(
    RUNTIME_DIR / "skill_memory.json",
    policy=resolve_memory_policy(
        RUNTIME_DIR
    ),
)
PROBLEM_LIBRARY = ProblemLibrary(
    core.PROBLEM_INTELLIGENCE,
    core.PROBLEM_ENRICHMENT,
    OUTBOX,
)
TEST_ASSETS = TestAssetStore(
    ROOT / "data" / "problem_enrichment",
    RUNTIME_DIR,
)
COGNITIVE = CognitiveOrchestrator()
LEARNER_SIGNALS = LearnerSignalStore(RUNTIME_DIR)
EXAM = ExamSessionStore(RUNTIME_DIR)

DEFAULT_SESSION_MINUTES = 60
DEFAULT_IMPLEMENTATION_REVIEW_MINUTES = 12
DEFAULT_READING_REVIEW_MINUTES = 6
TODAY_CAPACITY_PATH = RUNTIME_DIR / "today_capacity.json"
SELECTION_MODE_PATH = RUNTIME_DIR / "selection_mode.json"
TODAY_CAPACITY_CHOICES = (
    15,
    30,
    45,
    60,
    75,
    90,
    120,
    150,
    180,
    240,
)
SELECTION_MODES = ("practice", "exam")
EXAM_DURATION_CHOICES = (
    30,
    60,
    90,
    120,
    180,
)

ID_RE = re.compile(r"^([A-Za-z]\d+|\d+)(?:_|$)")

RESET = "\033[0m"
BOLD = "\033[1m"

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
WHITE = "\033[97m"
GRAY = "\033[90m"

# Internal sentinel for returning to the previous record-wizard step.
# None remains a valid field value (for example, skipped active minutes).
RECORD_BACK = object()
MODE_TOGGLE = object()

# Ephemeral UI state: preserves focus/filter position within one Control Center
# process without creating another durable source of truth.
UI_STATE = {
    "library_result_index": 0,
    "library_filter_kind": "results",
    "library_focus": 0,
    "library_filters_practice": None,
    "library_filters_exam": None,
    "library_query_practice": "",
    "library_query_exam": "",
}


# ============================================================
# Layout / text
# ============================================================

def char_width(ch: str) -> int:
    if unicodedata.combining(ch):
        return 0
    return 2 if unicodedata.east_asian_width(ch) in {"W", "F"} else 1


def display_width(text: str) -> int:
    return sum(char_width(ch) for ch in text)


def fit(text: str, width: int) -> str:
    """Single-line fallback for compact status fields.

    Learner-facing prose should prefer wrap_display() so information is not
    silently lost behind an ellipsis.
    """
    text = str(text)

    if display_width(text) <= width:
        return text

    out = ""
    used = 0

    for ch in text:
        w = char_width(ch)
        if used + w + 1 > width:
            break
        out += ch
        used += w

    return out + "…"


def pad_display(
    text: str,
    width: int,
) -> str:
    """Pad a plain terminal cell by display width."""

    clipped = fit(
        str(text),
        max(1, width),
    )
    return (
        clipped
        + " " * max(
            0,
            width - display_width(
                clipped
            ),
        )
    )


def wrap_display(text: str, width: int) -> list[str]:
    """Wrap text by terminal display width without dropping content."""
    width = max(1, int(width))
    result: list[str] = []

    for paragraph in str(text).split("\n"):
        if paragraph == "":
            result.append("")
            continue

        remaining = paragraph

        while display_width(remaining) > width:
            used = 0
            cut = 0
            last_space = 0

            for index, ch in enumerate(remaining):
                w = char_width(ch)

                if used + w > width:
                    break

                used += w
                cut = index + 1

                if ch.isspace():
                    last_space = cut

            if cut <= 0:
                cut = 1

            if last_space and last_space >= max(1, cut // 2):
                cut = last_space

            line = remaining[:cut]
            result.append(line)
            remaining = remaining[cut:]

        result.append(remaining)

    return result or [""]


def print_wrapped(
    text: str,
    width: int,
    *,
    prefix: str = "",
    continuation_prefix: str | None = None,
    color: str = "",
) -> None:
    continuation_prefix = (
        prefix
        if continuation_prefix is None
        else continuation_prefix
    )
    lines = wrap_display(
        text,
        max(1, width),
    )

    for index, line in enumerate(lines):
        lead = (
            prefix
            if index == 0
            else continuation_prefix
        )
        print(
            f"{color}{lead}{line}{RESET if color else ''}"
        )


def ui_width() -> int:
    return workbench_width()


def ui_height() -> int:
    return workbench_height()


def rule() -> None:
    print("─" * ui_width())


def clear() -> None:
    print("\033[2J\033[H", end="", flush=True)


def heading(title: str) -> None:
    print(f"{CYAN}{BOLD}APCS · {title}{RESET}")
    rule()


def read_key() -> str:
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)

    try:
        tty.setraw(fd)
        ch = os.read(fd, 1)

        if ch in {b"\r", b"\n"}:
            return "ENTER"

        if ch == b"\t":
            return "TAB"

        if ch == b"\x1b":
            ready, _, _ = select.select([fd], [], [], 0.04)

            if not ready:
                return "ESC"

            second = os.read(fd, 1)

            if second != b"[":
                return "ESC"

            ready, _, _ = select.select([fd], [], [], 0.04)

            if not ready:
                return "ESC"

            third = os.read(fd, 1)

            if third == b"A":
                return "UP"
            if third == b"B":
                return "DOWN"
            if third == b"C":
                return "RIGHT"
            if third == b"D":
                return "LEFT"
            if third == b"Z":
                return "BACKTAB"

            return "ESC"

        try:
            return ch.decode("utf-8")
        except UnicodeDecodeError:
            return ""

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def pause(text: str = "Enter / Esc 返回控制中心") -> None:
    print()
    print(f"{GRAY}{text}{RESET}")

    while True:
        if read_key() in {"ENTER", "ESC", "q", "Q"}:
            return


def confirm(question: str) -> bool:
    print()
    print(f"{YELLOW}{question}{RESET}")
    print(f"{GRAY}Y 確認 · N / Esc 取消{RESET}")

    while True:
        key = read_key()

        if key in {"y", "Y"}:
            return True

        if key in {"n", "N", "ESC", "q", "Q"}:
            return False


# ============================================================
# Problem state
# ============================================================

def clean_title(pid: str, title: str) -> str:
    title = str(title).strip()

    for pattern in (
        rf"^{re.escape(pid)}\s*[.．、:：\-]\s*",
        rf"^{re.escape(pid)}\s+",
    ):
        title = re.sub(
            pattern,
            "",
            title,
            flags=re.IGNORECASE,
        )

    return title or pid


def all_rows():
    rows, _ = core.build()
    return rows


def runtime_scratch_context(path: Path) -> tuple[str | None, str | None]:
    """Return (track, record_action) encoded by a v2.3 runtime scratch path."""

    parts = {
        part.lower()
        for part in path.parts
    }

    track = (
        "Reading"
        if "reading" in parts
        else (
            "Implementation"
            if {"learn", "review"} & parts
            else None
        )
    )
    action = (
        "review"
        if "review" in parts
        else (
            "finish"
            if "learn" in parts
            else None
        )
    )

    return track, action


def current_problem(filename: str | None):
    if not filename:
        return None

    try:
        context = resolve_problem_context(
            filename,
            root=ROOT,
            store=core.CATALOG,
            curriculum=CURRICULUM,
            intelligence_dir=(
                ROOT
                / "data"
                / "problem_intelligence"
            ),
        )
    except (
        OSError,
        CatalogError,
        RuntimeCurriculumError,
    ):
        context = None

    if context is None:
        return None

    pid = context.problem_id
    resolved = (
        context.solution_path
        .resolve()
    )

    legacy_placement_match = re.search(
        r"__([A-Za-z0-9_.:-]+)$",
        Path(filename).stem,
    )
    placement_uid = (
        context.placement_uid
        or (
            legacy_placement_match.group(1)
            if legacy_placement_match
            else None
        )
    )

    state = None
    due = None
    matched_path = (
        context.solution_path
    )

    for row in all_rows():
        if row[0] != pid:
            continue

        state = row[3]
        due = row[5]

        exact = next(
            (
                solution.path
                for solution in row[1]
                if solution.path.resolve()
                == resolved
            ),
            None,
        )
        if exact is not None:
            matched_path = exact
        break

    published_runtime = (
        context.identity_origin
        == "published_placement"
    )
    track, action = (
        runtime_scratch_context(
            context.solution_path
        )
        if published_runtime
        else (None, None)
    )

    return {
        "id": pid,
        "title": clean_title(
            pid,
            context.title,
        ),
        "path": matched_path,
        "state": state,
        "due": due,
        "placement_uid": (
            placement_uid
        ),
        "pb_uid": context.pb_uid,
        "published_runtime": (
            published_runtime
        ),
        "url": context.canonical_url,
        "source": context.source,
        "role": context.role,
        "runtime_track": track,
        "runtime_action": action,
        "identity_origin": (
            context.identity_origin
        ),
    }



def problem_line(problem) -> str:
    if not problem:
        return "— 尚未選擇 APCS 題目"

    return fit(
        f"{problem['id']} · {problem['title']}",
        ui_width(),
    )


def problem_status(problem) -> str:
    if not problem:
        return "請先開啟一個 APCS 題目檔案"

    state = problem.get("state")

    if state is None:
        return "尚無正式學習紀錄"

    parts = []

    if state.solved_on:
        parts.append("AC")

        if (
            state.last_review_on
            and state.last_result
            and state.last_result != "AC"
        ):
            parts.append(
                f"最近 {state.last_result}"
            )
    else:
        parts.append("尚未完成")

    if state.recall is not None:
        parts.append(f"Recall {state.recall}")

    return " · ".join(parts)


def print_problem_context(problem) -> None:
    print(f"{GRAY}目前題目{RESET}")
    print(f"{WHITE}{BOLD}{problem_line(problem)}{RESET}")

    status = problem_status(problem)

    if (
        problem
        and problem.get("state")
        and problem["state"].solved_on
    ):
        color = GREEN
    elif "逾期" in status or "到期" in status:
        color = YELLOW
    else:
        color = GRAY

    print(f"{color}{fit(status, ui_width())}{RESET}")


def today_state():
    """Legacy v2.2 problem-level due state.

    Kept only for compatibility surfaces while v2.3 transitions generated
    artifacts. Learner-facing Today uses adaptive_today_snapshot().
    """

    today = dt.date.today()

    due = [
        row
        for row in all_rows()
        if row[5] and row[5] <= today
    ]

    overdue = [
        row
        for row in due
        if row[5] < today
    ]

    return due, overdue


def _default_session_capacity_minutes() -> int:
    raw = os.environ.get(
        "APCS_SESSION_MINUTES",
        str(DEFAULT_SESSION_MINUTES),
    )

    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_SESSION_MINUTES

    return max(
        15,
        min(value, 240),
    )


def _today_capacity_override(
    on_date: dt.date,
) -> int | None:
    if not TODAY_CAPACITY_PATH.is_file():
        return None

    try:
        payload = json.loads(
            TODAY_CAPACITY_PATH.read_text(
                encoding="utf-8"
            )
        )
        if payload.get("date") != on_date.isoformat():
            return None

        minutes = int(
            payload.get("minutes")
        )
    except (
        OSError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
    ):
        return None

    if minutes not in TODAY_CAPACITY_CHOICES:
        return None

    return minutes


def session_capacity_minutes(
    on_date: dt.date | None = None,
) -> int:
    on_date = on_date or dt.date.today()

    override = _today_capacity_override(
        on_date
    )
    if override is not None:
        return override

    return _default_session_capacity_minutes()


def set_today_capacity_minutes(
    minutes: int,
    *,
    on_date: dt.date | None = None,
) -> None:
    on_date = on_date or dt.date.today()

    if minutes not in TODAY_CAPACITY_CHOICES:
        raise ValueError(
            "今日可用時間必須使用系統提供的時間選項。"
        )

    TODAY_CAPACITY_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    payload = {
        "date": on_date.isoformat(),
        "minutes": minutes,
    }
    temp_path = (
        TODAY_CAPACITY_PATH
        .with_suffix(".tmp")
    )
    temp_path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    temp_path.replace(
        TODAY_CAPACITY_PATH
    )


def today_capacity_menu(
    current_minutes: int,
) -> int | None:
    options = [
        {
            "label": f"{minutes} 分",
            "detail": (
                "目前設定"
                if minutes == current_minutes
                else ""
            ),
            "enabled": True,
            "action": "套用",
        }
        for minutes
        in TODAY_CAPACITY_CHOICES
    ]

    selected_index = min(
        range(
            len(TODAY_CAPACITY_CHOICES)
        ),
        key=lambda index: abs(
            TODAY_CAPACITY_CHOICES[index]
            - current_minutes
        ),
    )

    selected = choose_grid(
        "今日學習 · 可用時間",
        options,
        back_text="返回今日學習",
        selected_index=selected_index,
        enter_text="套用",
        wide_columns=5,
        compact_columns=2,
    )

    if selected is None:
        return None

    return TODAY_CAPACITY_CHOICES[
        selected
    ]


def selection_mode() -> str:
    if not SELECTION_MODE_PATH.is_file():
        return "practice"

    try:
        payload = json.loads(
            SELECTION_MODE_PATH.read_text(
                encoding="utf-8"
            )
        )
        mode = str(
            payload.get("mode") or ""
        ).strip().lower()
    except (
        OSError,
        TypeError,
        json.JSONDecodeError,
    ):
        return "practice"

    return (
        mode
        if mode in SELECTION_MODES
        else "practice"
    )


def set_selection_mode(mode: str) -> None:
    mode = str(mode or "").strip().lower()
    if mode not in SELECTION_MODES:
        raise ValueError(
            "選題模式必須是 practice 或 exam。"
        )

    SELECTION_MODE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    temp_path = (
        SELECTION_MODE_PATH
        .with_suffix(".tmp")
    )
    temp_path.write_text(
        json.dumps(
            {"mode": mode},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    temp_path.replace(
        SELECTION_MODE_PATH
    )


def toggle_selection_mode() -> str:
    mode = (
        "exam"
        if selection_mode() == "practice"
        else "practice"
    )
    set_selection_mode(mode)
    return mode


def selection_mode_label(
    mode: str | None = None,
) -> str:
    mode = mode or selection_mode()
    return (
        "練習"
        if mode == "practice"
        else "考試"
    )


def selection_mode_badge(
    mode: str | None = None,
) -> str:
    mode = mode or selection_mode()
    if mode == "exam":
        return (
            f"{YELLOW}{BOLD}"
            "[ 考試 · 防劇透 ]"
            f"{RESET}"
        )
    return (
        f"{GREEN}{BOLD}"
        "[ 練習 ]"
        f"{RESET}"
    )


def print_selection_mode_banner(
    mode: str | None = None,
    *,
    toggle_hint: bool = True,
) -> None:
    mode = mode or selection_mode()
    explanation = (
        "只顯示中性題目資訊"
        if mode == "exam"
        else "可依 Unit / Skill / 難度分類練習"
    )
    hint = (
        f" {GRAY}· M 切換{RESET}"
        if toggle_hint
        else ""
    )
    print(
        "選題模式  "
        + selection_mode_badge(mode)
        + f" {GRAY}{explanation}{RESET}"
        + hint
    )


def curriculum_target() -> str:
    value = os.environ.get(
        "APCS_TARGET",
        "3+3",
    ).strip()

    return (
        "5+5"
        if value == "5+5"
        else "3+3"
    )


def adaptive_today_snapshot(
    *,
    on_date: dt.date | None = None,
    total_capacity_minutes: int | None = None,
):
    on_date = on_date or dt.date.today()
    total_capacity_minutes = (
        total_capacity_minutes
        if total_capacity_minutes is not None
        else session_capacity_minutes(
            on_date
        )
    )

    warning = None
    reconcile_report = None

    try:
        envelopes = OUTBOX.all_envelopes()
    except (
        EvidenceOutboxError,
        OSError,
        ValueError,
    ) as exc:
        envelopes = ()
        warning = str(exc)

    target = curriculum_target()

    curriculum_blocker = None
    new_learning = None

    try:
        importance = (
            CURRICULUM
            .skill_importance(
                target=target
            )
        )
    except RuntimeCurriculumError as exc:
        importance = {}
        curriculum_blocker = str(exc)

    if curriculum_blocker is None:
        try:
            new_learning = (
                select_new_learning_plan(
                    CURRICULUM,
                    envelopes,
                    target=target,
                )
            )
        except (
            RuntimeCurriculumError,
            ValueError,
        ) as exc:
            curriculum_blocker = str(
                exc
            )

    try:
        reconcile_report = MEMORY.reconcile(
            envelopes
        )

        plan = MEMORY.review_plan(
            envelopes,
            on_date=on_date,
            total_capacity_minutes=(
                total_capacity_minutes
            ),
            importance_by_skill=(
                importance
            ),
        )

        memory_states = (
            MEMORY.load_states()
        )

        latest_problem = (
            MEMORY
            .latest_problem_by_key(
                envelopes
            )
        )

    except (
        EvidenceOutboxError,
        OSError,
        ValueError,
    ) as exc:
        from types import SimpleNamespace

        plan = SimpleNamespace(
            budget_minutes=0,
            selected=(),
            deferred=(),
            selected_minutes=0,
        )
        memory_states = {}
        latest_problem = {}

        if warning is None:
            warning = str(exc)

    cognitive_plan = COGNITIVE.plan(
        envelopes,
        total_capacity_minutes=total_capacity_minutes,
        review_selected_minutes=plan.selected_minutes,
        new_learning_active=bool(
            new_learning is not None
            and new_learning.skill is not None
            and new_learning.placement is not None
        ),
    )

    return {
        "date": on_date,
        "capacity_minutes": total_capacity_minutes,
        "target": target,
        "plan": plan,
        "due_count": (
            len(plan.selected)
            + len(plan.deferred)
        ),
        "memory_count": len(
            memory_states
        ),
        "reconcile_report": (
            reconcile_report
        ),
        "latest_problem": (
            latest_problem
        ),
        "curriculum_blocker": (
            curriculum_blocker
        ),
        "new_learning": (
            new_learning
        ),
        "warning": warning,
        "cognitive_plan": cognitive_plan,
    }


def learning_status_snapshot(
    *,
    on_date: dt.date | None = None,
    total_capacity_minutes: int | None = None,
):
    """Build read-only learner operational status from v2.3 durable inputs."""

    on_date = on_date or dt.date.today()
    today = adaptive_today_snapshot(
        on_date=on_date,
        total_capacity_minutes=total_capacity_minutes,
    )
    warnings = []

    if today["warning"]:
        warnings.append(
            today["warning"]
        )

    try:
        envelopes = OUTBOX.all_envelopes()
        pending = OUTBOX.pending()
    except (
        EvidenceOutboxError,
        OSError,
        ValueError,
    ) as exc:
        envelopes = ()
        pending = ()
        warnings.append(str(exc))

    evidence_by_track = {
        "Reading": 0,
        "Implementation": 0,
    }
    evidence_count = 0

    for envelope in envelopes:
        for claim in envelope.evidence:
            evidence_count += 1
            evidence_by_track[claim.track] = (
                evidence_by_track.get(
                    claim.track,
                    0,
                )
                + 1
            )

    try:
        states = MEMORY.load_states()
    except (OSError, ValueError) as exc:
        states = {}
        warnings.append(str(exc))

    retention = []

    for state in states.values():
        current_r = retrievability(
            state,
            on_date,
        )
        due_on = next_due_on(
            state,
            policy=MEMORY.policy,
        )
        retention.append(
            {
                "skill_uid": state.skill_uid,
                "track": state.track,
                "retrievability": current_r,
                "stability_days": state.stability_days,
                "last_evidence_on": state.last_evidence_on,
                "due_on": due_on,
                "evidence_count": state.evidence_count,
                "successful_retrievals": state.successful_retrievals,
                "lapses": state.lapses,
                "last_outcome": state.last_outcome,
            }
        )

    retention.sort(
        key=lambda item: (
            item["retrievability"],
            item["due_on"],
            item["skill_uid"],
            item["track"],
        )
    )

    plan = today["plan"]
    protected = max(
        0,
        today["capacity_minutes"]
        - plan.budget_minutes,
    )

    try:
        learner_signals = LEARNER_SIGNALS.load()
        learner_model = learner_model_snapshot(
            envelopes,
            learner_signals,
        )
    except (OSError, ValueError) as exc:
        learner_model = learner_model_snapshot(
            envelopes,
            (),
        )
        warnings.append(str(exc))

    return {
        "date": on_date,
        "target": today["target"],
        "attempts": len(envelopes),
        "evidence": evidence_count,
        "evidence_by_track": evidence_by_track,
        "remote_pending": len(pending),
        "remote_acknowledged": max(
            0,
            len(envelopes) - len(pending),
        ),
        "memory_states": len(states),
        "retention": tuple(retention),
        "capacity_minutes": today["capacity_minutes"],
        "review_budget_minutes": plan.budget_minutes,
        "review_selected": len(plan.selected),
        "review_selected_minutes": plan.selected_minutes,
        "review_deferred": len(plan.deferred),
        "protected_new_learning_minutes": protected,
        "learner_model": learner_model,
        "warnings": tuple(dict.fromkeys(warnings)),
        "learner_readiness": "NOT ASSESSED",
    }


def skill_display_name(
    skill_uid: str,
) -> str:
    try:
        context = CURRICULUM.skill_context(
            skill_uid
        )
    except RuntimeCurriculumError:
        context = None

    if (
        context is None
        or not context.name
    ):
        return skill_uid

    return (
        f"{skill_uid} · "
        f"{context.name}"
    )



def attempted_problem_ids_for_skill(
    skill_uid: str,
    *,
    track: str,
) -> set[str]:
    result = set()

    try:
        envelopes = (
            OUTBOX.all_envelopes()
        )
    except (
        EvidenceOutboxError,
        OSError,
    ):
        return result

    for envelope in envelopes:
        if not any(
            claim.skill_uid == skill_uid
            and claim.track == track
            for claim in envelope.evidence
        ):
            continue

        result.add(
            envelope.attempt.problem_id
            .strip()
            .lower()
        )

    return result


def review_placement_for_skill(
    skill_uid: str,
    *,
    track: str,
):
    attempted = (
        attempted_problem_ids_for_skill(
            skill_uid,
            track=track,
        )
    )

    try:
        return (
            CURRICULUM
            .review_placement_for_skill(
                skill_uid,
                exclude_problem_ids=attempted,
            )
        )
    except RuntimeCurriculumError:
        return None


def create_review_scratch(
    placement,
) -> Path:
    folder = (
        RUNTIME_DIR
        / "review"
        / dt.date.today().isoformat()
    )
    folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    target = (
        folder
        / (
            f"{placement.problem_id}"
            f"__{placement.placement_uid}"
            ".cpp"
        )
    )

    if target.exists():
        return target

    lines = [
        "// APCS adaptive review scratch",
        f"// Skill: {placement.primary_skill}",
        (
            f"// Problem: "
            f"{placement.problem_id} · "
            f"{placement.title}"
        ),
        f"// Role: {placement.role}",
    ]

    if placement.url:
        lines.append(
            f"// Judge: {placement.url}"
        )

    lines += [
        "//",
        "// 這是空白 retrieval scratch；不要查看舊 solution。",
        "",
    ]

    target.write_text(
        "\n".join(lines)
        + solution_template(
            "cpp"
        ),
        encoding="utf-8",
    )

    return target


def _safe_runtime_filename(
    value: str,
) -> str:
    cleaned = re.sub(
        r"[^A-Za-z0-9_.-]+",
        "_",
        str(value or "").strip(),
    ).strip("._")

    return cleaned or "problem"


def create_learning_scratch(
    placement,
) -> Path:
    folder = (
        RUNTIME_DIR
        / "learn"
        / dt.date.today().isoformat()
    )
    folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    target = (
        folder
        / (
            f"{_safe_runtime_filename(placement.problem_id)}"
            f"__{placement.placement_uid}"
            ".cpp"
        )
    )

    if target.exists():
        return target

    strict_spoiler = (
        placement.role
        in {
            "Transfer Challenge",
            "Mock",
        }
    )

    lines = [
        "// APCS B4 new-learning scratch",
        (
            f"// Problem: "
            f"{placement.problem_id} · "
            f"{placement.title}"
        ),
    ]

    if not strict_spoiler:
        lines.extend(
            [
                f"// Skill: {placement.primary_skill}",
                (
                    f"// Lesson: "
                    f"{placement.lesson_uid or '—'}"
                ),
                f"// Role: {placement.role}",
            ]
        )

    if placement.url:
        lines.append(
            f"// Judge: {placement.url}"
        )

    lines += [
        "//",
        (
            "// 嚴格防劇透：先自行辨認方法；"
            "不要查看分類、提示或舊解答。"
            if strict_spoiler
            else "// 先依 Lesson 建立 model，再自行完成本題。"
        ),
        "",
    ]

    target.write_text(
        "\n".join(lines)
        + solution_template(
            "cpp"
        ),
        encoding="utf-8",
    )

    return target


# ============================================================
# Generic menu
# ============================================================

def first_enabled(options) -> int:
    for i, option in enumerate(options):
        if option.get("enabled", True):
            return i
    return 0


def move_enabled(options, current: int, direction: int) -> int:
    if not options:
        return 0

    candidate = current

    for _ in range(len(options)):
        candidate = (candidate + direction) % len(options)

        if options[candidate].get("enabled", True):
            return candidate

    return current


def _control_dashboard_lines(
    problem,
    snapshot,
):
    problem_lines = [
        problem_line(problem),
        problem_status(problem),
    ]

    if problem is not None:
        try:
            solution = (
                current_catalog_solution(
                    problem
                )
            )
        except Exception:
            solution = None

        if solution is not None:
            language = (
                "C++"
                if solution.language == "cpp"
                else (
                    "Python"
                    if solution.language == "python"
                    else solution.language
                )
            )
            problem_lines.append(
                f"解法 {language}"
                f" · 複雜度 {solution.complexity or '未記錄'}"
            )

        try:
            bundle = TEST_ASSETS.load(
                problem.get("source"),
                problem["id"],
                include_candidates=True,
            )
            inventory = TEST_ASSETS.inventory(
                bundle
            )
        except Exception:
            inventory = {
                "official": 0,
                "verified": 0,
                "candidate": 0,
                "total": 0,
            }

        if inventory["total"]:
            problem_lines.append(
                "測資 "
                f"官方 {inventory['official']}"
                f" · 已驗證 {inventory['verified']}"
            )

        if problem.get("url"):
            problem_lines.append(
                "OJ 已連結"
            )

    plan = snapshot["plan"]
    protected = max(
        0,
        snapshot["capacity_minutes"]
        - plan.budget_minutes,
    )
    today_lines = [
        (
            f"{snapshot['capacity_minutes']} 分"
            f" · 複習 {plan.selected_minutes}/"
            f"{plan.budget_minutes} 分"
        ),
        (
            f"新學習 ≥ {protected} 分"
            + (
                f" · {snapshot['new_learning'].skill.uid}"
                if (
                    snapshot["new_learning"] is not None
                    and snapshot["new_learning"].skill is not None
                )
                else ""
            )
        ),
    ]

    if plan.selected:
        today_lines.append(
            f"到期複習 {len(plan.selected)} 項"
        )
    else:
        today_lines.append(
            "今天沒有到期複習"
        )

    if snapshot.get(
        "cognitive_tasks"
    ):
        today_lines.append(
            f"認知修復 {len(snapshot['cognitive_tasks'])} 項"
        )

    return problem_lines, today_lines



def print_control_dashboard(
    problem,
    snapshot,
) -> None:
    problem_lines, today_lines = (
        _control_dashboard_lines(
            problem,
            snapshot,
        )
    )
    width = ui_width()

    if width >= 88:
        gap = 3
        left_width = (
            width - gap
        ) // 2
        right_width = (
            width - gap - left_width
        )

        print(
            f"{CYAN}{BOLD}"
            f"{pad_display('目前題目', left_width)}"
            f"{RESET}"
            " │ "
            f"{CYAN}{BOLD}"
            f"{pad_display('今日規劃', right_width)}"
            f"{RESET}"
        )

        rows = max(
            len(problem_lines),
            len(today_lines),
        )
        for index in range(rows):
            left = (
                problem_lines[index]
                if index < len(problem_lines)
                else ""
            )
            right = (
                today_lines[index]
                if index < len(today_lines)
                else ""
            )
            print(
                f"{pad_display(left, left_width)}"
                " │ "
                f"{fit(right, right_width)}"
            )
    else:
        print(
            f"{CYAN}{BOLD}"
            "目前題目"
            f"{RESET}"
        )
        for line in problem_lines:
            print_wrapped(
                line,
                width,
                color=(
                    WHITE
                    if line == problem_lines[0]
                    else GRAY
                ),
            )

        print()
        print(
            f"{CYAN}{BOLD}"
            "今日規劃"
            f"{RESET}"
        )
        for index, line in enumerate(
            today_lines
        ):
            color = (
                GREEN
                if (
                    index == 2
                    and not snapshot["plan"].selected
                )
                else GRAY
            )
            print_wrapped(
                line,
                width,
                color=color,
            )

    if snapshot["curriculum_blocker"]:
        print_wrapped(
            "⚠ 新學習暫時無法啟動："
            + snapshot["curriculum_blocker"],
            width,
            color=YELLOW,
        )

    if snapshot["warning"]:
        print_wrapped(
            f"⚠ {snapshot['warning']}",
            width,
            color=YELLOW,
        )


def choose_menu(
    title: str,
    options,
    *,
    problem=None,
    main=False,
    footer_numbers=True,
    back_text: str | None = None,
    selected_index: int | None = None,
    enter_text: str | None = None,
    mode_toggle: bool = False,
):
    if (
        selected_index is not None
        and 0 <= selected_index < len(options)
        and options[selected_index].get("enabled", True)
    ):
        selected = selected_index
    else:
        selected = first_enabled(options)

    # Nothing that changes while merely moving the cursor needs to be
    # recomputed.  In particular, avoid re-reading adaptive state on every
    # ↑/↓ keypress.
    snapshot = (
        adaptive_today_snapshot()
        if main
        else None
    )
    while True:
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            heading(title)
            print()

            if main and snapshot is not None:
                print_control_dashboard(
                    problem,
                    snapshot,
                )
                if mode_toggle:
                    print()
                    print_selection_mode_banner()
                print()

            elif mode_toggle:
                print_selection_mode_banner()
                print()

            elif problem is not None:
                print_problem_context(problem)
                print()

            rule()
            print()

            window = 6

            if len(options) <= window:
                start = 0
                end = len(options)
            else:
                start = max(0, selected - 2)
                start = min(start, len(options) - window)
                end = start + window

            if start > 0:
                print(f"{GRAY}  ↑ 還有 {start} 項{RESET}")
                print()

            last_section = None

            for index in range(start, end):
                option = options[index]
                section = option.get("section")

                if section and section != last_section:
                    print(f"{GRAY}{section}{RESET}")
                    last_section = section

                enabled = option.get("enabled", True)
                prefix = "›" if index == selected else " "
                number = index + 1

                label_lines = wrap_display(
                    option["label"],
                    max(1, ui_width() - 6),
                )

                if not enabled:
                    label_color = GRAY
                elif index == selected:
                    label_color = CYAN + BOLD
                else:
                    label_color = ""

                for line_index, line in enumerate(label_lines):
                    if line_index == 0:
                        lead = f"{prefix} {number}  "
                    else:
                        lead = "     "

                    if label_color:
                        print(
                            f"{label_color}{lead}{line}{RESET}"
                        )
                    else:
                        print(f"{lead}{line}")

                detail = option.get("detail", "")

                if detail:
                    # Disabled is unavailable context, not an error.
                    # Reserve red for actual failure / destructive warnings.
                    detail_color = GRAY
                    print_wrapped(
                        detail,
                        max(1, ui_width() - 5),
                        prefix="     ",
                        continuation_prefix="     ",
                        color=detail_color,
                    )

                print()

            if end < len(options):
                print(
                    f"{GRAY}"
                    f"  ↓ 還有 {len(options) - end} 項"
                    f"{RESET}"
                )
                print()

            rule()

            selected_action = (
                options[selected].get("action")
                or enter_text
                or ("開啟" if main else "選擇")
            )

            if main:
                print(
                    f"{GRAY}"
                    f"↑↓ 選擇 · Enter {selected_action}"
                    f"{RESET}"
                )
                extra = (
                    " · M 切換選題模式"
                    if mode_toggle
                    else ""
                )
                print(
                    f"{GRAY}"
                    f"1–{len(options)} 直達"
                    f"{extra} · Esc / Q 關閉"
                    f"{RESET}"
                )
            else:
                print(
                    f"{GRAY}"
                    f"↑↓ 選擇 · Enter {selected_action}"
                    f"{RESET}"
                )
                label = back_text or "返回控制中心"
                extra = (
                    "M 切換選題模式 · "
                    if mode_toggle
                    else ""
                )
                print(
                    f"{GRAY}"
                    f"{extra}Esc / Q {label}"
                    f"{RESET}"
                )

        # Render the completed frame in one write.  Always clear the visible
        # terminal before redrawing: a HOME-only redraw is unsafe when the
        # previous frame wrapped or scrolled, because HOME then targets the
        # current viewport rather than the original frame origin and stale
        # text can remain on screen.
        sys.stdout.write(
            "\033[2J\033[H"
            + output.getvalue()
        )
        sys.stdout.flush()

        key = read_key()

        if key == "UP":
            selected = move_enabled(options, selected, -1)

        elif key == "DOWN":
            selected = move_enabled(options, selected, 1)

        elif key == "ENTER":
            if options[selected].get("enabled", True):
                return selected

        elif (
            mode_toggle
            and key in {"m", "M"}
        ):
            return MODE_TOGGLE

        elif key in {"ESC", "q", "Q"}:
            return None

        elif footer_numbers and key.isdigit():
            value = int(key)

            if 1 <= value <= len(options):
                index = value - 1

                if options[index].get("enabled", True):
                    return index


def _grid_rows(
    options,
    columns: int,
):
    rows = []
    current_section = None
    current = []

    for index, option in enumerate(options):
        section = option.get("section") or ""

        if (
            current
            and (
                section != current_section
                or len(current) >= columns
            )
        ):
            rows.append(
                (
                    current_section,
                    tuple(current),
                )
            )
            current = []

        if not current:
            current_section = section

        current.append(index)

    if current:
        rows.append(
            (
                current_section,
                tuple(current),
            )
        )

    return rows


def choose_grid(
    title: str,
    options,
    *,
    problem=None,
    main=False,
    back_text: str | None = None,
    selected_index: int | None = None,
    enter_text: str = "開啟",
    mode_toggle: bool = False,
    wide_columns: int = 3,
    compact_columns: int = 2,
):
    """Responsive spatial navigation for compact command-center choices.

    Wide terminals use a 3-column grid, compact terminals use 2 columns,
    and narrow terminals fall back to the proven linear menu.
    """

    width = ui_width()
    if width < 64:
        result = choose_menu(
            title,
            options,
            problem=problem,
            main=main,
            footer_numbers=True,
            back_text=back_text,
            selected_index=selected_index,
            enter_text=enter_text,
            mode_toggle=mode_toggle,
        )
        return result

    columns = (
        max(1, int(wide_columns))
        if width >= 86
        else max(1, int(compact_columns))
    )
    rows = _grid_rows(
        options,
        columns,
    )

    if (
        selected_index is not None
        and 0 <= selected_index < len(options)
        and options[selected_index].get(
            "enabled",
            True,
        )
    ):
        selected = selected_index
    else:
        selected = first_enabled(
            options
        )

    snapshot = (
        adaptive_today_snapshot()
        if main
        else None
    )

    def locate(index):
        for row_index, (_, indexes) in enumerate(rows):
            if index in indexes:
                return (
                    row_index,
                    indexes.index(index),
                )
        return (0, 0)

    def move_vertical(direction):
        nonlocal selected
        row_index, col_index = locate(
            selected
        )
        target = row_index + direction

        while 0 <= target < len(rows):
            indexes = rows[target][1]
            candidates = [
                index
                for index in indexes
                if options[index].get(
                    "enabled",
                    True,
                )
            ]
            if candidates:
                desired = min(
                    col_index,
                    len(indexes) - 1,
                )
                ordered = sorted(
                    candidates,
                    key=lambda index: abs(
                        indexes.index(index)
                        - desired
                    ),
                )
                selected = ordered[0]
                return
            target += direction

    def move_horizontal(direction):
        nonlocal selected
        row_index, col_index = locate(
            selected
        )
        indexes = rows[row_index][1]
        enabled = [
            index
            for index in indexes
            if options[index].get(
                "enabled",
                True,
            )
        ]
        if len(enabled) <= 1:
            return

        position = enabled.index(
            selected
        )
        selected = enabled[
            (
                position + direction
            )
            % len(enabled)
        ]

    while True:
        output = io.StringIO()

        with contextlib.redirect_stdout(
            output
        ):
            heading(title)
            print()

            if main and snapshot is not None:
                print_control_dashboard(
                    problem,
                    snapshot,
                )
                if mode_toggle:
                    print()
                    print_selection_mode_banner()
                print()
            elif mode_toggle:
                print_selection_mode_banner()
                print()
            elif problem is not None:
                print_problem_context(
                    problem
                )
                print()

            cell_gap = 3
            cell_width = max(
                14,
                (
                    width
                    - cell_gap * (columns - 1)
                )
                // columns,
            )

            previous_section = None
            for section, indexes in rows:
                if (
                    section
                    and section
                    != previous_section
                ):
                    if previous_section is not None:
                        print()
                    print(
                        f"{GRAY}"
                        f"{section}"
                        f"{RESET}"
                    )
                previous_section = section

                cells = []
                for index in indexes:
                    option = options[index]
                    enabled = option.get(
                        "enabled",
                        True,
                    )
                    prefix = (
                        "›"
                        if index == selected
                        else " "
                    )
                    label = (
                        f"{prefix} {index + 1} "
                        f"{option['label']}"
                    )
                    clipped = pad_display(
                        label,
                        cell_width,
                    )

                    if not enabled:
                        cells.append(
                            f"{GRAY}{clipped}{RESET}"
                        )
                    elif index == selected:
                        cells.append(
                            f"{CYAN}{BOLD}"
                            f"{clipped}"
                            f"{RESET}"
                        )
                    else:
                        cells.append(
                            clipped
                        )

                print(
                    (" " * cell_gap).join(
                        cells
                    )
                )

            detail = options[selected].get(
                "detail",
                "",
            )
            if detail:
                print()
                print_wrapped(
                    detail,
                    width,
                    color=GRAY,
                )

            print()
            rule()
            footer = (
                "←→ 選擇 · ↑↓ 換列"
                f" · Enter "
                f"{options[selected].get('action') or enter_text}"
            )
            if mode_toggle:
                footer += " · M 切換選題模式"
            print(
                f"{GRAY}{footer}{RESET}"
            )
            label = (
                back_text
                or (
                    "關閉"
                    if main
                    else "返回"
                )
            )
            direct = (
                f"1–{len(options)} 直達 · "
                if len(options) <= 9
                else ""
            )
            print(
                f"{GRAY}"
                f"{direct}"
                f"Esc / Q {label}"
                f"{RESET}"
            )

        sys.stdout.write(
            "\033[2J\033[H"
            + output.getvalue()
        )
        sys.stdout.flush()

        key = read_key()

        if key == "LEFT":
            move_horizontal(-1)
        elif key == "RIGHT":
            move_horizontal(1)
        elif key == "UP":
            move_vertical(-1)
        elif key == "DOWN":
            move_vertical(1)
        elif key == "ENTER":
            if options[selected].get(
                "enabled",
                True,
            ):
                return selected
        elif (
            mode_toggle
            and key in {"m", "M"}
        ):
            return MODE_TOGGLE
        elif key in {
            "ESC",
            "q",
            "Q",
        }:
            return None
        elif key.isdigit():
            value = int(key)
            if 1 <= value <= len(options):
                index = value - 1
                if options[index].get(
                    "enabled",
                    True,
                ):
                    return index


# ============================================================
# Recall
# ============================================================

def review_result_menu(
    problem,
    *,
    initial: str | None = None,
) -> str | None:
    options = [
        ("AC", "通過", "答案正確，完整通過測試"),
        ("WA", "答案錯誤", "程式可執行，但答案不正確"),
        ("TLE", "執行逾時", "時間複雜度或實作速度不足"),
        ("RE", "執行錯誤", "執行期間發生錯誤"),
        ("MLE", "記憶體超限", "使用記憶體超過限制"),
        ("CE", "編譯失敗", "本次程式無法成功編譯"),
    ]

    selected = next(
        (
            index
            for index, item in enumerate(options)
            if item[0] == initial
        ),
        0,
    )

    while True:
        clear()
        heading("複習結果")
        print()

        print_problem_context(problem)
        print()

        rule()
        print()
        print(f"{GRAY}這次重新解題的結果{RESET}")
        print()

        window = 5
        first = max(0, selected - 2)
        first = min(
            first,
            max(0, len(options) - window),
        )
        last = min(
            len(options),
            first + window,
        )

        if first > 0:
            print(
                f"{GRAY}"
                f"  ↑ 還有 {first} 項"
                f"{RESET}"
            )
            print()

        for index in range(first, last):
            result, label, detail = options[index]
            prefix = "›" if index == selected else " "
            color = (
                CYAN + BOLD
                if index == selected
                else ""
            )

            print(
                f"{color}"
                f"{prefix} {index + 1}  "
                f"{result} · {label}"
                f"{RESET}"
            )
            print_wrapped(
                detail,
                max(1, ui_width() - 5),
                prefix="     ",
                continuation_prefix="     ",
                color=GRAY,
            )
            print()

        if last < len(options):
            print(
                f"{GRAY}"
                f"  ↓ 還有 {len(options) - last} 項"
                f"{RESET}"
            )
            print()

        rule()
        print(f"{GRAY}↑↓ 選擇 · Enter 確認{RESET}")
        print(
            f"{GRAY}"
            "1–6 直達 · Esc / Q 返回上一步／取消"
            f"{RESET}"
        )

        key = read_key()

        if key == "UP":
            selected = (selected - 1) % len(options)
        elif key == "DOWN":
            selected = (selected + 1) % len(options)
        elif key == "ENTER":
            return options[selected][0]
        elif key in {"ESC", "q", "Q"}:
            return None
        elif key in {"1", "2", "3", "4", "5", "6"}:
            return options[int(key) - 1][0]


def recall_menu(
    title: str,
    problem,
    *,
    result: str = "AC",
    initial: int | None = None,
) -> int | None:
    if result == "AC":
        entries = [
            (
                0,
                "幾乎不會／需看答案",
                "無法自行重建；需要回到學習／修復",
            ),
            (
                1,
                "需要提示",
                "有部分記憶，但不能穩定獨立完成",
            ),
            (
                2,
                "可獨立但偏慢",
                "能完成，但流暢度／穩定度仍不足",
            ),
            (
                3,
                "流暢獨立",
                "高 Recall；不代表永久 Mastered",
            ),
        ]
    else:
        entries = [
            (
                0,
                "幾乎不會／需看答案",
                "本次失敗且無法自行重建",
            ),
            (
                1,
                "需要提示才能推進",
                "有部分理解，但仍存在關鍵缺口",
            ),
            (
                2,
                "主要思路可獨立完成",
                "方法大致成立，但本次 Judge 未通過",
            ),
        ]

    selected = next(
        (
            index
            for index, (score, _, _) in enumerate(entries)
            if score == initial
        ),
        0,
    )

    while True:
        clear()
        heading(title)
        print()

        print_problem_context(problem)

        if title == "複習題目":
            color = GREEN if result == "AC" else YELLOW
            print(
                f"{color}"
                f"本次結果 · {result}"
                f"{RESET}"
            )

        print()
        rule()
        print()
        print(f"{GRAY}這次掌握程度{RESET}")
        print()

        for index, (score, label, detail) in enumerate(entries):
            prefix = "›" if index == selected else " "
            color = (
                CYAN + BOLD
                if index == selected
                else ""
            )

            print(
                f"{color}"
                f"{prefix} {score}  {label}"
                f"{RESET}"
            )
            print_wrapped(
                detail,
                max(1, ui_width() - 5),
                prefix="     ",
                continuation_prefix="     ",
                color=GRAY,
            )
            print()

        rule()
        print(f"{GRAY}↑↓ 選擇 · Enter 確認{RESET}")
        range_hint = "0–3" if result == "AC" else "0–2"
        print(
            f"{GRAY}"
            f"{range_hint} 直達 · Esc / Q 返回上一步／取消"
            f"{RESET}"
        )

        key = read_key()

        if key == "UP":
            selected = (selected - 1) % len(entries)
        elif key == "DOWN":
            selected = (selected + 1) % len(entries)
        elif key == "ENTER":
            return entries[selected][0]
        elif key in {"ESC", "q", "Q"}:
            return None
        elif key.isdigit():
            value = int(key)
            allowed = {
                score
                for score, _, _ in entries
            }
            if value in allowed:
                return value


def minutes_input(
    title: str,
    problem,
    *,
    result: str = "AC",
    score: int,
    initial: int | None = None,
) -> int | None | object:
    value = (
        str(initial)
        if isinstance(initial, int)
        else ""
    )

    while True:
        clear()
        heading("練習耗時")
        print()

        print_problem_context(problem)
        print()

        if title == "複習題目":
            color = GREEN if result == "AC" else YELLOW
            print(
                f"結果    "
                f"{color}{result}{RESET}"
            )

        print(f"Recall  {score}")
        print()

        rule()
        print()
        print("本次實際解題大約花了幾分鐘？")
        print()

        shown = value if value else "—"
        print(
            f"{CYAN}{BOLD}"
            f"分鐘  {shown}"
            f"{RESET}"
        )

        print()
        rule()
        print(
            f"{GRAY}"
            "輸入數字 · Backspace 修改"
            f"{RESET}"
        )
        print(
            f"{GRAY}"
            "Enter 確認 · 空白 Enter 略過"
            f"{RESET}"
        )
        print(
            f"{GRAY}"
            "Esc / Q 返回上一步"
            f"{RESET}"
        )

        key = read_key()

        if key == "ENTER":
            if not value:
                return None

            minutes = int(value)

            if 1 <= minutes <= 999:
                return minutes

        elif key in {"ESC", "q", "Q"}:
            return RECORD_BACK

        elif key in {"\x7f", "\b"}:
            value = value[:-1]

        elif key.isdigit():
            candidate = value + key

            if int(candidate) <= 999:
                value = candidate


ASSISTANCE_OPTIONS = [
    (
        0,
        "A0 · 無提示",
        "完全沒有收到提示",
    ),
    (
        1,
        "A1 · 診斷問題",
        "只收到定位問題的診斷提問",
    ),
    (
        2,
        "A2 · 概念／性質",
        "收到關鍵概念、性質或表示提示",
    ),
    (
        3,
        "A3 · 演算法方向",
        "收到方法或演算法方向",
    ),
    (
        4,
        "A4 · pseudocode / skeleton",
        "收到偽碼、骨架或接近實作的提示",
    ),
    (
        5,
        "A5 · 完整解法 / reference",
        "看過完整解法、reference 或等價答案",
    ),
]


def assistance_menu(
    problem,
    *,
    initial: int | None = None,
) -> int | None:
    options = [
        {
            "label": label,
            "detail": detail,
            "enabled": True,
        }
        for _, label, detail
        in ASSISTANCE_OPTIONS
    ]

    selected_index = next(
        (
            index
            for index, (value, _, _)
            in enumerate(ASSISTANCE_OPTIONS)
            if value == initial
        ),
        None,
    )

    selected = choose_menu(
        "最高 Assistance",
        options,
        problem=problem,
        main=False,
        back_text="返回上一步",
        selected_index=selected_index,
    )

    if selected is None:
        return None

    return ASSISTANCE_OPTIONS[
        selected
    ][0]


def yes_no_menu(
    title: str,
    problem,
    *,
    yes_detail: str,
    no_detail: str,
    default_yes: bool = True,
    initial: bool | None = None,
) -> bool | None:
    options = [
        {
            "label": "是",
            "detail": yes_detail,
            "enabled": True,
        },
        {
            "label": "否",
            "detail": no_detail,
            "enabled": True,
        },
    ]

    if not default_yes:
        options.reverse()

    selected_index = None

    if initial is not None:
        wanted = "是" if initial else "否"
        selected_index = next(
            (
                index
                for index, option
                in enumerate(options)
                if option["label"] == wanted
            ),
            None,
        )

    selected = choose_menu(
        title,
        options,
        problem=problem,
        main=False,
        footer_numbers=False,
        back_text="返回上一步",
        selected_index=selected_index,
    )

    if selected is None:
        return None

    return options[selected]["label"] == "是"


def independent_menu(
    problem,
    assistance: int,
    *,
    initial: bool | None = None,
) -> bool | None:
    # Curriculum Authoring Standard: A2+ 不可標為 independent。
    if assistance >= 2:
        return False

    return yes_no_menu(
        "是否獨立完成",
        problem,
        yes_detail=(
            "方法與實作主要由你自行完成；"
            "A0/A1 可成立"
        ),
        no_detail=(
            "雖然最高提示不超過 A1，"
            "但實際完成仍依賴他人／AI"
        ),
        default_yes=True,
        initial=initial,
    )


def compact_support_menu(
    problem,
    *,
    initial: dict | None = None,
):
    """一次收集 Assistance + Independent，降低 Published Runtime 摩擦。"""

    values = [
        (
            0,
            True,
            "A0 · 無提示／獨立",
            "沒有提示，方法與實作主要由你自行完成",
        ),
        (
            0,
            False,
            "A0 · 無提示／非獨立",
            "沒有提示，但完成仍依賴他人、既有答案或外部協助",
        ),
        (
            1,
            True,
            "A1 · 診斷問題／獨立",
            "只收到診斷性提問，之後主要由你自行完成",
        ),
        (
            1,
            False,
            "A1 · 診斷問題／非獨立",
            "最高只有 A1，但實際完成仍依賴他人／AI",
        ),
        (
            2,
            False,
            "A2 · 概念／性質",
            "收到關鍵概念、性質或表示提示；Independent 自動為否",
        ),
        (
            3,
            False,
            "A3 · 演算法方向",
            "收到方法或演算法方向；Independent 自動為否",
        ),
        (
            4,
            False,
            "A4 · pseudocode / skeleton",
            "收到偽碼、骨架或接近實作的提示；Independent 自動為否",
        ),
        (
            5,
            False,
            "A5 · 完整解法 / reference",
            "看過完整解法、reference 或等價答案；Independent 自動為否",
        ),
    ]

    selected_index = None
    if initial is not None:
        selected_index = next(
            (
                index
                for index, (assistance, independent, _, _)
                in enumerate(values)
                if assistance == initial.get("assistance")
                and independent == initial.get("independent")
            ),
            None,
        )

    selected = choose_menu(
        "作答支援",
        [
            {
                "label": label,
                "detail": detail,
                "enabled": True,
            }
            for _, _, label, detail in values
        ],
        problem=problem,
        main=False,
        footer_numbers=False,
        back_text="返回上一步",
        selected_index=selected_index,
    )

    if selected is None:
        return None

    assistance, independent, _, _ = values[selected]
    return {
        "assistance": assistance,
        "independent": independent,
    }


def inferred_published_novelty(
    action: str,
    problem,
    placement,
) -> str | None:
    runtime_action = problem.get("runtime_action")

    if action == "review" and runtime_action == "review":
        return "delayed_retest"

    if action == "finish" and runtime_action == "finish":
        if placement is not None:
            if placement.role == "Transfer Challenge":
                return "transfer"
            if placement.role == "Mock":
                return "mixed"
        return "new"

    return None


def inferred_published_timed(problem) -> bool | None:
    try:
        session = EXAM.active()
    except ExamRuntimeError:
        session = None

    if session is not None:
        problem_id = (
            str(problem.get("id") or "")
            .strip()
            .casefold()
        )
        selected_id = (
            str(session.get("selected_problem_id") or "")
            .strip()
            .casefold()
        )
        if problem_id and problem_id == selected_id:
            return True

    if problem.get("runtime_action") in {
        "finish",
        "review",
    }:
        return False

    return None


def published_evidence_context_menu(
    action: str,
    problem,
    *,
    initial: dict | None = None,
    track: str = "Implementation",
):
    """Published Runtime 只詢問無法可靠自動取得的 learner facts。"""

    placement, placement_warning = placement_for_record(
        problem
    )
    if placement_warning == "__CANCEL__":
        return RECORD_BACK

    state = dict(initial or {})
    state["placement"] = placement
    state["placement_warning"] = placement_warning

    support = compact_support_menu(
        problem,
        initial=state,
    )
    if support is None:
        return RECORD_BACK

    state.update(support)

    novelty = inferred_published_novelty(
        action,
        problem,
        placement,
    )
    if novelty is None:
        novelty = novelty_menu(
            action,
            problem,
            placement=placement,
            initial=state.get("novelty"),
        )
        if novelty is None:
            return RECORD_BACK
    state["novelty"] = novelty

    timed = inferred_published_timed(
        problem
    )
    if timed is None:
        timed = timed_menu(
            problem,
            initial=state.get("timed"),
        )
        if timed is None:
            return RECORD_BACK
    state["timed"] = timed

    if (
        track == "Implementation"
        and placement is not None
        and placement.method_confirmation_required
    ):
        method_confirmed = target_method_confirmation_menu(
            problem,
            placement,
            initial=state.get(
                "method_confirmed"
            ),
        )
        if method_confirmed is None:
            return RECORD_BACK
        state["method_confirmed"] = (
            method_confirmed
        )
    else:
        state["method_confirmed"] = None

    return state


def novelty_menu(
    action: str,
    problem,
    *,
    placement=None,
    initial: str | None = None,
) -> str | None:
    if action == "review":
        values = [
            (
                "delayed_retest",
                "Delayed Retest",
                "隔了一段時間後重新提取與完成",
            ),
            (
                "seen",
                "Seen",
                "近期已看過或做過，本次再練習",
            ),
            (
                "same_problem_repeat",
                "Same-problem Repeat",
                "同一段學習內立即／短期重做同題",
            ),
        ]
    else:
        values = [
            (
                "new",
                "New",
                "第一次正式接觸或沒有可用記憶",
            ),
            (
                "transfer",
                "Transfer",
                "陌生變形；需要把既有技能遷移過來",
            ),
            (
                "seen",
                "Seen",
                "以前已看過或做過這題",
            ),
            (
                "mixed",
                "Mixed",
                "限時混合／Mock 中的一部分",
            ),
        ]

        if (
            placement is not None
            and placement.role
            == "Transfer Challenge"
        ):
            values = [
                values[1],
                values[0],
                values[2],
                values[3],
            ]

        if (
            placement is not None
            and placement.role == "Mock"
        ):
            values = [
                values[3],
                values[0],
                values[1],
                values[2],
            ]

    options = [
        {
            "label": label,
            "detail": detail,
            "enabled": True,
        }
        for _, label, detail in values
    ]

    selected_index = next(
        (
            index
            for index, (value, _, _)
            in enumerate(values)
            if value == initial
        ),
        None,
    )

    selected = choose_menu(
        "題目新鮮度",
        options,
        problem=problem,
        main=False,
        footer_numbers=False,
        back_text="返回上一步",
        selected_index=selected_index,
    )

    if selected is None:
        return None

    return values[selected][0]


def timed_menu(
    problem,
    *,
    initial: bool | None = None,
) -> bool | None:
    return yes_no_menu(
        "是否限時",
        problem,
        yes_detail=(
            "本次有事先明確設定 timebox / 正式限時"
        ),
        no_detail=(
            "有記錄耗時不等於 Timed；"
            "一般練習選否"
        ),
        default_yes=False,
        initial=initial,
    )


def target_method_confirmation_menu(
    problem,
    placement,
    *,
    initial: bool | None = None,
) -> bool | None:
    skill = CURRICULUM.skill_context(
        placement.primary_skill
    )
    requirement = (
        skill.implementation_requirement
        if skill is not None
        else placement.primary_skill
    )

    return yes_no_menu(
        "實際方法確認",
        problem,
        yes_detail=(
            f"本次解法確實展現 {placement.primary_skill}："
            f"{requirement}"
        ),
        no_detail=(
            "本次使用其他合法方法；Attempt 仍保存，"
            f"但不建立 {placement.primary_skill} Evidence"
        ),
        default_yes=True,
        initial=initial,
    )


def placement_for_record(
    problem,
):
    try:
        contexts = (
            CURRICULUM
            .placements_for_problem(
                problem["id"]
            )
        )
    except RuntimeCurriculumError as exc:
        return None, str(exc)

    if not contexts:
        return (
            None,
            "此題尚未出現在 Published curriculum；"
            "本次只保存 Attempt，不建立 Skill Evidence。",
        )

    requested_uid = problem.get(
        "placement_uid"
    )

    if requested_uid:
        exact = next(
            (
                context
                for context in contexts
                if context.placement_uid
                == requested_uid
            ),
            None,
        )

        if exact is not None:
            return exact, None

    if len(contexts) == 1:
        return contexts[0], None

    options = []

    for context in contexts:
        supporting = (
            ", ".join(
                context.supporting_skills
            )
            if context.supporting_skills
            else "—"
        )

        options.append(
            {
                "label": (
                    f"{context.primary_skill}"
                    f" · {context.role}"
                ),
                "detail": (
                    f"{context.placement_uid}"
                    f" · supporting {supporting}"
                ),
                "enabled": True,
            }
        )

    selected = choose_menu(
        "本次 Curriculum Placement",
        options,
        problem=problem,
        main=False,
        footer_numbers=False,
        back_text="取消本次紀錄",
    )

    if selected is None:
        return None, "__CANCEL__"

    return contexts[selected], None


def attempt_envelope_for_record(
    *,
    action: str,
    problem,
    result: str,
    minutes: int | None,
    assistance: int,
    independent: bool,
    novelty: str,
    timed: bool,
    placement=None,
    method_confirmed: bool | None = None,
    finished_at: dt.datetime | None = None,
    track: str = "Implementation",
    evidence_outcome: str | None = None,
):
    if action not in {"finish", "review"}:
        raise ValueError(
            f"unsupported action={action!r}"
        )

    finished_at = (
        finished_at
        or dt.datetime.now().astimezone()
    )

    language = {
        ".cpp": "cpp",
        ".py": "python",
    }.get(
        Path(problem["path"])
        .suffix
        .lower(),
        "unknown",
    )

    activity = (
        "Review"
        if action == "review"
        else (
            placement.role
            if placement is not None
            else None
        )
    )

    evidence = []
    attempt_note = ""

    if track not in {"Reading", "Implementation"}:
        raise ValueError(
            f"unsupported Evidence track={track!r}"
        )

    if track == "Reading":
        if evidence_outcome not in {
            "PASS",
            "PARTIAL",
            "FAIL",
        }:
            raise ValueError(
                "Reading Evidence requires PASS/PARTIAL/FAIL outcome"
            )
        resolved_outcome = evidence_outcome
    else:
        resolved_outcome = (
            "PASS"
            if result == "AC"
            else "FAIL"
        )

    claim_allowed = (
        placement is not None
        and (
            track != "Implementation"
            or not placement.method_confirmation_required
            or method_confirmed is True
        )
    )

    if claim_allowed:
        claim_note = (
            f"{activity or 'Practice'}"
            f" · {resolved_outcome}"
        )

        if (
            track == "Implementation"
            and placement is not None
            and placement.method_confirmation_required
        ):
            claim_note += " · target method confirmed"

        evidence.append(
            (
                placement.primary_skill,
                track,
                resolved_outcome,
                claim_note,
            )
        )
    elif (
        track == "Implementation"
        and placement is not None
        and placement.method_confirmation_required
    ):
        attempt_note = (
            "Primary Skill evidence withheld: "
            "target method not confirmed for "
            f"{placement.primary_skill}"
        )

    return build_envelope(
        problem_id=problem["id"],
        pb_uid=(
            placement.pb_uid
            if placement is not None
            else None
        ),
        started_at=None,
        finished_at=finished_at,
        language=language,
        judge_result=result,
        assistance=assistance,
        independent=independent,
        attempt_count=None,
        active_minutes=minutes,
        timed=timed,
        novelty=novelty,
        activity=activity,
        note=attempt_note,
        evidence=evidence,
    )


def evidence_context_menu(
    action: str,
    problem,
    *,
    initial: dict | None = None,
    track: str = "Implementation",
):
    placement, placement_warning = (
        placement_for_record(
            problem
        )
    )

    if placement_warning == "__CANCEL__":
        return RECORD_BACK

    state = dict(initial or {})
    state["placement"] = placement
    state["placement_warning"] = placement_warning
    step = "assistance"

    while True:
        if step == "assistance":
            assistance = assistance_menu(
                problem,
                initial=state.get(
                    "assistance"
                ),
            )

            if assistance is None:
                return RECORD_BACK

            state["assistance"] = assistance

            if assistance >= 2:
                state["independent"] = False
                step = "novelty"
            else:
                step = "independent"

            continue

        if step == "independent":
            independent = independent_menu(
                problem,
                state["assistance"],
                initial=state.get(
                    "independent"
                ),
            )

            if independent is None:
                step = "assistance"
                continue

            state["independent"] = independent
            step = "novelty"
            continue

        if step == "novelty":
            novelty = novelty_menu(
                action,
                problem,
                placement=placement,
                initial=state.get(
                    "novelty"
                ),
            )

            if novelty is None:
                step = (
                    "independent"
                    if state["assistance"] < 2
                    else "assistance"
                )
                continue

            state["novelty"] = novelty
            step = "timed"
            continue

        timed = timed_menu(
            problem,
            initial=state.get(
                "timed"
            ),
        )

        if timed is None:
            step = "novelty"
            continue

        state["timed"] = timed

        if (
            track == "Implementation"
            and placement is not None
            and placement.method_confirmation_required
        ):
            method_confirmed = (
                target_method_confirmation_menu(
                    problem,
                    placement,
                    initial=state.get(
                        "method_confirmed"
                    ),
                )
            )

            if method_confirmed is None:
                step = "timed"
                continue

            state["method_confirmed"] = (
                method_confirmed
            )
        else:
            state["method_confirmed"] = None

        return state


def reading_outcome_menu(
    problem,
) -> str | None:
    options = [
        {
            "label": "PASS · 推理成立",
            "detail": "formal response 的 model / trace / conclusion 經驗證後成立",
            "enabled": True,
            "value": "PASS",
        },
        {
            "label": "PARTIAL · 部分成立",
            "detail": "核心方向有證據，但仍有局部錯誤、缺口或不確定性",
            "enabled": True,
            "value": "PARTIAL",
        },
        {
            "label": "FAIL · 未能重建",
            "detail": "關鍵推理不成立，或仍需要重新學習",
            "enabled": True,
            "value": "FAIL",
        },
    ]

    selected = choose_menu(
        "Reading Outcome",
        options,
        problem=problem,
        main=False,
        back_text="取消 Reading 紀錄",
    )
    if selected is None:
        return None
    return options[selected]["value"]


def record_reading_problem(
    action: str,
    problem,
) -> None:
    if action not in {"finish", "review"}:
        raise ValueError(
            f"unsupported Reading action={action!r}"
        )

    if not formal_response_ready(
        Path(problem["path"])
    ):
        clear()
        heading("Reading Evidence")
        print()
        print(
            f"{YELLOW}"
            "⚠ Formal response 尚未完成；本次不建立 Reading Evidence。"
            f"{RESET}"
        )
        print()
        print_wrapped(
            "先在 Reading scratch 留下 reason / trace 並儲存；"
            "reference / executor / Judge 只能在 formal response 之後使用。",
            ui_width(),
            color=GRAY,
        )
        pause()
        return

    outcome = reading_outcome_menu(
        problem
    )
    if outcome is None:
        return

    # Published Reading runtime already knows Activity / Novelty / Timed.
    # Do not ask for optional minutes here; Exam Runtime owns timed telemetry.
    minutes = None

    evidence_context = published_evidence_context_menu(
        action,
        problem,
        track="Reading",
    )
    if evidence_context is RECORD_BACK:
        return

    placement = evidence_context["placement"]

    clear()
    heading(
        "完成 Reading"
        if action == "finish"
        else "Reading Review"
    )
    print()
    print_problem_context(problem)
    print()
    print(f"Outcome     {outcome}")
    print(
        f"{GRAY}"
        "耗時        一般 Reading 不另要求填寫；限時資料由考試模式記錄"
        f"{RESET}"
    )
    print(
        f"Assistance  A{evidence_context['assistance']}"
    )
    print(
        "Independent "
        + (
            "是"
            if evidence_context["independent"]
            else "否"
        )
    )
    print(
        f"Novelty     {evidence_context['novelty']}"
    )
    print(
        "Timed       "
        + (
            "是"
            if evidence_context["timed"]
            else "否"
        )
    )
    if placement is not None:
        print(
            "Evidence    "
            f"{placement.primary_skill} × Reading"
        )
        print(f"Placement   {placement.role}")
    else:
        print(
            f"{YELLOW}"
            "Evidence    尚未建立（無 Published Placement）"
            f"{RESET}"
        )
    print()
    print_wrapped(
        "Reading Attempt 使用 Judge Result N/A；不會把 reasoning 偽裝成 AC。",
        ui_width(),
        color=GRAY,
    )
    print()

    if not confirm("確認保存 Reading Attempt / Evidence？"):
        return

    envelope = None
    outbox_warning = None
    memory_warning = None

    try:
        envelope = attempt_envelope_for_record(
            action=action,
            problem=problem,
            result="N/A",
            minutes=minutes,
            assistance=evidence_context["assistance"],
            independent=evidence_context["independent"],
            novelty=evidence_context["novelty"],
            timed=evidence_context["timed"],
            placement=placement,
            track="Reading",
            evidence_outcome=outcome,
        )
        OUTBOX.enqueue(envelope)
    except (
        EvidenceOutboxError,
        OSError,
        ValueError,
    ) as exc:
        outbox_warning = str(exc)

    if (
        envelope is not None
        and outbox_warning is None
    ):
        try:
            MEMORY.reconcile(
                OUTBOX.all_envelopes()
            )
        except (
            EvidenceOutboxError,
            OSError,
            ValueError,
        ) as exc:
            memory_warning = str(exc)

    clear()
    heading("Reading Evidence")
    print()

    if outbox_warning:
        print(
            f"{RED}"
            f"✕ local evidence outbox 寫入失敗：{outbox_warning}"
            f"{RESET}"
        )
        pause()
        return

    print(
        f"{GREEN}"
        "✓ Reading Attempt 已保存到 local evidence outbox"
        f"{RESET}"
    )
    if envelope is not None and envelope.evidence:
        claim = envelope.evidence[0]
        print(
            f"{GREEN}"
            f"✓ Evidence：{claim.skill_uid} × {claim.track} · {claim.outcome}"
            f"{RESET}"
        )
    if memory_warning:
        print(
            f"{YELLOW}"
            "⚠ Evidence 已保存，但 adaptive memory cache 更新失敗；"
            "下次 Today 會重新 reconciliation。"
            f"{RESET}"
        )
    else:
        print(
            f"{GREEN}✓ Adaptive memory 已更新{RESET}"
        )
    print()
    print(
        f"{GRAY}"
        "Remote sync 使用同一 durable writeback_id / event_id；"
        "Reading 不會要求重做 learner task。"
        f"{RESET}"
    )
    pause()


def record_problem(action: str, problem) -> None:
    published_runtime = bool(
        problem
        and problem.get(
            "published_runtime",
            False,
        )
    )

    if (
        problem is not None
        and problem.get("runtime_track") == "Reading"
    ):
        record_reading_problem(
            action,
            problem,
        )
        return
    title = (
        "完成題目"
        if action == "finish"
        else "複習題目"
    )
    result = "AC"
    score = None
    minutes = None
    evidence_context = None
    finish_complexity = None
    complexity_solution = None

    if action == "finish" and not published_runtime:
        try:
            complexity_solution = (
                missing_finish_complexity(
                    problem
                )
            )
        except CatalogError as exc:
            clear()
            heading(title)
            print()
            print(
                f"{RED}"
                f"✕ Catalog 無法讀取：{exc}"
                f"{RESET}"
            )
            pause()
            return

    if published_runtime:
        step = (
            "result"
            if action == "review"
            else "evidence"
        )
    else:
        step = (
            "result"
            if action == "review"
            else "recall"
        )

    while True:
        if step == "result":
            selected_result = (
                review_result_menu(
                    problem,
                    initial=result,
                )
            )

            if selected_result is None:
                return

            result = selected_result

            if (
                result != "AC"
                and score not in {0, 1, 2}
            ):
                score = None

            step = (
                "evidence"
                if published_runtime
                else "recall"
            )
            continue

        if step == "recall":
            selected_score = recall_menu(
                title,
                problem,
                result=result,
                initial=score,
            )

            if selected_score is None:
                if action == "review":
                    step = "result"
                    continue

                return

            score = selected_score
            step = "minutes"
            continue

        if step == "minutes":
            selected_minutes = minutes_input(
                title,
                problem,
                result=result,
                score=score,
                initial=minutes,
            )

            if selected_minutes is RECORD_BACK:
                step = "recall"
                continue

            minutes = selected_minutes
            step = "evidence"
            continue

        if step == "evidence":
            if published_runtime:
                selected_context = (
                    published_evidence_context_menu(
                        action,
                        problem,
                        initial=evidence_context,
                    )
                )
            else:
                selected_context = (
                    evidence_context_menu(
                        action,
                        problem,
                        initial=evidence_context,
                    )
                )

            if selected_context is RECORD_BACK:
                if published_runtime:
                    if action == "review":
                        step = "result"
                        continue
                    return
                step = "minutes"
                continue

            evidence_context = selected_context
            step = (
                "complexity"
                if complexity_solution is not None
                else "confirm"
            )
            continue

        if step == "complexity":
            clear()
            heading("完成題目 · 複雜度")
            print()
            print_problem_context(problem)
            print()
            print(
                f"{YELLOW}"
                "此解法尚未記錄複雜度。"
                f"{RESET}"
            )
            print(
                f"{GRAY}"
                "請先判斷演算法時間複雜度，例如 "
                "O(1)、O(N)、O(N log N)。"
                f"{RESET}"
            )
            print(
                f"{GRAY}"
                "Ctrl+C / 空白 Enter 可返回上一步"
                f"{RESET}"
            )
            print()

            value = prompt_text(
                "複雜度（必填）",
                current=finish_complexity,
                required=True,
            )

            if value is None:
                step = "evidence"
                continue

            finish_complexity = value
            step = "confirm"
            continue

        clear()
        heading(title)
        print()

        print(
            f"{WHITE}"
            f"{problem_line(problem)}"
            f"{RESET}"
        )
        print()

        if action == "review":
            color = GREEN if result == "AC" else YELLOW
            print(
                f"結果    "
                f"{color}{result}{RESET}"
            )

        if published_runtime:
            print(
                f"{GRAY}"
                "紀錄      Published Runtime · 只詢問必要 learner facts"
                f"{RESET}"
            )
        else:
            print(f"Recall  {score}")
            print(
                "耗時    "
                + (
                    f"{minutes} 分鐘"
                    if minutes is not None
                    else "未記錄"
                )
            )

        if complexity_solution is not None:
            print(
                "複雜度      "
                f"{CYAN}{finish_complexity}{RESET}"
            )

        placement = evidence_context["placement"]
        assistance = evidence_context["assistance"]
        assistance_label = next(
            label
            for value, label, _
            in ASSISTANCE_OPTIONS
            if value == assistance
        )

        print(
            "Assistance  "
            f"{CYAN}{assistance_label}{RESET}"
        )
        print(
            "Independent "
            + (
                f"{GREEN}是{RESET}"
                if evidence_context["independent"]
                else f"{YELLOW}否{RESET}"
            )
        )
        print(
            "Novelty     "
            f"{evidence_context['novelty']}"
        )
        print(
            "Timed       "
            + (
                "是"
                if evidence_context["timed"]
                else "否"
            )
        )

        if placement is not None:
            print(
                "Evidence    "
                f"{CYAN}{placement.primary_skill}"
                " × Implementation"
                f"{RESET}"
            )
            print(
                "Placement   "
                f"{placement.role}"
            )
            print(
                "Evidence cap "
                f"L{placement.evidence_level_cap}"
            )

            if placement.method_confirmation_required:
                confirmed = evidence_context.get(
                    "method_confirmed"
                )
                print(
                    "Target Method "
                    + (
                        f"{GREEN}是{RESET}"
                        if confirmed is True
                        else f"{YELLOW}否{RESET}"
                    )
                )

                if confirmed is not True:
                    print(
                        f"{YELLOW}"
                        "Attempt only · 不建立 "
                        f"{placement.primary_skill} Evidence"
                        f"{RESET}"
                    )
        else:
            print(
                f"{YELLOW}"
                "Evidence    尚未建立（無 Published Placement）"
                f"{RESET}"
            )

        placement_warning = evidence_context[
            "placement_warning"
        ]

        if placement_warning:
            print()
            print_wrapped(
                f"⚠ {placement_warning}",
                ui_width() - 2,
                color=YELLOW,
            )

        print()
        rule()
        print(
            f"{GRAY}"
            "Enter / Y 寫入 · Esc 返回上一步 · Q 取消"
            f"{RESET}"
        )

        key = read_key()

        if key in {"ENTER", "y", "Y"}:
            break

        if key == "ESC":
            step = (
                "complexity"
                if complexity_solution is not None
                else "evidence"
            )
            continue

        if key in {"q", "Q"}:
            return

    print()
    print(f"{GRAY}正在更新學習紀錄…{RESET}")

    try:
        if published_runtime:
            # The durable v2.3 outbox / Evidence envelope is the authoritative
            # local learning mutation for Published Curriculum scratch files.
            # Legacy progress.csv cannot represent namespaced CF/CSES/LC IDs.
            command_result = 0
        else:
            with contextlib.redirect_stdout(io.StringIO()):
                if action == "finish":
                    command_result = (
                        finish_with_optional_complexity(
                            problem["id"],
                            score,
                            minutes=minutes,
                            complexity_solution=(
                                complexity_solution
                            ),
                            complexity=finish_complexity,
                            finish_runner=(
                                lambda pid, recall, *, minutes=None:
                                core.finish_cmd(
                                    pid,
                                    recall,
                                    minutes=minutes,
                                    sync_after=False,
                                )
                            ),
                        )
                    )
                else:
                    command_result = core.review_cmd(
                        problem["id"],
                        score,
                        result=result,
                        minutes=minutes,
                        sync_after=False,
                    )

    except (
        SystemExit,
        CatalogError,
        OSError,
    ) as exc:
        print()
        print(
            f"{RED}"
            f"✕ 更新失敗：{exc}"
            f"{RESET}"
        )
        pause()
        return

    sync_warning = None
    outbox_warning = None
    memory_warning = None
    memory_report = None
    outbox_envelope = None

    if command_result == 0:
        try:
            outbox_envelope = (
                attempt_envelope_for_record(
                    action=action,
                    problem=problem,
                    result=result,
                    minutes=minutes,
                    assistance=evidence_context[
                        "assistance"
                    ],
                    independent=evidence_context[
                        "independent"
                    ],
                    novelty=evidence_context[
                        "novelty"
                    ],
                    timed=evidence_context[
                        "timed"
                    ],
                    placement=evidence_context[
                        "placement"
                    ],
                    method_confirmed=evidence_context.get(
                        "method_confirmed"
                    ),
                )
            )

            OUTBOX.enqueue(
                outbox_envelope
            )

        except (
            EvidenceOutboxError,
            OSError,
        ) as exc:
            outbox_warning = str(exc)

        if (
            outbox_envelope is not None
            and outbox_warning is None
        ):
            try:
                memory_report = (
                    MEMORY.reconcile(
                        OUTBOX.all_envelopes()
                    )
                )
            except (
                EvidenceOutboxError,
                OSError,
                ValueError,
            ) as exc:
                memory_warning = str(exc)

        if not published_runtime:
            sync_warning = (
                core.sync_generated_best_effort()
            )

    print()

    if command_result == 0:
        print(
            f"{GREEN}"
            f"✓ 學習紀錄已更新"
            f"{RESET}"
        )

        if complexity_solution is not None:
            print(
                f"{GREEN}"
                f"✓ 複雜度已寫入題目資料："
                f"{finish_complexity}"
                f"{RESET}"
            )

        if (
            outbox_envelope is not None
            and outbox_warning is None
        ):
            print(
                f"{GREEN}"
                "✓ Attempt 已保存到 local evidence outbox"
                f"{RESET}"
            )

            if outbox_envelope.evidence:
                claim = outbox_envelope.evidence[0]
                print(
                    f"{GREEN}"
                    f"✓ Evidence：{claim.skill_uid}"
                    f" × {claim.track}"
                    f"{RESET}"
                )
            else:
                print(
                    f"{YELLOW}"
                    "⚠ 尚無 Published Placement；"
                    "本次 Attempt 不更新 Skill Evidence"
                    f"{RESET}"
                )

        if (
            memory_report is not None
            and outbox_envelope is not None
            and outbox_envelope.evidence
        ):
            print(
                f"{GREEN}"
                "✓ Adaptive memory 已更新"
                f"{RESET}"
            )

        if memory_warning:
            print()
            print(
                f"{YELLOW}"
                "⚠ Attempt 已保存，但 adaptive memory cache 更新失敗。"
                f"{RESET}"
            )
            print(
                f"{GRAY}"
                f"{fit(memory_warning, ui_width())}"
                f"{RESET}"
            )
            print(
                f"{GRAY}"
                "Evidence 不會遺失；下次開啟 Today 會重新 reconciliation。"
                f"{RESET}"
            )

        if outbox_warning:
            print()
            print(
                f"{YELLOW}"
                "⚠ 學習紀錄已成功，但 local evidence outbox 寫入失敗。"
                f"{RESET}"
            )
            print(
                f"{GRAY}"
                f"{fit(outbox_warning, ui_width())}"
                f"{RESET}"
            )
            print(
                f"{GRAY}"
                "不要重做 Finish / Review；"
                "之後使用 reconciliation 修復 Evidence。"
                f"{RESET}"
            )

        if sync_warning:
            print()
            print(
                f"{YELLOW}"
                "⚠ 學習紀錄已成功寫入，但 generated sync 失敗。"
                f"{RESET}"
            )
            print(
                f"{GRAY}"
                f"{fit(sync_warning, ui_width())}"
                f"{RESET}"
            )
            print(
                f"{GRAY}"
                "不需要重做本次 Finish / Review；"
                "之後可單獨重新執行 sync。"
                f"{RESET}"
            )
    else:
        print(
            f"{RED}"
            f"✕ 學習紀錄更新失敗"
            f"{RESET}"
        )

    pause()



# ============================================================
# Catalog workflow
# ============================================================

PROBLEM_ID_RE = re.compile(r"^(?:[A-Za-z]\d+|\d+)$")


def normalize_problem_id(value: str) -> str:
    value = str(value).strip().lower()

    if not PROBLEM_ID_RE.fullmatch(value):
        raise CatalogError(
            "題號格式必須是英文字母+數字（例如 b130）或純數字"
        )

    return value


def solution_template(language: str) -> str:
    language = language.strip().lower()

    if language == "cpp":
        return (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n\n"
            "int main() {\n"
            "    ios::sync_with_stdio(false);\n"
            "    cin.tie(nullptr);\n\n"
            "    return 0;\n"
            "}\n"
        )

    if language == "python":
        return (
            "def main():\n"
            "    pass\n\n\n"
            'if __name__ == "__main__":\n'
            "    main()\n"
        )

    raise CatalogError(f"不支援的語言：{language}")


def next_solution_path(
    pid: str,
    language: str,
    *,
    root: Path = ROOT,
) -> Path:
    pid = normalize_problem_id(pid)
    language = language.strip().lower()

    suffix = {
        "cpp": ".cpp",
        "python": ".py",
    }.get(language)

    if suffix is None:
        raise CatalogError(f"不支援的語言：{language}")

    folder = Path(root) / "solutions"
    candidate = folder / f"{pid}{suffix}"
    index = 2

    while candidate.exists():
        candidate = folder / f"{pid}_{index}{suffix}"
        index += 1

    return candidate


def create_problem_assets(
    problem: ProblemMeta,
    language: str,
    complexity: str = "",
    *,
    root: Path = ROOT,
    store=None,
) -> Path:
    store = store or core.CATALOG
    pid = normalize_problem_id(problem.problem_id)

    normalized = ProblemMeta(
        problem_id=pid,
        title=problem.title,
        source=problem.source,
        difficulty=problem.difficulty,
        tags=problem.tags,
    )

    target = next_solution_path(
        pid,
        language,
        root=root,
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        solution_template(language),
        encoding="utf-8",
    )

    relative = target.relative_to(root).as_posix()

    try:
        store.create_problem_with_solution(
            normalized,
            SolutionMeta(
                problem_id=pid,
                path=relative,
                language=language,
                complexity=complexity,
            ),
        )
    except Exception:
        target.unlink(missing_ok=True)
        raise

    return target


def add_solution_asset(
    pid: str,
    language: str,
    complexity: str = "",
    *,
    root: Path = ROOT,
    store=None,
) -> Path:
    store = store or core.CATALOG
    pid = normalize_problem_id(pid)
    target = next_solution_path(
        pid,
        language,
        root=root,
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        solution_template(language),
        encoding="utf-8",
    )

    relative = target.relative_to(root).as_posix()

    try:
        store.add_solution(
            SolutionMeta(
                problem_id=pid,
                path=relative,
                language=language,
                complexity=complexity,
            )
        )
    except Exception:
        target.unlink(missing_ok=True)
        raise

    return target


def solutions_for_problem(
    problem_id: str,
    *,
    store=None,
) -> list[SolutionMeta]:
    """Return every registered solution for one Catalog problem."""

    store = store or core.CATALOG
    pid = normalize_problem_id(
        problem_id
    )

    return sorted(
        (
            item
            for item in store.load_solutions()
            if item.problem_id == pid
        ),
        key=lambda item: (
            item.language,
            item.path,
        ),
    )


def current_catalog_solution(
    problem,
    *,
    store=None,
    root: Path = ROOT,
):
    if not problem:
        return None

    store = store or core.CATALOG
    root = Path(root)

    try:
        relative = (
            Path(problem["path"])
            .resolve()
            .relative_to(root.resolve())
            .as_posix()
        )
    except (KeyError, ValueError):
        return None

    for item in store.load_solutions():
        if item.path == relative:
            return item

    return None


def missing_finish_complexity(
    problem,
    *,
    store=None,
    root: Path = ROOT,
):
    solution = current_catalog_solution(
        problem,
        store=store,
        root=root,
    )

    if solution is None:
        return None

    if solution.complexity.strip():
        return None

    return solution


def finish_with_optional_complexity(
    problem_id: str,
    score: int,
    *,
    minutes: int | None = None,
    complexity_solution=None,
    complexity: str | None = None,
    store=None,
    finish_runner=None,
):
    store = store or core.CATALOG
    finish_runner = (
        finish_runner
        or core.finish_cmd
    )

    original = complexity_solution
    catalog_updated = False

    if original is not None:
        value = str(
            complexity or ""
        ).strip()

        if not value:
            raise CatalogError(
                "缺少 Complexity，無法完成 Finish。"
            )

        store.update_solution(
            SolutionMeta(
                problem_id=original.problem_id,
                path=original.path,
                language=original.language,
                complexity=value,
            )
        )

        catalog_updated = True

    def rollback_complexity():
        if not catalog_updated:
            return

        store.update_solution(
            original
        )

    try:
        result = finish_runner(
            problem_id,
            score,
            minutes=minutes,
        )

    except BaseException as exc:
        if catalog_updated:
            try:
                rollback_complexity()
            except Exception as rollback_exc:
                raise CatalogError(
                    "Finish 失敗，且 Complexity rollback "
                    f"亦失敗：{rollback_exc}"
                ) from exc

        raise

    if result != 0 and catalog_updated:
        try:
            rollback_complexity()
        except Exception as rollback_exc:
            raise CatalogError(
                "Finish 回傳失敗，且 Complexity rollback "
                f"亦失敗：{rollback_exc}"
            )

    return result


def prompt_text(
    label: str,
    *,
    current: str | None = None,
    required: bool = False,
    allow_clear: bool = False,
) -> str | None:
    shown = f" [{current}]" if current else ""
    clear_hint = " · 輸入 - 清除" if allow_clear else ""

    try:
        value = input(
            f"{label}{shown}{clear_hint}\n> "
        ).strip()
    except (EOFError, KeyboardInterrupt):
        return None

    if current is not None and not value:
        return current

    if allow_clear and value == "-":
        return ""

    if required and not value:
        return None

    return value




def _print_tag_header(title: str, selected: set[str], kept_legacy: set[str]) -> None:
    clear()
    heading(title)
    print()

    total = len(selected) + len(kept_legacy)
    print(f"{GRAY}已選 {total} 個 Tags{RESET}")

    if total:
        preview = ", ".join(sorted(selected) + sorted(kept_legacy))
        print(f"{WHITE}{fit(preview, ui_width())}{RESET}")

    print()
    rule()
    print()


def _tag_group_menu(
    group_name: str,
    group_tags,
    selected: set[str],
    kept_legacy: set[str],
) -> str:
    cursor = 0
    tags = list(group_tags)

    while True:
        _print_tag_header(
            f"Tags · {group_name}",
            selected,
            kept_legacy,
        )

        for index, tag in enumerate(tags):
            mark = "✓" if tag in selected else "○"
            prefix = "›" if index == cursor else " "
            color = CYAN + BOLD if index == cursor else ""

            print(
                f"{color}{prefix} {index + 1}  "
                f"{mark} {tag}{RESET}"
            )

        print()
        rule()
        print(f"{GRAY}↑↓ 選擇 · Enter / Space 切換{RESET}")
        print(f"{GRAY}S 完成 Tags 選擇 · Esc / Q 返回分類{RESET}")

        key = read_key()

        if key == "UP":
            cursor = (cursor - 1) % len(tags)
        elif key == "DOWN":
            cursor = (cursor + 1) % len(tags)
        elif key in {"ENTER", " "}:
            tag = tags[cursor]
            if tag in selected:
                selected.remove(tag)
            else:
                selected.add(tag)
        elif key in {"s", "S"}:
            return "save"
        elif key in {"ESC", "q", "Q"}:
            return "back"
        elif key.isdigit():
            index = int(key) - 1
            if 0 <= index < len(tags):
                cursor = index


def _legacy_tag_menu(
    tags: list[str],
    kept: set[str],
    selected: set[str],
) -> str:
    cursor = 0

    while True:
        _print_tag_header(
            "Tags · Legacy / 其他",
            selected,
            kept,
        )

        for index, tag in enumerate(tags):
            mark = "✓" if tag in kept else "○"
            prefix = "›" if index == cursor else " "
            color = CYAN + BOLD if index == cursor else ""

            print(
                f"{color}{prefix} {index + 1}  "
                f"{mark} {tag}{RESET}"
            )

        print()
        rule()
        print(f"{GRAY}↑↓ 選擇 · Enter / Space 切換{RESET}")
        print(f"{GRAY}S 完成 Tags 選擇 · Esc / Q 返回分類{RESET}")

        key = read_key()

        if key == "UP":
            cursor = (cursor - 1) % len(tags)
        elif key == "DOWN":
            cursor = (cursor + 1) % len(tags)
        elif key in {"ENTER", " "}:
            tag = tags[cursor]
            if tag in kept:
                kept.remove(tag)
            else:
                kept.add(tag)
        elif key in {"s", "S"}:
            return "save"
        elif key in {"ESC", "q", "Q"}:
            return "back"
        elif key.isdigit():
            index = int(key) - 1
            if 0 <= index < len(tags):
                cursor = index


def tag_selector(
    current: str = "",
    *,
    required: bool = False,
) -> str | None:
    canonical, unknown = split_tags(current)
    selected = set(canonical)
    legacy = list(unknown)
    kept_legacy = set(legacy)
    cursor = 0

    def finish() -> str | None:
        if required and not selected and not kept_legacy:
            return None

        return serialize_selection(
            selected,
            [
                tag
                for tag in legacy
                if tag in kept_legacy
            ],
        )

    while True:
        entries = [
            (
                "group",
                group_name,
                group_tags,
                sum(tag in selected for tag in group_tags),
                len(group_tags),
            )
            for group_name, group_tags in TAG_GROUPS
        ]

        if legacy:
            entries.append(
                (
                    "legacy",
                    "Legacy / 其他",
                    legacy,
                    sum(tag in kept_legacy for tag in legacy),
                    len(legacy),
                )
            )

        entries.append(
            (
                "save",
                "✓ 完成 Tags 選擇",
                None,
                len(selected) + len(kept_legacy),
                None,
            )
        )

        cursor %= len(entries)

        _print_tag_header(
            "Tags 分類",
            selected,
            kept_legacy,
        )

        for index, entry in enumerate(entries):
            kind, label, _, count, maximum = entry
            prefix = "›" if index == cursor else " "
            color = CYAN + BOLD if index == cursor else ""

            if kind == "save":
                detail = f"目前共 {count} 個 Tags"
            elif kind == "legacy":
                detail = f"{count}/{maximum} 保留"
            else:
                detail = f"{count}/{maximum} 已選"

            print(
                f"{color}{prefix} {index + 1}  "
                f"{label}{RESET}"
            )
            print(f"     {GRAY}{detail}{RESET}")

        print()
        rule()
        print(f"{GRAY}↑↓ 選擇 · Enter 選擇{RESET}")
        print(f"{GRAY}S 完成 Tags 選擇 · Esc / Q 取消 Tags 編輯{RESET}")

        key = read_key()

        if key == "UP":
            cursor = (cursor - 1) % len(entries)
            continue

        if key == "DOWN":
            cursor = (cursor + 1) % len(entries)
            continue

        if key in {"s", "S"}:
            result = finish()
            if result is not None:
                return result

            clear()
            heading("Tags 分類")
            print()
            print(
                f"{YELLOW}"
                "新題目至少需要選擇 1 個 Tag。"
                f"{RESET}"
            )
            pause()
            continue

        if key in {"ESC", "q", "Q"}:
            return None

        if key.isdigit():
            index = int(key) - 1
            if 0 <= index < len(entries):
                cursor = index
            continue

        if key != "ENTER":
            continue

        kind, label, values, _, _ = entries[cursor]

        if kind == "save":
            result = finish()
            if result is not None:
                return result

            clear()
            heading("Tags 分類")
            print()
            print(
                f"{YELLOW}"
                "新題目至少需要選擇 1 個 Tag。"
                f"{RESET}"
            )
            pause()
            continue

        if kind == "legacy":
            action = _legacy_tag_menu(
                values,
                kept_legacy,
                selected,
            )
        else:
            action = _tag_group_menu(
                label,
                values,
                selected,
                kept_legacy,
            )

        if action == "save":
            result = finish()
            if result is not None:
                return result

            clear()
            heading("Tags 分類")
            print()
            print(
                f"{YELLOW}"
                "新題目至少需要選擇 1 個 Tag。"
                f"{RESET}"
            )
            pause()


def language_menu() -> str | None:
    selected = choose_menu(
        "Solution 語言",
        [
            {
                "label": "C++",
                "detail": "建立 .cpp",
                "enabled": True,
            },
            {
                "label": "Python",
                "detail": "建立 .py",
                "enabled": True,
            },
        ],
        footer_numbers=True,
    )

    if selected is None:
        return None

    return "cpp" if selected == 0 else "python"


def open_in_vscode(path: Path) -> bool:
    result = subprocess.run(
        ["code", "--reuse-window", str(path)],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def create_problem_ui() -> str | None:
    clear()
    heading("新增題目")
    print()
    print(f"{GRAY}建立 Catalog metadata 與純 solution file{RESET}")
    print(f"{GRAY}Esc 可在選單步驟取消；文字欄位可 Ctrl+C 取消{RESET}")
    print()

    raw_pid = prompt_text("題號", required=True)
    if raw_pid is None:
        return None

    try:
        pid = normalize_problem_id(raw_pid)
    except CatalogError as exc:
        print(f"{RED}✕ {exc}{RESET}")
        pause()
        return None

    try:
        existing = core.CATALOG.load_problems()
    except CatalogError as exc:
        print(f"{RED}✕ Catalog 無法讀取：{exc}{RESET}")
        pause()
        return None

    if pid in existing:
        print(f"{RED}✕ 題目已存在：{pid}{RESET}")
        pause()
        return None

    title = prompt_text("題名", required=True)
    if title is None:
        return None

    source = prompt_text("來源 URL / 名稱（可略過）")
    if source is None:
        return None

    difficulty = prompt_text("難度 1–5（可略過）")
    if difficulty is None:
        return None

    tags = tag_selector(required=True)
    if tags is None:
        return None

    language = language_menu()
    if language is None:
        return None

    clear()
    heading("新增題目")
    print()
    print(f"{WHITE}{pid} · {title}{RESET}")
    print(f"{GRAY}Tags 已完成 · 接著設定 solution metadata{RESET}")
    print(f"{GRAY}Tags: {tags or '—'}{RESET}")
    print(f"{GRAY}Language: {language}{RESET}")
    print()

    complexity = prompt_text("Complexity（可略過）")
    if complexity is None:
        return None

    clear()
    heading("確認並建立")
    print()
    print(f"{WHITE}{pid} · {title}{RESET}")
    print()
    rule()
    print()
    print(f"來源        {source or '—'}")
    print(f"難度        {difficulty or '—'}")
    print(f"Tags        {tags or '—'}")
    print(f"Language    {language}")
    print(f"Complexity  {complexity or '—'}")
    print()
    rule()
    print()
    print(
        f"{GRAY}"
        "以上內容尚未寫入 Catalog"
        f"{RESET}"
    )

    if not confirm("確認建立題目與 solution？"):
        return None

    try:
        path = create_problem_assets(
            ProblemMeta(
                problem_id=pid,
                title=title,
                source=source,
                difficulty=difficulty,
                tags=tags,
            ),
            language,
            complexity,
        )
        with contextlib.redirect_stdout(io.StringIO()):
            core.sync()
    except (CatalogError, OSError) as exc:
        clear()
        heading("新增題目")
        print()
        print(f"{RED}✕ 建立失敗：{exc}{RESET}")
        pause()
        return None

    clear()
    heading("建立完成")
    print()
    print(
        f"{GREEN}{BOLD}"
        f"✓ {pid} 已成功寫入 Catalog"
        f"{RESET}"
    )
    print()
    print(path.relative_to(ROOT))

    if open_in_vscode(path):
        print(f"{GREEN}✓ 已在 VS Code 開啟{RESET}")
    else:
        print(f"{YELLOW}⚠ 無法自動開啟 VS Code{RESET}")

    pause()
    return str(path)


def edit_problem_ui(problem) -> None:
    if not problem:
        return

    pid = problem["id"]

    try:
        problems = core.CATALOG.load_problems()
        current = problems[pid]
        solution = current_catalog_solution(problem)
    except (CatalogError, KeyError) as exc:
        clear()
        heading("編輯題目")
        print()
        print(f"{RED}✕ 無法讀取 Catalog：{exc}{RESET}")
        pause()
        return

    clear()
    heading("編輯題目")
    print()
    print(f"{WHITE}{pid} · {current.title or pid}{RESET}")
    print(
        f"{GRAY}"
        "文字欄位 Enter 保留原值；Tags 使用分類選擇"
        f"{RESET}"
    )
    print()

    title = prompt_text(
        "題名",
        current=current.title,
        required=True,
    )
    if title is None:
        return

    source = prompt_text(
        "來源",
        current=current.source,
        allow_clear=True,
    )
    if source is None:
        return

    difficulty = prompt_text(
        "難度 1–5",
        current=current.difficulty,
        allow_clear=True,
    )
    if difficulty is None:
        return

    tags = tag_selector(current.tags)
    if tags is None:
        return

    clear()
    heading("編輯題目")
    print()
    print(f"{GREEN}✓ Tags 選擇完成{RESET}")
    print(f"{GRAY}{tags or '—'}{RESET}")
    print()
    print(
        f"{GRAY}"
        "尚未儲存；完成剩餘 metadata 後會統一確認"
        f"{RESET}"
    )
    print()

    complexity = None
    if solution is not None:
        clear()
        heading("編輯題目")
        print()
        print(f"{WHITE}{pid} · {title}{RESET}")
        print(f"{GRAY}Tags 已完成 · 接著設定目前 solution{RESET}")
        print(f"{GRAY}Tags: {tags or '—'}{RESET}")
        print(f"{GRAY}Solution: {solution.path}{RESET}")
        print()

        complexity = prompt_text(
            "目前 solution Complexity",
            current=solution.complexity,
            allow_clear=True,
        )
        if complexity is None:
            return

    clear()
    heading("確認並儲存")
    print()
    print(f"{WHITE}{pid} · {title}{RESET}")
    print()
    rule()
    print()
    print(f"來源        {source or '—'}")
    print(f"難度        {difficulty or '—'}")
    print(f"Tags        {tags or '—'}")

    if solution is not None:
        print(f"Complexity  {complexity or '—'}")

    print()
    rule()
    print()
    print(
        f"{GRAY}"
        "以上內容尚未寫入 Catalog"
        f"{RESET}"
    )

    if not confirm("確認儲存全部 metadata？"):
        return

    try:
        updated_problem = ProblemMeta(
            problem_id=pid,
            title=title,
            source=source,
            difficulty=difficulty,
            tags=tags,
        )

        if solution is not None:
            core.CATALOG.update_problem_with_solution(
                updated_problem,
                SolutionMeta(
                    problem_id=solution.problem_id,
                    path=solution.path,
                    language=solution.language,
                    complexity=complexity,
                ),
            )
        else:
            core.CATALOG.update_problem(
                updated_problem
            )

        with contextlib.redirect_stdout(io.StringIO()):
            core.sync()

    except (CatalogError, OSError) as exc:
        clear()
        heading("編輯題目")
        print()
        print(f"{RED}✕ 更新失敗：{exc}{RESET}")
        pause()
        return

    clear()
    heading("儲存完成")
    print()
    print(
        f"{GREEN}{BOLD}"
        "✓ metadata 已成功寫入 Catalog"
        f"{RESET}"
    )
    print()
    print(f"{WHITE}{pid} · {title}{RESET}")
    print(f"{GRAY}Tags: {tags or '—'}{RESET}")

    if solution is not None:
        print(
            f"{GRAY}"
            f"Complexity: {complexity or '—'}"
            f"{RESET}"
        )

    pause()


def add_solution_ui(problem) -> str | None:
    if not problem:
        return None

    pid = problem["id"]
    language = language_menu()

    if language is None:
        return None

    clear()
    heading("新增解法")
    print()
    print(f"{WHITE}{problem_line(problem)}{RESET}")
    print()

    complexity = prompt_text("Complexity（可略過）")
    if complexity is None:
        return None

    if not confirm(
        f"為 {pid} 建立新的 {language} 解法？"
    ):
        return None

    try:
        path = add_solution_asset(
            pid,
            language,
            complexity,
        )
        with contextlib.redirect_stdout(io.StringIO()):
            core.sync()
    except (CatalogError, OSError) as exc:
        clear()
        heading("新增 Solution")
        print()
        print(f"{RED}✕ 建立失敗：{exc}{RESET}")
        pause()
        return None

    clear()
    heading("新增 Solution")
    print()
    print(f"{GREEN}✓ 已建立{RESET}")
    print(path.relative_to(ROOT))

    if open_in_vscode(path):
        print(f"{GREEN}✓ 已在 VS Code 開啟{RESET}")
    else:
        print(f"{YELLOW}⚠ 無法自動開啟 VS Code{RESET}")

    pause()
    return str(path)


def _solution_language_label(
    language: str,
) -> str:
    folded = str(
        language or ""
    ).strip().casefold()
    return {
        "cpp": "C++",
        "c++": "C++",
        "py": "Python",
        "python": "Python",
    }.get(
        folded,
        str(language or "—"),
    )


def solution_center_ui(
    problem,
    current_filename: str | None,
) -> str | None:
    if not problem:
        return current_filename

    try:
        solutions = solutions_for_problem(
            problem["id"]
        )
    except CatalogError as exc:
        clear()
        heading("題目資料 · 解法")
        print()
        print(
            f"{RED}"
            f"✕ 題目資料無法讀取：{exc}"
            f"{RESET}"
        )
        pause()
        return current_filename

    options = [
        {
            "label": (
                f"{_solution_language_label(item.language)}"
                f" · {Path(item.path).name}"
            ),
            "detail": (
                f"複雜度 "
                f"{item.complexity or '未記錄'}"
            ),
            "enabled": True,
            "kind": "open",
            "solution": item,
            "action": "開啟",
        }
        for item in solutions
    ]
    options.append(
        {
            "label": "新增解法",
            "detail": "建立另一份 C++ / Python 解法；保留既有解法",
            "enabled": True,
            "kind": "add",
            "action": "建立",
        }
    )

    if ui_width() < 86:
        selected = choose_menu(
            f"題目資料 · 解法 · {problem['id']}",
            options,
            problem=problem,
            back_text="返回題目資料",
            enter_text="選擇",
        )
    else:
        selected = first_enabled(
            options
        )
        while True:
            output = io.StringIO()
            with contextlib.redirect_stdout(
                output
            ):
                heading("題目資料 · 解法")
                print()
                print_problem_context(
                    problem
                )
                print()

                width = ui_width()
                gap = 4
                left = 42
                right = max(
                    32,
                    width - left - gap,
                )

                print(
                    f"{CYAN}{BOLD}"
                    f"{pad_display(
                        f'已登錄解法 · {len(solutions)}',
                        left,
                    )}"
                    f"{RESET}"
                    + " " * gap
                    + f"{CYAN}{BOLD}"
                    "選中解法資訊"
                    f"{RESET}"
                )

                left_rows = []
                for index, option in enumerate(
                    options
                ):
                    prefix = (
                        "›"
                        if index == selected
                        else " "
                    )
                    label = (
                        f"{prefix} {index + 1} "
                        f"{option['label']}"
                    )
                    color = (
                        CYAN + BOLD
                        if index == selected
                        else ""
                    )
                    left_rows.append(
                        (
                            fit(label, left),
                            color,
                        )
                    )

                option = options[selected]
                info_rows = []
                if option["kind"] == "open":
                    item = option["solution"]
                    info_rows = [
                        (
                            "語言      "
                            f"{_solution_language_label(item.language)}"
                        ),
                        (
                            "複雜度    "
                            f"{item.complexity or '未記錄'}"
                        ),
                        "檔案",
                        f"  {item.path}",
                    ]
                else:
                    info_rows = [
                        "建立新的解法檔案",
                        "語言可選 C++ / Python",
                        "既有解法不會被覆寫",
                    ]

                rows = max(
                    len(left_rows),
                    len(info_rows),
                )
                for row in range(rows):
                    left_text, left_color = (
                        left_rows[row]
                        if row < len(left_rows)
                        else ("", "")
                    )
                    right_text = (
                        info_rows[row]
                        if row < len(info_rows)
                        else ""
                    )
                    print(
                        f"{left_color}"
                        f"{pad_display(left_text, left)}"
                        f"{RESET if left_color else ''}"
                        + " " * gap
                        + f"{fit(right_text, right)}"
                    )

                print()
                rule()
                print(
                    f"{GRAY}"
                    "↑↓ 選擇 · Enter "
                    f"{option.get('action') or '選擇'}"
                    " · Esc 返回題目資料"
                    f"{RESET}"
                )

            sys.stdout.write(
                "\033[2J\033[H"
                + output.getvalue()
            )
            sys.stdout.flush()

            key = read_key()
            if key == "UP":
                selected = move_enabled(
                    options,
                    selected,
                    -1,
                )
            elif key == "DOWN":
                selected = move_enabled(
                    options,
                    selected,
                    1,
                )
            elif key == "ENTER":
                break
            elif key in {
                "ESC",
                "q",
                "Q",
            }:
                return current_filename

    if selected is None:
        return current_filename

    option = options[selected]
    if option["kind"] == "add":
        created = add_solution_ui(
            problem
        )
        return created or current_filename

    item = option["solution"]
    target = ROOT / item.path

    if not target.is_file():
        clear()
        heading("題目資料 · 解法")
        print()
        print(
            f"{RED}"
            f"✕ 解法檔案不存在：{item.path}"
            f"{RESET}"
        )
        pause()
        return current_filename

    if open_in_vscode(target):
        clear()
        heading("題目資料 · 解法")
        print()
        print(
            f"{GREEN}"
            f"✓ 已開啟 {item.path}"
            f"{RESET}"
        )
        print(
            f"{GRAY}"
            "控制中心會依實際開啟的解法檔案辨識目前解法；"
            "複雜度只更新這一份解法。"
            f"{RESET}"
        )
        pause()
        return str(target)

    clear()
    heading("題目資料 · 解法")
    print()
    print(
        f"{YELLOW}"
        "⚠ 無法自動開啟 VS Code"
        f"{RESET}"
    )
    pause()
    return current_filename



def catalog_center(
    problem,
    current_filename: str | None,
):
    try:
        problems = (
            core.CATALOG.load_problems()
        )
        catalog_solutions = (
            core.CATALOG.load_solutions()
        )
    except CatalogError as exc:
        clear()
        heading("題目資料")
        print()
        print(
            f"{RED}"
            f"✕ 題目資料無法讀取：{exc}"
            f"{RESET}"
        )
        pause()
        return current_filename

    known = bool(
        problem
        and problem["id"] in problems
    )
    solution_count = (
        sum(
            1
            for item in catalog_solutions
            if (
                known
                and item.problem_id
                == problem["id"]
            )
        )
        if known
        else 0
    )

    options = [
        {
            "label": "新增題目",
            "detail": "建立題目 metadata 與第一份解法",
            "enabled": True,
            "section": "題目",
            "action": "建立",
        },
        {
            "label": "編輯目前題目",
            "detail": (
                "修改標題、來源、難度、標籤等 metadata"
                if known
                else "目前檔案不在題目資料庫"
            ),
            "enabled": known,
            "section": "題目",
            "action": "編輯",
        },
        {
            "label": "解法",
            "detail": (
                f"{solution_count} 份已登錄 · 開啟或新增解法"
                if known
                else "需先選擇已登錄題目"
            ),
            "enabled": known,
            "section": "解法",
            "action": "查看",
        },
    ]

    selected = choose_grid(
        "題目資料",
        options,
        problem=problem,
        back_text="返回更多工具",
        wide_columns=3,
        compact_columns=2,
    )

    if selected is None:
        return current_filename

    if selected == 0:
        created = create_problem_ui()
        return created or current_filename

    if selected == 1:
        edit_problem_ui(problem)
        return current_filename

    return solution_center_ui(
        problem,
        current_filename,
    )


# ============================================================
# Today / Notes
# ============================================================

def _print_new_learning_summary(
    route,
) -> None:
    if route is None:
        return

    if route.skill is not None:
        skill = route.skill

        print(
            f"{CYAN}{BOLD}"
            f"新學習 · {skill.uid}"
            f"{RESET}"
        )
        print(
            f"{WHITE}"
            f"{skill.name}"
            f"{RESET}"
        )
        print(
            f"單元      {skill.unit}"
        )
        print(
            f"階段      {skill.path_stage}"
        )
        print(
            f"狀態      {route.status}"
        )
        print(
            f"證據      "
            + (
                route.skill_evidence.label()
                if route.skill_evidence
                is not None
                else "—"
            )
        )
        print(
            f"安排原因  "
            f"{fit(route.why_now, max(10, ui_width() - 9))}"
        )

        if route.prerequisites:
            print("先備條件")

            for item in route.prerequisites:
                mark = (
                    f"{GREEN}✓{RESET}"
                    if item.satisfied
                    else f"{YELLOW}•{RESET}"
                )
                print(
                    f"  {mark} {item.skill_uid}"
                    f" · {item.evidence_label}"
                )
        else:
            print(
                f"先備條件  {GRAY}無{RESET}"
            )

        if route.placement is not None:
            placement = route.placement
            print(
                f"課程      {placement.lesson_uid or '—'}"
            )
            print(
                f"下一步    {placement.role}"
            )
            print(
                f"題目      {placement.problem_id}"
                f" · {fit(placement.title, max(10, ui_width() - 12))}"
            )
        else:
            print(
                f"{YELLOW}"
                "下一步    Published Placement 不足"
                f"{RESET}"
            )

        return

    if route.blocked_skill is not None:
        print(
            f"{YELLOW}{BOLD}"
            "新學習 · 暫時無法開始"
            f"{RESET}"
        )
        print(
            f"{WHITE}"
            f"{route.blocked_skill.uid}"
            " · "
            f"{route.blocked_skill.name}"
            f"{RESET}"
        )
        print(
            f"{GRAY}"
            f"{fit(route.why_now, ui_width())}"
            f"{RESET}"
        )

        for item in route.blocked_by:
            print(
                f"  {RED}✕{RESET} "
                f"{item.skill_uid}"
                f" · {item.evidence_label}"
            )

        return

    if route.route_complete:
        print(
            f"{GREEN}"
            "✓ Required 主線已達 B4 啟動門檻"
            f"{RESET}"
        )
        print(
            f"{GRAY}"
            f"{fit(route.why_now, ui_width())}"
            f"{RESET}"
        )


def _start_new_learning(
    route,
    current_filename: str | None,
    *,
    track: str = "Implementation",
):
    clear()
    heading("開始新學習")
    print()

    _print_new_learning_summary(
        route
    )

    placement = route.placement

    if placement is None:
        print()
        print(
            f"{YELLOW}"
            "⚠ 沒有可安全啟動的 Published Placement。"
            f"{RESET}"
        )
        print(
            f"{GRAY}"
            "不從 legacy Tags 或題名猜題；"
            "請先修正 Published Curriculum。"
            f"{RESET}"
        )
        pause()
        return current_filename

    print()
    rule()
    print()

    if (
        track == "Implementation"
        and placement.role == "Worked Example"
    ):
        print(
            f"{YELLOW}"
            "本次 Placement 是 Worked Example。"
            f"{RESET}"
        )
        print(
            f"{GRAY}"
            "先依 Lesson 完成 prediction → walkthrough → "
            "hide reference → reconstruction；"
            "Worked 不建立獨立 Gate Evidence。"
            f"{RESET}"
        )
        pause()
        return current_filename

    if placement.role == "Transfer Challenge":
        print(
            f"{YELLOW}"
            "Transfer Challenge：pre-attempt 不提供演算法名稱、"
            "關鍵 observation 或完整 state list。"
            f"{RESET}"
        )
        print()

    try:
        scratch = (
            create_reading_scratch(
                RUNTIME_DIR,
                placement,
                action="finish",
            )
            if track == "Reading"
            else create_learning_scratch(
                placement
            )
        )
    except (OSError, ValueError) as exc:
        print(
            f"{RED}"
            f"✕ 無法建立 new-learning scratch：{exc}"
            f"{RESET}"
        )
        pause()
        return current_filename

    opened = open_in_vscode(
        scratch
    )

    if opened:
        print(
            f"{GREEN}"
            + (
                "✓ 已開啟 Reading formal-response scratch"
                if track == "Reading"
                else "✓ 已開啟 B4 learning scratch"
            )
            + f"{RESET}"
        )
        print(
            f"{GRAY}"
            + (
                "先完成 Formal response，再驗證；之後回 Control Center 選「完成題目」。"
                if track == "Reading"
                else "完成外部 Judge 後回 Control Center 選「完成題目」；"
            )
            + " Placement UID 會直接接回 EV-v1 outbox。"
            + f"{RESET}"
        )
    else:
        print(
            f"{RED}"
            "✕ 無法在 VS Code 開啟 scratch"
            f"{RESET}"
        )

    pause()
    return str(scratch)


def _start_adaptive_review(
    candidate,
    current_filename: str | None,
):
    placement = review_placement_for_skill(
        candidate.skill_uid,
        track=candidate.track,
    )

    clear()
    heading("開始自適應複習")
    print()

    print(
        f"{WHITE}{BOLD}"
        f"{skill_display_name(candidate.skill_uid)}"
        f"{RESET}"
    )
    print(
        f"軌道    {candidate.track}"
    )
    print(
        f"R       ≈ {candidate.retrievability:.0%}"
    )
    print(
        f"到期    {candidate.due_on}"
    )
    print(
        f"預估    {candidate.estimated_minutes} min"
    )
    print()

    if placement is None:
        print(
            f"{YELLOW}"
            "⚠ Published curriculum 尚無可用 Placement。"
            f"{RESET}"
        )
        print(
            f"{GRAY}"
            "不從舊 Tags 猜題；保留這個 Skill review 候選，"
            "待 curriculum 修復後再選代表題。"
            f"{RESET}"
        )
        pause()
        return current_filename

    print(
        f"題目    {placement.problem_id} · "
        f"{fit(placement.title, max(10, ui_width() - 8))}"
    )
    print(
        f"用途    {placement.role}"
    )

    if placement.url:
        print(
            f"OJ      {placement.url}"
        )

    if candidate.track == "Reading":
        print()
        print(
            f"{YELLOW}"
            "Reading review 不自動開啟舊 solution。"
            f"{RESET}"
        )
        print(
            f"{GRAY}"
            "先完成 Formal response 的 trace / reasoning；"
            "儲存以前不得執行程式或查看完整 reference。"
            f"{RESET}"
        )

        try:
            scratch = create_reading_scratch(
                RUNTIME_DIR,
                placement,
                action="review",
            )
        except (OSError, ValueError) as exc:
            print()
            print(
                f"{RED}"
                f"✕ 無法建立 Reading scratch：{exc}"
                f"{RESET}"
            )
            pause()
            return current_filename

        opened = open_in_vscode(
            scratch
        )
        print()
        if opened:
            print(
                f"{GREEN}"
                "✓ 已開啟 Reading formal-response scratch"
                f"{RESET}"
            )
            print(
                f"{GRAY}"
                "完成 Formal response → verification 後，"
                "回控制中心選「複習題目」。"
                f"{RESET}"
            )
        else:
            print(
                f"{RED}"
                "✕ 無法在 VS Code 開啟 Reading scratch"
                f"{RESET}"
            )

        pause()
        return str(scratch)

    try:
        scratch = create_review_scratch(
            placement
        )
    except OSError as exc:
        print()
        print(
            f"{RED}"
            f"✕ 無法建立 retrieval scratch：{exc}"
            f"{RESET}"
        )
        pause()
        return current_filename

    opened = open_in_vscode(
        scratch
    )

    print()

    if opened:
        print(
            f"{GREEN}"
            "✓ 已開啟空白 retrieval scratch"
            f"{RESET}"
        )
        print(
            f"{GRAY}"
            "不會打開歷史 solution；完成 Judge 後"
            "回控制中心選「複習題目」。"
            f"{RESET}"
        )
    else:
        print(
            f"{RED}"
            "✕ 無法在 VS Code 開啟 scratch"
            f"{RESET}"
        )

    pause()

    return str(scratch)


def learning_status_detail_view(snapshot) -> None:
    clear()
    heading("學習狀態 · 詳細")
    print()
    print(
        f"{GRAY}"
        "衍生運作資料；只用於安排與診斷，不是 mastery / readiness 宣告。"
        f"{RESET}"
    )
    print()

    print(f"目標      {snapshot['target']}")
    print(
        f"作答      {snapshot['attempts']}"
        f" · Evidence {snapshot['evidence']}"
    )
    print(
        "軌道      "
        f"Reading {snapshot['evidence_by_track'].get('Reading', 0)}"
        " · Implementation "
        f"{snapshot['evidence_by_track'].get('Implementation', 0)}"
    )
    print(
        f"同步      已確認 {snapshot['remote_acknowledged']}"
        f" · 待同步 {snapshot['remote_pending']}"
    )
    print(
        f"記憶      {snapshot['memory_states']} Skill × Track"
    )

    print()
    rule()
    print()
    print(f"{CYAN}{BOLD}今日容量{RESET}")
    print(
        f"總容量    {snapshot['capacity_minutes']} min"
    )
    print(
        f"複習      {snapshot['review_selected_minutes']}/"
        f"{snapshot['review_budget_minutes']} min"
        f" · {snapshot['review_selected']} 項"
    )
    print(
        f"安全延後  {snapshot['review_deferred']}"
        " · 不計為欠作業"
    )
    print(
        f"新學習    ≥ {snapshot['protected_new_learning_minutes']} min 保留"
    )

    print()
    rule()
    print()
    print(f"{CYAN}{BOLD}記憶狀態 · 最低 R 優先{RESET}")

    if not snapshot["retention"]:
        print(f"{GRAY}尚無可計算的 Skill × Track retention state{RESET}")
    else:
        for item in snapshot["retention"][:10]:
            due_mark = (
                "到期"
                if item["due_on"] <= snapshot["date"]
                else f"預計 {item['due_on']:%m/%d}"
            )
            print(
                f"  {item['skill_uid']} × {item['track']}"
                f" · R≈{item['retrievability']:.0%}"
                f" · S≈{item['stability_days']:.1f}d"
                f" · {due_mark}"
                f" · ev={item['evidence_count']}"
            )

        hidden = len(snapshot["retention"]) - 10
        if hidden > 0:
            print(
                f"{GRAY}"
                f"  …另有 {hidden} 個 Skill × Track state"
                f"{RESET}"
            )

    model = snapshot["learner_model"]
    print()
    rule()
    print()
    print(f"{CYAN}{BOLD}學習模型 v2{RESET}")
    print(
        "提示依賴  "
        f"高 {len(model['hint_dependence_high'])}"
    )
    print(
        "遷移      "
        f"待驗證 {len(model['transfer_ready'])}"
        f" · 已有證據 {len(model['transfer_verified'])}"
    )
    print(
        "重複瓶頸  "
        f"{len(model['repeated_bottlenecks'])}"
    )
    print(
        "信心抽樣  "
        f"{len(model['confidence_samples'])}"
        f"{GRAY} · 不進 readiness Gate{RESET}"
    )

    for item in model["repeated_bottlenecks"][:3]:
        print_wrapped(
            (
                f"  {item.skill_uid} · {item.category} · "
                f"{item.root_cause} · "
                f"{len(item.distinct_problems)} 題重現"
            ),
            ui_width() - 2,
            color=GRAY,
        )

    if snapshot["warnings"]:
        print()
        rule()
        print()
        for warning in snapshot["warnings"]:
            print_wrapped(
                f"⚠ {warning}",
                ui_width() - 2,
                color=YELLOW,
            )

    print()
    rule()
    print(
        f"{YELLOW}"
        "LEARNER_READINESS = NOT ASSESSED"
        f"{RESET}"
    )
    print(
        f"{GRAY}"
        "Retention / capacity 只用於下一步安排；不等於 RR/IR PASS。"
        f"{RESET}"
    )
    pause("Enter / Esc 返回學習狀態")


def learning_status_view() -> None:
    snapshot = learning_status_snapshot()

    while True:
        clear()
        heading("學習狀態")
        print()
        print(
            f"{GRAY}"
            "只顯示會影響下一步學習決策的摘要；不是 mastery / readiness 宣告。"
            f"{RESET}"
        )
        print()

        width = ui_width()
        if width >= 86:
            gap = 3
            left = (
                width - gap
            ) // 2
            right = (
                width - gap - left
            )

            progress = [
                (
                    f"真實作答 {snapshot['attempts']}"
                    f" · Evidence {snapshot['evidence']}"
                ),
                (
                    "Reading "
                    f"{snapshot['evidence_by_track'].get('Reading', 0)}"
                    " · Implementation "
                    f"{snapshot['evidence_by_track'].get('Implementation', 0)}"
                ),
                (
                    f"記憶狀態 {snapshot['memory_states']} 個 Skill × Track"
                ),
            ]
            capacity = [
                (
                    f"總容量 {snapshot['capacity_minutes']} min"
                ),
                (
                    f"複習 {snapshot['review_selected_minutes']}/"
                    f"{snapshot['review_budget_minutes']} min"
                    f" · {snapshot['review_selected']} 項"
                ),
                (
                    f"新學習 ≥ "
                    f"{snapshot['protected_new_learning_minutes']} min"
                ),
            ]
            if snapshot[
                "review_deferred"
            ]:
                capacity.append(
                    f"安全延後 "
                    f"{snapshot['review_deferred']} 項"
                )

            print(
                f"{CYAN}{BOLD}"
                f"{pad_display('目前進度', left)}"
                f"{RESET}"
                "   "
                f"{CYAN}{BOLD}"
                f"{pad_display('今日容量', right)}"
                f"{RESET}"
            )
            for index in range(
                max(
                    len(progress),
                    len(capacity),
                )
            ):
                a = (
                    progress[index]
                    if index < len(progress)
                    else ""
                )
                b = (
                    capacity[index]
                    if index < len(capacity)
                    else ""
                )
                print(
                    f"{pad_display(a, left)}"
                    "   "
                    f"{fit(b, right)}"
                )

            print()
            rule()
            print()
            sync = (
                f"同步狀態：已確認 "
                f"{snapshot['remote_acknowledged']}"
                f" · 待同步 {snapshot['remote_pending']}"
            )
            readiness = (
                "LEARNER_READINESS = NOT ASSESSED"
            )
            print(
                f"{pad_display(sync, left)}"
                "   "
                f"{YELLOW}"
                f"{fit(readiness, right)}"
                f"{RESET}"
            )

        else:
            print(
                f"{CYAN}{BOLD}"
                "目前進度"
                f"{RESET}"
            )
            print(
                f"真實作答  {snapshot['attempts']}"
                f" · 能力證據 {snapshot['evidence']}"
            )
            print(
                "學習軌道  "
                f"Reading {snapshot['evidence_by_track'].get('Reading', 0)}"
                " · Implementation "
                f"{snapshot['evidence_by_track'].get('Implementation', 0)}"
            )
            print(
                f"記憶狀態  {snapshot['memory_states']} 個 Skill × Track"
            )

            print()
            rule()
            print()
            print(
                f"{CYAN}{BOLD}"
                "今日容量"
                f"{RESET}"
            )
            print(
                f"總容量    {snapshot['capacity_minutes']} min"
            )
            print(
                f"複習      {snapshot['review_selected_minutes']}/"
                f"{snapshot['review_budget_minutes']} min"
                f" · {snapshot['review_selected']} 項"
            )
            print(
                f"新學習    ≥ "
                f"{snapshot['protected_new_learning_minutes']} min 保留"
            )
            if snapshot[
                "review_deferred"
            ]:
                print(
                    f"安全延後  "
                    f"{snapshot['review_deferred']} 項 · 不算欠作業"
                )

            print()
            rule()
            print()
            print(
                f"{CYAN}{BOLD}"
                "同步狀態"
                f"{RESET}"
            )
            print(
                f"已確認    {snapshot['remote_acknowledged']}"
                f" · 待同步 {snapshot['remote_pending']}"
            )

            print()
            rule()
            print(
                f"{YELLOW}"
                "LEARNER_READINESS = NOT ASSESSED"
                f"{RESET}"
            )

        if snapshot["warnings"]:
            print()
            for warning in snapshot["warnings"]:
                print_wrapped(
                    f"⚠ {warning}",
                    ui_width() - 2,
                    color=YELLOW,
                )

        print()
        print(
            f"{GRAY}"
            "D 查看詳細技術狀態 · Enter / Esc 返回控制中心"
            f"{RESET}"
        )

        key = read_key()
        if key in {
            "ENTER",
            "ESC",
            "q",
            "Q",
        }:
            return
        if key in {"d", "D"}:
            learning_status_detail_view(
                snapshot
            )



def _today_action_menu(
    snapshot,
    options,
):
    if ui_width() < 86:
        return choose_menu(
            "今日學習 · 下一步",
            options,
            main=False,
            enter_text="開始",
        )

    selected = first_enabled(
        options
    )
    plan = snapshot["plan"]

    while True:
        output = io.StringIO()
        with contextlib.redirect_stdout(
            output
        ):
            heading("今日學習")
            print()

            width = ui_width()
            gap = 4
            left = 56
            right = max(
                30,
                width - left - gap,
            )

            print(
                f"{CYAN}{BOLD}"
                f"{pad_display('下一步', left)}"
                f"{RESET}"
                + " " * gap
                + f"{CYAN}{BOLD}"
                "今日規劃"
                f"{RESET}"
            )

            window = min(
                8,
                len(options),
            )
            start = max(
                0,
                min(
                    selected - 3,
                    len(options) - window,
                ),
            )
            visible = list(
                range(
                    start,
                    start + window,
                )
            )

            task_rows = []
            for index in visible:
                option = options[index]
                prefix = (
                    "›"
                    if index == selected
                    else " "
                )
                color = (
                    CYAN + BOLD
                    if index == selected
                    else ""
                )
                task_rows.append(
                    (
                        fit(
                            f"{prefix} {index + 1} "
                            f"{option['label']}",
                            left,
                        ),
                        color,
                    )
                )
                detail = (
                    option.get("detail")
                    or ""
                )
                if detail:
                    task_rows.append(
                        (
                            fit(
                                "    " + detail,
                                left,
                            ),
                            GRAY,
                        )
                    )

            protected = max(
                0,
                snapshot["capacity_minutes"]
                - plan.budget_minutes,
            )
            plan_rows = [
                (
                    f"目標      "
                    f"{snapshot['target']}"
                ),
                (
                    f"可用時間  "
                    f"{snapshot['capacity_minutes']} 分"
                ),
                (
                    f"複習      "
                    f"{plan.selected_minutes}/"
                    f"{plan.budget_minutes} 分"
                    f" · {len(plan.selected)} 項"
                ),
                (
                    f"新學習    ≥ "
                    f"{protected} 分"
                ),
            ]

            if plan.deferred:
                plan_rows.append(
                    f"安全延後  "
                    f"{len(plan.deferred)} 項"
                )
            elif not plan.selected:
                plan_rows.append(
                    "複習狀態  今天沒有到期複習"
                )

            plan_rows.extend(
                [
                    "",
                    "目前選中",
                    options[selected]["label"],
                ]
            )
            detail = (
                options[selected].get(
                    "detail"
                )
                or ""
            )
            if detail:
                plan_rows.extend(
                    wrap_display(
                        detail,
                        right,
                    )
                )

            rows = max(
                len(task_rows),
                len(plan_rows),
            )
            for row in range(rows):
                left_text, left_color = (
                    task_rows[row]
                    if row < len(task_rows)
                    else ("", "")
                )
                right_text = (
                    plan_rows[row]
                    if row < len(plan_rows)
                    else ""
                )
                print(
                    f"{left_color}"
                    f"{pad_display(left_text, left)}"
                    f"{RESET if left_color else ''}"
                    + " " * gap
                    + f"{fit(right_text, right)}"
                )

            if snapshot["warning"]:
                print()
                print_wrapped(
                    f"⚠ {snapshot['warning']}",
                    width,
                    color=YELLOW,
                )

            print()
            rule()
            action = (
                options[selected].get(
                    "action"
                )
                or (
                    "調整"
                    if options[selected].get(
                        "kind"
                    )
                    == "capacity"
                    else "開始"
                )
            )
            print(
                f"{GRAY}"
                f"↑↓ 選擇 · Enter {action}"
                " · Esc / Q 返回控制中心"
                f"{RESET}"
            )

        sys.stdout.write(
            "\033[2J\033[H"
            + output.getvalue()
        )
        sys.stdout.flush()

        key = read_key()
        if key == "UP":
            selected = move_enabled(
                options,
                selected,
                -1,
            )
        elif key == "DOWN":
            selected = move_enabled(
                options,
                selected,
                1,
            )
        elif key == "ENTER":
            return selected
        elif key in {
            "ESC",
            "q",
            "Q",
        }:
            return None
        elif (
            key.isdigit()
            and len(options) <= 9
        ):
            index = int(key) - 1
            if (
                0 <= index < len(options)
                and options[index].get(
                    "enabled",
                    True,
                )
            ):
                return index


def today_view(current_filename: str | None):
    snapshot = adaptive_today_snapshot()
    plan = snapshot["plan"]
    route = snapshot[
        "new_learning"
    ]

    options = []

    if (
        route is not None
        and route.skill is not None
        and route.placement is not None
    ):
        supported_tracks = set(
            route.skill.tracks
        )

        for track in (
            "Reading",
            "Implementation",
        ):
            if track not in supported_tracks:
                continue

            options.append(
                {
                    "label": (
                        "新學習 · "
                        f"{route.skill.uid}"
                        f" × {track}"
                    ),
                    "detail": (
                        f"{route.placement.role}"
                        f" · {route.placement.lesson_uid}"
                        f" · {route.placement.problem_id}"
                    ),
                    "enabled": True,
                    "kind": "new",
                    "track": track,
                    "route": route,
                }
            )

    for candidate in plan.selected:
        options.append(
            {
                "label": (
                    "複習 · "
                    f"{candidate.skill_uid}"
                    f" × {candidate.track}"
                ),
                "detail": (
                    f"R≈{candidate.retrievability:.0%}"
                    f" · due {candidate.due_on:%m/%d}"
                    f" · {candidate.estimated_minutes} min"
                ),
                "enabled": True,
                "kind": "review",
                "candidate": candidate,
            }
        )

    for task in cognitive_plan.selected:
        label = {
            "repair": "修復",
            "discrimination": "方法辨識",
            "transfer": "遷移",
        }.get(task.kind, "認知練習")
        options.append(
            {
                "label": f"{label} · {', '.join(task.skill_uids)}",
                "detail": (
                    f"{task.estimated_minutes} min"
                    f" · {task.reason}"
                ),
                "enabled": True,
                "kind": "cognitive",
                "task": task,
            }
        )

    options.append(
        {
            "label": (
                "調整今日可用時間 · "
                f"{snapshot['capacity_minutes']} min"
            ),
            "detail": (
                "短時段細分、長時段粗分 · 只影響今天的學習規劃"
            ),
            "enabled": True,
            "kind": "capacity",
            "section": "今日設定",
            "action": "調整",
        }
    )

    if not [
        option
        for option in options
        if option["kind"] != "capacity"
    ]:
        print()
        rule()
        print()

        if (
            route is not None
            and route.route_complete
        ):
            print(
                f"{GRAY}"
                "目前沒有新的 Required Skill start action；"
                "這不代表 RR/IR readiness 已通過。"
                f"{RESET}"
            )
        elif (
            route is not None
            and route.blocked_skill
            is not None
        ):
            print(
                f"{GRAY}"
                "先建立上列 prerequisite Evidence；"
                "系統不會以 Skill Status 或單次 AC 強制解鎖。"
                f"{RESET}"
            )
        else:
            print(
                f"{GRAY}"
                "目前沒有可安全啟動的 Today action。"
                f"{RESET}"
            )

        print()
        print(
            f"{GRAY}"
            "仍可調整本日可用時間，系統會重新計算規劃。"
            f"{RESET}"
        )

    selected = _today_action_menu(
        snapshot,
        options,
    )

    if selected is None:
        return current_filename

    option = options[
        selected
    ]

    if option["kind"] == "capacity":
        selected_minutes = (
            today_capacity_menu(
                snapshot[
                    "capacity_minutes"
                ]
            )
        )

        if selected_minutes is not None:
            try:
                set_today_capacity_minutes(
                    selected_minutes
                )
            except (
                OSError,
                ValueError,
            ) as exc:
                clear()
                heading(
                    "今日學習 · 可用時間"
                )
                print()
                print(
                    f"{RED}"
                    f"✕ 無法儲存：{exc}"
                    f"{RESET}"
                )
                pause(
                    "Enter / Esc 返回今日學習"
                )

        return today_view(
            current_filename
        )

    if option["kind"] == "new":
        return _start_new_learning(
            option["route"],
            current_filename,
            track=option.get(
                "track",
                "Implementation",
            ),
        )

    if option["kind"] == "cognitive":
        return cognitive_task_view(
            option["task"],
            current_filename,
        )

    return _start_adaptive_review(
        option["candidate"],
        current_filename,
    )


def _attempted_problem_ids() -> set[str]:
    return {
        str(item.external_id).strip().lower()
        for item in _problem_library_items()
        if item.attempted
    }


def _cognitive_placement(task):
    if not task.skill_uids:
        return None

    attempted = _attempted_problem_ids()
    source = str(
        task.source_problem_id or ""
    ).strip().lower()

    placements = []
    for uid in task.skill_uids:
        try:
            placements.extend(
                CURRICULUM.placements_for_skill(
                    uid
                )
            )
        except RuntimeCurriculumError:
            continue

    fresh = [
        item
        for item in placements
        if (
            item.problem_id.lower()
            not in attempted
            and item.problem_id.lower()
            != source
        )
    ]

    if task.kind == "transfer":
        fresh = [
            item
            for item in fresh
            if item.role
            == "Transfer Challenge"
        ]
    elif task.kind == "repair":
        role_rank = {
            "Guided Drill": 0,
            "Core Independent": 1,
            "Worked Example": 2,
            "Transfer Challenge": 3,
            "Mock": 4,
        }
        fresh.sort(
            key=lambda item: (
                role_rank.get(
                    item.role,
                    99,
                ),
                item.lesson_order
                if item.lesson_order
                is not None
                else float("inf"),
                item.placement_uid,
            )
        )
    else:
        fresh.sort(
            key=lambda item: (
                0
                if item.role
                in {
                    "Core Independent",
                    "Transfer Challenge",
                }
                else 1,
                item.lesson_order
                if item.lesson_order
                is not None
                else float("inf"),
                item.placement_uid,
            )
        )

    return fresh[0] if fresh else None


def cognitive_task_view(
    task,
    current_filename: str | None,
):
    labels = {
        "repair": "最小修復",
        "discrimination": "方法辨識",
        "transfer": "遷移驗證",
    }
    placement = _cognitive_placement(
        task
    )

    clear()
    heading(
        labels.get(
            task.kind,
            "認知練習",
        )
    )
    print()
    print_wrapped(
        task.reason,
        ui_width() - 2,
    )
    print()

    if task.kind == "repair":
        print(
            f"{CYAN}{BOLD}"
            "修復步驟"
            f"{RESET}"
        )
        print_wrapped(
            repair_instruction(),
            ui_width() - 2,
        )
        if task.source_problem_id:
            print(
                f"{GRAY}"
                f"來源題目：{task.source_problem_id}"
                f"{RESET}"
            )

    elif task.kind == "discrimination":
        print(
            f"{CYAN}{BOLD}"
            "辨識任務"
            f"{RESET}"
        )
        print(
            "先比較兩種方法的成立條件，"
            "再只看新題題面與 constraints 決定方法。"
        )
        for uid in task.skill_uids:
            print(
                f"  - {skill_display_name(uid)}"
            )

    elif task.kind == "transfer":
        print(
            f"{CYAN}{BOLD}"
            "遷移任務"
            f"{RESET}"
        )
        print(
            "系統會直接提供一題新的 Published Transfer；"
            "作答前不顯示 Skill、Lesson、Role 或方法。"
        )

    print()
    print(
        f"{GRAY}"
        f"建議支援上限：{task.guidance or '—'}"
        f"{RESET}"
    )

    if placement is None:
        print()
        print(
            f"{YELLOW}"
            "目前沒有可安全使用的新 Published 題目；"
            "系統不會要求你自己找題或猜分類。"
            f"{RESET}"
        )
        pause()
        return current_filename

    print()
    rule()
    print()
    print(
        f"{WHITE}{BOLD}"
        f"{placement.problem_id} · {placement.title}"
        f"{RESET}"
    )
    if placement.url:
        print(
            f"{GRAY}{placement.url}{RESET}"
        )

    if task.kind == "transfer":
        print(
            f"{YELLOW}"
            "嚴格防劇透：本頁不顯示題目分類。"
            f"{RESET}"
        )
    else:
        print(
            f"{GRAY}"
            "系統已選好題目；不需要回題庫自行搜尋。"
            f"{RESET}"
        )

    selected = choose_menu(
        f"{labels.get(task.kind, '認知練習')} · 下一步",
        [
            {
                "label": "開始",
                "detail": (
                    "建立防劇透 scratch 並開始正式遷移"
                    if task.kind == "transfer"
                    else "開啟系統選定的新題"
                ),
                "enabled": True,
                "action": "開始",
            }
        ],
        footer_numbers=False,
        back_text="返回今日學習",
        enter_text="開始",
    )
    if selected is None:
        return current_filename

    if task.kind != "transfer":
        if placement.url:
            webbrowser.open(
                placement.url
            )
        return current_filename

    try:
        scratch = (
            create_reading_scratch(
                RUNTIME_DIR,
                placement,
                action="finish",
            )
            if task.track == "Reading"
            else create_learning_scratch(
                placement
            )
        )
    except (
        OSError,
        ValueError,
    ) as exc:
        clear()
        heading("遷移驗證")
        print()
        print(
            f"{RED}"
            f"✕ 無法建立 transfer scratch：{exc}"
            f"{RESET}"
        )
        pause()
        return current_filename

    opened = open_in_vscode(
        scratch
    )
    if placement.url:
        webbrowser.open(
            placement.url
        )

    clear()
    heading("遷移驗證")
    print()
    if opened:
        print(
            f"{GREEN}"
            "✓ 已開啟防劇透 transfer scratch"
            f"{RESET}"
        )
        print(
            f"{GRAY}"
            "完成後回控制中心記錄「完成題目」；"
            "只有真實 independent outcome 才能成為 Transfer Evidence。"
            f"{RESET}"
        )
    else:
        print(
            f"{RED}"
            "✕ 無法在 VS Code 開啟 transfer scratch"
            f"{RESET}"
        )
    pause()
    return str(scratch)



def skill_display_name(uid: str) -> str:
    try:
        for row in CURRICULUM.load().get("skills") or []:
            if str(row.get("uid") or "").strip() == uid:
                name = str(row.get("name") or "").strip()
                return f"{name}（{uid}）" if name else uid
    except RuntimeCurriculumError:
        pass
    return uid


def open_note(problem) -> None:
    pid = problem["id"]
    note = ROOT / "notes" / f"{pid}.md"
    existed = note.exists()

    try:
        with contextlib.redirect_stdout(io.StringIO()):
            core.note_cmd(pid)
    except SystemExit as exc:
        clear()
        heading("題目筆記")
        print()
        print(f"{RED}✕ 建立失敗：{exc}{RESET}")
        pause()
        return

    result = subprocess.run(
        ["code", "--reuse-window", str(note)],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    clear()
    heading("題目筆記")
    print()

    print(f"{WHITE}{problem_line(problem)}{RESET}")
    print(f"檔案  notes/{pid}.md")

    if existed:
        print(f"狀態  {CYAN}• 已存在{RESET}")
    else:
        print(f"狀態  {GREEN}✓ 已建立{RESET}")

    print()

    if result.returncode == 0:
        print(f"{GREEN}✓ 已在 VS Code 開啟{RESET}")
    else:
        print(f"{RED}✕ 無法自動開啟{RESET}")

    pause()


# ============================================================
# Git support
# ============================================================

def run_git(*args, capture=True):
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=capture,
        text=True,
    )


def git_changes():
    result = run_git(
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    )

    if result.returncode != 0:
        return []

    parts = result.stdout.split("\0")
    changes = []
    i = 0

    while i < len(parts):
        token = parts[i]

        if not token:
            break

        code = token[:2]
        path = token[3:]
        paths = [path]
        display = path

        if "R" in code or "C" in code:
            i += 1

            if i < len(parts) and parts[i]:
                other = parts[i]
                paths.append(other)
                display = f"{other} → {path}"

        changes.append(
            {
                "code": code,
                "path": path,
                "paths": paths,
                "display": display,
            }
        )

        i += 1

    return changes


def staged_count(changes) -> int:
    return sum(
        1
        for change in changes
        if change["code"][0] not in {" ", "?"}
    )


def unstaged_count(changes) -> int:
    return sum(
        1
        for change in changes
        if (
            change["code"] == "??"
            or change["code"][1] != " "
        )
    )


def validate_summary():
    output = io.StringIO()

    with contextlib.redirect_stdout(output):
        code = core.validate()

    text = output.getvalue()

    match = re.search(
        r"(?:Errors|錯誤)\s*[：:]\s*(\d+).*?"
        r"(?:Warnings|警告)\s*[：:]\s*(\d+)",
        text,
        flags=re.S,
    )

    if match:
        return code, int(match.group(1)), int(match.group(2))

    return code, None, None


def whitespace_ok() -> bool:
    a = run_git("diff", "--check")
    b = run_git("diff", "--cached", "--check")
    return a.returncode == 0 and b.returncode == 0


def local_quality_gate():
    return subprocess.run(
        [
            sys.executable,
            "tools/quality_gate.py",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def branch_sync():
    branch_result = run_git("branch", "--show-current")
    branch = branch_result.stdout.strip()

    upstream_result = run_git(
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        "@{u}",
    )

    if upstream_result.returncode != 0:
        return {
            "branch": branch,
            "upstream": None,
            "ahead": 0,
            "behind": 0,
        }

    upstream = upstream_result.stdout.strip()

    counts = run_git(
        "rev-list",
        "--left-right",
        "--count",
        f"{upstream}...HEAD",
    )

    try:
        behind, ahead = map(
            int,
            counts.stdout.strip().split(),
        )
    except Exception:
        behind, ahead = 0, 0

    return {
        "branch": branch,
        "upstream": upstream,
        "ahead": ahead,
        "behind": behind,
    }


def status_color(code: str) -> str:
    if "D" in code:
        return RED
    if code == "??":
        return YELLOW
    if "A" in code:
        return GREEN
    return CYAN


def review_changes() -> None:
    changes = git_changes()

    clear()
    heading("Git 變更")
    print()

    if not changes:
        print(f"{GREEN}✓ 工作區乾淨{RESET}")
        pause()
        return

    for change in changes[:20]:
        color = status_color(change["code"])
        path = fit(
            change["display"],
            ui_width() - 5,
        )

        print(
            f"{color}{change['code']}{RESET}  "
            f"{path}"
        )

    if len(changes) > 20:
        print()
        print(
            f"{GRAY}"
            f"…另有 {len(changes) - 20} 個變更"
            f"{RESET}"
        )

    print()
    rule()

    unstaged_stat = run_git("diff", "--stat").stdout.strip()
    staged_stat = run_git("diff", "--cached", "--stat").stdout.strip()

    if unstaged_stat:
        print(f"{GRAY}未暫存{RESET}")
        for line in unstaged_stat.splitlines()[-4:]:
            print(fit(line, ui_width()))

    if staged_stat:
        print()
        print(f"{GRAY}已暫存{RESET}")
        for line in staged_stat.splitlines()[-4:]:
            print(fit(line, ui_width()))

    pause()


def stage_changes() -> None:
    changes = git_changes()
    unstaged = [
        change
        for change in changes
        if (
            change["code"] == "??"
            or change["code"][1] != " "
        )
    ]

    clear()
    heading("加入暫存區")
    print()

    if not unstaged:
        print(f"{GREEN}✓ 沒有未暫存變更{RESET}")
        pause()
        return

    print(f"準備加入 {len(unstaged)} 個變更：")
    print()

    for change in unstaged[:15]:
        print(
            f"{status_color(change['code'])}"
            f"{change['code']}"
            f"{RESET}  "
            f"{fit(change['display'], ui_width() - 5)}"
        )

    if len(unstaged) > 15:
        print(
            f"{GRAY}"
            f"…另有 {len(unstaged) - 15} 個"
            f"{RESET}"
        )

    if not confirm("將以上變更加入 Git staging area？"):
        return

    paths = []

    for change in unstaged:
        for path in change["paths"]:
            if path not in paths:
                paths.append(path)

    result = run_git(
        "add",
        "-A",
        "--",
        *paths,
    )

    clear()
    heading("加入暫存區")
    print()

    if result.returncode == 0:
        print(f"{GREEN}✓ 已加入暫存區{RESET}")
    else:
        print(f"{RED}✕ Stage 失敗{RESET}")
        if result.stderr:
            print(fit(result.stderr.strip(), ui_width()))

    pause()


def push_commit(skip_confirm=False) -> bool:
    sync = branch_sync()

    if not sync["branch"]:
        clear()
        heading("Push")
        print()
        print(f"{RED}✕ 目前不是一般 Git branch{RESET}")
        pause()
        return False

    if sync["behind"] > 0:
        clear()
        heading("Push")
        print()
        print(
            f"{YELLOW}"
            f"遠端領先 {sync['behind']} 個 commit。"
            f"{RESET}"
        )
        print("請先同步遠端後再 Push。")
        pause()
        return False

    if sync["upstream"] and sync["ahead"] <= 0:
        clear()
        heading("Push")
        print()
        print(f"{GREEN}✓ 沒有待 Push 的 commit{RESET}")
        pause()
        return True

    if not skip_confirm:
        clear()
        heading("Push 到 GitHub")
        print()
        print(f"Branch  {sync['branch']}")

        if sync["upstream"]:
            print(f"Remote  {sync['upstream']}")
            print(f"待 Push  {sync['ahead']} commit")
        else:
            print("Remote  origin（建立 upstream）")

        if not confirm("確認 Push 到 GitHub？"):
            return False

    if sync["upstream"]:
        result = run_git("push")
    else:
        result = run_git(
            "push",
            "-u",
            "origin",
            sync["branch"],
        )

    clear()
    heading("Push 到 GitHub")
    print()

    if result.returncode == 0:
        print(f"{GREEN}✓ Push 完成{RESET}")
        pause()
        return True

    print(f"{RED}✕ Push 失敗{RESET}")

    message = (
        result.stderr.strip()
        or result.stdout.strip()
    )

    if message:
        print()
        for line in message.splitlines()[-6:]:
            print(fit(line, ui_width()))

    pause()
    return False


def suggested_commit_message() -> str:
    changes = git_changes()
    staged_paths = []

    for change in changes:
        code = change["code"]
        if (
            code != "??"
            and code[0] != " "
        ):
            staged_paths.extend(
                change["paths"]
            )

    if not staged_paths:
        return "chore: update APCS learning system"

    try:
        problems = core.CATALOG.load_problems()
        solutions = core.CATALOG.load_solutions()
    except CatalogError:
        problems = {}
        solutions = []

    path_to_problem = {
        item.path: item.problem_id
        for item in solutions
    }
    problem_ids = {
        path_to_problem[path]
        for path in staged_paths
        if path in path_to_problem
    }

    test_problem_ids = set()
    for path in staged_paths:
        parts = Path(path).parts
        if (
            len(parts) >= 4
            and parts[0] == "data"
            and parts[1] == "problem_enrichment"
        ):
            test_problem_ids.add(
                parts[3]
            )

    if (
        len(test_problem_ids) == 1
        and not problem_ids
    ):
        pid = next(
            iter(test_problem_ids)
        )
        return (
            f"test: add verified cases for {pid}"
        )

    if len(problem_ids) == 1:
        pid = next(
            iter(problem_ids)
        )
        title = (
            problems[pid].title
            if pid in problems
            else ""
        )
        return (
            f"solve: {pid}"
            + (
                f" {title}"
                if title
                else ""
            )
        )

    if all(
        path.startswith("docs/")
        for path in staged_paths
    ):
        return "docs: update APCS learning system"

    if any(
        (
            path.startswith("tools/")
            or path.startswith("tests/")
        )
        for path in staged_paths
    ):
        return "feat: refine APCS learning runtime"

    return "chore: update APCS learning system"


def create_commit() -> None:
    changes = git_changes()
    staged = staged_count(changes)

    clear()
    heading("建立 Commit")
    print()

    if staged == 0:
        print(
            f"{YELLOW}"
            "尚未有已暫存變更。"
            f"{RESET}"
        )
        print("請先使用「加入暫存區」。")
        pause()
        return

    if not whitespace_ok():
        print(
            f"{RED}"
            "✕ Git whitespace 檢查未通過"
            f"{RESET}"
        )
        print("請先修正後再 Commit。")
        pause()
        return

    print(
        f"{GRAY}"
        "正在執行完整 regression + warning gate…"
        f"{RESET}"
    )

    quality = local_quality_gate()

    if quality.returncode != 0:
        print()
        print(
            f"{RED}"
            "✕ Quality Gate 未通過；不建立 Commit"
            f"{RESET}"
        )

        output = (
            quality.stdout.strip()
            or quality.stderr.strip()
        )

        if output:
            print()
            for line in output.splitlines()[-12:]:
                print(
                    fit(
                        line,
                        ui_width(),
                    )
                )

        pause()
        return

    print(
        f"{GREEN}"
        "✓ Regression + warning gate 通過"
        f"{RESET}"
    )
    print()

    stat = run_git(
        "diff",
        "--cached",
        "--stat",
    ).stdout.strip()

    print(
        f"已暫存  {staged} 個變更"
    )
    if stat:
        for line in stat.splitlines()[-5:]:
            print(
                fit(
                    line,
                    ui_width(),
                )
            )

    suggestion = (
        suggested_commit_message()
    )
    print()
    print(
        f"{CYAN}{BOLD}"
        "建議 Commit message"
        f"{RESET}"
    )
    print(
        f"{WHITE}{suggestion}{RESET}"
    )
    print(
        f"{GRAY}"
        "直接 Enter 採用 · 輸入文字可改寫 · Q 取消"
        f"{RESET}"
    )
    print()

    try:
        raw = input("> ").strip()
    except (
        EOFError,
        KeyboardInterrupt,
    ):
        return

    if raw.casefold() == "q":
        return

    message = raw or suggestion

    clear()
    heading("確認 Commit")
    print()

    print(
        f"{GRAY}Message{RESET}"
    )
    print(
        fit(
            message,
            ui_width(),
        )
    )
    print()

    if stat:
        for line in stat.splitlines()[-5:]:
            print(
                fit(
                    line,
                    ui_width(),
                )
            )

    if not confirm(
        "建立這個 Commit？"
    ):
        return

    result = run_git(
        "commit",
        "-m",
        message,
    )

    clear()
    heading("Commit")
    print()

    if result.returncode != 0:
        print(
            f"{RED}"
            "✕ Commit 失敗"
            f"{RESET}"
        )

        error = (
            result.stderr.strip()
            or result.stdout.strip()
        )

        if error:
            print()
            for line in error.splitlines()[-6:]:
                print(
                    fit(
                        line,
                        ui_width(),
                    )
                )

        pause()
        return

    sha = run_git(
        "rev-parse",
        "--short",
        "HEAD",
    ).stdout.strip()

    print(
        f"{GREEN}"
        "✓ Commit 已建立"
        f"{RESET}"
    )
    print(
        f"SHA  {sha}"
    )
    print()
    print(
        f"{GRAY}"
        "建議在一個穩定工作段結束後再 Push；"
        "不要求每題立即 Push。"
        f"{RESET}"
    )
    pause()


def git_center() -> None:
    selected = 0

    while True:
        validation_code, errors, warnings = (
            validate_summary()
        )
        changes = git_changes()
        staged = staged_count(changes)
        unstaged = unstaged_count(changes)
        sync = branch_sync()
        format_ok = whitespace_ok()

        if errors is None:
            validation_text = (
                "資料驗證通過"
                if validation_code == 0
                else "資料驗證失敗"
            )
        else:
            validation_text = (
                f"{errors} errors · "
                f"{warnings} warnings"
            )

        push_enabled = (
            bool(sync["branch"])
            and sync["behind"] == 0
            and (
                sync["ahead"] > 0
                or sync["upstream"] is None
            )
        )

        options = [
            {
                "label": "查看差異",
                "detail": (
                    f"{len(changes)} 個變更"
                ),
                "enabled": True,
            },
            {
                "label": "加入暫存",
                "detail": (
                    f"{unstaged} 個未暫存"
                    if unstaged
                    else "無未暫存變更"
                ),
                "enabled": unstaged > 0,
            },
            {
                "label": "Commit",
                "detail": (
                    f"{staged} 個已暫存"
                    if staged
                    else "尚未暫存"
                ),
                "enabled": (
                    staged > 0
                    and format_ok
                ),
            },
            {
                "label": "Push",
                "detail": (
                    f"↑{sync['ahead']} · "
                    f"↓{sync['behind']}"
                    if sync["upstream"]
                    else "建立 upstream"
                ),
                "enabled": push_enabled,
            },
        ]

        if (
            selected >= len(options)
            or not options[selected][
                "enabled"
            ]
        ):
            selected = first_enabled(
                options
            )

        if ui_width() < 86:
            chosen = choose_menu(
                "檢查與提交",
                options,
                footer_numbers=True,
                back_text="返回控制中心",
            )
            if chosen is None:
                return
        else:
            clear()
            heading("檢查與提交")
            print()

            width = ui_width()
            gap = 4
            left = 54
            right = max(
                30,
                width - left - gap,
            )

            left_lines = [
                f"{CYAN}{BOLD}變更{RESET}",
            ]
            visible_changes = max(
                6,
                min(
                    14,
                    ui_height() - 18,
                ),
            )
            for change in changes[
                :visible_changes
            ]:
                left_lines.append(
                    f"{status_color(change['code'])}"
                    f"{change['code']}"
                    f"{RESET} "
                    f"{fit(change['display'], left - 4)}"
                )
            if not changes:
                left_lines.append(
                    f"{GREEN}✓ 工作區乾淨{RESET}"
                )
            elif len(changes) > visible_changes:
                left_lines.append(
                    f"{GRAY}"
                    f"…另有 {len(changes) - visible_changes} 個變更"
                    f"{RESET}"
                )

            data_color = (
                GREEN
                if validation_code == 0
                else RED
            )
            right_lines = [
                f"{CYAN}{BOLD}品質與同步{RESET}",
                (
                    f"資料      {data_color}"
                    f"{'✓' if validation_code == 0 else '✕'} "
                    f"{validation_text}{RESET}"
                ),
                (
                    f"格式      "
                    f"{GREEN if format_ok else RED}"
                    f"{'✓ 通過' if format_ok else '✕ 有問題'}"
                    f"{RESET}"
                ),
                (
                    f"已暫存    {staged}"
                    f" · 未暫存 {unstaged}"
                ),
                (
                    f"Branch    "
                    f"{sync['branch'] or '—'}"
                ),
                (
                    f"同步      ↑{sync['ahead']}"
                    f" · ↓{sync['behind']}"
                ),
                "",
                f"{CYAN}{BOLD}建議 Commit{RESET}",
                fit(
                    suggested_commit_message(),
                    right,
                ),
            ]

            rows = max(
                len(left_lines),
                len(right_lines),
            )
            for row in range(rows):
                a = (
                    left_lines[row]
                    if row < len(left_lines)
                    else ""
                )
                b = (
                    right_lines[row]
                    if row < len(right_lines)
                    else ""
                )
                print(
                    f"{pad_display(a, left)}"
                    + " " * gap
                    + f"{fit(b, right)}"
                )

            print()
            print(
                f"{GRAY}操作{RESET}"
            )
            cell_gap = 3
            cell_width = (
                width
                - cell_gap * 3
            ) // 4
            cells = []
            for index, option in enumerate(
                options
            ):
                label = (
                    f"{index + 1} "
                    f"{option['label']}"
                )
                if not option["enabled"]:
                    cells.append(
                        f"{GRAY}"
                        f"{pad_display(label, cell_width)}"
                        f"{RESET}"
                    )
                elif index == selected:
                    cells.append(
                        f"{CYAN}{BOLD}"
                        f"› "
                        f"{pad_display(label, max(1, cell_width - 2))}"
                        f"{RESET}"
                    )
                else:
                    cells.append(
                        pad_display(
                            label,
                            cell_width,
                        )
                    )
            print(
                (" " * cell_gap).join(
                    cells
                )
            )
            print()
            print_wrapped(
                options[selected]["detail"],
                width,
                color=GRAY,
            )

            print()
            rule()
            print(
                f"{GRAY}"
                "←→ 選操作 · Enter 執行"
                " · 1–4 直達 · Esc 返回控制中心"
                f"{RESET}"
            )

            key = read_key()
            if key == "LEFT":
                selected = move_enabled(
                    options,
                    selected,
                    -1,
                )
                continue
            if key == "RIGHT":
                selected = move_enabled(
                    options,
                    selected,
                    1,
                )
                continue
            if key in {
                "ESC",
                "q",
                "Q",
            }:
                return

            chosen = None
            if key == "ENTER":
                if options[selected][
                    "enabled"
                ]:
                    chosen = selected
            elif key in {
                "1",
                "2",
                "3",
                "4",
            }:
                index = int(key) - 1
                if options[index][
                    "enabled"
                ]:
                    selected = index
                    chosen = index

            if chosen is None:
                continue

        if chosen == 0:
            review_changes()
        elif chosen == 1:
            stage_changes()
        elif chosen == 2:
            create_commit()
        elif chosen == 3:
            push_commit()


# ============================================================
# Problem Library
# ============================================================

PROBLEM_LIBRARY_UNIT_LABELS = {
    "U-FND": "基礎語法與函式",
    "U-DAT": "資料處理與模擬",
    "U-PSV": "問題求解與複雜度",
    "U-ORD": "排序與關聯容器",
    "U-PFX": "前綴與差分",
    "U-WIN": "雙指標與滑動視窗",
    "U-BIN": "二分搜尋",
    "U-REC": "遞迴、回溯與解析",
    "U-DS": "基礎資料結構",
    "U-GPH": "圖論與樹",
    "U-GRD": "貪心",
    "U-DP": "動態規劃",
    "U-RNG": "區間與離線技巧",
}

PROBLEM_LIBRARY_DIFFICULTIES = (
    ("D1", "D1 · 入門"),
    ("D2", "D2 · 基礎"),
    ("D3", "D3 · 中等"),
    ("D4", "D4 · 進階"),
    ("D5", "D5 · 高難"),
)

PROBLEM_LIBRARY_ROLES = (
    ("Worked Example", "範例拆解"),
    ("Guided Drill", "引導練習"),
    ("Core Independent", "獨立練習"),
    ("Transfer Challenge", "遷移挑戰"),
    ("Mock", "模擬題"),
)

PROBLEM_LIBRARY_SOURCE_LABELS = {
    "zerojudge": "ZeroJudge",
    "cses": "CSES",
    "codeforces": "Codeforces",
    "leetcode": "LeetCode",
    "apcs": "APCS",
}


def _problem_library_items() -> list[LibraryItem]:
    """Learner-facing union of L0/L1 intelligence and Published placements.

    Problem Intelligence remains the richer browse source. Published
    Curriculum fills baseline coverage so an empty local intelligence cache
    never turns the learner-facing library into a 0-item dead end.
    No new identity or classification truth is created here.
    """

    indexed = list(
        PROBLEM_LIBRARY.items()
    )
    by_key = {
        (
            item.source.casefold(),
            item.external_id.casefold(),
        ): item
        for item in indexed
    }

    attempted = (
        PROBLEM_LIBRARY.attempted_pb_uids()
    )

    try:
        placements = (
            CURRICULUM.all_placements()
        )
    except RuntimeCurriculumError:
        placements = ()

    for placement in placements:
        source = (
            placement.source_platform
            or placement.judge_platform
            or "published"
        ).strip().casefold()
        external_id = (
            placement.problem_id
            .strip()
        )
        key = (
            source,
            external_id.casefold(),
        )
        if key in by_key:
            continue

        by_key[key] = LibraryItem(
            source=source,
            external_id=external_id,
            canonical_url=placement.url,
            title=placement.title,
            statement_summary="",
            lifecycle="PUBLISHED",
            classification_status="PUBLISHED",
            difficulty=(
                placement.difficulty
                or None
            ),
            primary_skill=(
                placement.primary_skill
                or None
            ),
            supporting_skills=tuple(
                placement.supporting_skills
            ),
            role=placement.role or None,
            pb_uid=placement.pb_uid or None,
            attempted=bool(
                placement.pb_uid
                and placement.pb_uid
                in attempted
            ),
            has_l2=False,
            trust_status=None,
        )

    return sorted(
        by_key.values(),
        key=lambda item: (
            item.source,
            item.external_id,
        ),
    )


def _problem_library_skill_groups():
    """Return learner-facing Unit → Skill groups in curriculum order."""

    try:
        skills = CURRICULUM.load().get("skills") or []
    except RuntimeCurriculumError:
        return []

    grouped = {}
    order = []

    for skill in sorted(
        skills,
        key=lambda row: float(
            row.get("path_order") or 9999
        ),
    ):
        unit = str(
            skill.get("unit") or "其他"
        ).strip()

        if unit not in grouped:
            grouped[unit] = []
            order.append(unit)

        grouped[unit].append(
            {
                "uid": str(
                    skill.get("uid") or ""
                ).strip(),
                "name": str(
                    skill.get("name") or ""
                ).strip(),
            }
        )

    return [
        {
            "uid": unit,
            "label": (
                PROBLEM_LIBRARY_UNIT_LABELS.get(
                    unit,
                    unit,
                )
            ),
            "skills": tuple(grouped[unit]),
        }
        for unit in order
    ]


def _problem_library_item_skill_uids(item) -> set[str]:
    return {
        value
        for value in (
            item.primary_skill,
            *item.supporting_skills,
        )
        if value
    }


def _problem_library_filter_items(
    items,
    filters,
    *,
    limit: int = 100,
):
    skill_uids = set(
        filters.get("skill_uids") or ()
    )
    source = filters.get("source")
    difficulty = filters.get("difficulty")
    attempted = filters.get("attempted")
    role = filters.get("role")
    require_l2 = filters.get("require_l2")

    result = []

    for item in items:
        if source and item.source != source:
            continue

        if (
            difficulty
            and item.difficulty != difficulty
        ):
            continue

        if (
            attempted is not None
            and item.attempted is not attempted
        ):
            continue

        if role and item.role != role:
            continue

        if (
            require_l2 is not None
            and item.has_l2 is not require_l2
        ):
            continue

        if skill_uids:
            if not (
                _problem_library_item_skill_uids(
                    item
                )
                & skill_uids
            ):
                continue

        result.append(item)

        if len(result) >= max(
            1,
            int(limit),
        ):
            break

    return result


def _problem_library_filter_summary(filters) -> str:
    parts = []

    skill_label = filters.get(
        "skill_label"
    )
    if skill_label:
        parts.append(skill_label)

    if filters.get("difficulty"):
        parts.append(filters["difficulty"])

    if filters.get("source"):
        parts.append(
            PROBLEM_LIBRARY_SOURCE_LABELS.get(
                filters["source"].casefold(),
                filters["source"],
            )
        )

    if filters.get("attempted") is False:
        parts.append("未做")
    elif filters.get("attempted") is True:
        parts.append("已做")

    if filters.get("role"):
        parts.append(
            dict(PROBLEM_LIBRARY_ROLES).get(
                filters["role"],
                filters["role"],
            )
        )

    if filters.get("require_l2") is True:
        parts.append("有教學資料")
    elif filters.get("require_l2") is False:
        parts.append("無教學資料")

    return (
        " · ".join(parts)
        if parts
        else "尚未設定條件"
    )


def _problem_library_source_label(source: str) -> str:
    return PROBLEM_LIBRARY_SOURCE_LABELS.get(
        source.casefold(),
        source,
    )


def _problem_library_choose_skill(
    filters,
    all_items,
):
    groups = _problem_library_skill_groups()

    if not groups:
        clear()
        heading("題目庫 · 學習主題")
        print()
        print(
            f"{YELLOW}"
            "目前無法讀取 Published Curriculum 的 Skill 分組。"
            f"{RESET}"
        )
        pause()
        return

    unit_options = [
        {
            "label": "不限主題",
            "detail": "清除目前的 Unit / Skill 條件",
            "enabled": True,
        }
    ]

    visible_groups = []

    for group in groups:
        unit_skill_uids = {
            skill["uid"]
            for skill in group["skills"]
        }
        count = len(
            _problem_library_filter_items(
                all_items,
                {
                    "skill_uids": (
                        unit_skill_uids
                    ),
                },
                limit=10000,
            )
        )

        visible_groups.append(group)
        unit_options.append(
            {
                "label": group["label"],
                "detail": (
                    f"{len(group['skills'])} 個 Skill"
                    f" · 題庫 {count} 題"
                ),
                "enabled": count > 0,
            }
        )

    selected = choose_menu(
        "題目庫 · 學習主題",
        unit_options,
        footer_numbers=False,
        back_text="返回分類找題",
    )

    if selected is None:
        return

    if selected == 0:
        filters["skill_uids"] = ()
        filters["skill_label"] = None
        return

    group = visible_groups[
        selected - 1
    ]
    unit_skill_uids = tuple(
        skill["uid"]
        for skill in group["skills"]
    )

    skill_options = [
        {
            "label": f"整個單元 · {group['label']}",
            "detail": (
                f"包含 {len(group['skills'])} 個 Skill"
            ),
            "enabled": True,
        }
    ]

    for skill in group["skills"]:
        count = len(
            _problem_library_filter_items(
                all_items,
                {
                    "skill_uids": (
                        skill["uid"],
                    ),
                },
                limit=10000,
            )
        )
        skill_options.append(
            {
                "label": skill["name"],
                "detail": (
                    f"{skill['uid']} · 題庫 {count} 題"
                ),
                "enabled": count > 0,
            }
        )

    skill_selected = choose_menu(
        f"題目庫 · {group['label']}",
        skill_options,
        footer_numbers=False,
        back_text="返回單元選擇",
    )

    if skill_selected is None:
        return

    if skill_selected == 0:
        filters["skill_uids"] = (
            unit_skill_uids
        )
        filters["skill_label"] = (
            group["label"]
        )
        return

    skill = group["skills"][
        skill_selected - 1
    ]
    filters["skill_uids"] = (
        skill["uid"],
    )
    filters["skill_label"] = (
        skill["name"]
    )


def _problem_library_choose_difficulty(
    filters,
    all_items,
):
    options = [
        {
            "label": "不限難度",
            "detail": "顯示所有難度",
            "enabled": True,
        }
    ]

    for value, label in (
        PROBLEM_LIBRARY_DIFFICULTIES
    ):
        count = sum(
            1
            for item in all_items
            if item.difficulty == value
        )
        options.append(
            {
                "label": label,
                "detail": f"題庫 {count} 題",
                "enabled": count > 0,
            }
        )

    selected = choose_menu(
        "題目庫 · 難度",
        options,
        footer_numbers=False,
        back_text="返回分類找題",
    )

    if selected is None:
        return

    filters["difficulty"] = (
        None
        if selected == 0
        else PROBLEM_LIBRARY_DIFFICULTIES[
            selected - 1
        ][0]
    )


def _problem_library_choose_source(
    filters,
    all_items,
):
    sources = sorted(
        {
            item.source
            for item in all_items
            if item.source
        },
        key=lambda value: (
            _problem_library_source_label(
                value
            ).casefold()
        ),
    )

    options = [
        {
            "label": "不限來源",
            "detail": "顯示所有 OJ / 題目來源",
            "enabled": True,
        }
    ]

    for source in sources:
        count = sum(
            1
            for item in all_items
            if item.source == source
        )
        options.append(
            {
                "label": (
                    _problem_library_source_label(
                        source
                    )
                ),
                "detail": f"題庫 {count} 題",
                "enabled": True,
            }
        )

    selected = choose_menu(
        "題目庫 · 來源",
        options,
        footer_numbers=False,
        back_text="返回分類找題",
    )

    if selected is None:
        return

    filters["source"] = (
        None
        if selected == 0
        else sources[selected - 1]
    )


def _problem_library_choose_status(
    filters,
):
    options = [
        {
            "label": "不限作答狀態",
            "detail": "已做與未做都顯示",
            "enabled": True,
        },
        {
            "label": "未做",
            "detail": "只找尚未留下 Attempt 的題目",
            "enabled": True,
        },
        {
            "label": "已做",
            "detail": "只找已有 Attempt 的題目",
            "enabled": True,
        },
    ]

    selected = choose_menu(
        "題目庫 · 作答狀態",
        options,
        footer_numbers=False,
        back_text="返回分類找題",
    )

    if selected is None:
        return

    filters["attempted"] = (
        None
        if selected == 0
        else selected == 2
    )


def _problem_library_choose_role(
    filters,
    all_items,
):
    options = [
        {
            "label": "不限練習用途",
            "detail": "所有活動類型",
            "enabled": True,
        }
    ]

    for value, label in (
        PROBLEM_LIBRARY_ROLES
    ):
        count = sum(
            1
            for item in all_items
            if item.role == value
        )
        options.append(
            {
                "label": label,
                "detail": (
                    f"{value} · 題庫 {count} 題"
                ),
                "enabled": count > 0,
            }
        )

    selected = choose_menu(
        "題目庫 · 練習用途",
        options,
        footer_numbers=False,
        back_text="返回分類找題",
    )

    if selected is None:
        return

    filters["role"] = (
        None
        if selected == 0
        else PROBLEM_LIBRARY_ROLES[
            selected - 1
        ][0]
    )


def _problem_library_choose_teaching(
    filters,
):
    options = [
        {
            "label": "不限教學資料",
            "detail": "有無 L2 教學資料都顯示",
            "enabled": True,
        },
        {
            "label": "有教學資料",
            "detail": "作答後可解鎖完整教學內容",
            "enabled": True,
        },
        {
            "label": "無教學資料",
            "detail": "只顯示尚未建立 L2 的題目",
            "enabled": True,
        },
    ]

    selected = choose_menu(
        "題目庫 · 教學資料",
        options,
        footer_numbers=False,
        back_text="返回分類找題",
    )

    if selected is None:
        return

    filters["require_l2"] = (
        None
        if selected == 0
        else selected == 1
    )


def _problem_library_safe_detail(
    item,
    mode: str,
) -> str:
    state = (
        "已做"
        if item.attempted
        else "未做"
    )
    source = (
        _problem_library_source_label(
            item.source
        )
    )

    if mode == "exam":
        return (
            f"{source} · {state}"
        )

    role_label = (
        dict(
            PROBLEM_LIBRARY_ROLES
        ).get(
            item.role,
            item.role or "—",
        )
    )
    l2 = (
        " · 有教學"
        if item.has_l2
        else ""
    )
    skill = (
        f" · {item.primary_skill}"
        if item.primary_skill
        else ""
    )
    return (
        f"{source}"
        f" · {item.difficulty or '—'}"
        f" · {state}"
        f" · {role_label}"
        f"{skill}{l2}"
    )


def _problem_library_item_detail(
    item,
    *,
    mode: str = "practice",
):
    strict = mode == "exam"
    view = (
        {}
        if strict
        else PROBLEM_LIBRARY.learner_view(
            item,
            activity=(
                item.role
                or "Core Independent"
            ),
            post_attempt=item.attempted,
        )
    )

    clear()
    heading(
        "題目庫 · 題目"
        + (
            " · 考試選題"
            if strict
            else " · 練習"
        )
    )
    print()
    print(
        f"{WHITE}{item.external_id} · "
        f"{item.title}{RESET}"
    )
    print(
        f"{GRAY}{item.canonical_url}{RESET}"
    )
    print()
    print(
        f"狀態      "
        f"{'做過' if item.attempted else '未做'}"
    )
    print(
        f"來源      "
        f"{_problem_library_source_label(item.source)}"
    )

    if strict:
        print()
        print(
            f"{YELLOW}"
            "考試選題：Skill、難度、用途、提示與教學資料全部隱藏。"
            f"{RESET}"
        )
    else:
        print(
            f"難度      "
            f"{view.get('difficulty') or '—'}"
        )
        print(
            f"活動      "
            f"{view.get('activity') or '—'}"
        )
        if item.primary_skill:
            print(
                f"主要 Skill "
                f"{item.primary_skill}"
            )

        if item.role in {
            "Transfer Challenge",
            "Mock",
        }:
            print()
            print(
                f"{GRAY}"
                "目前是練習選題；若你已透過 Skill / Unit 看見分類，"
                "這次不應作為正式 Transfer / Mock Evidence。"
                f"{RESET}"
            )

        if item.attempted and item.has_l2:
            print()
            rule()
            print()
            print(
                f"{CYAN}{BOLD}"
                "作答後教學"
                f"{RESET}"
            )
            print_wrapped(
                view.get(
                    "key_observation",
                    "—",
                ),
                ui_width() - 2,
            )
            print(
                f"複雜度    "
                f"{view.get('time_complexity', '—')}"
                " / "
                f"{view.get('space_complexity', '—')}"
            )

            pitfalls = (
                view.get(
                    "common_pitfalls"
                )
                or []
            )
            if pitfalls:
                print("常見陷阱")
                for pitfall in pitfalls:
                    print_wrapped(
                        pitfall,
                        ui_width() - 4,
                        prefix="  - ",
                        continuation_prefix="    ",
                    )

    print()
    if confirm("開啟原題網址？"):
        webbrowser.open(
            item.canonical_url
        )

    pause(
        "Enter / Esc 返回題目列表"
    )


def _problem_test_inventory(item) -> dict[str, int]:
    try:
        bundle = TEST_ASSETS.load(
            item.source or None,
            item.external_id,
            include_candidates=True,
        )
    except Exception:
        bundle = None

    return TEST_ASSETS.inventory(
        bundle
    )


def _problem_library_testcase_lines(
    item,
    *,
    mode: str,
) -> list[str]:
    try:
        bundle = TEST_ASSETS.load(
            item.source or None,
            item.external_id,
            include_candidates=True,
        )
    except Exception:
        bundle = None

    if bundle is None:
        return [
            "測資",
            "  尚未建立本地測資資產",
        ]

    strict = mode == "exam"
    pre_attempt = not item.attempted
    lines = ["測資"]

    official = [
        case
        for case in bundle.cases
        if case.provenance == "OFFICIAL"
    ]
    verified_generated = [
        case
        for case in bundle.cases
        if (
            case.provenance != "OFFICIAL"
            and case.verified
        )
    ]
    candidates = [
        case
        for case in bundle.cases
        if not case.verified
    ]

    lines.append(
        f"  官方 {len(official)}"
    )
    for case in official[:3]:
        lines.append(
            f"    {case.case_id} · "
            f"{fit(case.name, 20)}"
        )
    if len(official) > 3:
        lines.append(
            f"    …另有 {len(official) - 3} 組"
        )

    if strict and pre_attempt:
        lines.extend(
            [
                f"  延伸測資  作答後解鎖",
                (
                    f"  Candidate {len(candidates)}"
                    if candidates
                    else ""
                ),
            ]
        )
        return [
            line
            for line in lines
            if line
        ]

    lines.append(
        f"  已驗證延伸 {len(verified_generated)}"
    )
    for index, case in enumerate(
        verified_generated[:3],
        start=1,
    ):
        reveal_name = (
            item.attempted
            or item.role
            not in {
                "Core Independent",
                "Transfer Challenge",
                "Mock",
            }
        )
        label = (
            case.name
            if reveal_name
            else f"Local Case {index}"
        )
        lines.append(
            f"    {case.case_id} · "
            f"{fit(label, 20)}"
        )
    if len(verified_generated) > 3:
        lines.append(
            f"    …另有 {len(verified_generated) - 3} 組"
        )

    lines.append(
        f"  Candidate {len(candidates)}"
    )
    if candidates:
        lines.append(
            "    未驗證，不影響 PASS / FAIL"
        )

    return lines


def _problem_library_inspector_lines(
    item,
    *,
    mode: str,
) -> list[str]:
    strict = mode == "exam"
    lines = [
        f"{WHITE}{BOLD}{item.external_id}{RESET}",
        fit(item.title, 34),
        "",
        f"來源      {_problem_library_source_label(item.source)}",
        f"狀態      {'已做' if item.attempted else '未做'}",
    ]

    if strict:
        lines.extend(
            [
                "",
                f"{YELLOW}{BOLD}考試 · 防劇透{RESET}",
                "Skill / 難度 / 用途已隱藏",
                "",
                *_problem_library_testcase_lines(
                    item,
                    mode=mode,
                ),
            ]
        )
        return lines

    lines.extend(
        [
            f"難度      {item.difficulty or '—'}",
            f"用途      {dict(PROBLEM_LIBRARY_ROLES).get(item.role, item.role or '—')}",
            f"Skill     {item.primary_skill or '—'}",
            "",
            *_problem_library_testcase_lines(
                item,
                mode=mode,
            ),
            "",
            f"{GRAY}Input / Expected / Actual / Diff{RESET}",
            f"{GRAY}於 Ctrl+Shift+B 測試中心顯示{RESET}",
        ]
    )

    if item.has_l2:
        lines.append(
            f"{GREEN}教學資料  已建立{RESET}"
        )
    else:
        lines.append(
            f"{GRAY}教學資料  尚未建立{RESET}"
        )

    return lines



def _problem_library_results_view(
    items,
    *,
    title: str = "題目庫 · 結果",
    context: str | None = None,
    mode: str = "practice",
    select_only: bool = False,
):
    items = list(items)

    if not items:
        clear()
        heading(title)
        print()
        print(
            f"{YELLOW}"
            "沒有符合條件的題目。"
            f"{RESET}"
        )
        if context:
            print_wrapped(
                f"目前條件：{context}",
                ui_width() - 2,
                color=GRAY,
            )
        pause(
            "Enter / Esc 返回題目庫"
        )
        return None

    if (
        select_only
        or ui_width() < 86
    ):
        selected_index = min(
            int(
                UI_STATE.get(
                    "library_result_index",
                    0,
                )
            ),
            len(items) - 1,
        )

        while True:
            options = [
                {
                    "label": (
                        f"{item.external_id} · "
                        f"{item.title}"
                    ),
                    "detail": (
                        _problem_library_safe_detail(
                            item,
                            mode,
                        )
                    ),
                    "enabled": True,
                    "action": (
                        "選取"
                        if select_only
                        else "查看"
                    ),
                }
                for item in items
            ]

            selected = choose_menu(
                f"{title} · {len(items)} 題",
                options,
                footer_numbers=False,
                back_text="返回題目庫",
                enter_text=(
                    "選取"
                    if select_only
                    else "查看"
                ),
                selected_index=selected_index,
            )
            if selected is None:
                return None

            UI_STATE[
                "library_result_index"
            ] = selected
            selected_index = selected

            if select_only:
                return items[selected]

            _problem_library_item_detail(
                items[selected],
                mode=mode,
            )

    selected = min(
        int(
            UI_STATE.get(
                "library_result_index",
                0,
            )
        ),
        len(items) - 1,
    )

    while True:
        clear()
        heading(
            f"{title} · {len(items)} 題"
        )
        print_selection_mode_banner(
            mode,
            toggle_hint=False,
        )
        if context:
            print(
                f"{GRAY}"
                f"{fit(context, ui_width())}"
                f"{RESET}"
            )
        print()

        width = ui_width()
        gap = 4
        left = 54
        right = max(
            30,
            width - left - gap,
        )

        print(
            f"{CYAN}{BOLD}"
            f"{pad_display('題目', left)}"
            f"{RESET}"
            + " " * gap
            + f"{CYAN}{BOLD}"
            "題目側欄"
            f"{RESET}"
        )

        visible_rows = max(
            8,
            min(
                19,
                ui_height() - 14,
            ),
        )
        start_index = max(
            0,
            min(
                selected
                - visible_rows // 2,
                len(items)
                - visible_rows,
            ),
        )
        indexes = range(
            start_index,
            min(
                len(items),
                start_index + visible_rows,
            ),
        )

        list_lines = []
        for index in indexes:
            item = items[index]
            prefix = (
                "›"
                if index == selected
                else " "
            )
            state = (
                "已做"
                if item.attempted
                else "未做"
            )
            label = (
                f"{prefix} "
                f"{item.external_id} · "
                f"{item.title}"
            )
            detail = (
                f"{_problem_library_source_label(item.source)} · "
                f"{state}"
            )
            color = (
                CYAN + BOLD
                if index == selected
                else ""
            )
            list_lines.append(
                (
                    fit(label, left),
                    color,
                )
            )
            list_lines.append(
                (
                    fit(
                        "    " + detail,
                        left,
                    ),
                    GRAY,
                )
            )

        inspector = (
            _problem_library_inspector_lines(
                items[selected],
                mode=mode,
            )
        )

        rows = max(
            len(list_lines),
            len(inspector),
        )
        for row in range(rows):
            left_text, left_color = (
                list_lines[row]
                if row < len(list_lines)
                else ("", "")
            )
            right_text = (
                inspector[row]
                if row < len(inspector)
                else ""
            )
            print(
                f"{left_color}"
                f"{pad_display(left_text, left)}"
                f"{RESET if left_color else ''}"
                + " " * gap
                + f"{fit(right_text, right)}"
            )

        print()
        rule()
        print(
            f"{GRAY}"
            "↑↓ 選題 · Enter 查看詳細 · O 開啟 OJ · Esc 返回"
            f"{RESET}"
        )

        key = read_key()

        if key == "UP":
            selected = (
                selected - 1
            ) % len(items)
            UI_STATE[
                "library_result_index"
            ] = selected
            continue

        if key == "DOWN":
            selected = (
                selected + 1
            ) % len(items)
            UI_STATE[
                "library_result_index"
            ] = selected
            continue

        if key == "ENTER":
            _problem_library_item_detail(
                items[selected],
                mode=mode,
            )
            continue

        if key in {"o", "O"}:
            url = (
                items[selected]
                .canonical_url
            )
            if url:
                webbrowser.open(url)
            continue

        if key in {
            "ESC",
            "q",
            "Q",
        }:
            return None



def _recommended_problem_items(
    limit: int = 30,
):
    """Practice recommendation from the current route."""

    skill_uid = None
    try:
        snapshot = adaptive_today_snapshot()
        route = snapshot.get(
            "new_learning"
        )
        if (
            route is not None
            and route.skill is not None
        ):
            skill_uid = route.skill.uid
    except Exception:
        skill_uid = None

    items = _problem_library_items()

    if skill_uid:
        candidates = (
            _problem_library_filter_items(
                items,
                {
                    "skill_uids": (
                        skill_uid,
                    ),
                    "attempted": False,
                    "require_l2": True,
                },
                limit=100,
            )
        )
        if not candidates:
            candidates = (
                _problem_library_filter_items(
                    items,
                    {
                        "skill_uids": (
                            skill_uid,
                        ),
                        "attempted": False,
                    },
                    limit=100,
                )
            )
        if candidates:
            return (
                candidates[:limit],
                (
                    "練習模式 · 依目前 Today 學習路徑找尚未做題；"
                    "分類可見，因此不自動視為 Transfer Evidence"
                ),
            )

    return (
        _problem_library_filter_items(
            items,
            {
                "attempted": False,
            },
            limit=limit,
        ),
        "練習模式 · 尚未做 · 題庫穩定排序",
    )



def _exam_safe_problem_items(
    *,
    limit: int = 100,
):
    """Strict-spoiler candidate pool for exam-style selection."""

    all_items = (
        _problem_library_items()
    )
    items = (
        _problem_library_filter_items(
            all_items,
            {
                "attempted": False,
            },
            limit=limit,
        )
    )
    if items:
        return items

    return all_items[:limit]


def _problem_library_filter_options(
    filters,
    current,
    *,
    mode: str,
):
    options = [
        {
            "label": f"查看 {len(current)} 題",
            "detail": (
                _problem_library_filter_summary(
                    filters
                )
                if mode == "practice"
                else "考試選題 · 嚴格防劇透"
            ),
            "enabled": bool(current),
            "section": "目前結果",
            "action": "查看",
            "kind": "results",
        }
    ]

    if mode == "practice":
        options.extend(
            [
                {
                    "label": "學習主題",
                    "detail": (
                        filters.get(
                            "skill_label"
                        )
                        or "不限 · Unit → Skill"
                    ),
                    "enabled": True,
                    "section": "篩選條件",
                    "action": "設定",
                    "kind": "skill",
                },
                {
                    "label": "難度",
                    "detail": (
                        filters.get(
                            "difficulty"
                        )
                        or "不限 · D1–D5"
                    ),
                    "enabled": True,
                    "section": "篩選條件",
                    "action": "設定",
                    "kind": "difficulty",
                },
            ]
        )

    options.extend(
        [
            {
                "label": "來源",
                "detail": (
                    _problem_library_source_label(
                        filters["source"]
                    )
                    if filters.get("source")
                    else "不限"
                ),
                "enabled": True,
                "section": "篩選條件",
                "action": "設定",
                "kind": "source",
            },
            {
                "label": "作答狀態",
                "detail": (
                    "未做"
                    if filters.get(
                        "attempted"
                    )
                    is False
                    else (
                        "已做"
                        if filters.get(
                            "attempted"
                        )
                        is True
                        else "不限"
                    )
                ),
                "enabled": True,
                "section": "篩選條件",
                "action": "設定",
                "kind": "status",
            },
        ]
    )

    if mode == "practice":
        options.extend(
            [
                {
                    "label": "練習用途",
                    "detail": (
                        dict(
                            PROBLEM_LIBRARY_ROLES
                        ).get(
                            filters.get(
                                "role"
                            ),
                            "不限",
                        )
                    ),
                    "enabled": True,
                    "section": "篩選條件",
                    "action": "設定",
                    "kind": "role",
                },
                {
                    "label": "教學資料",
                    "detail": (
                        "有教學資料"
                        if filters.get(
                            "require_l2"
                        )
                        is True
                        else (
                            "無教學資料"
                            if filters.get(
                                "require_l2"
                            )
                            is False
                            else "不限"
                        )
                    ),
                    "enabled": True,
                    "section": "篩選條件",
                    "action": "設定",
                    "kind": "teaching",
                },
            ]
        )

    has_filters = any(
        (
            filters.get("skill_uids"),
            filters.get("difficulty"),
            filters.get("source"),
            filters.get(
                "attempted"
            )
            is not None,
            filters.get("role"),
            filters.get(
                "require_l2"
            )
            is not None,
        )
    )
    options.append(
        {
            "label": "清除全部條件",
            "detail": "恢復成不限",
            "enabled": has_filters,
            "section": "篩選條件",
            "action": "清除",
            "kind": "clear",
        }
    )

    return options


def _problem_library_choice_preview(
    kind: str,
    filters,
    *,
    mode: str,
) -> list[str]:
    if kind == "skill":
        current = (
            filters.get("skill_label")
            or "不限"
        )
        return [
            f"目前：{current}",
            "Unit → Skill",
            "先選單元，再選 Skill",
        ]

    if kind == "difficulty":
        return [
            "不限  D1  D2",
            "D3    D4  D5",
        ]

    if kind == "source":
        sources = sorted(
            {
                _problem_library_source_label(
                    item.source
                )
                for item
                in _problem_library_items()
                if item.source
            }
        )
        return (
            ["不限"]
            + sources[:6]
        )

    if kind == "status":
        return [
            "不限",
            "未做",
            "已做",
        ]

    if kind == "role":
        return [
            "不限",
            "範例拆解",
            "引導練習",
            "獨立練習",
            "遷移挑戰",
            "模擬題",
        ]

    if kind == "teaching":
        return [
            "不限",
            "有教學資料",
            "無教學資料",
        ]

    if kind == "clear":
        return [
            "清除所有條件",
            "回到完整題庫",
        ]

    if kind == "results":
        return [
            "S 或 Enter",
            "開啟目前結果",
        ]

    return []


def _problem_library_filter_choice(
    filters,
    current,
    *,
    mode: str,
):
    options = (
        _problem_library_filter_options(
            filters,
            current,
            mode=mode,
        )
    )

    if ui_width() < 86:
        selected = choose_menu(
            "題目庫 · 分類找題",
            options,
            footer_numbers=False,
            back_text="返回題目庫",
        )
        return (
            None
            if selected is None
            else options[selected]["kind"]
        )

    selected = first_enabled(
        options
    )

    while True:
        output = io.StringIO()
        with contextlib.redirect_stdout(
            output
        ):
            heading(
                "題目庫 · 分類找題"
            )
            print_selection_mode_banner(
                mode,
                toggle_hint=False,
            )
            print()

            width = ui_width()
            gap = 3
            left = 28
            middle = 24
            right = max(
                28,
                width
                - left
                - middle
                - gap * 2,
            )

            result_color = (
                GREEN
                if current
                else YELLOW
            )
            print(
                f"{CYAN}{BOLD}"
                f"{pad_display('篩選條件', left)}"
                f"{RESET}"
                + " " * gap
                + f"{CYAN}{BOLD}"
                f"{pad_display('可選值', middle)}"
                f"{RESET}"
                + " " * gap
                + f"{result_color}{BOLD}"
                f"目前 {len(current)} 題"
                f"{RESET}"
            )

            filter_rows = []
            for index, option in enumerate(
                options
            ):
                if option["kind"] == "results":
                    continue
                prefix = (
                    "›"
                    if index == selected
                    else " "
                )
                value = (
                    option.get("detail")
                    or "不限"
                )
                label = (
                    f"{prefix} "
                    f"{option['label']}："
                    f"{value}"
                )
                color = (
                    CYAN + BOLD
                    if index == selected
                    else (
                        GRAY
                        if not option.get(
                            "enabled",
                            True,
                        )
                        else ""
                    )
                )
                filter_rows.append(
                    (
                        fit(label, left),
                        color,
                    )
                )

            selected_kind = (
                options[selected]["kind"]
            )
            choice_rows = (
                _problem_library_choice_preview(
                    selected_kind,
                    filters,
                    mode=mode,
                )
            )

            preview_count = max(
                6,
                min(
                    14,
                    ui_height() - 17,
                ),
            )
            result_rows = [
                (
                    f"{item.external_id} · "
                    f"{fit(
                        item.title,
                        max(8, right - 8),
                    )}"
                )
                for item in current[
                    :preview_count
                ]
            ]
            if not result_rows:
                result_rows = [
                    "沒有符合條件的題目"
                ]
            elif (
                len(current)
                > preview_count
            ):
                result_rows.append(
                    f"…另有 "
                    f"{len(current) - preview_count} 題"
                )

            rows = max(
                len(filter_rows),
                len(choice_rows),
                len(result_rows),
            )

            for row in range(rows):
                left_text, left_color = (
                    filter_rows[row]
                    if row < len(filter_rows)
                    else ("", "")
                )
                middle_text = (
                    choice_rows[row]
                    if row < len(choice_rows)
                    else ""
                )
                right_text = (
                    result_rows[row]
                    if row < len(result_rows)
                    else ""
                )

                print(
                    f"{left_color}"
                    f"{pad_display(left_text, left)}"
                    f"{RESET if left_color else ''}"
                    + " " * gap
                    + f"{GRAY}"
                    f"{pad_display(middle_text, middle)}"
                    f"{RESET}"
                    + " " * gap
                    + f"{fit(right_text, right)}"
                )

            print()
            print(
                f"{result_color}{BOLD}"
                f"S 查看目前 {len(current)} 題"
                f"{RESET}"
            )
            print()
            rule()
            print(
                f"{GRAY}"
                "↑↓ 選條件 · Enter 設定"
                " · S 查看結果 · Esc 返回"
                f"{RESET}"
            )

        sys.stdout.write(
            "\033[2J\033[H"
            + output.getvalue()
        )
        sys.stdout.flush()

        key = read_key()
        if key == "UP":
            selected = move_enabled(
                options,
                selected,
                -1,
            )
        elif key == "DOWN":
            selected = move_enabled(
                options,
                selected,
                1,
            )
        elif (
            key in {"s", "S"}
            and current
        ):
            return "results"
        elif key == "ENTER":
            if options[selected].get(
                "enabled",
                True,
            ):
                return options[selected][
                    "kind"
                ]
        elif key in {
            "ESC",
            "q",
            "Q",
        }:
            return None



def _problem_library_filter_count(
    all_items,
    filters,
    **overrides,
) -> int:
    candidate = dict(filters)
    candidate.update(overrides)
    return len(
        _problem_library_filter_items(
            all_items,
            candidate,
            limit=10000,
        )
    )


def _problem_library_direct_choices(
    kind: str,
    filters,
    all_items,
    *,
    skill_unit: str | None,
):
    if kind == "skill":
        groups = (
            _problem_library_skill_groups()
        )

        if skill_unit is None:
            choices = [
                {
                    "label": "不限主題",
                    "detail": (
                        f"{_problem_library_filter_count(
                            all_items,
                            filters,
                            skill_uids=(),
                            skill_label=None,
                        )} 題"
                    ),
                    "action": "skill_clear",
                }
            ]
            for group in groups:
                uids = tuple(
                    item["uid"]
                    for item in group["skills"]
                )
                choices.append(
                    {
                        "label": group["label"],
                        "detail": (
                            f"{len(group['skills'])} Skill"
                            f" · {_problem_library_filter_count(
                                all_items,
                                filters,
                                skill_uids=uids,
                            )} 題"
                        ),
                        "action": "skill_unit",
                        "unit": group["uid"],
                    }
                )
            return choices

        group = next(
            (
                item
                for item in groups
                if item["uid"] == skill_unit
            ),
            None,
        )
        if group is None:
            return []

        uids = tuple(
            item["uid"]
            for item in group["skills"]
        )
        choices = [
            {
                "label": "← 返回單元",
                "detail": group["label"],
                "action": "skill_back",
            },
            {
                "label": (
                    f"整個單元 · {group['label']}"
                ),
                "detail": (
                    f"{_problem_library_filter_count(
                        all_items,
                        filters,
                        skill_uids=uids,
                    )} 題"
                ),
                "action": "skill_value",
                "skill_uids": uids,
                "skill_label": group["label"],
            },
        ]

        for skill in group["skills"]:
            uid = skill["uid"]
            choices.append(
                {
                    "label": skill["name"],
                    "detail": (
                        f"{uid} · "
                        f"{_problem_library_filter_count(
                            all_items,
                            filters,
                            skill_uids=(uid,),
                        )} 題"
                    ),
                    "action": "skill_value",
                    "skill_uids": (uid,),
                    "skill_label": skill["name"],
                }
            )

        return choices

    if kind == "difficulty":
        values = [
            (None, "不限"),
            *PROBLEM_LIBRARY_DIFFICULTIES,
        ]
        return [
            {
                "label": label,
                "detail": (
                    f"{_problem_library_filter_count(
                        all_items,
                        filters,
                        difficulty=value,
                    )} 題"
                ),
                "action": "value",
                "field": "difficulty",
                "value": value,
            }
            for value, label in values
        ]

    if kind == "source":
        sources = sorted(
            {
                item.source
                for item in all_items
                if item.source
            },
            key=lambda value: (
                _problem_library_source_label(
                    value
                ).casefold()
            ),
        )
        values = [
            (None, "不限"),
            *[
                (
                    source,
                    _problem_library_source_label(
                        source
                    ),
                )
                for source in sources
            ],
        ]
        return [
            {
                "label": label,
                "detail": (
                    f"{_problem_library_filter_count(
                        all_items,
                        filters,
                        source=value,
                    )} 題"
                ),
                "action": "value",
                "field": "source",
                "value": value,
            }
            for value, label in values
        ]

    if kind == "status":
        values = [
            (None, "不限"),
            (False, "未做"),
            (True, "已做"),
        ]
        return [
            {
                "label": label,
                "detail": (
                    f"{_problem_library_filter_count(
                        all_items,
                        filters,
                        attempted=value,
                    )} 題"
                ),
                "action": "value",
                "field": "attempted",
                "value": value,
            }
            for value, label in values
        ]

    if kind == "role":
        values = [
            (None, "不限"),
            *PROBLEM_LIBRARY_ROLES,
        ]
        return [
            {
                "label": label,
                "detail": (
                    f"{_problem_library_filter_count(
                        all_items,
                        filters,
                        role=value,
                    )} 題"
                ),
                "action": "value",
                "field": "role",
                "value": value,
            }
            for value, label in values
        ]

    if kind == "teaching":
        values = [
            (None, "不限"),
            (True, "有教學資料"),
            (False, "無教學資料"),
        ]
        return [
            {
                "label": label,
                "detail": (
                    f"{_problem_library_filter_count(
                        all_items,
                        filters,
                        require_l2=value,
                    )} 題"
                ),
                "action": "value",
                "field": "require_l2",
                "value": value,
            }
            for value, label in values
        ]

    if kind == "clear":
        return [
            {
                "label": "清除全部條件",
                "detail": "恢復成完整題庫",
                "action": "clear",
            }
        ]

    return []


def _problem_library_apply_direct_choice(
    filters,
    choice,
    *,
    skill_unit: str | None,
):
    action = choice.get("action")

    if action == "skill_clear":
        filters["skill_uids"] = ()
        filters["skill_label"] = None
        return None

    if action == "skill_unit":
        return choice["unit"]

    if action == "skill_back":
        return None

    if action == "skill_value":
        filters["skill_uids"] = tuple(
            choice["skill_uids"]
        )
        filters["skill_label"] = (
            choice["skill_label"]
        )
        return None

    if action == "value":
        filters[choice["field"]] = (
            choice["value"]
        )
        return skill_unit

    if action == "clear":
        filters.update(
            {
                "skill_uids": (),
                "skill_label": None,
                "difficulty": None,
                "source": None,
                "attempted": None,
                "role": None,
                "require_l2": None,
            }
        )
        return None

    return skill_unit


def _problem_library_filter_browser(
    filters,
    all_items,
    *,
    mode: str,
):
    focus = 0
    filter_index = 0
    choice_index = 0
    result_index = min(
        int(
            UI_STATE.get(
                "library_result_index",
                0,
            )
        ),
        max(0, len(all_items) - 1),
    )
    skill_unit = None

    while True:
        current = (
            _problem_library_filter_items(
                all_items,
                filters,
                limit=10000,
            )
        )

        filter_options = [
            option
            for option in (
                _problem_library_filter_options(
                    filters,
                    current,
                    mode=mode,
                )
            )
            if option["kind"] != "results"
        ]
        filter_index = min(
            filter_index,
            max(
                0,
                len(filter_options) - 1,
            ),
        )

        kind = (
            filter_options[
                filter_index
            ]["kind"]
        )
        if kind != "skill":
            skill_unit = None

        choices = (
            _problem_library_direct_choices(
                kind,
                filters,
                all_items,
                skill_unit=skill_unit,
            )
        )
        choice_index = min(
            choice_index,
            max(
                0,
                len(choices) - 1,
            ),
        )
        result_index = min(
            result_index,
            max(
                0,
                len(current) - 1,
            ),
        )

        clear()
        heading("題目庫 · 分類找題")
        print_selection_mode_banner(
            mode,
            toggle_hint=False,
        )
        print()

        width = ui_width()
        gap = 3
        left = 29
        middle = 29
        right = max(
            30,
            width
            - left
            - middle
            - gap * 2,
        )

        headers = [
            "篩選條件",
            "可選值",
            f"目前 {len(current)} 題",
        ]
        header_cells = []
        for index, label in enumerate(
            headers
        ):
            color = (
                CYAN + BOLD
                if focus == index
                else GRAY
            )
            pane_width = (
                left
                if index == 0
                else (
                    middle
                    if index == 1
                    else right
                )
            )
            header_cells.append(
                f"{color}"
                f"{pad_display(label, pane_width)}"
                f"{RESET}"
            )
        print(
            (" " * gap).join(
                header_cells
            )
        )

        filter_lines = []
        for index, option in enumerate(
            filter_options
        ):
            prefix = (
                "›"
                if (
                    focus == 0
                    and index == filter_index
                )
                else " "
            )
            color = (
                CYAN + BOLD
                if (
                    focus == 0
                    and index == filter_index
                )
                else (
                    GRAY
                    if not option.get(
                        "enabled",
                        True,
                    )
                    else ""
                )
            )
            text = (
                f"{prefix} "
                f"{option['label']}"
            )
            filter_lines.append(
                (
                    fit(
                        text,
                        left,
                    ),
                    color,
                )
            )
            if option.get("detail"):
                filter_lines.append(
                    (
                        fit(
                            "    "
                            + str(
                                option["detail"]
                            ),
                            left,
                        ),
                        GRAY,
                    )
                )

        choice_lines = []
        for index, choice in enumerate(
            choices
        ):
            prefix = (
                "›"
                if (
                    focus == 1
                    and index == choice_index
                )
                else " "
            )
            color = (
                CYAN + BOLD
                if (
                    focus == 1
                    and index == choice_index
                )
                else ""
            )
            choice_lines.append(
                (
                    fit(
                        f"{prefix} "
                        f"{choice['label']}",
                        middle,
                    ),
                    color,
                )
            )
            if choice.get("detail"):
                choice_lines.append(
                    (
                        fit(
                            "    "
                            + str(
                                choice["detail"]
                            ),
                            middle,
                        ),
                        GRAY,
                    )
                )

        visible = max(
            7,
            min(
                16,
                ui_height() - 14,
            ),
        )
        result_start = max(
            0,
            min(
                result_index
                - visible // 2,
                len(current) - visible,
            ),
        )
        result_lines = []
        for index in range(
            result_start,
            min(
                len(current),
                result_start + visible,
            ),
        ):
            item = current[index]
            prefix = (
                "›"
                if (
                    focus == 2
                    and index == result_index
                )
                else " "
            )
            color = (
                CYAN + BOLD
                if (
                    focus == 2
                    and index == result_index
                )
                else ""
            )
            result_lines.append(
                (
                    fit(
                        f"{prefix} "
                        f"{item.external_id} · "
                        f"{item.title}",
                        right,
                    ),
                    color,
                )
            )
            result_lines.append(
                (
                    fit(
                        "    "
                        + _problem_library_safe_detail(
                            item,
                            mode,
                        ),
                        right,
                    ),
                    GRAY,
                )
            )

        if not current:
            result_lines = [
                (
                    "沒有符合條件的題目",
                    YELLOW,
                )
            ]

        rows = max(
            len(filter_lines),
            len(choice_lines),
            len(result_lines),
        )
        max_rows = max(
            10,
            ui_height() - 11,
        )

        for row in range(
            min(rows, max_rows)
        ):
            cells = []
            for lines, pane_width in (
                (filter_lines, left),
                (choice_lines, middle),
                (result_lines, right),
            ):
                if row < len(lines):
                    value, color = (
                        lines[row]
                    )
                else:
                    value, color = (
                        "",
                        "",
                    )
                cells.append(
                    f"{color}"
                    f"{pad_display(value, pane_width)}"
                    f"{RESET if color else ''}"
                )
            print(
                (" " * gap).join(
                    cells
                )
            )

        print()
        rule()

        if focus == 0:
            action = (
                "Enter 選擇此條件"
            )
        elif focus == 1:
            action = (
                "Enter 套用"
            )
        else:
            action = (
                "Enter 查看題目 · O 開啟 OJ"
            )

        print(
            f"{GRAY}"
            "Tab / Shift+Tab 切換區域"
            f" · ↑↓ 選擇 · {action}"
            " · Esc 返回"
            f"{RESET}"
        )

        key = read_key()

        if key == "TAB":
            focus = (
                focus + 1
            ) % 3
            continue

        if key == "BACKTAB":
            focus = (
                focus - 1
            ) % 3
            continue

        if key == "UP":
            if focus == 0 and filter_options:
                filter_index = (
                    filter_index - 1
                ) % len(filter_options)
                choice_index = 0
                skill_unit = None
            elif focus == 1 and choices:
                choice_index = (
                    choice_index - 1
                ) % len(choices)
            elif focus == 2 and current:
                result_index = (
                    result_index - 1
                ) % len(current)
                UI_STATE[
                    "library_result_index"
                ] = result_index
            continue

        if key == "DOWN":
            if focus == 0 and filter_options:
                filter_index = (
                    filter_index + 1
                ) % len(filter_options)
                choice_index = 0
                skill_unit = None
            elif focus == 1 and choices:
                choice_index = (
                    choice_index + 1
                ) % len(choices)
            elif focus == 2 and current:
                result_index = (
                    result_index + 1
                ) % len(current)
                UI_STATE[
                    "library_result_index"
                ] = result_index
            continue

        if key == "ENTER":
            if focus == 0:
                if (
                    filter_options
                    and filter_options[
                        filter_index
                    ]["kind"]
                    == "clear"
                ):
                    filters.update(
                        {
                            "skill_uids": (),
                            "skill_label": None,
                            "difficulty": None,
                            "source": None,
                            "attempted": None,
                            "role": None,
                            "require_l2": None,
                        }
                    )
                    choice_index = 0
                else:
                    focus = 1
                continue

            if focus == 1 and choices:
                skill_unit = (
                    _problem_library_apply_direct_choice(
                        filters,
                        choices[
                            choice_index
                        ],
                        skill_unit=skill_unit,
                    )
                )
                choice_index = 0
                result_index = 0
                UI_STATE[
                    "library_result_index"
                ] = 0
                continue

            if focus == 2 and current:
                _problem_library_item_detail(
                    current[
                        result_index
                    ],
                    mode=mode,
                )
                continue

        if (
            focus == 2
            and key in {"o", "O"}
            and current
        ):
            url = current[
                result_index
            ].canonical_url
            if url:
                webbrowser.open(url)
            continue

        if key in {
            "ESC",
            "q",
            "Q",
        }:
            if (
                focus == 1
                and skill_unit
            ):
                skill_unit = None
                choice_index = 0
                continue
            return



def _problem_library_empty_filters():
    return {
        "skill_uids": (),
        "skill_label": None,
        "difficulty": None,
        "source": None,
        "attempted": None,
        "role": None,
        "require_l2": None,
    }


def _problem_library_saved_filters(
    mode: str,
):
    key = (
        "library_filters_exam"
        if mode == "exam"
        else "library_filters_practice"
    )
    saved = UI_STATE.get(key)
    filters = (
        dict(saved)
        if isinstance(saved, dict)
        else _problem_library_empty_filters()
    )

    # Exam selection must never inherit hidden classification filters.
    if mode == "exam":
        filters.update(
            {
                "skill_uids": (),
                "skill_label": None,
                "difficulty": None,
                "role": None,
                "require_l2": None,
            }
        )

    return filters


def _problem_library_save_filters(
    mode: str,
    filters,
) -> None:
    key = (
        "library_filters_exam"
        if mode == "exam"
        else "library_filters_practice"
    )
    UI_STATE[key] = dict(filters)


def _problem_library_saved_query(
    mode: str,
) -> str:
    key = (
        "library_query_exam"
        if mode == "exam"
        else "library_query_practice"
    )
    return str(
        UI_STATE.get(key)
        or ""
    )


def _problem_library_save_query(
    mode: str,
    query: str,
) -> None:
    key = (
        "library_query_exam"
        if mode == "exam"
        else "library_query_practice"
    )
    UI_STATE[key] = str(
        query or ""
    ).strip()


def _problem_library_query_filter(
    items,
    query: str,
    *,
    mode: str,
):
    folded = str(
        query or ""
    ).strip().casefold()

    if not folded:
        return list(items)

    if mode == "exam":
        return [
            item
            for item in items
            if folded
            in (
                f"{item.external_id} "
                f"{item.title}"
            ).casefold()
        ]

    return [
        item
        for item in items
        if folded
        in " ".join(
            [
                item.external_id,
                item.title,
                item.source,
                item.difficulty or "",
                item.role or "",
                item.primary_skill or "",
                *item.supporting_skills,
            ]
        ).casefold()
    ]


def _problem_library_workbench_filter_options(
    filters,
    *,
    mode: str,
):
    if mode == "exam":
        return [
            {
                "label": "安全選題",
                "detail": "優先未做題 · strict spoiler",
                "kind": "safe",
                "enabled": True,
            },
            {
                "label": "來源",
                "detail": (
                    _problem_library_source_label(
                        filters["source"]
                    )
                    if filters.get("source")
                    else "不限"
                ),
                "kind": "source",
                "enabled": True,
            },
            {
                "label": "作答狀態",
                "detail": (
                    "未做"
                    if filters.get("attempted") is False
                    else (
                        "已做"
                        if filters.get("attempted") is True
                        else "不限"
                    )
                ),
                "kind": "status",
                "enabled": True,
            },
            {
                "label": "清除全部條件",
                "detail": "回到完整 strict-spoiler 題庫",
                "kind": "clear",
                "enabled": True,
            },
        ]

    return [
        {
            "label": "推薦給我",
            "detail": "依 Today 路徑找尚未做題",
            "kind": "recommend",
            "enabled": True,
        },
        {
            "label": "學習主題",
            "detail": (
                filters.get("skill_label")
                or "不限 · Unit → Skill"
            ),
            "kind": "skill",
            "enabled": True,
        },
        {
            "label": "難度",
            "detail": (
                filters.get("difficulty")
                or "不限 · D1–D5"
            ),
            "kind": "difficulty",
            "enabled": True,
        },
        {
            "label": "來源",
            "detail": (
                _problem_library_source_label(
                    filters["source"]
                )
                if filters.get("source")
                else "不限"
            ),
            "kind": "source",
            "enabled": True,
        },
        {
            "label": "作答狀態",
            "detail": (
                "未做"
                if filters.get("attempted") is False
                else (
                    "已做"
                    if filters.get("attempted") is True
                    else "不限"
                )
            ),
            "kind": "status",
            "enabled": True,
        },
        {
            "label": "練習用途",
            "detail": dict(
                PROBLEM_LIBRARY_ROLES
            ).get(
                filters.get("role"),
                "不限",
            ),
            "kind": "role",
            "enabled": True,
        },
        {
            "label": "教學資料",
            "detail": (
                "有教學資料"
                if filters.get("require_l2") is True
                else (
                    "無教學資料"
                    if filters.get("require_l2") is False
                    else "不限"
                )
            ),
            "kind": "teaching",
            "enabled": True,
        },
        {
            "label": "清除全部條件",
            "detail": "恢復完整練習題庫",
            "kind": "clear",
            "enabled": True,
        },
    ]


def _problem_library_apply_preset(
    mode: str,
    filters,
):
    if mode == "exam":
        filters.update(
            _problem_library_empty_filters()
        )
        filters["attempted"] = False
        return "優先未做 · strict spoiler"

    items, reason = _recommended_problem_items(
        limit=10000,
    )
    ids = {
        (
            item.source.casefold(),
            item.external_id.casefold(),
        )
        for item in items
    }
    return (
        reason,
        ids,
    )


def _problem_library_workbench(
    *,
    mode: str,
):
    all_items = (
        _problem_library_items()
    )
    filters = (
        _problem_library_saved_filters(
            mode
        )
    )
    query = (
        _problem_library_saved_query(
            mode
        )
    )

    focus = int(
        UI_STATE.get(
            "library_focus",
            0,
        )
    )
    focus = max(
        0,
        min(2, focus),
    )
    filter_index = 0
    choice_index = 0
    result_index = min(
        int(
            UI_STATE.get(
                "library_result_index",
                0,
            )
        ),
        max(0, len(all_items) - 1),
    )
    editing_kind = None
    skill_unit = None
    preset_ids = None
    preset_note = ""

    while True:
        current = (
            _problem_library_filter_items(
                all_items,
                filters,
                limit=10000,
            )
        )
        current = (
            _problem_library_query_filter(
                current,
                query,
                mode=mode,
            )
        )
        if preset_ids is not None:
            current = [
                item
                for item in current
                if (
                    item.source.casefold(),
                    item.external_id.casefold(),
                )
                in preset_ids
            ]

        result_index = min(
            result_index,
            max(0, len(current) - 1),
        )

        filter_options = (
            _problem_library_workbench_filter_options(
                filters,
                mode=mode,
            )
        )
        filter_index = min(
            filter_index,
            len(filter_options) - 1,
        )

        choices = []
        if editing_kind is not None:
            choice_base_items = (
                _problem_library_query_filter(
                    all_items,
                    query,
                    mode=mode,
                )
            )
            choices = (
                _problem_library_direct_choices(
                    editing_kind,
                    filters,
                    choice_base_items,
                    skill_unit=skill_unit,
                )
            )
            choice_index = min(
                choice_index,
                max(0, len(choices) - 1),
            )

        clear()
        heading("題目庫")
        print_selection_mode_banner(
            mode,
            toggle_hint=True,
        )
        if query:
            print(
                f"{GRAY}"
                f"搜尋：{query}"
                " · / 修改 · X 清除"
                f"{RESET}"
            )
        elif preset_note:
            print(
                f"{GRAY}"
                f"目前：{preset_note}"
                f"{RESET}"
            )
        print()

        width = ui_width()
        gap = 3
        left, middle, right = (
            workbench_pane_widths(
                width,
                (27, 38, 35),
                gap=gap,
                min_width=20,
            )
        )

        headers = [
            "篩選",
            f"題目 · {len(current)} 題",
            "題目側欄",
        ]
        header_cells = []
        for index, label in enumerate(
            headers
        ):
            pane_width = (
                left
                if index == 0
                else (
                    middle
                    if index == 1
                    else right
                )
            )
            color = (
                GREEN + BOLD
                if index == 1
                else (
                    CYAN + BOLD
                    if focus == index
                    else GRAY
                )
            )
            header_cells.append(
                f"{color}"
                f"{pad_display(label, pane_width)}"
                f"{RESET}"
            )
        print(
            (" " * gap).join(
                header_cells
            )
        )

        max_rows = max(
            12,
            ui_height() - 10,
        )

        left_lines = []
        if editing_kind is None:
            for index, option in enumerate(
                filter_options
            ):
                prefix = (
                    "›"
                    if (
                        focus == 0
                        and index == filter_index
                    )
                    else " "
                )
                color = (
                    CYAN + BOLD
                    if (
                        focus == 0
                        and index == filter_index
                    )
                    else ""
                )
                left_lines.append(
                    (
                        fit(
                            f"{prefix} "
                            f"{option['label']}",
                            left,
                        ),
                        color,
                    )
                )
                left_lines.append(
                    (
                        fit(
                            "    "
                            + str(
                                option.get(
                                    "detail"
                                )
                                or ""
                            ),
                            left,
                        ),
                        GRAY,
                    )
                )
        else:
            left_lines.append(
                (
                    fit(
                        "← 返回篩選條件",
                        left,
                    ),
                    GRAY,
                )
            )
            selected_filter = (
                filter_options[
                    filter_index
                ]["label"]
            )
            left_lines.append(
                (
                    fit(
                        f"{selected_filter} · 選項",
                        left,
                    ),
                    CYAN + BOLD,
                )
            )
            choice_rows = max(
                4,
                (max_rows - 2) // 2,
            )
            choice_start = max(
                0,
                min(
                    choice_index
                    - choice_rows // 2,
                    len(choices)
                    - choice_rows,
                ),
            )
            for index in range(
                choice_start,
                min(
                    len(choices),
                    choice_start + choice_rows,
                ),
            ):
                choice = choices[index]
                prefix = (
                    "›"
                    if index == choice_index
                    else " "
                )
                color = (
                    CYAN + BOLD
                    if index == choice_index
                    else ""
                )
                left_lines.append(
                    (
                        fit(
                            f"{prefix} "
                            f"{choice['label']}",
                            left,
                        ),
                        color,
                    )
                )
                if choice.get("detail"):
                    left_lines.append(
                        (
                            fit(
                                "    "
                                + str(
                                    choice["detail"]
                                ),
                                left,
                            ),
                            GRAY,
                        )
                    )

        visible = max(
            5,
            min(
                15,
                max_rows // 2,
            ),
        )
        start_index = max(
            0,
            min(
                result_index
                - visible // 2,
                len(current) - visible,
            ),
        )

        middle_lines = []
        for index in range(
            start_index,
            min(
                len(current),
                start_index + visible,
            ),
        ):
            item = current[index]
            prefix = (
                "›"
                if (
                    focus == 1
                    and index == result_index
                )
                else " "
            )
            color = (
                CYAN + BOLD
                if (
                    focus == 1
                    and index == result_index
                )
                else ""
            )
            middle_lines.append(
                (
                    fit(
                        f"{prefix} "
                        f"{item.external_id} · "
                        f"{item.title}",
                        middle,
                    ),
                    color,
                )
            )
            middle_lines.append(
                (
                    fit(
                        "    "
                        + _problem_library_safe_detail(
                            item,
                            mode,
                        ),
                        middle,
                    ),
                    GRAY,
                )
            )

        if not current:
            middle_lines = [
                (
                    "沒有符合條件的題目",
                    YELLOW,
                )
            ]

        if current:
            selected_item = current[
                result_index
            ]
            inspector = (
                _problem_library_inspector_lines(
                    selected_item,
                    mode=mode,
                )
            )
        else:
            selected_item = None
            inspector = [
                f"{YELLOW}"
                "目前沒有題目"
                f"{RESET}",
                "",
                "調整左側篩選條件",
                "或按 X 清除搜尋。",
            ]

        if focus == 2:
            inspector = [
                f"{CYAN}{BOLD}"
                "› 題目側欄"
                f"{RESET}",
                *inspector,
            ]

        inspector_lines = [
            (
                fit(
                    line,
                    right,
                ),
                "",
            )
            for line in inspector
        ]

        rows = max(
            len(left_lines),
            len(middle_lines),
            len(inspector_lines),
        )
        for row in range(
            min(rows, max_rows)
        ):
            cells = []
            for lines, pane_width in (
                (left_lines, left),
                (middle_lines, middle),
                (inspector_lines, right),
            ):
                if row < len(lines):
                    value, color = (
                        lines[row]
                    )
                else:
                    value, color = (
                        "",
                        "",
                    )
                cells.append(
                    f"{color}"
                    f"{pad_display(value, pane_width)}"
                    f"{RESET if color else ''}"
                )
            print(
                (" " * gap).join(
                    cells
                )
            )

        print()
        rule()

        if focus == 0:
            if editing_kind is None:
                action = "Enter 選擇條件"
            else:
                action = "Enter 套用 · Esc 返回條件"
        elif focus == 1:
            action = "Enter 開啟 OJ"
        else:
            action = "Enter 開啟 OJ · D 詳細資料"

        print(
            f"{GRAY}"
            "Tab / Shift+Tab 切換區域"
            f" · ↑↓ 選擇 · {action}"
            " · / 搜尋 · M 切換模式 · Esc 返回"
            f"{RESET}"
        )

        key = read_key()

        if key in {"m", "M"}:
            _problem_library_save_filters(
                mode,
                filters,
            )
            _problem_library_save_query(
                mode,
                query,
            )
            UI_STATE[
                "library_focus"
            ] = focus
            return MODE_TOGGLE

        if key == "TAB":
            focus = (
                focus + 1
            ) % 3
            UI_STATE[
                "library_focus"
            ] = focus
            continue

        if key == "BACKTAB":
            focus = (
                focus - 1
            ) % 3
            UI_STATE[
                "library_focus"
            ] = focus
            continue

        if key == "UP":
            if focus == 0:
                if editing_kind is None:
                    filter_index = (
                        filter_index - 1
                    ) % len(filter_options)
                elif choices:
                    choice_index = (
                        choice_index - 1
                    ) % len(choices)
            elif focus == 1 and current:
                result_index = (
                    result_index - 1
                ) % len(current)
                UI_STATE[
                    "library_result_index"
                ] = result_index
            continue

        if key == "DOWN":
            if focus == 0:
                if editing_kind is None:
                    filter_index = (
                        filter_index + 1
                    ) % len(filter_options)
                elif choices:
                    choice_index = (
                        choice_index + 1
                    ) % len(choices)
            elif focus == 1 and current:
                result_index = (
                    result_index + 1
                ) % len(current)
                UI_STATE[
                    "library_result_index"
                ] = result_index
            continue

        if key == "/" :
            raw = prompt_text(
                (
                    "題號／題名"
                    if mode == "exam"
                    else "題號／題名／Skill"
                ),
                default=query,
            )
            if raw is not None:
                query = raw.strip()
                preset_ids = None
                preset_note = ""
                _problem_library_save_query(
                    mode,
                    query,
                )
                result_index = 0
                UI_STATE[
                    "library_result_index"
                ] = 0
            continue

        if key in {"x", "X"}:
            query = ""
            preset_ids = None
            preset_note = ""
            _problem_library_save_query(
                mode,
                "",
            )
            result_index = 0
            UI_STATE[
                "library_result_index"
            ] = 0
            continue

        if key == "ENTER":
            if focus == 0:
                if editing_kind is None:
                    option = (
                        filter_options[
                            filter_index
                        ]
                    )
                    kind = option["kind"]

                    if kind == "recommend":
                        filters = (
                            _problem_library_empty_filters()
                        )
                        recommendation = (
                            _problem_library_apply_preset(
                                mode,
                                filters,
                            )
                        )
                        preset_note, preset_ids = (
                            recommendation
                        )
                        query = ""
                        _problem_library_save_filters(
                            mode,
                            filters,
                        )
                        _problem_library_save_query(
                            mode,
                            "",
                        )
                        result_index = 0
                        UI_STATE[
                            "library_result_index"
                        ] = 0
                        continue

                    if kind == "safe":
                        preset_note = (
                            _problem_library_apply_preset(
                                mode,
                                filters,
                            )
                        )
                        preset_ids = None
                        query = ""
                        _problem_library_save_query(
                            mode,
                            "",
                        )
                        _problem_library_save_filters(
                            mode,
                            filters,
                        )
                        result_index = 0
                        continue

                    if kind == "clear":
                        filters = (
                            _problem_library_empty_filters()
                        )
                        preset_ids = None
                        preset_note = ""
                        query = ""
                        skill_unit = None
                        _problem_library_save_filters(
                            mode,
                            filters,
                        )
                        _problem_library_save_query(
                            mode,
                            "",
                        )
                        result_index = 0
                        continue

                    editing_kind = kind
                    choice_index = 0
                    skill_unit = None
                    continue

                if choices:
                    choice = choices[
                        choice_index
                    ]
                    action = choice.get(
                        "action"
                    )

                    if action == "skill_unit":
                        skill_unit = (
                            choice["unit"]
                        )
                        choice_index = 0
                        continue

                    if action == "skill_back":
                        skill_unit = None
                        choice_index = 0
                        continue

                    skill_unit = (
                        _problem_library_apply_direct_choice(
                            filters,
                            choice,
                            skill_unit=skill_unit,
                        )
                    )
                    preset_ids = None
                    preset_note = ""
                    editing_kind = None
                    choice_index = 0
                    result_index = 0
                    _problem_library_save_filters(
                        mode,
                        filters,
                    )
                    UI_STATE[
                        "library_result_index"
                    ] = 0
                    continue

            elif (
                selected_item is not None
                and focus in {1, 2}
            ):
                if selected_item.canonical_url:
                    webbrowser.open(
                        selected_item.canonical_url
                    )
                continue

        if (
            key in {"o", "O"}
            and selected_item is not None
        ):
            if selected_item.canonical_url:
                webbrowser.open(
                    selected_item.canonical_url
                )
            continue

        if (
            key in {"d", "D"}
            and focus == 2
            and selected_item is not None
        ):
            _problem_library_item_detail(
                selected_item,
                mode=mode,
            )
            continue

        if key in {
            "ESC",
            "q",
            "Q",
        }:
            if (
                focus == 0
                and editing_kind is not None
            ):
                if (
                    editing_kind == "skill"
                    and skill_unit is not None
                ):
                    skill_unit = None
                    choice_index = 0
                    continue
                editing_kind = None
                choice_index = 0
                continue

            _problem_library_save_filters(
                mode,
                filters,
            )
            _problem_library_save_query(
                mode,
                query,
            )
            UI_STATE[
                "library_focus"
            ] = focus
            return None


def _problem_library_filter_view(
    *,
    mode: str,
):
    filters = {
        "skill_uids": (),
        "skill_label": None,
        "difficulty": None,
        "source": None,
        "attempted": None,
        "role": None,
        "require_l2": None,
    }
    all_items = (
        _problem_library_items()
    )
    if ui_width() >= 86:
        return _problem_library_filter_browser(
            filters,
            all_items,
            mode=mode,
        )


    while True:
        current = (
            _problem_library_filter_items(
                all_items,
                filters,
                limit=10000,
            )
        )
        choice = (
            _problem_library_filter_choice(
                filters,
                current,
                mode=mode,
            )
        )
        if choice is None:
            return

        if choice == "results":
            _problem_library_results_view(
                current,
                title="題目庫 · 分類結果",
                context=(
                    _problem_library_filter_summary(
                        filters
                    )
                ),
                mode=mode,
            )
        elif choice == "skill":
            _problem_library_choose_skill(
                filters,
                all_items,
            )
        elif choice == "difficulty":
            _problem_library_choose_difficulty(
                filters,
                all_items,
            )
        elif choice == "source":
            _problem_library_choose_source(
                filters,
                all_items,
            )
        elif choice == "status":
            _problem_library_choose_status(
                filters,
            )
        elif choice == "role":
            _problem_library_choose_role(
                filters,
                all_items,
            )
        elif choice == "teaching":
            _problem_library_choose_teaching(
                filters,
            )
        elif choice == "clear":
            filters.update(
                {
                    "skill_uids": (),
                    "skill_label": None,
                    "difficulty": None,
                    "source": None,
                    "attempted": None,
                    "role": None,
                    "require_l2": None,
                }
            )


def _problem_library_text_search(
    *,
    mode: str,
):
    clear()
    heading("題目庫 · 題號／題名")
    print()
    print(
        f"{GRAY}"
        "只輸入一般關鍵字；不需要記 filter 語法。"
        f"{RESET}"
    )
    print()

    query = prompt_text(
        "題號或題名"
    )
    if query is None:
        return

    folded = str(
        query or ""
    ).strip().casefold()
    all_items = (
        _problem_library_items()
    )

    if mode == "exam":
        items = [
            item
            for item in all_items
            if (
                not folded
                or folded
                in (
                    f"{item.external_id} "
                    f"{item.title}"
                ).casefold()
            )
        ][:100]
    else:
        items = [
            item
            for item in all_items
            if (
                not folded
                or folded
                in " ".join(
                    [
                        item.external_id,
                        item.title,
                        item.source,
                        item.difficulty or "",
                        item.role or "",
                        item.primary_skill or "",
                        *item.supporting_skills,
                    ]
                ).casefold()
            )
        ][:100]

    _problem_library_results_view(
        items,
        title="題目庫 · 搜尋結果",
        context=(
            f"關鍵字：{query}"
            if query
            else "全部題目"
        ),
        mode=mode,
    )


def problem_library_view() -> None:
    while True:
        mode = selection_mode()

        if ui_width() >= 86:
            result = (
                _problem_library_workbench(
                    mode=mode,
                )
            )
            if result is MODE_TOGGLE:
                try:
                    toggle_selection_mode()
                except (
                    OSError,
                    ValueError,
                ) as exc:
                    clear()
                    heading("題目庫")
                    print()
                    print(
                        f"{RED}"
                        f"✕ 無法切換選題模式：{exc}"
                        f"{RESET}"
                    )
                    pause()
                continue
            return

        if mode == "practice":
            options = [
                {
                    "label": "推薦給我",
                    "detail": "依目前 Today 路徑找尚未做題；分類可見，適合 deliberate practice",
                    "enabled": True,
                    "section": "快速開始",
                    "action": "查看",
                    "kind": "recommend",
                },
                {
                    "label": "分類找題",
                    "detail": "Unit / Skill / 難度 / 來源 / 狀態 / 用途 / 教學資料",
                    "enabled": True,
                    "section": "瀏覽",
                    "action": "設定",
                    "kind": "filter",
                },
                {
                    "label": "題號／題名",
                    "detail": "已知道題目時使用",
                    "enabled": True,
                    "section": "瀏覽",
                    "action": "搜尋",
                    "kind": "search",
                },
                {
                    "label": "全部題目",
                    "detail": "完整練習題庫",
                    "enabled": True,
                    "section": "瀏覽",
                    "action": "查看",
                    "kind": "all",
                },
            ]
        else:
            options = [
                {
                    "label": "安全選題",
                    "detail": "優先未做題；不顯示 Skill、難度、用途或教學資料",
                    "enabled": True,
                    "section": "快速開始",
                    "action": "查看",
                    "kind": "safe",
                },
                {
                    "label": "安全篩選",
                    "detail": "只允許來源與作答狀態；分類資訊保持隱藏",
                    "enabled": True,
                    "section": "瀏覽",
                    "action": "設定",
                    "kind": "filter",
                },
                {
                    "label": "題號／題名",
                    "detail": "只用中性題目資訊搜尋",
                    "enabled": True,
                    "section": "瀏覽",
                    "action": "搜尋",
                    "kind": "search",
                },
                {
                    "label": "全部題目",
                    "detail": "以 strict spoiler view 瀏覽",
                    "enabled": True,
                    "section": "瀏覽",
                    "action": "查看",
                    "kind": "all",
                },
            ]

        selected = choose_grid(
            (
                "題目庫 · "
                f"{selection_mode_label(mode)}選題"
            ),
            options,
            back_text="返回控制中心",
            mode_toggle=True,
        )

        if selected is MODE_TOGGLE:
            try:
                toggle_selection_mode()
            except (
                OSError,
                ValueError,
            ) as exc:
                clear()
                heading("題目庫")
                print()
                print(
                    f"{RED}✕ 無法切換選題模式：{exc}{RESET}"
                )
                pause()
            continue

        if selected is None:
            return

        kind = options[selected]["kind"]

        if kind == "recommend":
            items, reason = (
                _recommended_problem_items(
                    limit=30,
                )
            )
            _problem_library_results_view(
                items,
                title="題目庫 · 推薦",
                context=reason,
                mode=mode,
            )
        elif kind == "safe":
            _problem_library_results_view(
                _exam_safe_problem_items(
                    limit=30,
                ),
                title="題目庫 · 安全選題",
                context="strict spoiler",
                mode="exam",
            )
        elif kind == "filter":
            _problem_library_filter_view(
                mode=mode,
            )
        elif kind == "search":
            _problem_library_text_search(
                mode=mode,
            )
        elif kind == "all":
            _problem_library_results_view(
                _problem_library_items(),
                title="題目庫 · 全部",
                mode=mode,
            )


# ============================================================
# Exam Runtime
# ============================================================

def _exam_duration_menu(
    current: int = 60,
) -> int | None:
    options = [
        {
            "label": f"{minutes} 分",
            "detail": (
                "常用"
                if minutes == current
                else ""
            ),
            "enabled": True,
            "action": "套用",
        }
        for minutes in EXAM_DURATION_CHOICES
    ]
    selected_index = min(
        range(
            len(EXAM_DURATION_CHOICES)
        ),
        key=lambda index: abs(
            EXAM_DURATION_CHOICES[index]
            - current
        ),
    )
    selected = choose_grid(
        "模擬考 · 時間",
        options,
        selected_index=selected_index,
        enter_text="套用",
        back_text="返回",
        wide_columns=5,
        compact_columns=2,
    )
    if selected is None:
        return None
    return EXAM_DURATION_CHOICES[
        selected
    ]


def _exam_question_count_menu() -> int | None:
    counts = (1, 2, 3, 4)
    selected = choose_grid(
        "模擬考 · 題數",
        [
            {
                "label": f"{count} 題",
                "detail": (
                    "完整 mixed set"
                    if count == 4
                    else "短時限練習"
                ),
                "enabled": True,
                "action": "選擇",
            }
            for count in counts
        ],
        selected_index=1,
        enter_text="選擇",
        back_text="返回",
        wide_columns=4,
        compact_columns=2,
    )
    if selected is None:
        return None
    return counts[selected]


def _quick_exam_problem_ids(
    count: int,
) -> list[str]:
    candidates = list(
        _exam_safe_problem_items(
            limit=200,
        )
    )
    preferred = [
        item
        for item in candidates
        if item.role
        in {
            "Core Independent",
            "Transfer Challenge",
            "Mock",
        }
    ]
    if len(preferred) < count:
        preferred = candidates

    selected = []
    used_skills = set()

    # First pass: maximize Skill diversity without revealing it to learner.
    for item in preferred:
        skill = item.primary_skill or ""
        if (
            skill
            and skill in used_skills
        ):
            continue
        selected.append(item)
        if skill:
            used_skills.add(skill)
        if len(selected) >= count:
            break

    if len(selected) < count:
        selected_ids = {
            item.external_id
            for item in selected
        }
        for item in preferred:
            if item.external_id in selected_ids:
                continue
            selected.append(item)
            if len(selected) >= count:
                break

    return [
        item.external_id
        for item in selected[:count]
    ]


def _exam_library_pick_ids() -> list[str] | None:
    candidates = _exam_safe_problem_items(
        limit=40,
    )
    chosen: list[str] = []

    while True:
        options = [
            {
                "label": (
                    f"完成選題 · {len(chosen)} 題"
                ),
                "detail": "最多 4 題",
                "enabled": bool(chosen),
                "action": "完成",
                "kind": "done",
            }
        ]

        for item in candidates:
            picked = (
                item.external_id in chosen
            )
            options.append(
                {
                    "label": (
                        f"{'✓ ' if picked else ''}"
                        f"{item.external_id} · {item.title}"
                    ),
                    "detail": (
                        _problem_library_safe_detail(
                            item,
                            "exam",
                        )
                    ),
                    "enabled": (
                        picked
                        or len(chosen) < 4
                    ),
                    "action": (
                        "取消"
                        if picked
                        else "加入"
                    ),
                    "kind": "problem",
                    "problem_id": item.external_id,
                }
            )

        selected = choose_menu(
            "模擬考 · 題庫選題",
            options,
            footer_numbers=False,
            back_text="返回",
            enter_text="選擇",
        )
        if selected is None:
            return None

        option = options[selected]
        if option["kind"] == "done":
            return list(chosen)

        pid = option["problem_id"]
        if pid in chosen:
            chosen.remove(pid)
        else:
            chosen.append(pid)


def _exam_custom_problem_ids() -> list[str] | None:
    clear()
    heading("模擬考 · 自訂題組")
    print()
    print(
        f"{GRAY}"
        "只有指定特定題組時才需要手動輸入題號。"
        f"{RESET}"
    )
    print()
    raw = prompt_text(
        "題號（空白或逗號分隔）",
        required=True,
    )
    if raw is None:
        return None
    return [
        token.strip().lower()
        for token in re.split(
            r"[\s,]+",
            raw,
        )
        if token.strip()
    ]


def _exam_start_ui() -> None:
    options = [
        {
            "label": "快速組題",
            "detail": "系統從未做／獨立題池建立 mixed set；不顯示分類",
            "enabled": True,
            "section": "建議",
            "action": "開始設定",
            "kind": "quick",
        },
        {
            "label": "從題庫選題",
            "detail": "strict spoiler；最多選 4 題",
            "enabled": True,
            "section": "選題",
            "action": "選擇",
            "kind": "library",
        },
        {
            "label": "輸入題號",
            "detail": "只在已有指定題組時使用",
            "enabled": True,
            "section": "選題",
            "action": "輸入",
            "kind": "custom",
        },
    ]

    selected = choose_grid(
        "模擬考 · 建立題組",
        options,
        back_text="返回控制中心",
    )
    if selected is None:
        return

    kind = options[selected]["kind"]
    problem_ids = None

    if kind == "quick":
        count = (
            _exam_question_count_menu()
        )
        if count is None:
            return
        problem_ids = (
            _quick_exam_problem_ids(
                count
            )
        )
        if len(problem_ids) < count:
            clear()
            heading("模擬考")
            print()
            print(
                f"{YELLOW}"
                "目前沒有足夠的安全題目建立這個題組。"
                f"{RESET}"
            )
            pause()
            return

    elif kind == "library":
        problem_ids = (
            _exam_library_pick_ids()
        )
        if problem_ids is None:
            return

    else:
        problem_ids = (
            _exam_custom_problem_ids()
        )
        if problem_ids is None:
            return

    minutes = _exam_duration_menu(
        60
    )
    if minutes is None:
        return

    try:
        EXAM.start(
            problem_ids,
            duration_minutes=minutes,
        )
    except (
        ValueError,
        ExamRuntimeError,
    ) as exc:
        clear()
        heading("模擬考")
        print()
        print(
            f"{RED}✕ {exc}{RESET}"
        )
        pause()



def _exam_submit_ui(session) -> None:
    pid = session.get("selected_problem_id")
    if not pid:
        print(f"{YELLOW}請先選擇目前作答題目。{RESET}")
        pause()
        return

    values = ["AC", "WA", "TLE", "RE", "CE", "MLE", "N/A"]
    selected = choose_menu(
        "記錄提交",
        [
            {
                "label": value,
                "detail": (
                    "外部 OJ 結果"
                    if value != "N/A"
                    else "只記錄提交時間，結果未知"
                ),
                "enabled": True,
            }
            for value in values
        ],
        footer_numbers=True,
        back_text="返回模擬考",
    )
    if selected is None:
        return

    try:
        EXAM.mark_submit(
            pid,
            result=values[selected],
        )
    except ExamRuntimeError as exc:
        print(f"{RED}✕ {exc}{RESET}")
        pause()


def _exam_end_ui() -> None:
    reasons = list(POSTMORTEM_REASONS.items())
    selected = choose_menu(
        "模擬考後檢討 · 主要失分原因",
        [
            {
                "label": label,
                "detail": (
                    "只選最主要原因；不需要填長表單"
                    if key != "NONE"
                    else "本次沒有明顯執行失分"
                ),
                "enabled": True,
            }
            for key, label in reasons
        ],
        footer_numbers=True,
        back_text="繼續考試",
    )
    if selected is None:
        return

    key, _ = reasons[selected]
    try:
        session = EXAM.end(
            postmortem_reason=key,
        )
    except ExamRuntimeError as exc:
        print(f"{RED}✕ {exc}{RESET}")
        pause()
        return

    summary = EXAM.summary(session)
    clear()
    heading("模擬考完成")
    print()
    print(f"總時間    {summary['elapsed_minutes']} min")
    print(
        "掃題      "
        f"{summary['scan_minutes'] if summary['scan_minutes'] is not None else '—'} min"
    )
    print(
        "首次編譯  "
        f"{summary['first_compile_minutes'] if summary['first_compile_minutes'] is not None else '—'} min"
    )
    print(f"編譯      {summary['compile_count']} 次")
    print(f"提交      {summary['submit_count']} 次")
    print(f"切題      {summary['switch_count']} 次")
    print(
        "主要失分  "
        f"{POSTMORTEM_REASONS[summary['postmortem_reason']]}"
    )
    print()
    print(
        f"{GRAY}"
        "Exam telemetry 只分析考試流程；真正能力 Evidence 仍由正式作答紀錄產生。"
        f"{RESET}"
    )
    pause()


def exam_center() -> None:
    while True:
        try:
            session = EXAM.active()
        except ExamRuntimeError as exc:
            clear()
            heading("模擬考")
            print()
            print(f"{RED}✕ {exc}{RESET}")
            pause()
            return

        if session is None:
            _exam_start_ui()
            try:
                if EXAM.active() is None:
                    return
            except ExamRuntimeError:
                return
            continue

        summary = EXAM.summary(session)
        elapsed = summary["elapsed_minutes"]
        remaining = max(
            0,
            session["duration_minutes"] - elapsed,
        )

        options = []
        for pid in session["problem_ids"]:
            selected_now = (
                pid == session["selected_problem_id"]
            )
            options.append(
                {
                    "label": (
                        f"{'目前 · ' if selected_now else ''}{pid}"
                    ),
                    "detail": (
                        "保持作答"
                        if selected_now
                        else "選擇 / 切換到這題"
                    ),
                    "enabled": True,
                    "kind": "select",
                    "problem_id": pid,
                }
            )

        options.extend(
            [
                {
                    "label": "記錄提交",
                    "detail": (
                        "只需選外部 OJ 結果"
                        if session["selected_problem_id"]
                        else "請先選題"
                    ),
                    "enabled": bool(session["selected_problem_id"]),
                    "kind": "submit",
                },
                {
                    "label": "結束並檢討",
                    "detail": "只問一個主要失分原因",
                    "enabled": True,
                    "kind": "end",
                },
            ]
        )

        clear()
        heading("考試模式")
        print()
        print(
            f"時間      {elapsed}/{session['duration_minutes']} min"
            f" · 剩餘約 {remaining} min"
        )
        print(
            f"目前題目  {session['selected_problem_id'] or '掃題中'}"
        )
        print(
            f"編譯 {summary['compile_count']} · "
            f"提交 {summary['submit_count']} · "
            f"切題 {summary['switch_count']}"
        )
        print()
        print(
            f"{GRAY}"
            "Ctrl+Shift+B 編譯會自動留下考試時間點。"
            f"{RESET}"
        )
        print()

        chosen = choose_menu(
            "模擬考 · 下一步",
            options,
            footer_numbers=True,
            back_text="返回控制中心（計時持續）",
        )
        if chosen is None:
            return

        option = options[chosen]
        if option["kind"] == "select":
            try:
                EXAM.select(option["problem_id"])
            except ExamRuntimeError as exc:
                print(f"{RED}✕ {exc}{RESET}")
                pause()
        elif option["kind"] == "submit":
            _exam_submit_ui(session)
        else:
            _exam_end_ui()


# ============================================================
# Main
# ============================================================

def closed_screen() -> None:
    clear()
    heading("控制中心已關閉")
    print()
    print(f"{CYAN}Ctrl+Alt+A{RESET}    重新開啟")
    print(f"{CYAN}Ctrl+Shift+B{RESET}  編譯並執行")
    print()


def record_action_state(
    problem,
) -> tuple[bool, bool, str, str]:
    """Return Finish/Review enablement for the current learner surface."""

    if not problem:
        return (
            False,
            False,
            "需先開啟 APCS 題目檔案",
            "需先開啟 APCS 題目檔案",
        )

    if problem.get("published_runtime"):
        runtime_action = problem.get(
            "runtime_action"
        )
        track = (
            problem.get("runtime_track")
            or "Implementation"
        )

        if runtime_action == "review":
            return (
                False,
                True,
                "此 runtime scratch 是 Review",
                f"記錄 {track} Review Evidence",
            )

        if runtime_action == "finish":
            return (
                True,
                False,
                f"記錄 {track} New Learning Evidence",
                "此 runtime scratch 是 New Learning",
            )

    state = problem.get("state")
    solved = bool(
        state
        and state.solved_on
    )

    return (
        not solved,
        solved,
        (
            "首次 AC 後記錄掌握程度"
            if not solved
            else "已標記 AC；後續請使用「複習題目」"
        ),
        (
            "重做後更新 Result、Recall 與 Evidence"
            if solved
            else "需先完成題目並取得 AC"
        ),
    )


def more_tools_center(
    problem,
    current_filename: str | None,
):
    while True:
        changes = git_changes()
        options = [
            {
                "label": "題目資料",
                "detail": (
                    "新增題目、編輯 metadata、建立 solution"
                ),
                "enabled": True,
                "section": "維護",
                "kind": "catalog",
                "action": "開啟",
            },
            {
                "label": "檢查與提交",
                "detail": (
                    f"{len(changes)} 個 Git 變更待處理"
                    if changes
                    else "目前 Git 工作區乾淨"
                ),
                "enabled": True,
                "section": "維護",
                "kind": "git",
                "action": "開啟",
            },
        ]

        selected = choose_grid(
            "更多工具",
            options,
            problem=problem,
            back_text="返回控制中心",
            wide_columns=2,
            compact_columns=2,
        )
        if selected is None:
            return current_filename

        option = options[selected]
        if option["kind"] == "catalog":
            current_filename = (
                catalog_center(
                    problem,
                    current_filename,
                )
            )
            problem = current_problem(
                current_filename
            )
        else:
            git_center()


def main() -> int:
    filename = (
        sys.argv[1]
        if len(sys.argv) >= 2
        else None
    )

    while True:
        problem = current_problem(
            filename
        )

        (
            finish_enabled,
            review_enabled,
            finish_detail,
            review_detail,
        ) = record_action_state(
            problem
        )

        options = [
            {
                "label": "今日學習",
                "detail": "依目前 Evidence、記憶與容量安排下一個高價值活動",
                "enabled": True,
                "section": "主要",
                "kind": "today",
                "action": "開啟",
            },
            {
                "label": "題目庫",
                "detail": (
                    "練習模式可按主題找題；考試模式會隱藏方法分類"
                ),
                "enabled": True,
                "section": "主要",
                "kind": "library",
                "action": "開啟",
            },
            {
                "label": "模擬考",
                "detail": "計時 mixed practice；選題與執行時間點由 Exam Runtime 管理",
                "enabled": True,
                "section": "主要",
                "kind": "exam",
                "action": "開啟",
            },
        ]

        if problem is not None:
            if finish_enabled:
                options.append(
                    {
                        "label": "完成題目",
                        "detail": finish_detail,
                        "enabled": True,
                        "section": "目前題目",
                        "kind": "finish",
                        "action": "記錄",
                    }
                )
            elif review_enabled:
                options.append(
                    {
                        "label": (
                            "完成複習"
                            if (
                                problem.get(
                                    "published_runtime"
                                )
                                and problem.get(
                                    "runtime_action"
                                )
                                == "review"
                            )
                            else "複習題目"
                        ),
                        "detail": review_detail,
                        "enabled": True,
                        "section": "目前題目",
                        "kind": "review",
                        "action": "記錄",
                    }
                )

            note = (
                ROOT
                / "notes"
                / f"{problem['id']}.md"
            )
            options.append(
                {
                    "label": "題目筆記",
                    "detail": (
                        "已建立；直接開啟"
                        if note.exists()
                        else "尚未建立；選取後建立並開啟"
                    ),
                    "enabled": True,
                    "section": "目前題目",
                    "kind": "note",
                    "action": "開啟",
                }
            )

        options.extend(
            [
                {
                    "label": "學習狀態",
                    "detail": "Evidence、記憶、容量與同步摘要",
                    "enabled": True,
                    "section": "其他",
                    "kind": "status",
                    "action": "查看",
                },
                {
                    "label": "更多工具",
                    "detail": "題目資料與 Git 維護；不屬於日常學習主流程",
                    "enabled": True,
                    "section": "其他",
                    "kind": "tools",
                    "action": "開啟",
                },
            ]
        )

        selected = choose_grid(
            "控制中心",
            options,
            problem=problem,
            main=True,
            mode_toggle=True,
            back_text="關閉",
        )

        if selected is MODE_TOGGLE:
            try:
                toggle_selection_mode()
            except (
                OSError,
                ValueError,
            ) as exc:
                clear()
                heading("控制中心")
                print()
                print(
                    f"{RED}✕ 無法切換選題模式：{exc}{RESET}"
                )
                pause()
            continue

        if selected is None:
            closed_screen()
            return 0

        option = options[selected]
        kind = option["kind"]

        if kind == "today":
            filename = today_view(
                filename
            )

        elif kind == "library":
            problem_library_view()

        elif kind == "exam":
            exam_center()

        elif kind == "finish":
            record_problem(
                "finish",
                problem,
            )

        elif kind == "review":
            record_problem(
                "review",
                problem,
            )

        elif kind == "note":
            open_note(problem)

        elif kind == "status":
            learning_status_view()

        elif kind == "tools":
            filename = more_tools_center(
                problem,
                filename,
            )


if __name__ == "__main__":
    raise SystemExit(main())
