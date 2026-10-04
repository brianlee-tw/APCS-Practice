#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import io
import re
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

try:
    from . import apcs as core
    from . import apcs_control as control
    from .catalog_store import CatalogStore
    from .exam_runtime import ExamSessionStore
    from .local_test_runner import (
        OUTPUT_LIMIT,
        PASS,
        RUNTIME_ERROR,
        TIMEOUT,
        UNVERIFIED,
        WRONG_OUTPUT,
        CaseResult,
        CompileResult,
        LocalTestError,
        SuiteResult,
        compile_cpp as compile_cpp_safe,
        run_case,
        run_suite,
        unified_diff,
    )
    from .runtime_curriculum import RuntimeCurriculum
    from .test_assets import (
        SUITE_FAST,
        SUITE_FULL,
        TestAssetStore,
        TestBundle,
    )
    from .workbench_context import (
        ProblemContext,
        resolve_problem_context,
    )
    from .workbench_tui import (
        BOLD,
        CYAN,
        GRAY,
        GREEN,
        RED,
        RESET,
        WHITE,
        YELLOW,
        clear,
        command_bar,
        fit,
        heading,
        pad,
        pane_widths,
        render_columns,
        rule,
        status_badge,
        terminal_height,
        terminal_width,
        wrap,
    )
except ImportError:
    import apcs as core
    import apcs_control as control
    from catalog_store import CatalogStore
    from exam_runtime import ExamSessionStore
    from local_test_runner import (
        OUTPUT_LIMIT,
        PASS,
        RUNTIME_ERROR,
        TIMEOUT,
        UNVERIFIED,
        WRONG_OUTPUT,
        CaseResult,
        CompileResult,
        LocalTestError,
        SuiteResult,
        compile_cpp as compile_cpp_safe,
        run_case,
        run_suite,
        unified_diff,
    )
    from runtime_curriculum import RuntimeCurriculum
    from test_assets import (
        SUITE_FAST,
        SUITE_FULL,
        TestAssetStore,
        TestBundle,
    )
    from workbench_context import (
        ProblemContext,
        resolve_problem_context,
    )
    from workbench_tui import (
        BOLD,
        CYAN,
        GRAY,
        GREEN,
        RED,
        RESET,
        WHITE,
        YELLOW,
        clear,
        command_bar,
        fit,
        heading,
        pad,
        pane_widths,
        render_columns,
        rule,
        status_badge,
        terminal_height,
        terminal_width,
        wrap,
    )


ROOT = Path(__file__).resolve().parents[1]
BUILD_DIR = ROOT / "build"
RUNTIME_DIR = ROOT / ".apcs" / "runtime"
EXAM = ExamSessionStore(RUNTIME_DIR)
CATALOG = CatalogStore(ROOT / "data")
CURRICULUM = RuntimeCurriculum(
    ROOT / "curriculum" / "published.v23.json"
)
TEST_ASSETS = TestAssetStore(
    ROOT / "data" / "problem_enrichment",
    RUNTIME_DIR,
)

PROBLEM_ID_RE = re.compile(
    r"^([A-Za-z]\d+|\d+)(?:_|$)"
)
RECALL_RE = re.compile(
    r"^\s*([0-3])"
)

STATUS_LABELS = {
    PASS: ("✓", GREEN, "通過"),
    WRONG_OUTPUT: ("✕", RED, "輸出錯誤"),
    RUNTIME_ERROR: ("!", RED, "執行錯誤"),
    TIMEOUT: ("⏱", YELLOW, "逾時"),
    OUTPUT_LIMIT: ("⚠", YELLOW, "輸出過量"),
    UNVERIFIED: ("?", GRAY, "未驗證"),
}


def fail(
    message: str,
    code: int = 2,
) -> int:
    print(
        f"{RED}✕ {message}{RESET}",
        file=sys.stderr,
    )
    return code


def problem_id(filename: str) -> str:
    match = PROBLEM_ID_RE.match(
        Path(filename).stem
    )
    if not match:
        raise ValueError(
            "無法辨識題號。"
        )
    return match.group(1).lower()


