#!/usr/bin/env python3
"""APCS v2.3 curriculum compiler.

The runtime never reads live Notion.  This compiler consumes a normalized
Notion authoring export, validates it, and emits a deterministic published
snapshot for VS Code / Git runtime use.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


SOURCE_SCHEMA = "v2.3-authoring-1"
PUBLISHED_SCHEMA = "v2.3-published-1"
CONTRACT_VERSION = "v2.3-draft-0"

TRACKS = {"Reading", "Implementation"}
PUBLISH_STATES = {"Draft", "Published", "Retired"}
ROLES = {
    "Worked Example",
    "Guided Drill",
    "Core Independent",
    "Transfer Challenge",
    "Mock",
}

ROLE_EVIDENCE_LEVEL_CAP = {
    "Worked Example": 0,
    "Guided Drill": 2,
    "Core Independent": 3,
    "Transfer Challenge": 4,
    "Mock": 0,
}
METHOD_CONFIRMATION_RISKS = {
    "Medium",
    "High",
}
DIFFICULTIES = {"D1", "D2", "D3", "D4", "D5"}
UID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]*$")


class CurriculumError(ValueError):
    pass


def _text(value: Any) -> str:
    return str(value or "").strip()


def _require_text(obj: dict[str, Any], key: str, where: str) -> str:
    value = _text(obj.get(key))
    if not value:
        raise CurriculumError(f"{where}: missing {key}")
    return value


def _require_uid(value: Any, where: str) -> str:
    uid = _text(value)
    if not uid:
        raise CurriculumError(f"{where}: missing uid")
    if not UID_RE.fullmatch(uid):
        raise CurriculumError(f"{where}: invalid uid={uid!r}")
    return uid


def _unique_by(
    rows: list[dict[str, Any]],
    key: str,
    label: str,
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}

    for index, row in enumerate(rows, start=1):
        value = _text(row.get(key))
        where = f"{label}[{index}]"

        if not value:
            raise CurriculumError(f"{where}: missing {key}")

        if value in result:
            raise CurriculumError(
                f"{label}: duplicate {key}={value}"
            )

        result[value] = row

    return result


def _validate_cycle(
    skills: dict[str, dict[str, Any]],
) -> None:
    graph: dict[str, list[str]] = {}

    for uid, row in skills.items():
        prereqs = list(row.get("prerequisites") or [])
        graph[uid] = [_text(item) for item in prereqs if _text(item)]

    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(uid: str) -> None:
        mark = state.get(uid, 0)

        if mark == 2:
            return

        if mark == 1:
            if uid in stack:
                start = stack.index(uid)
                cycle = stack[start:] + [uid]
            else:
                cycle = stack + [uid]

            raise CurriculumError(
                "skill prerequisite cycle: "
                + " -> ".join(cycle)
            )

        state[uid] = 1
        stack.append(uid)

        for dep in graph[uid]:
            visit(dep)

        stack.pop()
        state[uid] = 2

    for uid in sorted(graph):
        visit(uid)


def validate_source(data: dict[str, Any]) -> None:
    if data.get("schema_version") != SOURCE_SCHEMA:
        raise CurriculumError(
            "source schema_version must be "
            f"{SOURCE_SCHEMA}"
        )

    _require_text(
        data,
        "curriculum_version",
        "source",
    )

    skills_raw = list(data.get("skills") or [])
    problems_raw = list(data.get("problems") or [])
    placements_raw = list(data.get("placements") or [])

    skills = _unique_by(
        skills_raw,
        "uid",
        "skills",
    )
    problems = _unique_by(
        problems_raw,
        "pb_uid",
        "problems",
    )
    placements = _unique_by(
        placements_raw,
        "placement_uid",
        "placements",
    )

    path_orders: dict[float, str] = {}

    for uid, row in skills.items():
        _require_uid(uid, f"skill {uid}")
        _require_text(row, "name", f"skill {uid}")
        _require_text(row, "unit", f"skill {uid}")
        _require_text(row, "path_stage", f"skill {uid}")

        order = row.get("path_order")
        if not isinstance(order, (int, float)):
            raise CurriculumError(
                f"skill {uid}: path_order must be numeric"
            )

        if order in path_orders:
            raise CurriculumError(
                "skills: duplicate path_order="
                f"{order} for {path_orders[order]} and {uid}"
            )

        path_orders[order] = uid

        tracks = set(row.get("tracks") or [])
        if not tracks:
            raise CurriculumError(
                f"skill {uid}: at least one track is required"
            )

        unknown_tracks = tracks - TRACKS
        if unknown_tracks:
            raise CurriculumError(
                f"skill {uid}: invalid tracks "
                f"{sorted(unknown_tracks)}"
            )

        for dep in row.get("prerequisites") or []:
            dep_uid = _text(dep)

            if dep_uid == uid:
                raise CurriculumError(
                    f"skill {uid}: self prerequisite"
                )

            if dep_uid not in skills:
                raise CurriculumError(
                    f"skill {uid}: unknown prerequisite "
                    f"{dep_uid}"
                )

    _validate_cycle(skills)

    published_problem_ids: dict[str, str] = {}

    for pb_uid, row in problems.items():
        _require_uid(pb_uid, f"problem {pb_uid}")

        state = _text(row.get("publish_state"))
        if state not in PUBLISH_STATES:
            raise CurriculumError(
                f"problem {pb_uid}: invalid publish_state={state!r}"
            )

        problem_id = _require_text(
            row,
            "problem_id",
            f"problem {pb_uid}",
        )

        _require_text(
            row,
            "title",
            f"problem {pb_uid}",
        )

        if state == "Published":
            difficulty = _text(row.get("difficulty"))

            if difficulty not in DIFFICULTIES:
                raise CurriculumError(
                    f"problem {pb_uid}: Published problem "
                    "requires difficulty D1-D5"
                )

            identity = (
                _text(row.get("source_platform")).lower(),
                problem_id.lower(),
            )

            identity_key = "::".join(identity)

            if identity_key in published_problem_ids:
                raise CurriculumError(
                    "Published problems: duplicate external identity "
                    f"{identity_key} in "
                    f"{published_problem_ids[identity_key]} and {pb_uid}"
                )

            published_problem_ids[identity_key] = pb_uid

    placement_count = defaultdict(int)

    for placement_uid, row in placements.items():
        _require_uid(
            placement_uid,
            f"placement {placement_uid}",
        )

        pb_uid = _require_text(
            row,
            "pb_uid",
            f"placement {placement_uid}",
        )

        if pb_uid not in problems:
            raise CurriculumError(
                f"placement {placement_uid}: unknown pb_uid={pb_uid}"
            )

        role = _text(row.get("role"))
        if role not in ROLES:
            raise CurriculumError(
                f"placement {placement_uid}: invalid role={role!r}"
            )

        raw_cap = row.get(
            "evidence_level_cap"
        )
        role_cap = ROLE_EVIDENCE_LEVEL_CAP[
            role
        ]

        if raw_cap is None:
            evidence_level_cap = role_cap
        elif (
            isinstance(raw_cap, bool)
            or not isinstance(raw_cap, int)
        ):
            raise CurriculumError(
                f"placement {placement_uid}: "
                "evidence_level_cap must be an integer"
            )
        else:
            evidence_level_cap = raw_cap

        if not 0 <= evidence_level_cap <= role_cap:
            raise CurriculumError(
                f"placement {placement_uid}: "
                f"evidence_level_cap={evidence_level_cap} "
                f"exceeds role cap {role_cap}"
            )

        raw_confirmation = row.get(
            "method_confirmation_required"
        )

        if (
            raw_confirmation is not None
            and not isinstance(
                raw_confirmation,
                bool,
            )
        ):
            raise CurriculumError(
                f"placement {placement_uid}: "
                "method_confirmation_required must be boolean"
            )

        primary = _require_text(
            row,
            "primary_skill",
            f"placement {placement_uid}",
        )

        if primary not in skills:
            raise CurriculumError(
                f"placement {placement_uid}: "
                f"unknown primary_skill={primary}"
            )

        supporting = [
            _text(item)
            for item in (row.get("supporting_skills") or [])
            if _text(item)
        ]

        if len(supporting) != len(set(supporting)):
            raise CurriculumError(
                f"placement {placement_uid}: "
                "duplicate supporting_skills"
            )

        if primary in supporting:
            raise CurriculumError(
                f"placement {placement_uid}: "
                "primary_skill cannot also be supporting"
            )

        for skill_uid in supporting:
            if skill_uid not in skills:
                raise CurriculumError(
                    f"placement {placement_uid}: "
                    f"unknown supporting skill={skill_uid}"
                )

        lesson_order = row.get("lesson_order")
        if (
            lesson_order is not None
            and not isinstance(
                lesson_order,
                (int, float),
            )
        ):
            raise CurriculumError(
                f"placement {placement_uid}: "
                "lesson_order must be numeric or null"
            )

        placement_count[pb_uid] += 1

    for pb_uid, row in problems.items():
        if _text(row.get("publish_state")) != "Published":
            continue

        assessment_only = bool(
            row.get("assessment_only", False)
        )

        if not assessment_only and placement_count[pb_uid] == 0:
            raise CurriculumError(
                f"problem {pb_uid}: Published problem "
                "requires a placement or assessment_only=true"
            )


def _skill_projection(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "uid": _text(row.get("uid")),
        "name": _text(row.get("name")),
        "unit": _text(row.get("unit")),
        "cl": _text(row.get("cl")),
        "path_stage": _text(row.get("path_stage")),
        "path_order": row.get("path_order"),
        "tracks": sorted(set(row.get("tracks") or [])),
        "prerequisites": sorted(
            {
                _text(item)
                for item in (row.get("prerequisites") or [])
                if _text(item)
            }
        ),
        "relevance": {
            "3+3": _text(
                (row.get("relevance") or {}).get("3+3")
            ),
            "5+5": _text(
                (row.get("relevance") or {}).get("5+5")
            ),
        },
        "conceptual_requirement": _text(
            row.get("conceptual_requirement")
        ),
        "implementation_requirement": _text(
            row.get("implementation_requirement")
        ),
        "recommended_problem_types": _text(
            row.get("recommended_problem_types")
        ),
        "evidence_suitability": _text(
            row.get("evidence_suitability")
        ),
    }


def _problem_projection(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "pb_uid": _text(row.get("pb_uid")),
        "problem_id": _text(row.get("problem_id")),
        "title": _text(row.get("title")),
        "source_platform": _text(
            row.get("source_platform")
        ),
        "judge_platform": _text(
            row.get("judge_platform")
        ),
        "url": _text(row.get("url")),
        "difficulty": _text(row.get("difficulty")),
        "exam_band": _text(row.get("exam_band")),
        "suitability": {
            "3+3": _text(
                (row.get("suitability") or {}).get("3+3")
            ),
            "5+5": _text(
                (row.get("suitability") or {}).get("5+5")
            ),
        },
        "alternate_solution_risk": _text(
            row.get("alternate_solution_risk")
        ),
        "training_purpose": _text(
            row.get("training_purpose")
        ),
        "assessment_only": bool(
            row.get("assessment_only", False)
        ),
    }


def _placement_projection(
    row: dict[str, Any],
    *,
    problem: dict[str, Any],
) -> dict[str, Any]:
    role = _text(
        row.get("role")
    )
    role_cap = ROLE_EVIDENCE_LEVEL_CAP[
        role
    ]
    raw_cap = row.get(
        "evidence_level_cap"
    )
    evidence_level_cap = (
        role_cap
        if raw_cap is None
        else int(raw_cap)
    )

    raw_confirmation = row.get(
        "method_confirmation_required"
    )

    if raw_confirmation is None:
        method_confirmation_required = (
            role
            in {
                "Core Independent",
                "Transfer Challenge",
            }
            and _text(
                problem.get(
                    "alternate_solution_risk"
                )
            )
            in METHOD_CONFIRMATION_RISKS
        )
    else:
        method_confirmation_required = bool(
            raw_confirmation
        )

    return {
        "placement_uid": _text(
            row.get("placement_uid")
        ),
        "pb_uid": _text(row.get("pb_uid")),
        "primary_skill": _text(
            row.get("primary_skill")
        ),
        "supporting_skills": sorted(
            {
                _text(item)
                for item in (
                    row.get("supporting_skills")
                    or []
                )
                if _text(item)
            }
        ),
        "role": _text(row.get("role")),
        "lesson_uid": _text(
            row.get("lesson_uid")
        ),
        "lesson_order": row.get("lesson_order"),
        "evidence_level_cap": evidence_level_cap,
        "method_confirmation_required": (
            method_confirmation_required
        ),
    }


def compile_source(
    data: dict[str, Any],
) -> dict[str, Any]:
    validate_source(data)

    published_problems = [
        row
        for row in data.get("problems") or []
        if _text(row.get("publish_state")) == "Published"
    ]

    published_pb_uids = {
        _text(row.get("pb_uid"))
        for row in published_problems
    }

    skills = sorted(
        (
            _skill_projection(row)
            for row in data.get("skills") or []
        ),
        key=lambda row: (
            row["path_order"],
            row["uid"],
        ),
    )

    problems = sorted(
        (
            _problem_projection(row)
            for row in published_problems
        ),
        key=lambda row: (
            row["pb_uid"],
            row["problem_id"],
        ),
    )

    published_problem_by_uid = {
        _text(row.get("pb_uid")): row
        for row in published_problems
    }

    placements = sorted(
        (
            _placement_projection(
                row,
                problem=(
                    published_problem_by_uid[
                        _text(
                            row.get("pb_uid")
                        )
                    ]
                ),
            )
            for row in data.get("placements") or []
            if _text(row.get("pb_uid"))
            in published_pb_uids
        ),
        key=lambda row: (
            row["pb_uid"],
            (
                float("inf")
                if row["lesson_order"] is None
                else row["lesson_order"]
            ),
            row["placement_uid"],
        ),
    )

    return {
        "schema_version": PUBLISHED_SCHEMA,
        "contract_version": CONTRACT_VERSION,
        "curriculum_version": _text(
            data.get("curriculum_version")
        ),
        "skills": skills,
        "problems": problems,
        "placements": placements,
        "stats": {
            "skills": len(skills),
            "problems": len(problems),
            "placements": len(placements),
        },
    }


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise CurriculumError(
            f"cannot read {path}: {exc}"
        ) from exc

    if not isinstance(value, dict):
        raise CurriculumError(
            f"{path}: top-level JSON must be an object"
        )

    return value


def _dump(value: dict[str, Any]) -> str:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=False,
        )
        + "\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate and compile APCS v2.3 curriculum authoring exports"
        )
    )

    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    validate_parser = sub.add_parser("validate")
    validate_parser.add_argument("source", type=Path)

    compile_parser = sub.add_parser("compile")
    compile_parser.add_argument("source", type=Path)
    compile_parser.add_argument("output", type=Path)

    check_parser = sub.add_parser("check")
    check_parser.add_argument("source", type=Path)
    check_parser.add_argument("output", type=Path)

    args = parser.parse_args(argv)

    try:
        source = _load(args.source)
        compiled = compile_source(source)

        if args.command == "validate":
            print(
                "PASS: curriculum source valid "
                f"({compiled['stats']['skills']} skills, "
                f"{compiled['stats']['problems']} published problems, "
                f"{compiled['stats']['placements']} placements)"
            )
            return 0

        expected = _dump(compiled)

        if args.command == "compile":
            args.output.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            args.output.write_text(
                expected,
                encoding="utf-8",
            )
            print(
                f"PASS: wrote {args.output}"
            )
            return 0

        actual = args.output.read_text(
            encoding="utf-8"
        )

        if actual != expected:
            print(
                "FAIL: published snapshot is stale; "
                "run curriculum compiler",
                file=sys.stderr,
            )
            return 1

        print(
            "PASS: published curriculum snapshot is deterministic"
        )
        return 0

    except (CurriculumError, OSError) as exc:
        print(
            f"FAIL: {exc}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
