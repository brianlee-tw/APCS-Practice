#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import datetime as dt
import io
import re
import subprocess
import sys
from pathlib import Path

import apcs as core
import apcs_control as control


ROOT = Path(__file__).resolve().parents[1]
BUILD_DIR = ROOT / "build"

PROBLEM_ID_RE = re.compile(r"^([A-Za-z]\d+)(?:_|$)")
RECALL_RE = re.compile(r"^\s*([0-3])")

UI_WIDTH = 28

RECALL_TEXT = {
    0: "幾乎不會／需看答案",
    1: "需要提示",
    2: "可獨立但偏慢",
    3: "流暢獨立",
}

def rule() -> None:
    print("─" * UI_WIDTH)


def header(title: str) -> None:
    print()
    print(f"APCS · {title}")
    rule()


def clip(text: str, limit: int = 25) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def fail(message: str, code: int = 2) -> int:
    print(f"✕ {message}", file=sys.stderr)
    return code


def problem_id(filename: str) -> str:
    match = PROBLEM_ID_RE.match(Path(filename).stem)
    if not match:
        raise ValueError(
            "無法辨識題號；檔名需以 a001、b130 等題號開頭。"
        )
    return match.group(1).lower()


def recall_score(choice: str) -> int:
    match = RECALL_RE.match(choice)
    if not match:
        raise ValueError("無法辨識 Recall 分數。")
    return int(match.group(1))


def compile_cpp(filename: str) -> tuple[int, Path | None]:
    source = Path(filename).resolve()

    if source.suffix.lower() != ".cpp":
        return fail("目前檔案不是 C++（.cpp）。"), None

    if not source.is_file():
        return fail("找不到目前檔案。"), None

    BUILD_DIR.mkdir(exist_ok=True)
    output = BUILD_DIR / source.stem

    print(f"檔案  {clip(source.name)}")
    print("編譯  …")

    result = subprocess.run(
        [
            "g++",
            "-std=c++17",
            "-O2",
            "-Wall",
            "-Wextra",
            str(source),
            "-o",
            str(output),
        ],
        cwd=ROOT,
    )

    if result.returncode != 0:
        print()
        return fail("編譯失敗。", result.returncode), None

    print("編譯  ✓ 完成")
    return 0, output


def build_only(filename: str) -> int:
    header("編譯")
    code, output = compile_cpp(filename)

    if code == 0 and output is not None:
        print(f"輸出  build/{clip(output.name, 19)}")

    return code


def build_and_run(filename: str) -> int:
    header("編譯與執行")

    code, executable = compile_cpp(filename)
    if code != 0 or executable is None:
        return code

    print()
    print("程式輸入／輸出")
    rule()

    result = subprocess.run([str(executable)], cwd=ROOT)

    rule()
    if result.returncode == 0:
        print("結束  ✓ 正常")
    else:
        print(f"結束  ✕ code {result.returncode}")

    return result.returncode


def today_view() -> int:
    header("今日學習")

    snapshot = (
        control.adaptive_today_snapshot()
    )
    plan = snapshot["plan"]

    print(
        f"容量  {snapshot['capacity_minutes']} min"
    )
    print(
        f"Review  {plan.selected_minutes}/"
        f"{plan.budget_minutes} min"
    )
    print(
        f"Skill due  {snapshot['due_count']}"
    )
    print(
        f"Selected   {len(plan.selected)}"
    )
    print(
        f"Deferred   {len(plan.deferred)}"
    )

    protected = max(
        0,
        snapshot["capacity_minutes"]
        - plan.budget_minutes,
    )
    print(
        f"New learning  >= {protected} min"
    )

    if snapshot["warning"]:
        print(
            f"Warning  {snapshot['warning']}"
        )

    if not plan.selected:
        print(
            "✓ 沒有需要透過這個非互動 Task 啟動的 review"
        )
        print(
            "使用 Ctrl+Alt+A 開啟 Control Center 進行今日學習。"
        )
        return 0

    for item in plan.selected:
        print()
        print(
            f"{item.skill_uid} x {item.track}"
        )
        print(
            f"R≈{item.retrievability:.0%}"
            f" · due {item.due_on}"
            f" · {item.estimated_minutes} min"
        )

    print()
    print(
        "使用 Ctrl+Alt+A 開啟 Control Center 並選擇「今日學習」。"
    )
    return 0


def record_current(
    action: str,
    filename: str,
    choice: str,
) -> int:
    """Retired compatibility entry point.

    v2.3 Finish / Review must capture Assistance, Independent, Novelty,
    Timed, Placement, durable outbox, and adaptive memory.  The old direct
    `record(pid, recall)` path would silently bypass that evidence model.
    """

    _ = (
        action,
        filename,
        choice,
    )

    return fail(
        "v2.3 已停用舊式 Finish / Review Task；"
        "請按 Ctrl+Alt+A，在 Control Center 使用「完成題目／複習題目」。"
    )


def create_note(filename: str) -> int:
    try:
        pid = problem_id(filename)
    except ValueError as exc:
        return fail(str(exc))

    header("建立筆記")
    print(f"題號  {pid}")

    buf = io.StringIO()

    try:
        with contextlib.redirect_stdout(buf):
            result = core.note_cmd(pid)
    except SystemExit as exc:
        return fail("建立筆記失敗。", int(exc.code or 1))

    if result != 0:
        return fail("建立筆記失敗。", result)

    print("狀態  ✓ 完成")
    return 0


def precommit() -> int:
    header("提交前檢查")

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        validate_code = core.validate()

    validation = buf.getvalue()
    match = re.search(
        r"錯誤[：:]\s*(\d+).*警告[：:]\s*(\d+)",
        validation,
    )

    if match:
        errors, warnings = match.groups()
        mark = "✓" if validate_code == 0 else "✕"
        print(f"資料  {mark} {errors} 錯誤 · {warnings} 警告")
    else:
        print(f"資料  {'✓' if validate_code == 0 else '✕'}")

    diff = subprocess.run(
        ["git", "diff", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    print(f"格式  {'✓' if diff.returncode == 0 else '✕'}")

    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    changes = [
        line for line in status.stdout.splitlines()
        if line.strip()
    ]

    print(f"Git   {len(changes)} 個變更")
    rule()

    if validate_code == 0 and diff.returncode == 0:
        print("✓ 可以進入 commit review")
        return 0

    print("✕ 尚不建議提交")
    return 1


def main() -> int:
    if len(sys.argv) < 2:
        return fail("缺少 Task 動作。")

    action = sys.argv[1]

    if action == "today":
        return today_view()

    if action == "build":
        if len(sys.argv) != 3:
            return fail("缺少目前檔案。")
        return build_only(sys.argv[2])

    if action == "build-run":
        if len(sys.argv) != 3:
            return fail("缺少目前檔案。")
        return build_and_run(sys.argv[2])

    if action in {"finish", "review"}:
        if len(sys.argv) != 4:
            return fail("缺少題目或 Recall。")
        return record_current(action, sys.argv[2], sys.argv[3])

    if action == "note":
        if len(sys.argv) != 3:
            return fail("缺少目前檔案。")
        return create_note(sys.argv[2])

    if action == "precommit":
        return precommit()

    return fail(f"未知 Task：{action}")


if __name__ == "__main__":
    raise SystemExit(main())
