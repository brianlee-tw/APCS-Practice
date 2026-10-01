#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import datetime as dt
import io
import os
import re
import select
import shutil
import subprocess
import sys
import termios
import tty
import unicodedata
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
    from .learning_route import (
        select_new_learning_plan,
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
    from learning_route import (
        select_new_learning_plan,
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
    RUNTIME_DIR / "skill_memory.json"
)

DEFAULT_SESSION_MINUTES = 60
DEFAULT_IMPLEMENTATION_REVIEW_MINUTES = 12
DEFAULT_READING_REVIEW_MINUTES = 6

ID_RE = re.compile(r"^([A-Za-z]\d+|\d+)(?:_|$)")

RESET = "\033[0m"
BOLD = "\033[1m"

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
WHITE = "\033[97m"
GRAY = "\033[90m"


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


def ui_width() -> int:
    columns = shutil.get_terminal_size((38, 24)).columns
    return max(28, min(columns - 2, 42))


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


def current_problem(filename: str | None):
    if not filename:
        return None

    path = Path(filename)
    candidate = (
        path
        if path.is_absolute()
        else ROOT / path
    )
    resolved = candidate.resolve()

    placement_match = re.search(
        r"__([A-Za-z0-9_.:-]+)$",
        path.stem,
    )
    placement_uid = (
        placement_match.group(1)
        if placement_match
        else None
    )

    # v2.3 runtime scratch identity is the Published Placement, not the
    # legacy local-catalog filename convention.  This allows CF / CSES /
    # LeetCode / APCS canonical Problem IDs to participate in B4 without
    # inventing a second local Problem identity.
    if placement_uid:
        try:
            placement = (
                CURRICULUM
                .placement_by_uid(
                    placement_uid
                )
            )
        except RuntimeCurriculumError:
            placement = None

        if placement is not None:
            return {
                "id": (
                    placement.problem_id
                    .strip()
                    .lower()
                ),
                "title": placement.title,
                "path": path,
                "state": None,
                "due": None,
                "placement_uid": (
                    placement_uid
                ),
                "pb_uid": placement.pb_uid,
                "published_runtime": True,
                "url": placement.url,
            }

    match = ID_RE.match(
        path.stem
    )

    if not match:
        return None

    pid = match.group(1).lower()

    for row in all_rows():
        if row[0] == pid:
            matched_path = next(
                (
                    solution.path
                    for solution in row[1]
                    if solution.path.resolve()
                    == resolved
                ),
                resolved,
            )

            return {
                "id": pid,
                "title": clean_title(
                    pid,
                    row[2].title,
                ),
                "path": matched_path,
                "state": row[3],
                "due": row[5],
                "placement_uid": (
                    placement_uid
                ),
                "published_runtime": False,
            }

    return {
        "id": pid,
        "title": clean_title(
            pid,
            path.stem,
        ),
        "path": path,
        "state": None,
        "due": None,
        "placement_uid": (
            placement_uid
        ),
        "published_runtime": False,
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


def session_capacity_minutes() -> int:
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
        else session_capacity_minutes()
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

    lines = [
        "// APCS B4 new-learning scratch",
        f"// Skill: {placement.primary_skill}",
        (
            f"// Lesson: "
            f"{placement.lesson_uid or '—'}"
        ),
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
        "// 先依 Lesson 建立 model，再自行完成本題。",
        "// Core / Transfer pre-attempt 不查看舊解答或關鍵觀察。",
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


def choose_menu(
    title: str,
    options,
    *,
    problem=None,
    main=False,
    footer_numbers=True,
    back_text: str | None = None,
):
    selected = first_enabled(options)

    while True:
        clear()
        heading(title)
        print()

        if problem is not None:
            print_problem_context(problem)
            print()

        if main:
            snapshot = (
                adaptive_today_snapshot()
            )
            plan = snapshot["plan"]

            print(f"{GRAY}今日學習{RESET}")
            print(
                f"容量 {snapshot['capacity_minutes']} min"
                f" · Review budget {plan.budget_minutes} min"
            )

            if plan.selected:
                print(
                    f"{YELLOW}"
                    f"Adaptive review {len(plan.selected)} 項"
                    f" · {plan.selected_minutes} min"
                    f"{RESET}"
                )
            else:
                print(
                    f"{GREEN}"
                    "✓ 今天沒有已選定的 adaptive review"
                    f"{RESET}"
                )

            if plan.deferred:
                print(
                    f"{GRAY}"
                    f"安全延後 {len(plan.deferred)} 項"
                    "（不是欠題）"
                    f"{RESET}"
                )

            protected = max(
                0,
                snapshot["capacity_minutes"]
                - plan.budget_minutes,
            )
            print(
                f"{GRAY}"
                f"新學習保留 ≥ {protected} min"
                f"{RESET}"
            )

            if snapshot[
                "curriculum_blocker"
            ]:
                print(
                    f"{YELLOW}"
                    "新學習 · BLOCKED"
                    f"{RESET}"
                )
                print(
                    f"{GRAY}"
                    f"{fit(snapshot['curriculum_blocker'], ui_width() - 2)}"
                    f"{RESET}"
                )
            elif snapshot[
                "new_learning"
            ] is not None:
                route = snapshot[
                    "new_learning"
                ]

                if route.skill is not None:
                    print(
                        f"{CYAN}"
                        "新學習 · "
                        f"{route.skill.uid}"
                        f"{RESET}"
                    )
                    print(
                        f"{GRAY}"
                        f"{fit(route.why_now, ui_width() - 2)}"
                        f"{RESET}"
                    )
                elif route.blocked_skill is not None:
                    print(
                        f"{YELLOW}"
                        "新學習 · BLOCKED · "
                        f"{route.blocked_skill.uid}"
                        f"{RESET}"
                    )
                    print(
                        f"{GRAY}"
                        f"{fit(route.why_now, ui_width() - 2)}"
                        f"{RESET}"
                    )
                elif route.route_complete:
                    print(
                        f"{GREEN}"
                        "✓ Required route 已達 start threshold"
                        f"{RESET}"
                    )

            if snapshot["warning"]:
                print(
                    f"{YELLOW}"
                    f"⚠ {fit(snapshot['warning'], ui_width() - 2)}"
                    f"{RESET}"
                )

            print()

        rule()
        print()

        # Keep long menus usable in the narrow right-side terminal.
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

        for index in range(start, end):
            option = options[index]
            enabled = option.get("enabled", True)

            prefix = "›" if index == selected else " "
            number = index + 1
            label = fit(option["label"], ui_width() - 6)

            if not enabled:
                print(f"{GRAY}  {number}  {label}{RESET}")
            elif index == selected:
                print(
                    f"{CYAN}{BOLD}"
                    f"{prefix} {number}  {label}"
                    f"{RESET}"
                )
            else:
                print(f"  {number}  {label}")

            detail = option.get("detail", "")

            if detail:
                detail = fit(detail, ui_width() - 5)

                if enabled:
                    print(f"     {GRAY}{detail}{RESET}")
                else:
                    print(f"     {RED}{detail}{RESET}")

            print()

        if end < len(options):
            print(f"{GRAY}  ↓ 還有 {len(options) - end} 項{RESET}")
            print()

        rule()

        if main:
            print(f"{GRAY}↑↓ 選擇 · Enter 執行{RESET}")
            print(f"{GRAY}1–{len(options)} 直達 · Esc / Q 關閉{RESET}")
        else:
            print(f"{GRAY}↑↓ 選擇 · Enter 執行{RESET}")
            label = back_text or "返回控制中心"
            print(f"{GRAY}Esc / Q {label}{RESET}")

        key = read_key()

        if key == "UP":
            selected = move_enabled(options, selected, -1)

        elif key == "DOWN":
            selected = move_enabled(options, selected, 1)

        elif key == "ENTER":
            if options[selected].get("enabled", True):
                return selected

        elif key in {"ESC", "q", "Q"}:
            return None

        elif footer_numbers and key.isdigit():
            value = int(key)

            if 1 <= value <= len(options):
                index = value - 1

                if options[index].get("enabled", True):
                    return index


# ============================================================
# Recall
# ============================================================

def review_result_menu(problem) -> str | None:
    options = [
        ("AC", "通過", "答案正確，完整通過測試"),
        ("WA", "答案錯誤", "程式可執行，但答案不正確"),
        ("TLE", "執行逾時", "時間複雜度或實作速度不足"),
        ("RE", "執行錯誤", "執行期間發生錯誤"),
        ("MLE", "記憶體超限", "使用記憶體超過限制"),
        ("CE", "編譯失敗", "本次程式無法成功編譯"),
    ]

    selected = 0

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

            if index == selected:
                color = CYAN + BOLD
            else:
                color = ""

            print(
                f"{color}"
                f"{prefix} {index + 1}  "
                f"{result} · {label}"
                f"{RESET}"
            )

            print(
                f"     {GRAY}"
                f"{fit(detail, ui_width() - 5)}"
                f"{RESET}"
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
        print(f"{GRAY}1–6 直達 · Esc / Q 取消{RESET}")

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

    selected = 0

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

            if index == selected:
                color = CYAN + BOLD
            else:
                color = ""

            print(
                f"{color}"
                f"{prefix} {score}  {label}"
                f"{RESET}"
            )

            print(
                f"     {GRAY}"
                f"{fit(detail, ui_width() - 5)}"
                f"{RESET}"
            )
            print()

        rule()
        print(f"{GRAY}↑↓ 選擇 · Enter 確認{RESET}")

        if result == "AC":
            print(f"{GRAY}0–3 直達 · Esc / Q 取消{RESET}")
        else:
            print(f"{GRAY}0–2 直達 · Esc / Q 取消{RESET}")

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
) -> int | None | object:

    CANCEL = object()
    value = ""

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
            "Esc / Q 取消整次紀錄"
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
            return CANCEL

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


def assistance_menu(problem) -> int | None:
    options = [
        {
            "label": label,
            "detail": detail,
            "enabled": True,
        }
        for _, label, detail
        in ASSISTANCE_OPTIONS
    ]

    selected = choose_menu(
        "最高 Assistance",
        options,
        problem=problem,
        main=False,
        back_text="取消本次紀錄",
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

    selected = choose_menu(
        title,
        options,
        problem=problem,
        main=False,
        footer_numbers=False,
        back_text="取消本次紀錄",
    )

    if selected is None:
        return None

    return options[selected]["label"] == "是"


def independent_menu(
    problem,
    assistance: int,
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
    )


def novelty_menu(
    action: str,
    problem,
    *,
    placement=None,
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

    selected = choose_menu(
        "題目新鮮度",
        options,
        problem=problem,
        main=False,
        footer_numbers=False,
        back_text="取消本次紀錄",
    )

    if selected is None:
        return None

    return values[selected][0]


def timed_menu(problem) -> bool | None:
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
    finished_at: dt.datetime | None = None,
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

    if placement is not None:
        evidence.append(
            (
                placement.primary_skill,
                "Implementation",
                (
                    "PASS"
                    if result == "AC"
                    else "FAIL"
                ),
                (
                    f"{activity or 'Practice'}"
                    f" · {result}"
                ),
            )
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
        evidence=evidence,
    )


def evidence_context_menu(
    action: str,
    problem,
):
    placement, placement_warning = (
        placement_for_record(
            problem
        )
    )

    if placement_warning == "__CANCEL__":
        return None

    assistance = assistance_menu(
        problem
    )

    if assistance is None:
        return None

    independent = independent_menu(
        problem,
        assistance,
    )

    if independent is None:
        return None

    novelty = novelty_menu(
        action,
        problem,
        placement=placement,
    )

    if novelty is None:
        return None

    timed = timed_menu(
        problem
    )

    if timed is None:
        return None

    return {
        "placement": placement,
        "placement_warning": placement_warning,
        "assistance": assistance,
        "independent": independent,
        "novelty": novelty,
        "timed": timed,
    }


def record_problem(action: str, problem) -> None:
    title = (
        "完成題目"
        if action == "finish"
        else "複習題目"
    )

    result = "AC"

    if action == "review":
        result = review_result_menu(problem)

        if result is None:
            return

    score = recall_menu(
        title,
        problem,
        result=result,
    )

    if score is None:
        return

    minutes_result = minutes_input(
        title,
        problem,
        result=result,
        score=score,
    )

    # minutes_input 用 object sentinel 表示取消。
    # int 或 None 才是有效結果。
    if (
        minutes_result is not None
        and not isinstance(minutes_result, int)
    ):
        return

    minutes = minutes_result

    evidence_context = (
        evidence_context_menu(
            action,
            problem,
        )
    )

    if evidence_context is None:
        return

    complexity_solution = None
    finish_complexity = None

    if action == "finish":
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

        if complexity_solution is not None:
            clear()
            heading("完成題目 · Complexity")
            print()
            print_problem_context(problem)
            print()
            print(
                f"{YELLOW}"
                "此 solution 尚未記錄 Complexity。"
                f"{RESET}"
            )
            print(
                f"{GRAY}"
                "請先判斷演算法時間複雜度，例如 "
                "O(1)、O(N)、O(N log N)。"
                f"{RESET}"
            )
            print()

            finish_complexity = prompt_text(
                "Complexity（必填）",
                required=True,
            )

            if finish_complexity is None:
                return

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
            "Complexity  "
            f"{CYAN}{finish_complexity}{RESET}"
        )

    placement = evidence_context[
        "placement"
    ]

    assistance = evidence_context[
        "assistance"
    ]

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
            if evidence_context[
                "independent"
            ]
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
        print(
            f"{YELLOW}"
            f"⚠ {fit(placement_warning, ui_width() - 2)}"
            f"{RESET}"
        )

    print()
    rule()
    print()

    if not confirm("確認寫入這次學習紀錄？"):
        return

    print()
    print(f"{GRAY}正在更新學習紀錄…{RESET}")

    published_runtime = bool(
        problem.get(
            "published_runtime",
            False,
        )
    )

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
                f"✓ Complexity 已寫入 Catalog："
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
        print(f"{GRAY}↑↓ 選擇 · Enter 執行{RESET}")
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
    heading("新增 Solution")
    print()
    print(f"{WHITE}{problem_line(problem)}{RESET}")
    print()

    complexity = prompt_text("Complexity（可略過）")
    if complexity is None:
        return None

    if not confirm(
        f"為 {pid} 建立新的 {language} solution？"
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


def catalog_center(problem, current_filename: str | None):
    try:
        problems = core.CATALOG.load_problems()
    except CatalogError as exc:
        clear()
        heading("題目資料")
        print()
        print(f"{RED}✕ Catalog 無法讀取：{exc}{RESET}")
        pause()
        return current_filename

    known = bool(
        problem
        and problem["id"] in problems
    )

    options = [
        {
            "label": "新增題目",
            "detail": "建立 metadata 與第一份 solution",
            "enabled": True,
        },
        {
            "label": "編輯目前題目",
            "detail": (
                "修改 title / source / difficulty / tags / complexity"
                if known
                else "目前檔案不在 Catalog"
            ),
            "enabled": known,
        },
        {
            "label": "新增 Solution",
            "detail": (
                "為目前題目建立另一份 C++ / Python 解法"
                if known
                else "需先選擇 Catalog 題目"
            ),
            "enabled": known,
        },
    ]

    selected = choose_menu(
        "題目資料",
        options,
        problem=problem,
    )

    if selected is None:
        return current_filename

    if selected == 0:
        created = create_problem_ui()
        return created or current_filename

    if selected == 1:
        edit_problem_ui(problem)
        return current_filename

    created = add_solution_ui(problem)
    return created or current_filename
# ============================================================
# Today / Notes
# ============================================================

def today_view(current_filename: str | None):
    snapshot = adaptive_today_snapshot()
    plan = snapshot["plan"]

    clear()
    heading("今日學習")
    print()

    print(
        f"目標    {snapshot['target']}"
    )
    print(
        f"容量    {snapshot['capacity_minutes']} min"
    )
    print(
        f"Review  {plan.selected_minutes}/"
        f"{plan.budget_minutes} min"
    )

    protected = max(
        0,
        snapshot["capacity_minutes"]
        - plan.budget_minutes,
    )

    print(
        f"新學習  ≥ {protected} min 保留"
    )

    if plan.deferred:
        print(
            f"{GRAY}"
            f"Deferred {len(plan.deferred)} Skill"
            " · 不計為欠作業"
            f"{RESET}"
        )

    if snapshot["warning"]:
        print()
        print(
            f"{YELLOW}"
            "⚠ Adaptive memory reconciliation 有問題"
            f"{RESET}"
        )
        print(
            f"{GRAY}"
            f"{fit(snapshot['warning'], ui_width())}"
            f"{RESET}"
        )

    print()
    rule()
    print()

    if snapshot["memory_count"] == 0:
        print(
            f"{GREEN}"
            "✓ 尚無 adaptive Skill memory"
            f"{RESET}"
        )
        print()
        print(
            f"{GRAY}"
            "目前應把容量用在新學習與正式 Practice；"
            "完成有 Published Placement 的題目後，"
            "系統會開始建立 Skill × Track retention state。"
            f"{RESET}"
        )
        pause()
        return current_filename

    if snapshot["due_count"] == 0:
        print(
            f"{GREEN}"
            "✓ 今天沒有 Skill 到達 review threshold"
            f"{RESET}"
        )
        print()
        print(
            f"{GRAY}"
            "不需要為了維持 streak 額外刷舊題；"
            "直接進行新學習／Transfer。"
            f"{RESET}"
        )
        pause()
        return current_filename

    if not plan.selected:
        print(
            f"{GREEN}"
            "✓ 今日 review budget 不安排專門複習"
            f"{RESET}"
        )
        print()
        print(
            f"{GRAY}"
            f"目前有 {snapshot['due_count']} 個候選，"
            "但都超出本次 review 容量；"
            "已安全延後，不形成 backlog debt。"
            f"{RESET}"
        )
        pause()
        return current_filename

    options = []

    for candidate in plan.selected:
        label = skill_display_name(
            candidate.skill_uid
        )

        detail = (
            f"{candidate.track}"
            f" · R≈{candidate.retrievability:.0%}"
            f" · due {candidate.due_on:%m/%d}"
            f" · {candidate.estimated_minutes} min"
        )

        options.append(
            {
                "label": label,
                "detail": detail,
                "enabled": True,
                "candidate": candidate,
            }
        )

    selected = choose_menu(
        "今日學習 · Adaptive Review",
        options,
        main=False,
    )

    if selected is None:
        return current_filename

    candidate = options[
        selected
    ]["candidate"]

    placement = review_placement_for_skill(
        candidate.skill_uid,
        track=candidate.track,
    )

    clear()
    heading("開始 Adaptive Review")
    print()

    print(
        f"{WHITE}{BOLD}"
        f"{skill_display_name(candidate.skill_uid)}"
        f"{RESET}"
    )
    print(
        f"Track   {candidate.track}"
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
            "待 curriculum publish 後再選代表題。"
            f"{RESET}"
        )
        pause()
        return current_filename

    print(
        f"題目    {placement.problem_id} · "
        f"{fit(placement.title, max(10, ui_width() - 8))}"
    )
    print(
        f"Role    {placement.role}"
    )

    if placement.url:
        print(
            f"Judge   {placement.url}"
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
            "請依題面先完成 trace / reasoning，"
            "正式作答前不要執行程式驗證。"
            f"{RESET}"
        )
        pause()
        return current_filename

    try:
        path = create_review_scratch(
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

    result = subprocess.run(
        [
            "code",
            "--reuse-window",
            str(path),
        ],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    print()

    if result.returncode == 0:
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

    return str(path)

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


def create_commit() -> None:
    changes = git_changes()
    staged = staged_count(changes)

    clear()
    heading("建立 Commit")
    print()

    if staged == 0:
        print(f"{YELLOW}尚未有 staged changes。{RESET}")
        print("請先使用「加入暫存區」。")
        pause()
        return

    if not whitespace_ok():
        print(f"{RED}✕ Git whitespace 檢查未通過{RESET}")
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

    print(f"已暫存  {staged} 個變更")
    print()

    if stat:
        for line in stat.splitlines()[-5:]:
            print(fit(line, ui_width()))

    print()
    print(f"{GRAY}Commit message{RESET}")
    print(f"{GRAY}留空直接 Enter 可取消{RESET}")
    print()

    try:
        message = input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        return

    if not message:
        return

    clear()
    heading("確認 Commit")
    print()

    print(f"{GRAY}Message{RESET}")
    print(fit(message, ui_width()))
    print()

    if stat:
        for line in stat.splitlines()[-5:]:
            print(fit(line, ui_width()))

    if not confirm("建立這個 Commit？"):
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
        print(f"{RED}✕ Commit 失敗{RESET}")

        error = (
            result.stderr.strip()
            or result.stdout.strip()
        )

        if error:
            print()
            for line in error.splitlines()[-6:]:
                print(fit(line, ui_width()))

        pause()
        return

    sha = run_git(
        "rev-parse",
        "--short",
        "HEAD",
    ).stdout.strip()

    print(f"{GREEN}✓ Commit 已建立{RESET}")
    print(f"SHA  {sha}")
    print()

    if confirm("現在 Push 到 GitHub？"):
        push_commit(skip_confirm=True)


def git_center() -> None:
    selected = 0

    while True:
        validation_code, errors, warnings = validate_summary()
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
                "label": "查看變更",
                "detail": (
                    f"{len(changes)} 個變更 · "
                    f"{staged} 已暫存"
                ),
                "enabled": True,
            },
            {
                "label": "加入暫存區",
                "detail": (
                    f"{unstaged} 個未暫存變更"
                    if unstaged
                    else "目前沒有未暫存變更"
                ),
                "enabled": unstaged > 0,
            },
            {
                "label": "建立 Commit",
                "detail": (
                    f"{staged} 個 staged changes"
                    if staged
                    else "請先加入暫存區"
                ),
                "enabled": staged > 0 and format_ok,
            },
            {
                "label": "Push 到 GitHub",
                "detail": (
                    f"ahead {sync['ahead']} · "
                    f"behind {sync['behind']}"
                    if sync["upstream"]
                    else "尚未設定 upstream"
                ),
                "enabled": push_enabled,
            },
        ]

        # 狀態更新後，若目前選項失效才重新找可用項目。
        if (
            selected >= len(options)
            or not options[selected]["enabled"]
        ):
            selected = first_enabled(options)

        clear()
        heading("檢查與提交")
        print()

        data_color = GREEN if validation_code == 0 else RED
        data_mark = "✓" if validation_code == 0 else "✕"

        print(
            f"資料  "
            f"{data_color}"
            f"{data_mark} "
            f"{fit(validation_text, ui_width() - 7)}"
            f"{RESET}"
        )

        print(
            f"格式  "
            f"{GREEN if format_ok else RED}"
            f"{'✓ 通過' if format_ok else '✕ 有問題'}"
            f"{RESET}"
        )

        print(
            f"Git   {len(changes)} 變更 · "
            f"{staged} staged"
        )

        if sync["upstream"]:
            sync_color = (
                YELLOW
                if sync["behind"] > 0
                else GRAY
            )

            print(
                f"{sync_color}"
                f"同步  ↑{sync['ahead']} · ↓{sync['behind']}"
                f"{RESET}"
            )

        print()
        rule()
        print()

        for index, option in enumerate(options):
            enabled = option["enabled"]
            prefix = "›" if index == selected else " "

            if not enabled:
                label_color = GRAY
            elif index == selected:
                label_color = CYAN + BOLD
            else:
                label_color = ""

            print(
                f"{label_color}"
                f"{prefix} {index + 1}  {option['label']}"
                f"{RESET}"
            )

            detail_color = GRAY if enabled else RED

            print(
                f"     {detail_color}"
                f"{fit(option['detail'], ui_width() - 5)}"
                f"{RESET}"
            )
            print()

        rule()
        print(f"{GRAY}↑↓ 選擇 · Enter 執行{RESET}")
        print(f"{GRAY}1–4 直達 · Esc / Q 返回控制中心{RESET}")

        key = read_key()

        if key == "UP":
            selected = move_enabled(
                options,
                selected,
                -1,
            )
            continue

        if key == "DOWN":
            selected = move_enabled(
                options,
                selected,
                1,
            )
            continue

        if key in {"ESC", "q", "Q"}:
            return

        chosen = None

        if key == "ENTER":
            if options[selected]["enabled"]:
                chosen = selected

        elif key in {"1", "2", "3", "4"}:
            index = int(key) - 1

            if options[index]["enabled"]:
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

        # Action 執行後回到這一層重新讀取 Git state。
        # selected 會保留；只有該項因狀態改變而 disabled
        # 才會在下一輪自動移到可用項目。


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


def main() -> int:
    filename = sys.argv[1] if len(sys.argv) >= 2 else None

    while True:
        problem = current_problem(filename)

        if problem:
            state = problem.get("state")
            solved = bool(
                state
                and state.solved_on
            )

            finish_enabled = not solved
            review_enabled = solved

            note = ROOT / "notes" / f"{problem['id']}.md"

            note_detail = (
                "已建立；選取後直接開啟"
                if note.exists()
                else "尚未建立；選取後建立並開啟"
            )

            finish_detail = (
                "首次 AC 後記錄掌握程度"
                if finish_enabled
                else "已標記 AC；後續請使用「複習題目」"
            )

            review_detail = (
                "重做後更新 Result、Recall 與 Evidence"
                if review_enabled
                else "需先完成題目並取得 AC"
            )

        else:
            finish_enabled = False
            review_enabled = False
            note_detail = "需先開啟 APCS 題目檔案"
            finish_detail = "需先開啟 APCS 題目檔案"
            review_detail = "需先開啟 APCS 題目檔案"

        changes = git_changes()

        options = [
            {
                "label": "今日學習",
                "detail": "Adaptive review + 保留新學習容量",
                "enabled": True,
            },
            {
                "label": "題目資料",
                "detail": "新增題目、編輯 metadata、建立 solution",
                "enabled": True,
            },
            {
                "label": "完成題目",
                "detail": finish_detail,
                "enabled": finish_enabled,
            },
            {
                "label": "複習題目",
                "detail": review_detail,
                "enabled": review_enabled,
            },
            {
                "label": "題目筆記",
                "detail": note_detail,
                "enabled": problem is not None,
            },
            {
                "label": "檢查與提交",
                "detail": (
                    f"{len(changes)} 個 Git 變更待處理"
                    if changes
                    else "目前 Git 工作區乾淨"
                ),
                "enabled": True,
            },
        ]

        selected = choose_menu(
            "控制中心",
            options,
            problem=problem,
            main=True,
        )

        if selected is None:
            closed_screen()
            return 0

        if selected == 0:
            filename = today_view(filename)

        elif selected == 1:
            filename = catalog_center(problem, filename)

        elif selected == 2:
            record_problem("finish", problem)

        elif selected == 3:
            record_problem("review", problem)

        elif selected == 4:
            open_note(problem)

        elif selected == 5:
            git_center()


if __name__ == "__main__":
    raise SystemExit(main())
