#!/usr/bin/env python3
from __future__ import annotations

import difflib
import os
import resource
import shutil
import signal
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

try:
    from .test_assets import (
        TestCase,
        same_output,
    )
except ImportError:
    from test_assets import (
        TestCase,
        same_output,
    )


PASS = "PASS"
WRONG_OUTPUT = "WRONG_OUTPUT"
RUNTIME_ERROR = "RUNTIME_ERROR"
TIMEOUT = "TIMEOUT"
OUTPUT_LIMIT = "OUTPUT_LIMIT"
UNVERIFIED = "UNVERIFIED"


class LocalTestError(RuntimeError):
    pass


@dataclass(frozen=True)
class CompileResult:
    success: bool
    executable: Path | None
    duration_ms: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class CaseResult:
    case: TestCase
    status: str
    duration_ms: int
    actual_output: str
    stderr: str
    returncode: int | None

    @property
    def passed(self) -> bool:
        return self.status == PASS


@dataclass(frozen=True)
class SuiteResult:
    cases: tuple[CaseResult, ...]

    @property
    def runnable_count(self) -> int:
        return sum(
            1
            for result in self.cases
            if result.status != UNVERIFIED
        )

    @property
    def passed_count(self) -> int:
        return sum(
            1
            for result in self.cases
            if result.status == PASS
        )

    @property
    def all_passed(self) -> bool:
        return (
            self.runnable_count > 0
            and self.passed_count
            == self.runnable_count
        )

    @property
    def first_failure_index(self) -> int | None:
        for index, result in enumerate(
            self.cases
        ):
            if result.status not in {
                PASS,
                UNVERIFIED,
            }:
                return index
        return None


def _preexec_output_limit(
    output_limit_bytes: int,
):
    def apply() -> None:
        try:
            resource.setrlimit(
                resource.RLIMIT_FSIZE,
                (
                    output_limit_bytes,
                    output_limit_bytes,
                ),
            )
        except (
            ValueError,
            OSError,
        ):
            pass

    return apply


def compile_cpp(
    source: Path,
    executable: Path,
    *,
    root: Path,
) -> CompileResult:
    source = Path(source).resolve()
    executable = Path(executable).resolve()

    if source.suffix.casefold() != ".cpp":
        raise LocalTestError(
            "目前檔案不是 C++（.cpp）。"
        )
    if not source.is_file():
        raise LocalTestError(
            "找不到目前 C++ 檔案。"
        )

    compiler = shutil.which("g++")
    if compiler is None:
        raise LocalTestError(
            "找不到 g++。"
        )

    executable.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    started = time.perf_counter()
    result = subprocess.run(
        [
            compiler,
            "-std=c++17",
            "-O2",
            "-Wall",
            "-Wextra",
            str(source),
            "-o",
            str(executable),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    duration_ms = int(
        round(
            (
                time.perf_counter()
                - started
            )
            * 1000
        )
    )

    return CompileResult(
        success=result.returncode == 0,
        executable=(
            executable
            if result.returncode == 0
            else None
        ),
        duration_ms=duration_ms,
        stdout=result.stdout or "",
        stderr=result.stderr or "",
    )


def run_case(
    executable: Path,
    case: TestCase,
    *,
    root: Path,
    timeout_seconds: float = 2.0,
    output_limit_bytes: int = 1_000_000,
) -> CaseResult:
    if not case.runnable:
        return CaseResult(
            case=case,
            status=UNVERIFIED,
            duration_ms=0,
            actual_output="",
            stderr="",
            returncode=None,
        )

    started = time.perf_counter()

    with tempfile.TemporaryDirectory() as temp:
        temp_dir = Path(temp)
        stdout_path = temp_dir / "stdout.txt"
        stderr_path = temp_dir / "stderr.txt"

        with (
            stdout_path.open("wb") as stdout_handle,
            stderr_path.open("wb") as stderr_handle,
        ):
            process = subprocess.Popen(
                [str(executable)],
                cwd=root,
                stdin=subprocess.PIPE,
                stdout=stdout_handle,
                stderr=stderr_handle,
                preexec_fn=_preexec_output_limit(
                    output_limit_bytes
                ),
            )
            try:
                process.communicate(
                    input=case.input_text.encode(
                        "utf-8"
                    ),
                    timeout=timeout_seconds,
                )
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                duration_ms = int(
                    round(
                        (
                            time.perf_counter()
                            - started
                        )
                        * 1000
                    )
                )
                return CaseResult(
                    case=case,
                    status=TIMEOUT,
                    duration_ms=duration_ms,
                    actual_output="",
                    stderr="",
                    returncode=None,
                )

        duration_ms = int(
            round(
                (
                    time.perf_counter()
                    - started
                )
                * 1000
            )
        )

        stdout_bytes = stdout_path.read_bytes()
        stderr_bytes = stderr_path.read_bytes()

        actual = stdout_bytes.decode(
            "utf-8",
            errors="replace",
        )
        stderr = stderr_bytes.decode(
            "utf-8",
            errors="replace",
        )

        if (
            len(stdout_bytes)
            >= output_limit_bytes
            or process.returncode
            in {
                -getattr(
                    signal,
                    "SIGXFSZ",
                    25,
                ),
            }
        ):
            status = OUTPUT_LIMIT
        elif process.returncode != 0:
            status = RUNTIME_ERROR
        elif same_output(
            actual,
            case.expected_output,
        ):
            status = PASS
        else:
            status = WRONG_OUTPUT

        return CaseResult(
            case=case,
            status=status,
            duration_ms=duration_ms,
            actual_output=actual,
            stderr=stderr,
            returncode=process.returncode,
        )


def run_suite(
    executable: Path,
    cases: tuple[TestCase, ...],
    *,
    root: Path,
    timeout_seconds: float = 2.0,
    output_limit_bytes: int = 1_000_000,
) -> SuiteResult:
    return SuiteResult(
        cases=tuple(
            run_case(
                executable,
                case,
                root=root,
                timeout_seconds=timeout_seconds,
                output_limit_bytes=output_limit_bytes,
            )
            for case in cases
        )
    )


def unified_diff(
    expected: str,
    actual: str,
    *,
    max_lines: int = 16,
) -> list[str]:
    lines = list(
        difflib.unified_diff(
            expected.splitlines(),
            actual.splitlines(),
            fromfile="Expected",
            tofile="Actual",
            lineterm="",
            n=2,
        )
    )
    if len(lines) > max_lines:
        return [
            *lines[:max_lines],
            f"…另有 {len(lines) - max_lines} 行差異",
        ]
    return lines
