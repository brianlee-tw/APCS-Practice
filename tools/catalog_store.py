#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

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


PROBLEM_ID_RE = re.compile(
    r"^(?:[A-Za-z]\d+|\d+)$"
)

LANGUAGE_SUFFIX = {
    "cpp": ".cpp",
    "python": ".py",
}

WINDOWS_ABS_RE = re.compile(
    r"^[A-Za-z]:/"
)


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

    def load_problems(
        self,
    ) -> dict[str, ProblemMeta]:
        rows = self._read_rows(
            self.problems_path,
            PROBLEM_FIELDS,
        )

        result: dict[str, ProblemMeta] = {}

        for row in rows:
            pid = self._clean_problem_id(
                row["problem_id"]
            )
            difficulty = self._clean_difficulty(
                pid,
                row["difficulty"],
            )

            if pid in result:
                raise CatalogError(
                    f"problems.csv: duplicate problem_id {pid}"
                )

            result[pid] = ProblemMeta(
                problem_id=pid,
                title=row["title"],
                source=row["source"],
                difficulty=difficulty,
                tags=row["tags"],
            )

        return result

    def load_solutions(
        self,
    ) -> list[SolutionMeta]:
        rows = self._read_rows(
            self.solutions_path,
            SOLUTION_FIELDS,
        )

        seen_paths: set[str] = set()
        result: list[SolutionMeta] = []

        for row in rows:
            pid = self._clean_problem_id(
                row["problem_id"]
            )
            path = self._clean_solution_path(
                pid,
                row["path"],
            )
            language = self._clean_language(
                pid,
                row["language"],
            )

            self._validate_language_suffix(
                pid,
                path,
                language,
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
                    language=language,
                    complexity=row["complexity"],
                )
            )

        return result


    @staticmethod
    def _clean_problem_id(
        value: str,
    ) -> str:
        pid = str(value).strip().lower()

        if not PROBLEM_ID_RE.fullmatch(pid):
            raise CatalogError(
                f"invalid problem_id: {value!r}"
            )

        return pid

    @staticmethod
    def _clean_difficulty(
        pid: str,
        value: str,
    ) -> str:
        difficulty = str(value).strip()

        if not difficulty:
            return ""

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

        return str(level)

    @staticmethod
    def _clean_tags(value: str) -> str:
        return normalize_tags(value)

    @staticmethod
    def _clean_solution_path(
        pid: str,
        value: str,
    ) -> str:
        path = str(value).strip().replace(
            "\\",
            "/",
        )

        if not path:
            raise CatalogError(
                f"{pid}: solution path cannot be empty"
            )

        candidate = PurePosixPath(path)

        if (
            candidate.is_absolute()
            or ".." in candidate.parts
            or WINDOWS_ABS_RE.match(path)
            or candidate.as_posix() == "."
        ):
            raise CatalogError(
                f"{pid}: solution path must be "
                "repository-relative"
            )

        return candidate.as_posix()

    @staticmethod
    def _clean_language(
        pid: str,
        value: str,
    ) -> str:
        language = str(value).strip().lower()

        if language not in LANGUAGE_SUFFIX:
            raise CatalogError(
                f"{pid}: unsupported language "
                f"{language!r}"
            )

        return language

    @staticmethod
    def _validate_language_suffix(
        pid: str,
        path: str,
        language: str,
    ) -> None:
        expected = LANGUAGE_SUFFIX[language]
        actual = PurePosixPath(path).suffix.lower()

        if actual != expected:
            raise CatalogError(
                f"{pid}: {language} solution must use "
                f"{expected} path"
            )

    @classmethod
    def _problem_row(
        cls,
        item: ProblemMeta,
    ) -> dict[str, str]:
        pid = cls._clean_problem_id(
            item.problem_id
        )

        return {
            "problem_id": pid,
            "title": item.title.strip(),
            "source": item.source.strip(),
            "difficulty": cls._clean_difficulty(
                pid,
                item.difficulty,
            ),
            "tags": cls._clean_tags(
                item.tags
            ),
        }

    @classmethod
    def _solution_row(
        cls,
        item: SolutionMeta,
    ) -> dict[str, str]:
        pid = cls._clean_problem_id(
            item.problem_id
        )
        path = cls._clean_solution_path(
            pid,
            item.path,
        )
        language = cls._clean_language(
            pid,
            item.language,
        )

        cls._validate_language_suffix(
            pid,
            path,
            language,
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

    def _prepare_problem_rows(
        self,
        problems: list[ProblemMeta],
    ) -> list[dict[str, str]]:
        rows = [
            self._problem_row(item)
            for item in problems
        ]

        ids = [
            row["problem_id"]
            for row in rows
        ]

        if len(ids) != len(set(ids)):
            raise CatalogError(
                "problems.csv: duplicate problem_id"
            )

        rows.sort(
            key=lambda row: row["problem_id"]
        )

        return rows

    def _prepare_solution_rows(
        self,
        solutions: list[SolutionMeta],
    ) -> list[dict[str, str]]:
        rows = [
            self._solution_row(item)
            for item in solutions
        ]

        paths = [
            row["path"]
            for row in rows
        ]

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

        return rows

    def save_problems(
        self,
        problems: list[ProblemMeta],
    ) -> None:
        self._write_rows(
            self.problems_path,
            PROBLEM_FIELDS,
            self._prepare_problem_rows(
                problems
            ),
        )

    def save_solutions(
        self,
        solutions: list[SolutionMeta],
    ) -> None:
        self._write_rows(
            self.solutions_path,
            SOLUTION_FIELDS,
            self._prepare_solution_rows(
                solutions
            ),
        )

    @staticmethod
    def _restore_bytes(
        path: Path,
        payload: bytes | None,
    ) -> None:
        rollback = path.with_name(
            path.name + ".rollback.tmp"
        )

        try:
            if payload is None:
                path.unlink(
                    missing_ok=True
                )
                return

            path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            rollback.write_bytes(
                payload
            )
            rollback.replace(
                path
            )

        finally:
            rollback.unlink(
                missing_ok=True
            )

    def _save_catalog_pair(
        self,
        problems: list[ProblemMeta],
        solutions: list[SolutionMeta],
    ) -> None:
        problem_rows = (
            self._prepare_problem_rows(
                problems
            )
        )
        solution_rows = (
            self._prepare_solution_rows(
                solutions
            )
        )

        problem_ids = {
            row["problem_id"]
            for row in problem_rows
        }
        solution_ids = {
            row["problem_id"]
            for row in solution_rows
        }

        unknown = sorted(
            solution_ids - problem_ids
        )

        if unknown:
            raise CatalogError(
                "solutions reference unknown "
                "problem_id: "
                + ", ".join(unknown)
            )

        missing = sorted(
            problem_ids - solution_ids
        )

        if missing:
            raise CatalogError(
                "problems without solutions: "
                + ", ".join(missing)
            )

        snapshots = {
            self.problems_path:
                self.problems_path.read_bytes()
                if self.problems_path.exists()
                else None,
            self.solutions_path:
                self.solutions_path.read_bytes()
                if self.solutions_path.exists()
                else None,
        }

        try:
            self._write_rows(
                self.problems_path,
                PROBLEM_FIELDS,
                problem_rows,
            )
            self._write_rows(
                self.solutions_path,
                SOLUTION_FIELDS,
                solution_rows,
            )

        except Exception as exc:
            rollback_errors: list[str] = []

            for path, payload in snapshots.items():
                try:
                    self._restore_bytes(
                        path,
                        payload,
                    )
                except Exception as rollback_exc:
                    rollback_errors.append(
                        f"{path.name}: "
                        f"{rollback_exc}"
                    )

            if rollback_errors:
                raise CatalogError(
                    "catalog pair write failed and "
                    "rollback also failed: "
                    + "; ".join(
                        rollback_errors
                    )
                ) from exc

            raise

    def create_problem_with_solution(
        self,
        problem: ProblemMeta,
        solution: SolutionMeta,
    ) -> None:
        problem_row = self._problem_row(
            problem
        )
        solution_row = self._solution_row(
            solution
        )

        if (
            problem_row["problem_id"]
            != solution_row["problem_id"]
        ):
            raise CatalogError(
                "problem and solution "
                "problem_id mismatch"
            )

        problems = self.load_problems()
        solutions = self.load_solutions()
        pid = problem_row["problem_id"]

        if pid in problems:
            raise CatalogError(
                f"problem already exists: {pid}"
            )

        if any(
            item.path
            == solution_row["path"]
            for item in solutions
        ):
            raise CatalogError(
                "solution path already exists: "
                f"{solution_row['path']}"
            )

        self._save_catalog_pair(
            [
                *problems.values(),
                ProblemMeta(**problem_row),
            ],
            [
                *solutions,
                SolutionMeta(**solution_row),
            ],
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

    def update_problem_with_solution(
        self,
        problem: ProblemMeta,
        solution: SolutionMeta,
    ) -> None:
        problem_row = self._problem_row(
            problem
        )
        solution_row = self._solution_row(
            solution
        )

        pid = problem_row["problem_id"]

        if pid != solution_row["problem_id"]:
            raise CatalogError(
                "problem and solution "
                "problem_id mismatch"
            )

        problems = self.load_problems()
        solutions = self.load_solutions()

        if pid not in problems:
            raise CatalogError(
                f"problem not found: {pid}"
            )

        found = False
        updated_solutions: list[
            SolutionMeta
        ] = []

        for item in solutions:
            if item.path == solution_row["path"]:
                if item.problem_id != pid:
                    raise CatalogError(
                        "solution problem_id "
                        "cannot be changed"
                    )

                updated_solutions.append(
                    SolutionMeta(
                        **solution_row
                    )
                )
                found = True
            else:
                updated_solutions.append(
                    item
                )

        if not found:
            raise CatalogError(
                "solution not found: "
                f"{solution_row['path']}"
            )

        problems[pid] = ProblemMeta(
            **problem_row
        )

        self._save_catalog_pair(
            list(problems.values()),
            updated_solutions,
        )

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