def recall_score(choice: str) -> int:
    match = RECALL_RE.match(choice)
    if not match:
        raise ValueError(
            "無法辨識 Recall 分數。"
        )
    return int(match.group(1))


def problem_context(
    filename: str,
) -> ProblemContext | None:
    return resolve_problem_context(
        filename,
        root=ROOT,
        store=CATALOG,
        curriculum=CURRICULUM,
        intelligence_dir=(
            ROOT
            / "data"
            / "problem_intelligence"
        ),
    )


def _mark_exam_compile(
    context: ProblemContext | None,
    *,
    success: bool,
) -> None:
    if context is None:
        return
    try:
        EXAM.mark_compile(
            context.problem_id,
            success=success,
        )
    except (ValueError, OSError):
        # Telemetry must never break ordinary coding.
        pass


def compile_current(
    filename: str,
) -> tuple[
    ProblemContext | None,
    CompileResult,
]:
    source = Path(filename).resolve()
    output = BUILD_DIR / source.stem

    context = problem_context(
        filename
    )

    result = compile_cpp_safe(
        source,
        output,
        root=ROOT,
    )
    _mark_exam_compile(
        context,
        success=result.success,
    )

    return context, result


def _compile_screen(
    filename: str,
    context: ProblemContext | None,
    result: CompileResult,
) -> None:
    clear()
    suffix = (
        f"{context.problem_id} · {context.title}"
        if context is not None
        else Path(filename).name
    )
    heading(
        "編譯",
        suffix=fit(
            suffix,
            46,
        ),
    )
    print()

    if result.success:
        print(
            status_badge(
                "編譯成功",
                status="ok",
            )
            + f"  {result.duration_ms} ms"
        )
        print(
            f"{GRAY}"
            f"輸出：build/{Path(filename).stem}"
            f"{RESET}"
        )
    else:
        print(
            status_badge(
                "編譯失敗",
                status="error",
            )
            + f"  {result.duration_ms} ms"
        )
        print()
        if result.stderr:
            print(
                result.stderr.rstrip()
            )
        elif result.stdout:
            print(
                result.stdout.rstrip()
            )


def build_only(filename: str) -> int:
    try:
        context, result = (
            compile_current(
                filename
            )
        )
    except LocalTestError as exc:
        return fail(str(exc))

    _compile_screen(
        filename,
        context,
        result,
    )

    if not result.success:
        if result.stderr:
            print(
                result.stderr,
                file=sys.stderr,
            )
        return 1

    return 0


def _post_attempt(
    filename: str,
) -> bool:
    problem = control.current_problem(
        filename
    )
    state = (
        problem.get("state")
        if problem
        else None
    )
    return bool(
        state
        and state.solved_on
    )


def _test_bundle(
    context: ProblemContext | None,
) -> TestBundle | None:
    if context is None:
        return None

    return TEST_ASSETS.load(
        context.source,
        context.problem_id,
        include_candidates=True,
    )


def _visible_cases(
    bundle: TestBundle | None,
    context: ProblemContext | None,
    filename: str,
    *,
    suite: str,
):
    if bundle is None:
        return ()

    return TEST_ASSETS.visible_cases(
        bundle,
        mode=control.selection_mode(),
        activity=(
            context.role
            if context is not None
            else None
        ),
        post_attempt=_post_attempt(
            filename
        ),
        suite=suite,
    )


