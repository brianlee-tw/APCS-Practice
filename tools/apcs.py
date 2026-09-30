#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

try:
    from .learning_engine import (
        EVENT_FINISH,
        EVENT_REVIEW,
        LearningEngine,
        LearningError,
        LearningStore,
        ProgressState,
        VALID_RESULTS,
    )
except ImportError:
    from learning_engine import (
        EVENT_FINISH,
        EVENT_REVIEW,
        LearningEngine,
        LearningError,
        LearningStore,
        ProgressState,
        VALID_RESULTS,
    )


try:
    from .catalog_store import CatalogError, CatalogStore
except ImportError:
    from catalog_store import CatalogError, CatalogStore


try:
    from .tag_analytics import (
        build_tag_stats,
        display_tags,
        weakness_stats,
    )
except ImportError:
    from tag_analytics import (
        build_tag_stats,
        display_tags,
        weakness_stats,
    )


ROOT = Path(__file__).resolve().parents[1]

DATA = Path(
    os.environ.get(
        "APCS_DATA_DIR",
        str(ROOT / "data"),
    )
)

DOCS = ROOT / "docs"
NOTES = ROOT / "notes"

INDEX = DOCS / "PROBLEM_INDEX.md"
QUEUE = DOCS / "REVIEW_QUEUE.md"

STORE = LearningStore(DATA)
ENGINE = LearningEngine(STORE)
CATALOG = CatalogStore(DATA)

START = "<!-- APCS_DASHBOARD_START -->"
END = "<!-- APCS_DASHBOARD_END -->"

ID_RE = re.compile(r"([a-z]\d+|\d+)", re.I)

@dataclass
class Sol:
    path: Path
    pid: str
    meta: dict[str, str]

    @property
    def title(self):
        return self.meta.get("title") or self.path.stem

    @property
    def tags(self):
        return [
            x.strip()
            for x in self.meta.get("tag", "").split(",")
            if x.strip()
        ]

    @property
    def complexity(self):
        return self.meta.get("complexity") or "—"

    @property
    def difficulty(self):
        try:
            return max(
                1,
                min(
                    5,
                    int(
                        self.meta.get(
                            "difficulty",
                            "1",
                        )
                    ),
                ),
            )
        except Exception:
            return 1

def norm(value: str | None) -> str:
    match = ID_RE.search(
        (value or "").lower()
    )
    return match.group(1) if match else ""


def ensure():
    STORE.ensure()
    DOCS.mkdir(exist_ok=True)
    NOTES.mkdir(exist_ok=True)


def load_progress():
    ensure()
    return STORE.load_progress()


def build_catalog():
    progress = load_progress()
    by = defaultdict(list)
    warnings = []

    problems = CATALOG.load_problems()
    catalog_solutions = CATALOG.load_solutions()

    for entry in catalog_solutions:
        problem = problems.get(entry.problem_id)

        if problem is None:
            warnings.append(
                f"Catalog: {entry.problem_id} 不存在題目資料"
            )
            continue

        path = ROOT / entry.path
        meta = {
            "title": problem.title,
            "source": problem.source,
            "difficulty": problem.difficulty,
            "tag": problem.tags,
            "complexity": entry.complexity,
        }

        by[entry.problem_id].append(
            Sol(
                path=path,
                pid=entry.problem_id,
                meta=meta,
            )
        )

    rows = []

    for pid, solutions in sorted(by.items()):
        primary = sorted(
            solutions,
            key=lambda x: (
                0 if x.path.suffix == ".cpp" else 1,
                str(x.path),
            ),
        )[0]

        state = progress.get(
            pid,
            ProgressState(problem_id=pid),
        )

        due = (
            ENGINE.next_due(pid)
            if state.solved_on
            else None
        )

        rows.append(
            (
                pid,
                solutions,
                primary,
                state,
                False,
                due,
                display_tags(
                    primary.meta.get(
                        "tag",
                        "",
                    )
                ),
            )
        )

    return rows, warnings


def build():
    return build_catalog()


