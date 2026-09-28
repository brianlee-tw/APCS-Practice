#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path

PROBLEM_FIELDS = (
    "problem_id",
    "title",
    "source",
    "difficulty",
    "tags",
)

SOLUTION_FIELDS = (
    "problem_id",
    "path",
    "language",
    "complexity",
)

SUFFIX_LANGUAGE = {
    ".cpp": "cpp",
    ".py": "python",
}

EXCLUDE = {
    ".git",
    ".github",
    ".vscode",
    "tools",
    "tests",
    "docs",
    "data",
    "notes",
    "build",
    "Build",
    "__pycache__",
}

META_RE = re.compile(
    r"^(?://|#)\s*APCS\s+([^:]+):\s*(.*?)\s*$",
    re.I,
)

FILENAME_ID_RE = re.compile(
    r"^([A-Za-z]\d+|\d+)(?:_|$)"
)

TITLE_ID_RE = re.compile(
    r"^\s*([A-Za-z]\d+|\d+)\s*[.．:：-]\s*(.*)$"
)


@dataclass(frozen=True)
class CatalogIssue:
    code: str
    path: str
    detail: str


def _norm_id(value: str) -> str:
    return value.strip().lower()


def problem_id_from_path(path: Path) -> str:
    match = FILENAME_ID_RE.match(path.stem)
    return _norm_id(match.group(1)) if match else ""


def parse_legacy_metadata(path: Path) -> dict[str, str]:
    lines = path.read_text(
        encoding="utf-8",
        errors="ignore",
    ).splitlines()[:32]

    metadata: dict[str, str] = {}

    for line in lines:
        match = META_RE.match(line)
        if not match:
            continue

        key = match.group(1).strip().lower()
        value = match.group(2).strip()
        metadata[key] = value

    return metadata


def split_title(value: str) -> tuple[str, str]:
    value = value.strip()
    match = TITLE_ID_RE.match(value)

    if not match:
        return "", value

    return (
        _norm_id(match.group(1)),
        match.group(2).strip(),
    )


def iter_solution_files(root: Path):
    for path in root.rglob("*"):
        if (
            not path.is_file()
            or path.suffix.lower() not in SUFFIX_LANGUAGE
        ):
            continue

        relative = path.relative_to(root)

        if any(
            part in EXCLUDE or part == ".cph"
            for part in relative.parts[:-1]
        ):
            continue

        if "tempCodeRunner" in path.name:
            continue

        yield path


def _merge_problem_value(
    problem: dict[str, str],
    field: str,
    incoming: str,
    pid: str,
    rel_path: str,
    issues: list[CatalogIssue],
) -> None:
    incoming = incoming.strip()
    current = problem[field].strip()

    if not incoming:
        return

    if not current:
        problem[field] = incoming
        return

    if current != incoming:
        issues.append(
            CatalogIssue(
                "PROBLEM_METADATA_CONFLICT",
                rel_path,
                (
                    f"{pid}: {field} conflict "
                    f"{current!r} != {incoming!r}"
                ),
            )
        )


def scan_repository(
    root: Path,
) -> tuple[
    list[dict[str, str]],
    list[dict[str, str]],
    list[CatalogIssue],
]:
    root = root.resolve()

    problems_by_id: dict[str, dict[str, str]] = {}
    solutions: list[dict[str, str]] = []
    issues: list[CatalogIssue] = []

    for path in sorted(iter_solution_files(root)):
        rel_path = path.relative_to(root).as_posix()
        pid = problem_id_from_path(path)

        if not pid:
            issues.append(
                CatalogIssue(
                    "UNRESOLVED_PROBLEM_ID",
                    rel_path,
                    "filename must start with a letter+digits or numeric ID",
                )
            )
            continue

        metadata = parse_legacy_metadata(path)

        title_id, title = split_title(
            metadata.get("title", "")
        )

        if title_id and title_id != pid:
            issues.append(
                CatalogIssue(
                    "TITLE_ID_MISMATCH",
                    rel_path,
                    f"filename ID={pid}; APCS Title ID={title_id}",
                )
            )

        problem = problems_by_id.setdefault(
            pid,
            {
                "problem_id": pid,
                "title": "",
                "source": "",
                "difficulty": "",
                "tags": "",
            },
        )

        values = {
            "title": title,
            "source": metadata.get("source", ""),
            "difficulty": metadata.get("difficulty", ""),
            "tags": metadata.get("tag", ""),
        }

        for field, value in values.items():
            _merge_problem_value(
                problem,
                field,
                value,
                pid,
                rel_path,
                issues,
            )

        solutions.append(
            {
                "problem_id": pid,
                "path": rel_path,
                "language": SUFFIX_LANGUAGE[path.suffix.lower()],
                "complexity": metadata.get("complexity", "").strip(),
            }
        )

    problems = [
        problems_by_id[pid]
        for pid in sorted(problems_by_id)
    ]

    solutions.sort(
        key=lambda row: (
            row["problem_id"],
            row["path"],
        )
    )

    issues.sort(
        key=lambda issue: (
            issue.code,
            issue.path,
            issue.detail,
        )
    )

    return problems, solutions, issues


def write_csv(
    path: Path,
    fieldnames: tuple[str, ...],
    rows: list[dict[str, str]],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def write_preview(
    root: Path,
    output_dir: Path,
) -> tuple[int, int, int]:
    problems, solutions, issues = scan_repository(root)

    write_csv(
        output_dir / "problems.csv",
        PROBLEM_FIELDS,
        problems,
    )
    write_csv(
        output_dir / "solutions.csv",
        SOLUTION_FIELDS,
        solutions,
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    with (output_dir / "issues.txt").open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        for issue in issues:
            handle.write(
                f"{issue.code}\t"
                f"{issue.path}\t"
                f"{issue.detail}\n"
            )

    return (
        len(problems),
        len(solutions),
        len(issues),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="APCS v2.2 Problem Catalog scanner"
    )

    parser.add_argument(
        "--root",
        type=Path,
        default=Path("."),
    )

    parser.add_argument(
        "--preview-dir",
        type=Path,
    )

    args = parser.parse_args()

    problems, solutions, issues = scan_repository(
        args.root
    )

    print(f"Problems : {len(problems)}")
    print(f"Solutions: {len(solutions)}")
    print(f"Issues   : {len(issues)}")

    for issue in issues:
        print(
            f"{issue.code}: "
            f"{issue.path}: "
            f"{issue.detail}"
        )

    if args.preview_dir:
        write_preview(
            args.root,
            args.preview_dir,
        )
        print(
            "Preview  : "
            f"{args.preview_dir.resolve()}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
