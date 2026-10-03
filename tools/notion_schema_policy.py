#!/usr/bin/env python3
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = (
    ROOT
    / "curriculum"
    / "notion_schema_policy.v23.json"
)


@lru_cache(maxsize=1)
def load_notion_schema_policy() -> dict[str, Any]:
    return json.loads(
        POLICY_PATH.read_text(
            encoding="utf-8"
        )
    )


def forbidden_projection_fields(
    surface: str,
) -> frozenset[str]:
    policy = load_notion_schema_policy()
    row = policy["databases"][surface]
    return frozenset(
        row.get(
            "client_forbidden_writes",
            [],
        )
    )


def validate_projection_fields(
    *,
    surface: str,
    properties: dict[str, Any],
) -> None:
    forbidden = (
        forbidden_projection_fields(
            surface
        )
    )
    found = forbidden.intersection(
        properties
    )

    if found:
        names = ", ".join(
            sorted(found)
        )
        raise ValueError(
            f"{surface} projection writes "
            f"forbidden Notion field(s): "
            f"{names}"
        )
