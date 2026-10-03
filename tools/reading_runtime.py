"""Reading Track learner runtime for APCS v2.3.

Reading Evidence is deliberately response-first:
- the learner must save an explicit reason / trace before verification;
- the runtime never opens an old solution or executor automatically;
- Reading attempts use Judge Result N/A rather than pretending AC;
- Placement identity remains the same Published Curriculum authority.
"""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path


FORMAL_START = "<!-- APCS_READING_FORMAL_START -->"
FORMAL_END = "<!-- APCS_READING_FORMAL_END -->"


def _safe_name(value: str) -> str:
    cleaned = re.sub(
        r"[^A-Za-z0-9_.-]+",
        "_",
        str(value or "").strip(),
    ).strip("._")
    return cleaned or "problem"


def create_reading_scratch(
    runtime_dir: Path,
    placement,
    *,
    action: str,
    today: dt.date | None = None,
) -> Path:
    """Create one response-first Reading activity bound to a Placement."""

    if action not in {"finish", "review"}:
        raise ValueError(
            f"unsupported Reading action={action!r}"
        )

    today = today or dt.date.today()
    folder = (
        Path(runtime_dir)
        / "reading"
        / action
        / today.isoformat()
    )
    folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    target = (
        folder
        / (
            f"{_safe_name(placement.problem_id)}"
            f"__{placement.placement_uid}.md"
        )
    )

    if target.exists():
        return target

    mode = (
        "New Learning"
        if action == "finish"
        else "Adaptive Review"
    )
    lesson = placement.lesson_uid or "—"
    judge = placement.url or "—"

    text = f"""# APCS Reading · {mode}

- Skill: {placement.primary_skill}
- Lesson: {lesson}
- Problem: {placement.problem_id} · {placement.title}
- Role: {placement.role}
- Reference / Judge URL: {judge}

## Evidence rule

1. **先 reason / trace，再驗證。**
2. Formal response 完成並儲存以前，不執行程式、不送 Judge、不看完整解答。
3. Formal response 完成後才可用 reference / executor / Judge 做 verification。
4. 驗證後回 Control Center 記錄 Reading Outcome；Reading Evidence 不偽裝成 AC。

## Formal response · verification 前完成

{FORMAL_START}

{FORMAL_END}

建議至少留下：model / invariant、關鍵 trace 或 prediction、boundary / counterexample、complexity reasoning（若適用）。

## Verification · Formal response 後

- 對照方式：
- First divergence / 修正：
- 最終仍不確定的點：

## Transfer note

- 這個 reasoning 在什麼條件下成立？
- 換一題時最先辨認哪個 signal？
"""

    target.write_text(
        text,
        encoding="utf-8",
    )
    return target


def formal_response(path: Path) -> str:
    """Return saved pre-verification response, or empty string if absent."""

    try:
        text = Path(path).read_text(
            encoding="utf-8"
        )
    except OSError:
        return ""

    if FORMAL_START not in text or FORMAL_END not in text:
        return ""

    return (
        text.split(FORMAL_START, 1)[1]
        .split(FORMAL_END, 1)[0]
        .strip()
    )


def formal_response_ready(path: Path) -> bool:
    return bool(formal_response(path))
