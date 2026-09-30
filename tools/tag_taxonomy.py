#!/usr/bin/env python3
from __future__ import annotations

TAG_GROUPS = (
    (
        "基礎",
        (
            "Basic Syntax",
            "I/O",
            "Conditionals",
            "Loops",
            "Simulation",
        ),
    ),
    (
        "資料結構",
        (
            "Array",
            "Vector",
            "String",
            "Struct",
            "Stack",
            "Queue",
            "Set",
            "Map",
        ),
    ),
    (
        "演算法",
        (
            "Sorting",
            "Searching",
            "Binary Search",
            "Prefix Sum",
            "Two Pointers",
            "Greedy",
        ),
    ),
    (
        "數學",
        (
            "Math",
            "Number Theory",
            "Prime",
            "GCD / LCM",
            "Geometry",
            "Combinatorics",
        ),
    ),
    (
        "圖論",
        (
            "Graph",
            "BFS",
            "DFS",
            "Shortest Path",
        ),
    ),
    (
        "進階",
        (
            "Dynamic Programming",
            "Recursion",
            "Backtracking",
        ),
    ),
)

TAG_ALIASES = {
    "io": "I/O",
    "io optimization": "I/O",
    "i/o": "I/O",
    "i/o optimization": "I/O",
}

CANONICAL_TAGS = tuple(
    tag
    for _, tags in TAG_GROUPS
    for tag in tags
)
CANONICAL_SET = frozenset(CANONICAL_TAGS)


def _alias(tag: str) -> str:
    cleaned = str(tag).strip()
    return TAG_ALIASES.get(cleaned.lower(), cleaned)


def parse_tags(value: str) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []

    for raw in str(value).split(","):
        tag = _alias(raw)

        if tag and tag not in seen:
            seen.add(tag)
            result.append(tag)

    return result


def normalize_tags(value: str) -> str:
    return ", ".join(parse_tags(value))


def split_tags(value: str) -> tuple[list[str], list[str]]:
    canonical: list[str] = []
    unknown: list[str] = []

    for tag in parse_tags(value):
        if tag in CANONICAL_SET:
            canonical.append(tag)
        else:
            unknown.append(tag)

    return canonical, unknown


def serialize_selection(
    selected: set[str] | list[str] | tuple[str, ...],
    unknown: list[str] | tuple[str, ...] = (),
) -> str:
    chosen = set(selected)
    result = [
        tag
        for tag in CANONICAL_TAGS
        if tag in chosen
    ]

    for tag in unknown:
        tag = _alias(tag)
        if tag and tag not in result:
            result.append(tag)

    return ", ".join(result)