def link(
    path: Path,
    label=None,
    from_docs=False,
):
    relative = path.relative_to(
        ROOT
    ).as_posix()

    prefix = "../" if from_docs else "./"

    return (
        f"[{label or path.name}]"
        f"({prefix}{relative})"
    )


def status(state, _legacy):
    if state.solved_on:
        if (
            state.last_review_on
            and state.last_result
            and state.last_result != "AC"
        ):
            return (
                "✅ AC · "
                f"最近 {state.last_result}"
            )

        return "✅ AC"


    return "📝 Untracked"


def render_dashboard(rows):
    today = dt.date.today()

    solved = sum(
        bool(row[3].solved_on)
        for row in rows
    )

    due = sum(
        bool(
            row[5]
            and row[5] <= today
        )
        for row in rows
    )

    mastery = defaultdict(int)
    mastery_by_pid = {}

    for row in rows:
        level = ENGINE.mastery(
            row[0]
        )

        mastery[level] += 1
        mastery_by_pid[
            row[0]
        ] = level

    tag_stats, legacy_tags = (
        build_tag_stats(
            rows,
            today=today,
            mastery_by_pid=mastery_by_pid,
        )
    )

    weak = weakness_stats(
        tag_stats
    )

    lines = [
        "## APCS Training Dashboard",
        "",
        "| 指標 | 數量 |",
        "| :--- | ---: |",
        f"| 索引題目 | **{len(rows)}** |",
        f"| 明確 AC | **{solved}** |",
        f"| Mastered | **{mastery['MASTERED']}** |",
        f"| 今日到期複習 | **{due}** |",
        "",
        "### Canonical Tag 能力分布",
        "",
        "> 一題可同時計入多個 Tag，"
        "因此 Tag 題數加總可能大於索引題目總數。",
        "",
        "| 類別 | Tag | 題數 | AC | "
        "Mastered | Recall 0–1 | 到期 |",
        "| :--- | :--- | ---: | ---: | "
        "---: | ---: | ---: |",
    ]

    if tag_stats:
        for stat in tag_stats:
            lines.append(
                f"| {stat.group} | "
                f"{stat.tag} | "
                f"{stat.total} | "
                f"{stat.solved} | "
                f"{stat.mastered} | "
                f"{stat.low_recall} | "
                f"{stat.due} |"
            )
    else:
        lines.append(
            "| — | 尚無 canonical Tag | "
            "— | — | — | — | — |"
        )

    lines += [
        "",
        "### 弱項訊號",
        "",
        "> 只使用可觀察資料：Recall 0–1 "
        "或已到期題目；不使用黑箱分數。",
        "",
        "| Tag | 已 AC | Recall 0–1 | 到期 | Mastered |",
        "| :--- | ---: | ---: | ---: | ---: |",
    ]

    if weak:
        for stat in weak:
            lines.append(
                f"| {stat.tag} | "
                f"{stat.solved} | "
                f"{stat.low_recall} | "
                f"{stat.due} | "
                f"{stat.mastered} |"
            )
    else:
        lines.append(
            "| — | — | — | — | "
            "目前沒有明確弱項訊號 |"
        )

    if legacy_tags:
        lines += [
            "",
            "### Legacy Tag 待整理",
            "",
            "> 下列標籤未被 taxonomy 自動推測或轉換；"
            "保留原值，待後續人工確認。",
            "",
            "| Legacy Tag | 題數 |",
            "| :--- | ---: |",
        ]

        for tag, count in legacy_tags:
            lines.append(
                f"| {tag} | {count} |"
            )

    lines += [
        "",
        "### 今日複習優先序",
        "",
        "| ID | 題目 | Tags | Recall | 到期日 |",
        "| :--- | :--- | :--- | ---: | :---: |",
    ]

    table = {
        row[0]: row
        for row in rows
    }

    queue = ENGINE.due_queue(
        on=today
    )

    if queue:
        for item in queue[:12]:
            row = table.get(
                item.problem_id
            )

            if not row:
                continue

            lines.append(
                f"| `{item.problem_id}` | "
                f"{row[2].title} | "
                f"{row[6]} | "
                f"{item.recall if item.recall is not None else '—'} | "
                f"{item.due_on} |"
            )

    else:
        lines.append(
            "| — | 目前沒有到期題目 | "
            "— | — | — |"
        )

    lines += [
        "",
        "完整題庫見 "
        "[Problem Index](./docs/PROBLEM_INDEX.md)，"
        "複習佇列見 "
        "[Review Queue](./docs/REVIEW_QUEUE.md)。",
    ]

    return "\n".join(lines)


