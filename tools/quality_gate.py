#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

KNOWN_WARNINGS = (
    ROOT
    / ".github"
    / "apcs-known-warnings.txt"
)


def extract_warnings(
    output: str,
) -> list[str]:
    warnings = []

    for line in output.splitlines():
        stripped = line.strip()

        for prefix in (
            "警告：",
            "警告:",
            "Warning:",
            "Warnings:",
        ):
            if stripped.startswith(prefix):
                warning = stripped[
                    len(prefix):
                ].strip()

                if warning:
                    warnings.append(
                        warning
                    )

                break

    return warnings


def load_known_warnings(
    path: Path = KNOWN_WARNINGS,
) -> list[str]:
    if not path.is_file():
        raise RuntimeError(
            f"known-warning baseline missing: {path}"
        )

    return [
        line.strip()
        for line in path.read_text(
            encoding="utf-8"
        ).splitlines()
        if (
            line.strip()
            and not line.lstrip().startswith("#")
        )
    ]


def compare_warning_multiset(
    current: list[str],
    known: list[str],
) -> tuple[list[str], list[str]]:
    current_counter = Counter(
        current
    )
    known_counter = Counter(
        known
    )

    unexpected_counter = (
        current_counter
        - known_counter
    )

    resolved_counter = (
        known_counter
        - current_counter
    )

    unexpected = list(
        unexpected_counter.elements()
    )
    resolved = list(
        resolved_counter.elements()
    )

    return unexpected, resolved


def run(
    args: list[str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def run_tests() -> bool:
    print(
        "QUALITY · full regression"
    )

    result = run(
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-q",
        ]
    )

    if result.stdout:
        print(
            result.stdout.rstrip()
        )

    if result.stderr:
        print(
            result.stderr.rstrip()
        )

    if result.returncode != 0:
        print(
            "FAIL: regression tests"
        )
        return False

    print(
        "PASS: regression tests"
    )
    return True


def run_validation() -> bool:
    print(
        "QUALITY · validation / warning budget"
    )

    result = run(
        [
            sys.executable,
            "tools/apcs.py",
            "validate",
        ]
    )

    output = (
        result.stdout
        + result.stderr
    )

    if result.stdout:
        print(
            result.stdout.rstrip()
        )

    if result.returncode != 0:
        print(
            "FAIL: APCS validation errors"
        )
        return False

    current = extract_warnings(
        output
    )

    try:
        known = load_known_warnings()
    except RuntimeError as exc:
        print(
            f"FAIL: {exc}"
        )
        return False

    unexpected, resolved = (
        compare_warning_multiset(
            current,
            known,
        )
    )

    if unexpected:
        print()
        print(
            "FAIL: new/unbudgeted warnings:"
        )

        for warning in unexpected:
            print(
                f"  + {warning}"
            )

        return False

    print()
    print(
        f"PASS: {len(current)} current warning(s) "
        f"within {len(known)} known-warning budget"
    )

    if resolved:
        print(
            f"INFO: {len(resolved)} known warning(s) "
            "are currently resolved"
        )

        for warning in resolved:
            print(
                f"  - {warning}"
            )

    return True


def run_diff_checks() -> bool:
    print(
        "QUALITY · git diff --check"
    )

    commands = [
        [
            "git",
            "diff",
            "--check",
        ],
        [
            "git",
            "diff",
            "--cached",
            "--check",
        ],
    ]

    for command in commands:
        result = run(
            command
        )

        if result.returncode != 0:
            output = (
                result.stdout
                or result.stderr
            )

            if output:
                print(
                    output.rstrip()
                )

            print(
                "FAIL: whitespace check"
            )
            return False

    print(
        "PASS: whitespace checks"
    )
    return True


def quality_gate(
    *,
    validate_only: bool = False,
) -> int:
    if not validate_only:
        if not run_tests():
            return 1

        if not run_diff_checks():
            return 1

    if not run_validation():
        return 1

    print()
    print(
        "QUALITY GATE: PASS"
    )
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "APCS local/CI quality gate"
        )
    )

    parser.add_argument(
        "--validate-only",
        action="store_true",
        help=(
            "Skip regression tests and Git diff checks; "
            "used after CI already ran tests."
        ),
    )

    args = parser.parse_args(
        argv
    )

    return quality_gate(
        validate_only=args.validate_only,
    )


if __name__ == "__main__":
    raise SystemExit(main())
