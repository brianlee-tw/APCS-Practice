"""Fail-closed projection from legacy Notion curriculum rows to v2.3 authoring data.

This module does not call Notion.  It consumes normalized legacy rows produced by
an extraction step and requires an explicit Primary Skill resolution for every
main-curriculum placement before a Problem may become Published.
"""

from __future__ import annotations

from typing import Any


ROLES = {
    "Worked Example",
    "Guided Drill",
    "Core Independent",
    "Transfer Challenge",
    "Mock",
}


class CurriculumMigrationError(ValueError):
    pass


def _text(value: Any) -> str:
    return str(value or "").strip()


def _difficulty(value: Any) -> str:
    raw = _text(value)

    if not raw:
        return ""

    return raw.split()[0]


def _unit_from_lesson(lesson_uid: str) -> str:
    parts = lesson_uid.split("-")

    if len(parts) < 3 or parts[0] != "L":
        raise CurriculumMigrationError(
            f"invalid lesson_uid={lesson_uid!r}"
        )

    return f"U-{parts[1]}"


def project_formal_problem_rows(
    rows: list[dict[str, Any]],
    *,
    main_lessons: set[str],
    skill_uid_by_url: dict[str, str],
    primary_skill_by_pb: dict[str, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Project reviewed legacy PB rows into v2.3 Problems + Placements.

    A row with a Primary Lesson inside the main 52 is considered a formal
    placement candidate.  Such a row must be Active, Placement QA PASS, have a
    supported Role, and have an explicit Primary Skill resolution.  Nothing is
    inferred from relation order.

    Rows outside the main-lesson set are ignored here.  This intentionally keeps
    extensions, deferred candidates, and benchmark-only rows out of the first
    learner runtime snapshot unless they are separately reviewed.
    """

    problems: list[dict[str, Any]] = []
    placements: list[dict[str, Any]] = []

    seen_pb: set[str] = set()

    for index, row in enumerate(rows, start=1):
        lesson_uid = _text(
            row.get("primary_lesson")
        )

        if lesson_uid not in main_lessons:
            continue

        pb_uid = _text(row.get("pb_uid"))
        where = (
            f"row[{index}]"
            if not pb_uid
            else f"problem {pb_uid}"
        )

        if not pb_uid:
            raise CurriculumMigrationError(
                f"{where}: missing pb_uid"
            )

        if pb_uid in seen_pb:
            raise CurriculumMigrationError(
                f"duplicate formal pb_uid={pb_uid}"
            )

        seen_pb.add(pb_uid)

        status = _text(row.get("status"))
        if status != "Active":
            raise CurriculumMigrationError(
                f"{where}: formal main placement "
                f"must be Active, got {status!r}"
            )

        placement_qa = _text(
            row.get("placement_qa")
        )
        if placement_qa != "PASS":
            raise CurriculumMigrationError(
                f"{where}: formal main placement "
                f"requires Placement QA PASS, "
                f"got {placement_qa!r}"
            )

        role = _text(row.get("role"))
        if role not in ROLES:
            raise CurriculumMigrationError(
                f"{where}: invalid role={role!r}"
            )

        primary_skill = _text(
            primary_skill_by_pb.get(pb_uid)
        )
        if not primary_skill:
            raise CurriculumMigrationError(
                f"{where}: missing explicit "
                "Primary Skill resolution"
            )

        raw_skill_urls = list(
            row.get("skill_urls") or []
        )
        skill_uids: list[str] = []

        for skill_url in raw_skill_urls:
            url = _text(skill_url)

            if not url:
                continue

            skill_uid = _text(
                skill_uid_by_url.get(url)
            )

            if not skill_uid:
                raise CurriculumMigrationError(
                    f"{where}: unknown Skill relation "
                    f"{url}"
                )

            if skill_uid not in skill_uids:
                skill_uids.append(skill_uid)

        if primary_skill not in skill_uids:
            raise CurriculumMigrationError(
                f"{where}: resolved Primary Skill "
                f"{primary_skill} is not present in "
                "the current Skill relations"
            )

        supporting = sorted(
            uid
            for uid in skill_uids
            if uid != primary_skill
        )

        unit = _text(row.get("unit"))
        expected_unit = _unit_from_lesson(
            lesson_uid
        )

        if unit and not unit.startswith(
            expected_unit
        ):
            raise CurriculumMigrationError(
                f"{where}: unit {unit!r} conflicts "
                f"with {lesson_uid}"
            )

        difficulty = _difficulty(
            row.get("difficulty")
        )

        problems.append(
            {
                "pb_uid": pb_uid,
                "problem_id": _text(
                    row.get("problem_id")
                ),
                "title": _text(
                    row.get("title")
                ),
                "source_platform": _text(
                    row.get("source_platform")
                ),
                "judge_platform": _text(
                    row.get("judge_platform")
                ),
                "url": _text(row.get("url")),
                "difficulty": difficulty,
                "exam_band": _text(
                    row.get("exam_band")
                ),
                "suitability": {
                    "3+3": _text(
                        row.get(
                            "suitability_33"
                        )
                    ),
                    "5+5": _text(
                        row.get(
                            "suitability_55"
                        )
                    ),
                },
                "alternate_solution_risk": (
                    _text(
                        row.get(
                            "alternate_solution_risk"
                        )
                    )
                ),
                "training_purpose": _text(
                    row.get(
                        "training_purpose"
                    )
                ),
                "assessment_only": False,
                "publish_state": "Published",
            }
        )

        placements.append(
            {
                "placement_uid": (
                    f"PL-{pb_uid}-{lesson_uid}"
                ),
                "pb_uid": pb_uid,
                "primary_skill": primary_skill,
                "supporting_skills": supporting,
                "role": role,
                "lesson_uid": lesson_uid,
                "lesson_order": row.get(
                    "lesson_order"
                ),
            }
        )

    return problems, placements
