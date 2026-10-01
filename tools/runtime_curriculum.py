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


@dataclass(frozen=True)
class PlacementContext:
    placement_uid: str
    pb_uid: str
    problem_id: str
    title: str
    difficulty: str
    primary_skill: str
    supporting_skills: tuple[str, ...]
    role: str
    lesson_uid: str
    lesson_order: int | float | None


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
                        difficulty=str(
                            problem.get(
                                "difficulty",
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
            )

        return None

    def importance_for_skill(
        self,
        skill_uid: str,
        *,
        target: str = "3+3",
    ) -> str:
        context = self.skill_context(
            skill_uid
        )

        if context is None:
            return "supporting"

        value = (
            context.relevance_33
            if target == "3+3"
            else context.relevance_55
        ).strip().lower()

        if "required" in value:
            return "required"

        if (
            "extension" in value
            or "optional" in value
        ):
            return "extension"

        return "supporting"