def render_index(rows):
    lines = [
        "# Problem Index",
        "",
        "> 自動產生；請勿手動編輯。",
        "",
        "| ID | 題目 | Tags | 程式 | 複雜度 | "
        "難度 | 狀態 | Recall | Mastery | 筆記 |",
        "| :--- | :--- | :--- | :--- | :--- | "
        ":---: | :---: | ---: | :---: | :--- |",
    ]

    for (
        pid,
        solutions,
        primary,
        state,
        legacy,
        due,
        area,
    ) in rows:
        programs = "<br>".join(
            link(
                solution.path,
                (
                    "C++"
                    if solution.path.suffix == ".cpp"
                    else "Py"
                ),
                True,
            )
            for solution in sorted(
                solutions,
                key=lambda x: x.path.suffix,
            )
        )

        local = NOTES / f"{pid}.md"

        note = (
            link(local, "Local", True)
            if local.exists()
            else "—"
        )

        lines.append(
            f"| `{pid}` | "
            f"{primary.title} | "
            f"{area} | "
            f"{programs} | "
            f"`{primary.complexity}` | "
            f"{'★' * primary.difficulty} | "
            f"{status(state, legacy)} | "
            f"{state.recall if state.recall is not None else '—'} | "
            f"{ENGINE.mastery(pid)} | "
            f"{note} |"
        )

    return "\n".join(lines) + "\n"


def render_queue(rows):
    today = dt.date.today()

    queue = [
        row
        for row in rows
        if (
            row[3].solved_on
            and row[5]
        )
    ]

    lines = [
        "# Review Queue",
        "",
        "> 自動產生；依 v2.1 adaptive review 排序。",
        "",
        "| 到期日 | ID | 題目 | Tags | Recall | Mastery | 狀態 |",
        "| :---: | :--- | :--- | :--- | ---: | :---: | :---: |",
    ]

    queue.sort(
        key=lambda row: (
            (
                -(today - row[5]).days
                if row[5] <= today
                else 10**6
            ),
            (
                row[3].recall
                if row[3].recall is not None
                else -1
            ),
            row[5],
            row[0],
        )
    )

    if not queue:
        lines.append(
            "| — | — | 尚無明確 AC / review 資料 | "
            "— | — | — | — |"
        )

    for row in queue:
        if row[5] < today:
            mark = "🔴 逾期"
        elif row[5] == today:
            mark = "🟡 今天"
        else:
            mark = "🟢 排程"

        lines.append(
            f"| {row[5]} | "
            f"`{row[0]}` | "
            f"{row[2].title} | "
            f"{row[6]} | "
            f"{row[3].recall if row[3].recall is not None else '—'} | "
            f"{ENGINE.mastery(row[0])} | "
            f"{mark} |"
        )

    return "\n".join(lines) + "\n"


def replace_between(
    text,
    start,
    end,
    body,
):
    if (
        start in text
        and end in text
    ):
        before, rest = text.split(
            start,
            1,
        )

        _, after = rest.split(
            end,
            1,
        )

        return (
            before
            + start
            + "\n"
            + body
            + "\n"
            + end
            + after
        )

    return (
        text.rstrip()
        + f"\n\n{start}\n"
        + body
        + f"\n{end}\n"
    )


