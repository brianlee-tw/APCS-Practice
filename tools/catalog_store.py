#!/usr/bin/env python3
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


PROBLEM_FIELDS = [
    "problem_id",
    "title",
    "source",
    "difficulty",
    "tags",
]

SOLUTION_FIELDS = [
    "problem_id",
    "path",
    "language",
    "complexity",
]


class CatalogError(ValueError):
    pass


@dataclass(frozen=True)
class ProblemMeta:
    problem_id: str
    title: str = ""
    source: str = ""
    difficulty: str = ""
    tags: str = ""

    @property
    def tag_list(self) -> list[str]:
        return [
            item.strip()
            for item in self.tags.split(",")
            if item.strip()
        ]


@dataclass(frozen=True)
class SolutionMeta:
    problem_id: str
    path: str
    language: str
    complexity: str = ""


class CatalogStore:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.problems_path = self.data_dir / "problems.csv"
        self.solutions_path = self.data_dir / "solutions.csv"

    @staticmethod
    def _read_rows(path: Path, fields: list[str]) -> list[dict[str, str]]:
        if not path.exists():
            raise CatalogError(f"catalog file missing: {path}")

        with path.open(
            encoding="utf-8",
            newline="",
        ) as handle:
            reader = csv.DictReader(handle)

            if reader.fieldnames != fields:
                raise CatalogError(
                    f"{path.name}: schema mismatch; "
                    f"expected {fields}, got {reader.fieldnames}"
                )

            return [
                {
                    key: (value or "").strip()
                    for key, value in row.items()
                }
                for row in reader
            ]

    def load_problems(self) -> dict[str, ProblemMeta]:
        rows = self._read_rows(
            self.problems_path,
            PROBLEM_FIELDS,
        )

        result: dict[str, ProblemMeta] = {}

        for row in rows:
            pid = row["problem_id"].lower()

            if not pid:
                raise CatalogError(
                    "problems.csv: empty problem_id"
                )

            if pid in result:
                raise CatalogError(
                    f"problems.csv: duplicate problem_id {pid}"
                )

            result[pid] = ProblemMeta(
                problem_id=pid,
                title=row["title"],
                source=row["source"],
                difficulty=row["difficulty"],
                tags=row["tags"],
            )

        return result

    def load_solutions(self) -> list[SolutionMeta]:
        rows = self._read_rows(
            self.solutions_path,
            SOLUTION_FIELDS,
        )

        seen_paths: set[str] = set()
        result: list[SolutionMeta] = []

        for row in rows:
            pid = row["problem_id"].lower()
            path = row["path"]

            if not pid:
                raise CatalogError(
                    "solutions.csv: empty problem_id"
                )

            if not path:
                raise CatalogError(
                    f"solutions.csv: empty path for {pid}"
                )

            if path in seen_paths:
                raise CatalogError(
                    f"solutions.csv: duplicate path {path}"
                )

            seen_paths.add(path)

            result.append(
                SolutionMeta(
                    problem_id=pid,
                    path=path,
                    language=row["language"],
                    complexity=row["complexity"],
                )
            )

        return result

    def validate(
        self,
        root: Path | None = None,
    ) -> list[str]:
        problems = self.load_problems()
        solutions = self.load_solutions()
        errors: list[str] = []

        for solution in solutions:
            if solution.problem_id not in problems:
                errors.append(
                    f"{solution.path}: unknown problem_id "
                    f"{solution.problem_id}"
                )

            if root is not None:
                target = Path(root) / solution.path

                if not target.is_file():
                    errors.append(
                        f"{solution.path}: solution file missing"
                    )

        for pid in problems:
            if not any(
                solution.problem_id == pid
                for solution in solutions
            ):
                errors.append(
                    f"{pid}: no solution registered"
                )

        return errors