def _copy_text(
    text: str,
) -> tuple[bool, str]:
    commands = []

    if shutil.which("clip.exe"):
        commands.append(
            (["clip.exe"], "Windows 剪貼簿")
        )
    if shutil.which("wl-copy"):
        commands.append(
            (["wl-copy"], "Wayland 剪貼簿")
        )
    if shutil.which("xclip"):
        commands.append(
            (
                [
                    "xclip",
                    "-selection",
                    "clipboard",
                ],
                "X11 剪貼簿",
            )
        )
    if shutil.which("xsel"):
        commands.append(
            (
                [
                    "xsel",
                    "--clipboard",
                    "--input",
                ],
                "X11 剪貼簿",
            )
        )
    if shutil.which("pbcopy"):
        commands.append(
            (["pbcopy"], "macOS 剪貼簿")
        )

    for command, label in commands:
        try:
            result = subprocess.run(
                command,
                input=text,
                text=True,
                capture_output=True,
                check=False,
            )
        except OSError:
            continue

        if result.returncode == 0:
            return True, label

    return (
        False,
        "找不到可用的系統剪貼簿工具",
    )


def copy_current_code(
    filename: str,
) -> tuple[bool, str]:
    source = Path(filename).resolve()
    if not source.is_file():
        return False, "找不到目前程式碼檔案"

    try:
        text = source.read_text(
            encoding="utf-8"
        )
    except OSError as exc:
        return False, str(exc)

    ok, detail = _copy_text(text)
    if not ok:
        return False, detail

    return (
        True,
        f"已複製 {source.name} · {detail}",
    )


def _oj_url(
    context: ProblemContext | None,
    bundle: TestBundle | None,
) -> str | None:
    if (
        context is not None
        and context.canonical_url
    ):
        return context.canonical_url

    if bundle is not None and bundle.canonical_url:
        return bundle.canonical_url

    if context is not None:
        source = str(
            context.source or ""
        ).strip().casefold()
        problem_id = str(
            context.problem_id or ""
        ).strip().casefold()

        if (
            source in {
                "zerojudge",
                "zerojudge.tw",
            }
            and re.fullmatch(
                r"(?:[a-z]\d+|\d+)",
                problem_id,
                flags=re.I,
            )
        ):
            return (
                "https://zerojudge.tw/"
                "ShowProblem?problemid="
                f"{problem_id}"
            )

    return None


def _interactive_run(
    executable: Path,
) -> int:
    clear()
    heading("手動執行")
    print()
    print(
        f"{GRAY}"
        "目前沒有可直接判定結果的可信測資，"
        "以下改用標準輸入／輸出。"
        f"{RESET}"
    )
    print(rule())
    result = subprocess.run(
        [str(executable)],
        cwd=ROOT,
    )
    print(rule())
    if result.returncode == 0:
        print(
            f"{GREEN}✓ 程式正常結束{RESET}"
        )
    else:
        print(
            f"{RED}"
            f"✕ 程式結束碼 {result.returncode}"
            f"{RESET}"
        )
    return result.returncode


def _compile_warning_count(
    result: CompileResult,
) -> int:
    return sum(
        1
        for line in result.stderr.splitlines()
        if "warning:" in line
    )


def _case_display_name(
    result: CaseResult,
    *,
    index: int,
    context: ProblemContext | None,
    post_attempt: bool,
) -> str:
    case = result.case

    if case.provenance == "OFFICIAL":
        return case.name

    if (
        context is not None
        and context.role == "Core Independent"
        and not post_attempt
    ):
        return f"Local Case {index + 1}"

    return case.name


def _status_text(
    result: CaseResult,
) -> str:
    mark, _, label = STATUS_LABELS[
        result.status
    ]
    return (
        f"{mark} {label}"
        f" · {result.duration_ms} ms"
    )


def _result_color(
    result: CaseResult,
) -> str:
    return STATUS_LABELS[
        result.status
    ][1]