def sync():
    ensure()
    rows, warnings = build()

    readme = ROOT / "README.md"

    text = (
        readme.read_text(
            encoding="utf-8"
        )
        if readme.exists()
        else "# APCS-Practice\n"
    )

    readme.write_text(
        replace_between(
            text,
            START,
            END,
            render_dashboard(rows),
        ),
        encoding="utf-8",
    )

    INDEX.write_text(
        render_index(rows),
        encoding="utf-8",
    )

    QUEUE.write_text(
        render_queue(rows),
        encoding="utf-8",
    )

    print(
        f"已同步 {len(rows)} 題。"
    )

    if warnings:
        print(
            f"有 {len(warnings)} 個索引警告；"
            "完整 metadata 檢查請執行 validate。"
        )

    return 0


def validate(strict=False):
    ensure()

    rows = []
    warnings = []
    errors = []
    metadata_label = "Catalog"

    try:
        rows, build_warnings = build()
        warnings.extend(
            build_warnings
        )

        errors.extend(
            f"Catalog: {message}"
            for message in CATALOG.validate(
                root=ROOT
            )
        )

    except CatalogError as exc:
        errors.append(
            f"Catalog: {exc}"
        )

    for (
        _,
        solutions,
        _,
        _,
        _,
        _,
        _,
    ) in rows:
        for solution in solutions:
            relative = solution.path.relative_to(
                ROOT
            )

            if not solution.meta.get("title"):
                warnings.append(
                    f"{relative}: 缺少 {metadata_label} Title"
                )

            if not solution.tags:
                warnings.append(
                    f"{relative}: 缺少 {metadata_label} Tag"
                )

            if solution.complexity == "—":
                warnings.append(
                    f"{relative}: 缺少 {metadata_label} Complexity"
                )

    progress = STORE.load_progress()

    for pid, state in progress.items():
        if (
            state.recall is not None
            and state.recall not in {0, 1, 2, 3}
        ):
            errors.append(
                f"{pid}: Recall 必須介於 0–3"
            )

        if (
            state.last_review_on
            and not state.solved_on
        ):
            errors.append(
                f"{pid}: 未完成題目卻存在 Review 日期"
            )

        if (
            state.last_result
            and state.last_result not in VALID_RESULTS
        ):
            errors.append(
                f"{pid}: 無效 result={state.last_result}"
            )

    events = STORE.load_events()
    finish_count = defaultdict(int)

    for event in events:
        if event.event_type not in {
            EVENT_FINISH,
            EVENT_REVIEW,
        }:
            errors.append(
                f"{event.problem_id}: "
                f"無效 event_type={event.event_type}"
            )

        if event.score not in {
            0,
            1,
            2,
            3,
        }:
            errors.append(
                f"{event.problem_id}: "
                "event Recall 必須介於 0–3"
            )

        if event.result not in VALID_RESULTS:
            errors.append(
                f"{event.problem_id}: "
                f"無效 event result={event.result}"
            )

        if event.event_type == EVENT_FINISH:
            finish_count[event.problem_id] += 1

            if event.result != "AC":
                errors.append(
                    f"{event.problem_id}: "
                    "Finish 必須為 AC"
                )

        if (
            event.event_type == EVENT_REVIEW
            and event.result != "AC"
            and event.score == 3
        ):
            errors.append(
                f"{event.problem_id}: "
                "未 AC Review 不能是 Recall 3"
            )

    for pid, count in finish_count.items():
        if count > 1:
            errors.append(
                f"{pid}: 存在 {count} 個 Finish events"
            )

    errors.extend(
        STORE.validate_consistency()
    )

    print(
        f"題目：{len(rows)} | "
        f"錯誤：{len(errors)} | "
        f"警告：{len(warnings)}"
    )

    for error in errors:
        print("錯誤：", error)

    for warning in warnings:
        print("警告：", warning)

    return (
        1
        if (
            errors
            or (strict and warnings)
        )
        else 0
    )


def known_problem_ids():
    rows, _ = build()

    return {
        row[0]
        for row in rows
    }


def finish_cmd(
    pid,
    score,
    *,
    minutes=None,
    note="",
):
    pid = norm(pid)

    if pid not in known_problem_ids():
        raise SystemExit(
            f"找不到題號：{pid}"
        )

    try:
        ENGINE.finish(
            pid,
            score,
            minutes=minutes,
            note=note,
        )
    except LearningError as exc:
        raise SystemExit(str(exc))

    if os.environ.get(
        "APCS_DISABLE_SYNC"
    ) != "1":
        sync()

    print(
        f"已完成 {pid}："
        f"Recall={score}/3"
    )

    return 0


