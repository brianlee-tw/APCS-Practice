#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

try:
    from .catalog_store import (
        CatalogError,
        CatalogStore,
        ProblemMeta,
        SolutionMeta,
    )
    from .runtime_curriculum import (
        RuntimeCurriculum,
        RuntimeCurriculumError,
    )
except ImportError:
    from catalog_store import (
        CatalogError,
        CatalogStore,
        ProblemMeta,
        SolutionMeta,
    )
    from runtime_curriculum import (
        RuntimeCurriculum,
        RuntimeCurriculumError,
    )


PLACEMENT_RE = re.compile(
    r"__([A-Za-z0-9_.:-]+)$"
)
LEGACY_ID_RE = re.compile(
    r"^([A-Za-z]\d+|\d+)(?:_|$)"
)


@dataclass(frozen=True)
class ProblemContext:
    problem_id: str
    title: str
    source: str | None
    canonical_url: str | None
    solution_path: Path
    placement_uid: str | None
    role: str | None
    pb_uid: str | None
    identity_origin: str


def _relative_to_root(
    path: Path,
    root: Path,
) -> str | None:
    try:
        return (
            path.resolve()
            .relative_to(
                root.resolve()
            )
            .as_posix()
        )
    except ValueError:
        return None


def _intelligence_identity(
    intelligence_dir: Path,
    external_id: str,
    *,
    source_hint: str | None = None,
) -> tuple[str | None, str | None, str | None]:
    if not intelligence_dir.is_dir():
        return None, None, None

    external_folded = external_id.casefold()
    source_folded = (
        str(source_hint or "")
        .strip()
        .casefold()
    )
    matches: list[
        tuple[
            str | None,
            str | None,
            str | None,
        ]
    ] = []

    for path in sorted(
        intelligence_dir.rglob("*.json")
    ):
        try:
            payload = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )
        except (
            OSError,
            json.JSONDecodeError,
        ):
            continue

        identity = payload.get("identity")
        if not isinstance(identity, dict):
            continue

        if (
            str(
                identity.get("external_id")
                or ""
            ).casefold()
            != external_folded
        ):
            continue

        source = str(
            identity.get("source")
            or ""
        ).strip().casefold()
        if (
            source_folded
            and source
            != source_folded
        ):
            continue

        url = str(
            identity.get("canonical_url")
            or ""
        ).strip()
        metadata = payload.get(
            "source_metadata"
        )
        title = ""
        if isinstance(metadata, dict):
            title = str(
                metadata.get("title")
                or ""
            ).strip()

        matches.append(
            (
                source or None,
                url or None,
                title or None,
            )
        )

    # External IDs are not globally unique across judges.  If source
    # authority is unavailable and more than one identity matches, do not
    # let filesystem ordering choose a canonical URL/title by accident.
    if len(matches) != 1:
        return None, None, None

    return matches[0]


def resolve_problem_context(
    filename: str | Path,
    *,
    root: Path,
    store: CatalogStore,
    curriculum: RuntimeCurriculum,
    intelligence_dir: Path,
) -> ProblemContext | None:
    source_path = Path(filename)
    if not source_path.is_absolute():
        source_path = (
            root
            / source_path
        )
    source_path = source_path.resolve()

    # Published runtime identity is encoded in the scratch filename and must
    # remain recoverable even in tests / recovery paths where the scratch file
    # itself is temporarily absent.
    placement_match = PLACEMENT_RE.search(
        source_path.stem
    )
    if placement_match:
        placement_uid = (
            placement_match.group(1)
        )
        try:
            placement = (
                curriculum
                .placement_by_uid(
                    placement_uid
                )
            )
        except RuntimeCurriculumError:
            placement = None

        if placement is not None:
            return ProblemContext(
                problem_id=(
                    placement.problem_id
                    .strip()
                    .lower()
                ),
                title=placement.title,
                source=(
                    getattr(
                        placement,
                        "source_platform",
                        None,
                    )
                    or getattr(
                        placement,
                        "judge_platform",
                        None,
                    )
                    or None
                ),
                canonical_url=(
                    getattr(
                        placement,
                        "url",
                        None,
                    )
                    or None
                ),
                solution_path=source_path,
                placement_uid=placement_uid,
                role=(
                    getattr(
                        placement,
                        "role",
                        None,
                    )
                    or None
                ),
                pb_uid=(
                    getattr(
                        placement,
                        "pb_uid",
                        None,
                    )
                    or None
                ),
                identity_origin="published_placement",
            )

    if not source_path.is_file():
        return None

    relative = _relative_to_root(
        source_path,
        root,
    )

    try:
        problems = store.load_problems()
        solutions = store.load_solutions()
    except CatalogError:
        problems = {}
        solutions = []

    if relative is not None:
        solution = next(
            (
                item
                for item in solutions
                if item.path == relative
            ),
            None,
        )
        if solution is not None:
            problem = problems.get(
                solution.problem_id
            )
            pid = solution.problem_id
            title = (
                problem.title
                if problem is not None
                and problem.title
                else pid
            )
            source = (
                problem.source.strip()
                if problem is not None
                and problem.source.strip()
                else None
            )
            intel_source, intel_url, intel_title = (
                _intelligence_identity(
                    intelligence_dir,
                    pid,
                    source_hint=source,
                )
            )
            return ProblemContext(
                problem_id=pid,
                title=(
                    intel_title
                    or title
                ),
                source=(
                    source.casefold()
                    if source
                    else intel_source
                ),
                canonical_url=intel_url,
                solution_path=source_path,
                placement_uid=None,
                role=None,
                pb_uid=None,
                identity_origin="catalog_solution",
            )

    match = LEGACY_ID_RE.match(
        source_path.stem
    )
    if not match:
        return None

    pid = match.group(1).casefold()
    problem = problems.get(pid)
    intel_source, intel_url, intel_title = (
        _intelligence_identity(
            intelligence_dir,
            pid,
            source_hint=(
                problem.source
                if (
                    problem is not None
                    and problem.source.strip()
                )
                else None
            ),
        )
    )

    return ProblemContext(
        problem_id=pid,
        title=(
            intel_title
            or (
                problem.title
                if problem is not None
                and problem.title
                else pid
            )
        ),
        source=(
            problem.source.strip().casefold()
            if problem is not None
            and problem.source.strip()
            else intel_source
        ),
        canonical_url=intel_url,
        solution_path=source_path,
        placement_uid=None,
        role=None,
        pb_uid=None,
        identity_origin="filename_fallback",
    )