def _case_detail_lines(
    result: CaseResult,
    width: int,
    *,
    strict_pre_attempt: bool,
) -> list[str]:
    case = result.case
    result_lines = [
        "來源",
        (
            f"  {case.provenance}"
            f" · {case.trust}"
        ),
        "",
        "Input",
        *[
            "  " + line
            for line in wrap(
                case.input_text.rstrip()
                or "(空輸入)",
                max(8, width - 2),
            )[:7]
        ],
    ]

    if result.status == UNVERIFIED:
        result_lines.extend(
            [
                "",
                "Expected",
                "  尚未驗證；不顯示 AI / candidate 猜測值",
                "",
                f"{GRAY}此測資不影響 PASS / FAIL。{RESET}",
            ]
        )
        return result_lines

    if strict_pre_attempt and (
        case.provenance != "OFFICIAL"
    ):
        result_lines.extend(
            [
                "",
                "Expected / Actual",
                "  正式作答前隱藏",
            ]
        )
        return result_lines

    result_lines.extend(
        [
            "",
            "Expected",
            *[
                "  " + line
                for line in wrap(
                    (
                        case.expected_output
                        if case.expected_output
                        is not None
                        else "(未驗證)"
                    ),
                    max(8, width - 2),
                )[:6]
            ],
            "",
            "Actual",
            *[
                "  " + line
                for line in wrap(
                    result.actual_output
                    or "(無輸出)",
                    max(8, width - 2),
                )[:6]
            ],
        ]
    )

    if (
        result.status
        == WRONG_OUTPUT
        and case.expected_output
        is not None
    ):
        result_lines.extend(
            [
                "",
                "Difference",
                *[
                    "  " + line
                    for line in unified_diff(
                        case.expected_output,
                        result.actual_output,
                        max_lines=8,
                    )
                ],
            ]
        )

    if result.stderr:
        result_lines.extend(
            [
                "",
                "stderr",
                *[
                    "  " + line
                    for line in wrap(
                        result.stderr,
                        max(8, width - 2),
                    )[:4]
                ],
            ]
        )

    return result_lines



def _summary_badge(
    suite_result: SuiteResult,
) -> str:
    runnable = suite_result.runnable_count
    passed = suite_result.passed_count

    if runnable == 0:
        return status_badge(
            "沒有可判定測資",
            status="neutral",
        )
    if passed == runnable:
        return status_badge(
            f"本地測試 {passed}/{runnable} 通過",
            status="ok",
        )
    return status_badge(
        f"本地測試 {passed}/{runnable} 通過",
        status="error",
    )


