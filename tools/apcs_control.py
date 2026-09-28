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

import apcs as core


ROOT = Path(__file__).resolve().parents[1]
ID_RE = re.compile(r"^([A-Za-z]\d+)(?:_|$)")

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

    for row in all_rows():
        if row[0] == pid:
            return {
                "id": pid,
                "title": clean_title(pid, row[2].title),
                "path": row[2].path,
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
            print(f"{GRAY}1–5 直達 · Esc / Q 關閉{RESET}")
        else:
            print(f"{GRAY}↑↓ 選擇 · Enter 執行{RESET}")
            print(f"{GRAY}Esc / Q 返回控制中心{RESET}")

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
                command_result = core.finish_cmd(
                    problem["id"],
                    score,
                    minutes=minutes,
                )
            else:
                command_result = core.review_cmd(
                    problem["id"],
                    score,
                    result=result,
                    minutes=minutes,
                )

    except SystemExit as exc:
        print()
        print(
            f"{RED}"
            f"✕ 更新失敗：{exc}"
            f"{RESET}"
        )
        pause()
        return

    print()

    if command_result == 0:
        print(
            f"{GREEN}"
            f"✓ 學習紀錄已更新"
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
            record_problem("finish", problem)

        elif selected == 2:
            record_problem("review", problem)

        elif selected == 3:
            open_note(problem)

        elif selected == 4:
            git_center()


if __name__ == "__main__":
    raise SystemExit(main())