def review_cmd(
    pid,
    score,
    *,
    result="AC",
    minutes=None,
    note="",
):
    pid = norm(pid)

    if pid not in known_problem_ids():
        raise SystemExit(
            f"找不到題號：{pid}"
        )

    try:
        ENGINE.review(
            pid,
            score,
            result=result,
            minutes=minutes,
            note=note,
        )
    except LearningError as exc:
        raise SystemExit(str(exc))

    if os.environ.get(
        "APCS_DISABLE_SYNC"
    ) != "1":
        sync()

    print(
        f"已複習 {pid}："
        f"{result}, Recall={score}/3"
    )

    return 0


def today_cmd():
    rows, _ = build()

    table = {
        row[0]: row
        for row in rows
    }

    queue = ENGINE.due_queue()

    if not queue:
        print(
            "今天沒有到期的複習題。"
        )
        return 0

    print(
        f"今日到期複習：{len(queue)} 題"
    )

    for item in queue:
        row = table.get(
            item.problem_id
        )

        title = (
            row[2].title
            if row
            else item.problem_id
        )

        state = (
            f"逾期 {item.days_overdue} 天"
            if item.days_overdue > 0
            else "今天到期"
        )

        print(
            f"{item.problem_id}  "
            f"Recall={item.recall}  "
            f"{state}  "
            f"{title}"
        )

    return 0


def note_cmd(pid):
    pid = norm(pid)

    rows, _ = build()

    table = {
        row[0]: row
        for row in rows
    }

    if pid not in table:
        raise SystemExit(
            f"找不到題號：{pid}"
        )

    path = NOTES / f"{pid}.md"

    if path.exists():
        print(
            path.relative_to(ROOT)
        )
        return 0

    title = table[pid][2].title

    path.write_text(
        f"# {pid} — {title}\n\n"
        "## 核心解法\n\n-\n\n"
        "## 我卡住的地方\n\n-\n\n"
        "## 關鍵觀念\n\n-\n\n"
        "## 複雜度\n\n-\n\n"
        "## 下次重解注意\n\n-\n",
        encoding="utf-8",
    )

    print(
        path.relative_to(ROOT)
    )

    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="APCS-Practice v2.2 catalog workflow"
    )

    sub = parser.add_subparsers(
        dest="cmd",
        required=True,
    )

    sub.add_parser("sync")

    validate_parser = sub.add_parser(
        "validate"
    )
    validate_parser.add_argument(
        "--strict",
        action="store_true",
    )

    sub.add_parser("today")

    finish = sub.add_parser("finish")
    finish.add_argument("problem_id")
    finish.add_argument(
        "score",
        type=int,
    )
    finish.add_argument(
        "--minutes",
        type=int,
    )
    finish.add_argument(
        "--note",
        default="",
    )

    review = sub.add_parser("review")
    review.add_argument("problem_id")
    review.add_argument(
        "score",
        type=int,
    )
    review.add_argument(
        "--result",
        default="AC",
        choices=sorted(VALID_RESULTS),
    )
    review.add_argument(
        "--minutes",
        type=int,
    )
    review.add_argument(
        "--note",
        default="",
    )

    note = sub.add_parser("note")
    note.add_argument("problem_id")

    args = parser.parse_args(argv)

    if args.cmd == "sync":
        return sync()

    if args.cmd == "validate":
        return validate(
            args.strict
        )

    if args.cmd == "today":
        return today_cmd()

    if args.cmd == "finish":
        return finish_cmd(
            args.problem_id,
            args.score,
            minutes=args.minutes,
            note=args.note,
        )

    if args.cmd == "review":
        return review_cmd(
            args.problem_id,
            args.score,
            result=args.result,
            minutes=args.minutes,
            note=args.note,
        )

    if args.cmd == "note":
        return note_cmd(
            args.problem_id
        )

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