def _test_center(
    filename: str,
    executable: Path,
    context: ProblemContext | None,
    bundle: TestBundle | None,
    initial: SuiteResult,
    compile_result: CompileResult,
) -> int:
    results = initial
    selected = (
        results.first_failure_index
        if results.first_failure_index
        is not None
        else 0
    )
    message = ""
    full_mode = False

    while True:
        clear()

        mode = control.selection_mode()
        mode_badge = (
            status_badge(
                "考試 · 防劇透",
                status="warn",
            )
            if mode == "exam"
            else status_badge(
                "練習",
                status="ok",
            )
        )
        suffix = (
            f"{mode_badge}  "
            + (
                f"{context.problem_id} · {context.title}"
                if context is not None
                else Path(filename).name
            )
        )
        heading(
            "測試中心",
            suffix=suffix,
        )
        print()

        width = terminal_width()
        warning_count = (
            _compile_warning_count(
                compile_result
            )
        )
        compile_line = (
            status_badge(
                "編譯成功",
                status="ok",
            )
            + f"  {compile_result.duration_ms} ms"
            + (
                f"  {YELLOW}· {warning_count} warnings{RESET}"
                if warning_count
                else ""
            )
        )
        print(
            fit(
                compile_line,
                width,
            )
        )

        if results.cases:
            summary_line = (
                _summary_badge(results)
                + (
                    f"  {GRAY}· Full Suite{RESET}"
                    if full_mode
                    else f"  {GRAY}· Fast Suite{RESET}"
                )
            )
            print(
                fit(
                    summary_line,
                    width,
                )
            )
        else:
            no_case_line = (
                status_badge(
                    "尚無可執行的可信測資",
                    status="neutral",
                )
                + f"  {GRAY}· Enter / I 手動執行{RESET}"
            )
            print(
                fit(
                    no_case_line,
                    width,
                )
            )

        inventory = TEST_ASSETS.inventory(
            bundle
        )
        for line in wrap(
            "測資資產  "
            f"官方 {inventory['official']}"
            f" · 已驗證 {inventory['verified']}"
            f" · Candidate {inventory['candidate']}",
            width,
        ):
            print(
                f"{GRAY}{line}{RESET}"
            )
        for line in wrap(
            "來源檔案  "
            f"{Path(filename).name}"
            " · 比較規則：忽略最後換行與行尾空白",
            width,
        ):
            print(
                f"{GRAY}{line}{RESET}"
            )
        print()

        if width >= 64:
            left, right = pane_widths(
                width,
                (42, 58),
                gap=3,
                min_width=28,
            )
        else:
            left = right = width

        list_lines = [
            f"{CYAN}{BOLD}"
            f"{pad('測資', left)}"
            f"{RESET}"
        ]
        post_attempt = _post_attempt(
            filename
        )

        for index, result in enumerate(
            results.cases
        ):
            mark, color, _ = (
                STATUS_LABELS[
                    result.status
                ]
            )
            prefix = (
                "›"
                if index == selected
                else " "
            )
            name = _case_display_name(
                result,
                index=index,
                context=context,
                post_attempt=post_attempt,
            )
            label = (
                f"{prefix} "
                f"{result.case.case_id} "
                f"{name}"
            )
            status = (
                f"{mark} "
                f"{result.duration_ms}ms"
            )
            available = max(
                8,
                left
                - len(status)
                - 2,
            )
            line = (
                fit(label, available)
                + " "
                + status
            )
            if index == selected:
                list_lines.append(
                    f"{CYAN}{BOLD}"
                    f"{fit(line, left)}"
                    f"{RESET}"
                )
            else:
                list_lines.append(
                    f"{color}"
                    f"{fit(line, left)}"
                    f"{RESET}"
                )

        strict = (
            mode == "exam"
            or (
                context is not None
                and context.role
                in {
                    "Transfer Challenge",
                    "Mock",
                }
            )
        ) and not post_attempt

        if results.cases:
            detail_result = (
                results.cases[selected]
            )
            detail_lines = [
                f"{CYAN}{BOLD}"
                "選中測資"
                f"{RESET}",
                (
                    f"{_result_color(detail_result)}"
                    f"{_status_text(detail_result)}"
                    f"{RESET}"
                ),
                "",
                *[
                    fit(line, right)
                    for line
                    in _case_detail_lines(
                        detail_result,
                        right,
                        strict_pre_attempt=strict,
                    )
                ],
            ]
        else:
            detail_lines = [
                f"{CYAN}{BOLD}"
                "執行資訊"
                f"{RESET}",
                "目前沒有可直接判定結果的可信測資。",
                "",
                "你仍可：",
                "  Enter / I 以標準輸入手動執行",
                "  C 複製剛剛實際編譯的 source",
                "  O 開啟正式 OJ（若有 canonical URL）",
            ]
            if inventory["candidate"]:
                detail_lines.extend(
                    [
                        "",
                        f"{YELLOW}"
                        f"另有 {inventory['candidate']} 組 Candidate；"
                        "未驗證前不作 PASS / FAIL。"
                        f"{RESET}",
                    ]
                )

        if width >= 64:
            frame_lines = render_columns(
                [
                    list_lines,
                    detail_lines,
                ],
                (left, right),
                gap=3,
            )
        else:
            frame_lines = [
                *list_lines,
                "",
                *detail_lines,
            ]

        for line in frame_lines[: max(
            12,
            terminal_height() - 14,
        )]:
            print(
                fit(
                    line,
                    width,
                )
            )

        if message:
            print()
            print(
                fit(
                    message,
                    width,
                )
            )

        oj_url = _oj_url(
            context,
            bundle,
        )

        commands = []
        if results.cases:
            commands.extend(
                [
                    ("↑↓", "選測資"),
                    ("R", "重跑"),
                ]
            )
        else:
            commands.append(
                ("Enter", "手動執行")
            )

        if bundle is not None:
            commands.append(
                ("T", "完整測試")
            )

        commands.extend(
            [
                ("I", "手動輸入"),
                ("C", "複製程式碼"),
            ]
        )
        if oj_url:
            commands.append(
                ("O", "開啟 OJ")
            )
        commands.append(
            ("Esc", "關閉")
        )
        command_bar(commands)

        key = control.read_key()

        if key == "UP" and results.cases:
            selected = (
                selected - 1
            ) % len(results.cases)
            message = ""
            continue

        if key == "DOWN" and results.cases:
            selected = (
                selected + 1
            ) % len(results.cases)
            message = ""
            continue

        if key in {"r", "R"} and results.cases:
            case_result = run_case(
                executable,
                results.cases[selected].case,
                root=ROOT,
            )
            mutable = list(
                results.cases
            )
            mutable[selected] = case_result
            results = SuiteResult(
                tuple(mutable)
            )
            message = (
                f"{_result_color(case_result)}"
                f"已重跑 {case_result.case.case_id} · "
                f"{_status_text(case_result)}"
                f"{RESET}"
            )
            continue

        if (
            key in {"t", "T"}
            and bundle is not None
        ):
            cases = _visible_cases(
                bundle,
                context,
                filename,
                suite=SUITE_FULL,
            )
            results = run_suite(
                executable,
                cases,
                root=ROOT,
            )
            full_mode = True
            selected = (
                results.first_failure_index
                if results.first_failure_index
                is not None
                else 0
            )
            runnable = (
                results.runnable_count
            )
            message = (
                ""
                if runnable
                else (
                    f"{YELLOW}"
                    "完整測試目前也沒有可判定的 verified cases。"
                    f"{RESET}"
                )
            )
            continue

        if (
            key == "ENTER"
            and not results.cases
        ) or key in {"i", "I"}:
            _interactive_run(
                executable
            )
            message = (
                f"{GRAY}"
                "已完成一次手動執行"
                f"{RESET}"
            )
            continue

        if key in {"c", "C"}:
            ok, detail = copy_current_code(
                filename
            )
            message = (
                f"{GREEN}✓ {detail}{RESET}"
                if ok
                else f"{RED}✕ {detail}{RESET}"
            )
            continue

        if (
            key in {"o", "O"}
            and oj_url
        ):
            webbrowser.open(
                oj_url
            )
            local_state = (
                "本地測試已通過；"
                if results.all_passed
                else "本地測試尚未全數通過；"
            )
            message = (
                f"{YELLOW if not results.all_passed else GREEN}"
                "✓ 已開啟正式 OJ；"
                f"{local_state}"
                "OJ verdict 才是正式判定"
                f"{RESET}"
            )
            continue

        if key in {
            "ESC",
            "q",
            "Q",
        }:
            # Closing the Test Center is a UI action, not a verdict. A failed
            # local suite still returns non-zero so VS Code clearly preserves
            # the failure state; no-test/manual-only sessions close cleanly.
            if not results.cases:
                return 0
            return (
                0
                if results.all_passed
                else 1
            )



