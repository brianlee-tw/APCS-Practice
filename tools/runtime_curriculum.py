"""Published curriculum runtime reader for APCS v2.3.

VS Code consumes only the Git-published curriculum snapshot.  This module never
queries live Notion.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PUBLISHED_SCHEMA = "v2.3-published-1"


class RuntimeCurriculumError(ValueError):
    pass


class RuntimeCurriculumUnavailable(RuntimeCurriculumError):
    pass


@dataclass(frozen=True)
class SkillContext:
    uid: str
    name: str
    unit: str
    path_stage: str


@dataclass(frozen=True)
class PlacementContext:
    placement_uid: str
    pb_uid: str
    problem_id: str
    problem_title: str
    problem_url: str
    difficulty: str
    primary_skill: SkillContext
    supporting_skills: tuple[SkillContext, ...]
    role: str
    lesson_uid: str
    lesson_order: float | int | None


class PublishedCurriculum:
    def __init__(
        self,
        path: Path,
    ):
        self.path = Path(path)
        self._loaded = False
        self._skills: dict[str, dict[str, Any]] = {}
        self._problems: dict[str, dict[str, Any]] = {}
        self._placements_by_pb: dict[
            str,
            list[dict[str, Any]],
        ] = {}

    def _load(self) -> None:
        if self._loaded:
            return

        if not self.path.exists():
            raise RuntimeCurriculumUnavailable(
                f"published curriculum snapshot not found: {self.path}"
            )

        try:
            value = json.loads(
                self.path.read_text(
                    encoding="utf-8",
                )
            )
        except json.JSONDecodeError as exc:
            raise RuntimeCurriculumError(
                f"invalid published curriculum JSON: {self.path}"
            ) from exc

        if not isinstance(value, dict):
            raise RuntimeCurriculumError(
                "published curriculum must be a JSON object"
            )

        if value.get("schema_version") != PUBLISHED_SCHEMA:
            raise RuntimeCurriculumError(
                "unsupported published curriculum schema: "
                f"{value.get('schema_version')!r}"
            )

        skills = value.get("skills")
        problems = value.get("problems")
        placements = value.get("placements")

        if not isinstance(skills, list):
            raise RuntimeCurriculumError(
                "published curriculum skills must be an array"
            )

        if not isinstance(problems, list):
            raise RuntimeCurriculumError(
                "published curriculum problems must be an array"
            )

        if not isinstance(placements, list):
            raise RuntimeCurriculumError(
                "published curriculum placements must be an array"
            )

        self._skills = {}

        for row in skills:
            if not isinstance(row, dict):
                raise RuntimeCurriculumError(
                    "skill row must be an object"
                )

            uid = str(row.get("uid") or "").strip()

            if not uid:
                raise RuntimeCurriculumError(
                    "skill row missing uid"
                )

            if uid in self._skills:
                raise RuntimeCurriculumError(
                    f"duplicate runtime skill uid={uid}"
                )

            self._skills[uid] = row

        self._problems = {}

        for row in problems:
            if not isinstance(row, dict):
                raise RuntimeCurriculumError(
                    "problem row must be an object"
                )

            pb_uid = str(
                row.get("pb_uid")
                or ""
            ).strip()
            problem_id = str(
                row.get("problem_id")
                or ""
            ).strip().lower()

            if not pb_uid or not problem_id:
                raise RuntimeCurriculumError(
                    "problem row requires pb_uid and problem_id"
                )

            if problem_id in self._problems:
                raise RuntimeCurriculumError(
                    "runtime currently requires one published problem "
                    f"per problem_id; duplicate={problem_id}"
                )

            self._problems[problem_id] = row

        self._placements_by_pb = {}

        seen_placements: set[str] = set()

        for row in placements:
            if not isinstance(row, dict):
                raise RuntimeCurriculumError(
                    "placement row must be an object"
                )

            placement_uid = str(
                row.get("placement_uid")
                or ""
            ).strip()
            pb_uid = str(
                row.get("pb_uid")
                or ""
            ).strip()

            if not placement_uid or not pb_uid:
                raise RuntimeCurriculumError(
                    "placement requires placement_uid and pb_uid"
                )

            if placement_uid in seen_placements:
                raise RuntimeCurriculumError(
                    f"duplicate placement_uid={placement_uid}"
                )

            seen_placements.add(
                placement_uid
            )

            self._placements_by_pb.setdefault(
                pb_uid,
                [],
            ).append(row)

        self._loaded = True

    def _skill(
        self,
        uid: str,
    ) -> SkillContext:
        row = self._skills.get(uid)

        if row is None:
            raise RuntimeCurriculumError(
                f"placement references unknown skill={uid}"
            )

        return SkillContext(
            uid=uid,
            name=str(
                row.get("name")
                or uid
            ).strip(),
            unit=str(
                row.get("unit")
                or ""
            ).strip(),
            path_stage=str(
                row.get("path_stage")
                or ""
            ).strip(),
        )

    def placements_for_problem(
        self,
        problem_id: str,
    ) -> tuple[PlacementContext, ...]:
        self._load()

        pid = str(problem_id or "").strip().lower()

        problem = self._problems.get(pid)

        if problem is None:
            return ()

        pb_uid = str(problem["pb_uid"])

        result = []

        for row in self._placements_by_pb.get(
            pb_uid,
            [],
        ):
            primary_uid = str(
                row.get("primary_skill")
                or ""
            ).strip()

            if not primary_uid:
                raise RuntimeCurriculumError(
                    f"placement {row.get('placement_uid')} "
                    "missing primary_skill"
                )

            supporting = tuple(
                self._skill(str(uid))
                for uid in (
                    row.get("supporting_skills")
                    or []
                )
            )

            result.append(
                PlacementContext(
                    placement_uid=str(
                        row.get("placement_uid")
                    ),
                    pb_uid=pb_uid,
                    problem_id=pid,
                    problem_title=str(
                        problem.get("title")
                        or pid
                    ).strip(),
                    problem_url=str(
                        problem.get("url")
                        or ""
                    ).strip(),
                    difficulty=str(
                        problem.get("difficulty")
                        or ""
                    ).strip(),
                    primary_skill=self._skill(
                        primary_uid
                    ),
                    supporting_skills=supporting,
                    role=str(
                        row.get("role")
                        or ""
                    ).strip(),
                    lesson_uid=str(
                        row.get("lesson_uid")
                        or ""
                    ).strip(),
                    lesson_order=row.get(
                        "lesson_order"
                    ),
                )
            )

        return tuple(
            sorted(
                result,
                key=lambda item: (
                    (
                        float("inf")
                        if item.lesson_order is None
                        else float(item.lesson_order)
                    ),
                    item.placement_uid,
                ),
            )
        )


def default_curriculum(
    root: Path,
) -> PublishedCurriculum:
    return PublishedCurriculum(
        Path(root)
        / "curriculum"
        / "published.v23.json"
    )


def evidence_activity(
    *,
    action: str,
    placement: PlacementContext,
) -> str | None:
    if action == "review":
        return "Review"

    if action != "finish":
        raise RuntimeCurriculumError(
            f"unsupported action={action!r}"
        )

    if placement.role == "Worked Example":
        return None

    if placement.role in {
        "Guided Drill",
        "Core Independent",
        "Transfer Challenge",
        "Mock",
    }:
        return placement.role

    raise RuntimeCurriculumError(
        f"unsupported placement role={placement.role!r}"
    )
