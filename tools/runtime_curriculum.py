"""Runtime reader for the published APCS v2.3 curriculum snapshot.

The daily VS Code runtime reads only the published Git snapshot.  It never
queries live Notion and never falls back to repository Tags for evidence.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from .curriculum_compiler import PUBLISHED_SCHEMA
except ImportError:
    from curriculum_compiler import PUBLISHED_SCHEMA


class RuntimeCurriculumError(ValueError):
    pass


@dataclass(frozen=True)
class SkillContext:
    uid: str
    name: str
    unit: str
    path_stage: str
    path_order: int | float
    relevance_33: str
    relevance_55: str
    tracks: tuple[str, ...] = ()
    prerequisites: tuple[str, ...] = ()
    conceptual_requirement: str = ""
    implementation_requirement: str = ""


@dataclass(frozen=True)
class PlacementContext:
    placement_uid: str
    pb_uid: str
    problem_id: str
    title: str
    url: str
    difficulty: str
    primary_skill: str
    supporting_skills: tuple[str, ...]
    role: str
    lesson_uid: str
    lesson_order: int | float | None
    source_platform: str = ""
    judge_platform: str = ""


class RuntimeCurriculum:
    def __init__(self, snapshot_path: Path):
        self.snapshot_path = Path(snapshot_path)

    def available(self) -> bool:
        return self.snapshot_path.is_file()

    def load(self) -> dict[str, Any]:
        try:
            value = json.loads(
                self.snapshot_path.read_text(
                    encoding="utf-8"
                )
            )
        except FileNotFoundError as exc:
            raise RuntimeCurriculumError(
                "Published curriculum snapshot 尚未建立。"
            ) from exc
        except json.JSONDecodeError as exc:
            raise RuntimeCurriculumError(
                "Published curriculum snapshot JSON 損壞。"
            ) from exc
        except OSError as exc:
            raise RuntimeCurriculumError(
                f"無法讀取 Published curriculum：{exc}"
            ) from exc

        if not isinstance(value, dict):
            raise RuntimeCurriculumError(
                "Published curriculum top-level 必須是 object。"
            )

        if value.get("schema_version") != PUBLISHED_SCHEMA:
            raise RuntimeCurriculumError(
                "Published curriculum schema 不相容："
                f"{value.get('schema_version')!r}"
            )

        return value

    def skill_importance(
        self,
        *,
        target: str = "3+3",
    ) -> dict[str, str]:
        """Map published relevance into scheduler importance.

        Unknown wording intentionally falls back to supporting rather than
        inventing a stronger requirement.
        """

        data = self.load()
        result: dict[str, str] = {}

        for row in data.get(
            "skills"
        ) or []:
            uid = str(
                row.get(
                    "uid",
                    "",
                )
            ).strip()

            if not uid:
                continue

            relevance = (
                row.get(
                    "relevance"
                )
                or {}
            )

            raw = str(
                relevance.get(
                    target,
                    "",
                )
            ).strip().lower()

            if raw in {
                "not required",
                "not-required",
                "n/a",
            }:
                value = "supporting"
            elif any(
                token in raw
                for token in (
                    "required",
                    "critical",
                    "core",
                )
            ):
                value = "required"
            elif any(
                token in raw
                for token in (
                    "extension",
                    "optional",
                )
            ):
                value = "extension"
            else:
                value = "supporting"

            result[uid] = value

        return result

    def all_placements(
        self,
    ) -> tuple[
        PlacementContext,
        ...,
    ]:
        data = self.load()
        problems = {
            str(
                row.get(
                    "pb_uid",
                    "",
                )
            ).strip(): row
            for row in (
                data.get(
                    "problems"
                )
                or []
            )
            if str(
                row.get(
                    "pb_uid",
                    "",
                )
            ).strip()
        }

        result = []

        for placement in (
            data.get(
                "placements"
            )
            or []
        ):
            pb_uid = str(
                placement.get(
                    "pb_uid",
                    "",
                )
            ).strip()
            problem = problems.get(
                pb_uid
            )

            if problem is None:
                continue

            result.append(
                PlacementContext(
                    placement_uid=str(
                        placement.get(
                            "placement_uid",
                            "",
                        )
                    ).strip(),
                    pb_uid=pb_uid,
                    problem_id=str(
                        problem.get(
                            "problem_id",
                            "",
                        )
                    ).strip().lower(),
                    title=str(
                        problem.get(
                            "title",
                            "",
                        )
                    ).strip(),
                    url=str(
                        problem.get(
                            "url",
                            "",
                        )
                    ).strip(),
                    difficulty=str(
                        problem.get(
                            "difficulty",
                            "",
                        )
                    ).strip(),
                    source_platform=str(
                        problem.get(
                            "source_platform",
                            "",
                        )
                    ).strip(),
                    judge_platform=str(
                        problem.get(
                            "judge_platform",
                            "",
                        )
                    ).strip(),
                    primary_skill=str(
                        placement.get(
                            "primary_skill",
                            "",
                        )
                    ).strip(),
                    supporting_skills=tuple(
                        str(item).strip()
                        for item in (
                            placement.get(
                                "supporting_skills"
                            )
                            or []
                        )
                        if str(item).strip()
                    ),
                    role=str(
                        placement.get(
                            "role",
                            "",
                        )
                    ).strip(),
                    lesson_uid=str(
                        placement.get(
                            "lesson_uid",
                            "",
                        )
                    ).strip(),
                    lesson_order=(
                        placement.get(
                            "lesson_order"
                        )
                    ),
                )
            )

        return tuple(result)

    def placement_by_uid(
        self,
        placement_uid: str,
    ) -> PlacementContext | None:
        placement_uid = str(
            placement_uid or ""
        ).strip()

        if not placement_uid:
            return None

        return next(
            (
                item
                for item
                in self.all_placements()
                if item.placement_uid
                == placement_uid
            ),
            None,
        )

    def review_placement_for_skill(
        self,
        skill_uid: str,
        *,
        exclude_problem_ids: (
            set[str]
            | None
        ) = None,
    ) -> PlacementContext | None:
        """Pick a deterministic representative Implementation review item.

        Prefer transfer/core placements and, when possible, avoid the most
        recently used Problem.  Falling back to a seen Problem is allowed when
        the published curriculum has no alternative.
        """

        skill_uid = str(
            skill_uid
            or ""
        ).strip()
        exclude = {
            str(item).strip().lower()
            for item in (
                exclude_problem_ids
                or set()
            )
        }

        candidates = [
            item
            for item in self.all_placements()
            if item.primary_skill
            == skill_uid
        ]

        if not candidates:
            return None

        role_rank = {
            "Transfer Challenge": 0,
            "Core Independent": 1,
            "Guided Drill": 2,
            "Worked Example": 3,
            "Mock": 4,
        }

        candidates.sort(
            key=lambda item: (
                role_rank.get(
                    item.role,
                    99,
                ),
                item.lesson_order
                if item.lesson_order
                is not None
                else float("inf"),
                item.placement_uid,
            )
        )

        fresh = [
            item
            for item in candidates
            if item.problem_id
            not in exclude
        ]

        return (
            fresh[0]
            if fresh
            else candidates[0]
        )

    def placements_for_problem(
        self,
        problem_id: str,
    ) -> tuple[PlacementContext, ...]:
        problem_id = str(problem_id or "").strip().lower()

        if not problem_id:
            return ()

        data = self.load()

        problems = list(
            data.get("problems") or []
        )
        placements = list(
            data.get("placements") or []
        )

        matched_problems = [
            row
            for row in problems
            if str(
                row.get(
                    "problem_id",
                    "",
                )
            ).strip().lower()
            == problem_id
        ]

        if not matched_problems:
            return ()

        result: list[PlacementContext] = []

        for problem in matched_problems:
            pb_uid = str(
                problem.get(
                    "pb_uid",
                    "",
                )
            ).strip()

            if not pb_uid:
                continue

            for placement in placements:
                if str(
                    placement.get(
                        "pb_uid",
                        "",
                    )
                ).strip() != pb_uid:
                    continue

                result.append(
                    PlacementContext(
                        placement_uid=str(
                            placement.get(
                                "placement_uid",
                                "",
                            )
                        ).strip(),
                        pb_uid=pb_uid,
                        problem_id=problem_id,
                        title=str(
                            problem.get(
                                "title",
                                "",
                            )
                        ).strip(),
                        url=str(
                            problem.get(
                                "url",
                                "",
                            )
                        ).strip(),
                        difficulty=str(
                            problem.get(
                                "difficulty",
                                "",
                            )
                        ).strip(),
                        source_platform=str(
                            problem.get(
                                "source_platform",
                                "",
                            )
                        ).strip(),
                        judge_platform=str(
                            problem.get(
                                "judge_platform",
                                "",
                            )
                        ).strip(),
                        primary_skill=str(
                            placement.get(
                                "primary_skill",
                                "",
                            )
                        ).strip(),
                        supporting_skills=tuple(
                            str(item).strip()
                            for item in (
                                placement.get(
                                    "supporting_skills"
                                )
                                or []
                            )
                            if str(item).strip()
                        ),
                        role=str(
                            placement.get(
                                "role",
                                "",
                            )
                        ).strip(),
                        lesson_uid=str(
                            placement.get(
                                "lesson_uid",
                                "",
                            )
                        ).strip(),
                        lesson_order=placement.get(
                            "lesson_order"
                        ),
                    )
                )

        return tuple(
            sorted(
                result,
                key=lambda item: (
                    float("inf")
                    if item.lesson_order is None
                    else item.lesson_order,
                    item.placement_uid,
                ),
            )
        )


    def placements_for_skill(
        self,
        skill_uid: str,
    ) -> tuple[PlacementContext, ...]:
        skill_uid = str(
            skill_uid or ""
        ).strip()

        if not skill_uid:
            return ()

        return tuple(
            sorted(
                (
                    item
                    for item
                    in self.all_placements()
                    if item.primary_skill
                    == skill_uid
                ),
                key=lambda item: (
                    float("inf")
                    if item.lesson_order is None
                    else item.lesson_order,
                    item.placement_uid,
                ),
            )
        )

    def skill_context(
        self,
        skill_uid: str,
    ) -> SkillContext | None:
        skill_uid = str(
            skill_uid or ""
        ).strip()

        if not skill_uid:
            return None

        data = self.load()

        for row in data.get("skills") or []:
            if str(
                row.get(
                    "uid",
                    "",
                )
            ).strip() != skill_uid:
                continue

            relevance = (
                row.get("relevance")
                or {}
            )

            order = row.get(
                "path_order",
                10**9,
            )

            if not isinstance(
                order,
                (int, float),
            ):
                order = 10**9

            return SkillContext(
                uid=skill_uid,
                name=str(
                    row.get(
                        "name",
                        "",
                    )
                ).strip(),
                unit=str(
                    row.get(
                        "unit",
                        "",
                    )
                ).strip(),
                path_stage=str(
                    row.get(
                        "path_stage",
                        "",
                    )
                ).strip(),
                path_order=order,
                relevance_33=str(
                    relevance.get(
                        "3+3",
                        "",
                    )
                ).strip(),
                relevance_55=str(
                    relevance.get(
                        "5+5",
                        "",
                    )
                ).strip(),
                tracks=tuple(
                    str(item).strip()
                    for item in (
                        row.get("tracks")
                        or []
                    )
                    if str(item).strip()
                ),
                prerequisites=tuple(
                    str(item).strip()
                    for item in (
                        row.get(
                            "prerequisites"
                        )
                        or []
                    )
                    if str(item).strip()
                ),
                conceptual_requirement=str(
                    row.get(
                        "conceptual_requirement",
                        "",
                    )
                ).strip(),
                implementation_requirement=str(
                    row.get(
                        "implementation_requirement",
                        "",
                    )
                ).strip(),
            )

        return None

    def skill_contexts(
        self,
    ) -> tuple[SkillContext, ...]:
        data = self.load()
        result = []

        for row in data.get("skills") or []:
            uid = str(
                row.get("uid", "")
            ).strip()

            if not uid:
                continue

            context = self.skill_context(
                uid
            )

            if context is not None:
                result.append(
                    context
                )

        return tuple(
            sorted(
                result,
                key=lambda item: (
                    item.path_order,
                    item.uid,
                ),
            )
        )

    def importance_for_skill(
        self,
        skill_uid: str,
        *,
        target: str = "3+3",
    ) -> str:
        skill_uid = str(
            skill_uid or ""
        ).strip()

        if not skill_uid:
            return "supporting"

        return (
            self.skill_importance(
                target=target
            )
            .get(
                skill_uid,
                "supporting",
            )
        )