def build_and_run(filename: str) -> int:
    try:
        context, compile_result = (
            compile_current(
                filename
            )
        )
    except LocalTestError as exc:
        return fail(str(exc))

    if not compile_result.success:
        _compile_screen(
            filename,
            context,
            compile_result,
        )
        if compile_result.stderr:
            print(
                compile_result.stderr,
                file=sys.stderr,
            )
        return 1

    executable = (
        compile_result.executable
    )
    assert executable is not None

    bundle = _test_bundle(
        context
    )

    if bundle is None:
        return _test_center(
            filename,
            executable,
            context,
            None,
            SuiteResult(()),
            compile_result,
        )

    fast_cases = _visible_cases(
        bundle,
        context,
        filename,
        suite=SUITE_FAST,
    )

    results = run_suite(
        executable,
        fast_cases,
        root=ROOT,
    )

    return _test_center(
        filename,
        executable,
        context,
        bundle,
        results,
        compile_result,
    )



def today_view() -> int:
    clear()
    heading("今日學習")
    print()

    snapshot = (
        control.adaptive_today_snapshot()
    )
    plan = snapshot["plan"]

    print(
        f"可用時間  {snapshot['capacity_minutes']} 分"
    )
    print(
        f"複習      {plan.selected_minutes}/"
        f"{plan.budget_minutes} 分"
    )

    protected = max(
        0,
        snapshot["capacity_minutes"]
        - plan.budget_minutes,
    )
    print(
        f"新學習    ≥ {protected} 分"
    )
    print()
    print(
        f"{GRAY}"
        "請使用 Ctrl+Alt+A 開啟 Control Center；"
        "這個非互動 Task 不建立第二套 Today 流程。"
        f"{RESET}"
    )
    return 0


