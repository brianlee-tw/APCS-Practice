#!/usr/bin/env python3
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

try:
    from .tag_taxonomy import normalize_tags
except ImportError:
    from tag_taxonomy import normalize_tags


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


    @staticmethod
    def _clean_tags(value: str) -> str:
        return normalize_tags(value)

    @classmethod
    def _problem_row(cls, item: ProblemMeta) -> dict[str, str]:
        pid = item.problem_id.strip().lower()

        if not pid:
            raise CatalogError("problem_id cannot be empty")

        difficulty = item.difficulty.strip()

        if difficulty:
            try:
                level = int(difficulty)
            except ValueError as exc:
                raise CatalogError(
                    f"{pid}: difficulty must be 1-5"
                ) from exc

            if level not in {1, 2, 3, 4, 5}:
                raise CatalogError(
                    f"{pid}: difficulty must be 1-5"
                )

            difficulty = str(level)

        return {
            "problem_id": pid,
            "title": item.title.strip(),
            "source": item.source.strip(),
            "difficulty": difficulty,
            "tags": cls._clean_tags(item.tags),
        }

    @staticmethod
    def _solution_row(item: SolutionMeta) -> dict[str, str]:
        pid = item.problem_id.strip().lower()
        path = item.path.strip().replace("\\", "/")
        language = item.language.strip().lower()

        if not pid:
            raise CatalogError("solution problem_id cannot be empty")

        if not path:
            raise CatalogError(
                f"{pid}: solution path cannot be empty"
            )

        candidate = Path(path)

        if candidate.is_absolute() or ".." in candidate.parts:
            raise CatalogError(
                f"{pid}: solution path must be repository-relative"
            )

        if language not in {"cpp", "python"}:
            raise CatalogError(
                f"{pid}: unsupported language {language!r}"
            )

        return {
            "problem_id": pid,
            "path": path,
            "language": language,
            "complexity": item.complexity.strip(),
        }

    @staticmethod
    def _write_rows(
        path: Path,
        fields: list[str],
        rows: list[dict[str, str]],
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(path.name + ".tmp")

        try:
            with temp.open(
                "w",
                encoding="utf-8",
                newline="",
            ) as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=fields,
                    lineterminator="\n",
                )
                writer.writeheader()
                writer.writerows(rows)

            temp.replace(path)

        finally:
            if temp.exists():
                temp.unlink()

    def save_problems(
        self,
        problems: list[ProblemMeta],
    ) -> None:
        rows = [
            self._problem_row(item)
            for item in problems
        ]

        ids = [row["problem_id"] for row in rows]

        if len(ids) != len(set(ids)):
            raise CatalogError(
                "problems.csv: duplicate problem_id"
            )

        rows.sort(key=lambda row: row["problem_id"])
        self._write_rows(
            self.problems_path,
            PROBLEM_FIELDS,
            rows,
        )

    def save_solutions(
        self,
        solutions: list[SolutionMeta],
    ) -> None:
        rows = [
            self._solution_row(item)
            for item in solutions
        ]

        paths = [row["path"] for row in rows]

        if len(paths) != len(set(paths)):
            raise CatalogError(
                "solutions.csv: duplicate path"
            )

        rows.sort(
            key=lambda row: (
                row["problem_id"],
                row["path"],
            )
        )
        self._write_rows(
            self.solutions_path,
            SOLUTION_FIELDS,
            rows,
        )

    def create_problem_with_solution(
        self,
        problem: ProblemMeta,
        solution: SolutionMeta,
    ) -> None:
        problem_row = self._problem_row(problem)
        solution_row = self._solution_row(solution)

        if (
            problem_row["problem_id"]
            != solution_row["problem_id"]
        ):
            raise CatalogError(
                "problem and solution problem_id mismatch"
            )

        problems = self.load_problems()
        solutions = self.load_solutions()
        pid = problem_row["problem_id"]

        if pid in problems:
            raise CatalogError(
                f"problem already exists: {pid}"
            )

        if any(
            item.path == solution_row["path"]
            for item in solutions
        ):
            raise CatalogError(
                f"solution path already exists: "
                f"{solution_row['path']}"
            )

        new_problem = ProblemMeta(**problem_row)
        new_solution = SolutionMeta(**solution_row)

        self.save_problems(
            [*problems.values(), new_problem]
        )
        self.save_solutions(
            [*solutions, new_solution]
        )

    def add_solution(
        self,
        solution: SolutionMeta,
    ) -> None:
        row = self._solution_row(solution)
        problems = self.load_problems()
        solutions = self.load_solutions()
        pid = row["problem_id"]

        if pid not in problems:
            raise CatalogError(
                f"problem not found: {pid}"
            )

        if any(
            item.path == row["path"]
            for item in solutions
        ):
            raise CatalogError(
                f"solution path already exists: "
                f"{row['path']}"
            )

        self.save_solutions(
            [*solutions, SolutionMeta(**row)]
        )

    def update_problem(
        self,
        problem: ProblemMeta,
    ) -> None:
        row = self._problem_row(problem)
        problems = self.load_problems()
        pid = row["problem_id"]

        if pid not in problems:
            raise CatalogError(
                f"problem not found: {pid}"
            )

        problems[pid] = ProblemMeta(**row)
        self.save_problems(list(problems.values()))

    def update_solution(
        self,
        solution: SolutionMeta,
    ) -> None:
        row = self._solution_row(solution)
        solutions = self.load_solutions()
        found = False
        updated: list[SolutionMeta] = []

        for item in solutions:
            if item.path == row["path"]:
                if item.problem_id != row["problem_id"]:
                    raise CatalogError(
                        "solution problem_id cannot be changed"
                    )

                updated.append(SolutionMeta(**row))
                found = True
            else:
                updated.append(item)

        if not found:
            raise CatalogError(
                f"solution not found: {row['path']}"
            )

        self.save_solutions(updated)
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
