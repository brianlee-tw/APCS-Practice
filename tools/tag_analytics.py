#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
from collections import Counter
from dataclasses import dataclass

try:
    from .tag_taxonomy import (
        TAG_GROUPS,
        split_tags,
    )
except ImportError:
    from tag_taxonomy import (
        TAG_GROUPS,
        split_tags,
    )


@dataclass
class TagStat:
    group: str
    tag: str
    total: int = 0
    solved: int = 0
    mastered: int = 0
    low_recall: int = 0
    due: int = 0


TAG_TO_GROUP = {
    tag: group
    for group, tags in TAG_GROUPS
    for tag in tags
}

TAG_ORDER = tuple(
    tag
    for _, tags in TAG_GROUPS
    for tag in tags
)


def display_tags(value: str) -> str:
    canonical, unknown = split_tags(
        value
    )

    selected = set(
        canonical
    )

    ordered = [
        tag
        for tag in TAG_ORDER
        if tag in selected
    ]

    labels = [
        *ordered,
        *(
            f"{tag} (Legacy)"
            for tag in unknown
        ),
    ]

    return ", ".join(labels) or "—"


def build_tag_stats(
    rows,
    *,
    today: dt.date,
    mastery_by_pid: dict[str, str],
) -> tuple[
    list[TagStat],
    list[tuple[str, int]],
]:
    stats = {
        tag: TagStat(
            group=TAG_TO_GROUP[tag],
            tag=tag,
        )
        for tag in TAG_ORDER
    }

    legacy = Counter()

    for row in rows:
        pid = row[0]
        primary = row[2]
        state = row[3]
        due_on = row[5]

        canonical, unknown = split_tags(
            primary.meta.get(
                "tag",
                "",
            )
        )

        for tag in unknown:
            legacy[tag] += 1

        solved = bool(
            state.solved_on
        )

        is_due = bool(
            solved
            and due_on
            and due_on <= today
        )

        low_recall = bool(
            solved
            and state.recall is not None
            and state.recall <= 1
        )

        mastered = (
            solved
            and mastery_by_pid.get(pid)
            == "MASTERED"
        )

        for tag in canonical:
            stat = stats[tag]

            stat.total += 1
            stat.solved += int(solved)
            stat.mastered += int(
                mastered
            )
            stat.low_recall += int(
                low_recall
            )
            stat.due += int(
                is_due
            )

    active = [
        stats[tag]
        for tag in TAG_ORDER
        if stats[tag].total
    ]

    legacy_rows = sorted(
        legacy.items(),
        key=lambda item: (
            -item[1],
            item[0].lower(),
        ),
    )

    return active, legacy_rows


def weakness_stats(
    stats: list[TagStat],
) -> list[TagStat]:
    """
    Only evidence-based weakness signals:

    - at least one solved problem with Recall 0-1, or
    - at least one due/overdue problem.

    No opaque synthetic score is created.
    """

    result = [
        stat
        for stat in stats
        if (
            stat.low_recall > 0
            or stat.due > 0
        )
    ]

    return sorted(
        result,
        key=lambda stat: (
            -stat.due,
            -stat.low_recall,
            TAG_ORDER.index(
                stat.tag
            ),
        ),
    )