def record_current(
    action: str,
    filename: str,
    choice: str,
) -> int:
    _ = (
        action,
        filename,
        choice,
    )
    return fail(
        "已停用舊式 Finish / Review Task；"
        "請使用 Ctrl+Alt+A → Control Center。"
    )


def create_note(filename: str) -> int:
    context = problem_context(
        filename
    )
    pid = (
        context.problem_id
        if context is not None
        else problem_id(filename)
    )

    clear()
    heading("建立筆記")
    print(
        f"題號  {pid}"
    )

    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(
            buf
        ):
            result = core.note_cmd(pid)
    except SystemExit as exc:
        return fail(
            "建立筆記失敗。",
            int(exc.code or 1),
        )

    if result != 0:
        return fail(
            "建立筆記失敗。",
            result,
        )

    print(
        f"{GREEN}✓ 已建立筆記{RESET}"
    )
    return 0


def precommit() -> int:
    clear()
    heading("提交前檢查")
    print()

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        validate_code = core.validate()

    validation = buf.getvalue()
    match = re.search(
        r"錯誤[：:]\s*(\d+).*警告[：:]\s*(\d+)",
        validation,
    )

    if match:
        errors, warnings = (
            match.groups()
        )
        mark = (
            "✓"
            if validate_code == 0
            else "✕"
        )
        print(
            f"資料  {mark} "
            f"{errors} 錯誤 · "
            f"{warnings} 警告"
        )
    else:
        print(
            f"資料  "
            f"{'✓' if validate_code == 0 else '✕'}"
        )

    diff = subprocess.run(
        [
            "git",
            "diff",
            "--check",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    print(
        "格式  "
        + (
            "✓"
            if diff.returncode == 0
            else "✕"
        )
    )

    status = subprocess.run(
        [
            "git",
            "status",
            "--porcelain",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    changes = [
        line
        for line
        in status.stdout.splitlines()
        if line.strip()
    ]
    print(
        f"Git   {len(changes)} 個變更"
    )
    print(rule())

    if (
        validate_code == 0
        and diff.returncode == 0
    ):
        print(
            f"{GREEN}"
            "✓ 可以進入 commit review"
            f"{RESET}"
        )
        return 0

    print(
        f"{RED}"
        "✕ 尚不建議提交"
        f"{RESET}"
    )
    return 1


def main() -> int:
    if len(sys.argv) < 2:
        return fail(
            "缺少 Task 動作。"
        )

    action = sys.argv[1]

    if action == "today":
        return today_view()

    if action == "build":
        if len(sys.argv) != 3:
            return fail(
                "缺少目前檔案。"
            )
        return build_only(
            sys.argv[2]
        )

    if action == "build-run":
        if len(sys.argv) != 3:
            return fail(
                "缺少目前檔案。"
            )
        return build_and_run(
            sys.argv[2]
        )

    if action in {
        "finish",
        "review",
    }:
        if len(sys.argv) != 4:
            return fail(
                "缺少題目或 Recall。"
            )
        return record_current(
            action,
            sys.argv[2],
            sys.argv[3],
        )

    if action == "note":
        if len(sys.argv) != 3:
            return fail(
                "缺少目前檔案。"
            )
        return create_note(
            sys.argv[2]
        )

    if action == "precommit":
        return precommit()

    return fail(
        f"未知 Task：{action}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
