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
    from .attempt_capture import build_attempt_envelope
    from .catalog_store import CatalogError, ProblemMeta, SolutionMeta
    from .evidence_outbox import EvidenceOutbox, EvidenceOutboxError
    from .runtime_curriculum import (
        RuntimeCurriculumError,
        RuntimeCurriculumUnavailable,
        default_curriculum,
    )
    from .tag_taxonomy import TAG_GROUPS, serialize_selection, split_tags
except ImportError:
    import apcs as core
    from attempt_capture import build_attempt_envelope
    from catalog_store import CatalogError, ProblemMeta, SolutionMeta
    from evidence_outbox import EvidenceOutbox, EvidenceOutboxError
    from runtime_curriculum import (
        RuntimeCurriculumError,
        RuntimeCurriculumUnavailable,
        default_curriculum,
    )
    from tag_taxonomy import TAG_GROUPS, serialize_selection, split_tags


ROOT = Path(__file__).resolve().parents[1]
ID_RE = re.compile(r"^([A-Za-z]\d+|\d+)(?:_|$)")

CURRICULUM = default_curriculum(ROOT)
OUTBOX = EvidenceOutbox(
    ROOT / ".apcs" / "runtime"
)

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
    match = ID_RE.match(path.stem)

    if not match:
        return None

    pid = match.group(1).lower()
    candidate = path if path.is_absolute() else ROOT / path
    resolved = candidate.resolve()

    for row in all_rows():
        if row[0] == pid:
            matched_path = next(
                (
                    solution.path
                    for solution in row[1]
                    if solution.path.resolve() == resolved
                ),
                row[2].path,
            )

            return {
                "id": pid,
                "title": clean_title(pid, row[2].title),
                "path": matched_path,
                "state": row[3],
                "due": row[5],
            }

    return {
        "id": pid,
        "title": clean_title(pid, path.stem),
        "path": path,
        "state": None,
        "due": None,
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

    due = problem.get("due")

    if due:
        today = dt.date.today()

        if due < today:
            parts.append(f"逾期 {(today - due).days} 天")
        elif due == today:
            parts.append("今天到期")
        else:
            parts.append(f"下次 {due:%m/%d}")

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
            due, overdue = today_state()

            print(f"{GRAY}今日狀態{RESET}")

            if due:
                text = f"待複習 {len(due)} 題"
                if overdue:
                    text += f" · 逾期 {len(overdue)} 題"
                print(f"{YELLOW}{text}{RESET}")
            else:
                print(f"{GREEN}✓ 沒有到期複習{RESET}")

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
            (0, "幾乎不會／需看答案", "1 天後再做"),
            (1, "需要提示", "3 天後再做"),
            (2, "可獨立但偏慢", "7 天後再做"),
            (3, "流暢獨立", "30 天後起"),
        ]
    else:
        entries = [
            (0, "幾乎不會／需看答案", "1 天後再做"),
            (1, "需要提示才能推進", "3 天後再做"),
            (2, "主要思路可獨立完成", "本次未 AC · 7 天後再做"),
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

    print()
    rule()
    print()

    if not confirm("確認寫入這次學習紀錄？"):
        return

    print()
    print(f"{GRAY}正在更新學習紀錄…{RESET}")

    try:
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

    if command_result == 0:
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
    due, _ = today_state()

    if not due:
        clear()
        heading("今日複習")
        print()
        print(f"{GREEN}✓ 今天沒有到期題目{RESET}")
        print()
        print(f"{GRAY}可以直接進行新題。{RESET}")
        pause()
        return current_filename

    today = dt.date.today()

    rows = sorted(
        due,
        key=lambda row: (row[5], row[0]),
    )

    options = []

    for row in rows:
        pid = row[0]
        title = clean_title(pid, row[2].title)
        recall = (
            row[3].recall
            if row[3].recall is not None
            else "—"
        )

        if row[5] < today:
            due_text = f"逾期 {(today - row[5]).days} 天"
        else:
            due_text = "今天到期"

        options.append(
            {
                "label": f"{pid} · {title}",
                "detail": f"Recall {recall} · {due_text}",
                "enabled": True,
                "path": row[2].path,
            }
        )

    selected = choose_menu(
        "今日複習",
        options,
        main=False,
    )

    if selected is None:
        return current_filename

    path = options[selected]["path"]

    result = subprocess.run(
        ["code", "--reuse-window", str(path)],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    clear()
    heading("今日複習")
    print()

    if result.returncode == 0:
        print(f"{GREEN}✓ 已開啟題目{RESET}")
        print(fit(options[selected]["label"], ui_width()))
        print()
        print(f"{GRAY}完成重解後回到控制中心，選擇「複習題目」。{RESET}")
    else:
        print(f"{RED}✕ 無法開啟題目{RESET}")

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
                "重做後更新 Recall 與下次日期"
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
                "label": "今日複習",
                "detail": "開始今天排定的複習",
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
