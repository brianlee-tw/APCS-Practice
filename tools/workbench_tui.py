#!/usr/bin/env python3
from __future__ import annotations

import shutil
import unicodedata
from dataclasses import dataclass


RESET = "\033[0m"
BOLD = "\033[1m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
WHITE = "\033[97m"
GRAY = "\033[90m"


def char_width(ch: str) -> int:
    if unicodedata.combining(ch):
        return 0
    return (
        2
        if unicodedata.east_asian_width(ch)
        in {"W", "F"}
        else 1
    )


def display_width(text: str) -> int:
    return sum(
        char_width(ch)
        for ch in str(text)
    )


def fit(
    text: str,
    width: int,
) -> str:
    width = max(1, int(width))
    text = str(text)

    if display_width(text) <= width:
        return text

    result = ""
    used = 0

    for ch in text:
        size = char_width(ch)
        if used + size + 1 > width:
            break
        result += ch
        used += size

    return result + "…"


def pad(
    text: str,
    width: int,
) -> str:
    clipped = fit(
        text,
        width,
    )
    return (
        clipped
        + " " * max(
            0,
            width
            - display_width(clipped),
        )
    )


def wrap(
    text: str,
    width: int,
) -> list[str]:
    width = max(1, int(width))
    result: list[str] = []

    for paragraph in str(text).split("\n"):
        if paragraph == "":
            result.append("")
            continue

        current = ""
        used = 0

        for ch in paragraph:
            size = char_width(ch)
            if (
                current
                and used + size > width
            ):
                result.append(current)
                current = ""
                used = 0
            current += ch
            used += size

        result.append(current)

    return result or [""]


def terminal_width() -> int:
    columns = shutil.get_terminal_size(
        (100, 42)
    ).columns
    return min(
        96,
        max(32, columns - 2),
    )


def terminal_height() -> int:
    rows = shutil.get_terminal_size(
        (100, 42)
    ).lines
    return max(
        18,
        min(42, rows - 1),
    )


def clear() -> None:
    print(
        "\033[2J\033[H",
        end="",
        flush=True,
    )


def rule(
    width: int | None = None,
) -> str:
    return "─" * (
        width
        if width is not None
        else terminal_width()
    )


def heading(
    title: str,
    *,
    suffix: str = "",
) -> None:
    width = terminal_width()
    left = f"APCS · {title}"
    if suffix:
        space = max(
            1,
            width
            - display_width(left)
            - display_width(suffix),
        )
        print(
            f"{CYAN}{BOLD}{left}{RESET}"
            + " " * space
            + suffix
        )
    else:
        print(
            f"{CYAN}{BOLD}{left}{RESET}"
        )
    print(rule(width))


def status_badge(
    label: str,
    *,
    status: str,
) -> str:
    color = {
        "ok": GREEN,
        "warn": YELLOW,
        "error": RED,
        "focus": CYAN,
        "neutral": GRAY,
    }.get(
        status,
        GRAY,
    )
    return (
        f"{color}{BOLD}"
        f"[ {label} ]"
        f"{RESET}"
    )


@dataclass(frozen=True)
class PaneSpec:
    width: int
    title: str


def pane_widths(
    total: int,
    ratios: tuple[int, ...],
    *,
    gap: int = 3,
    min_width: int = 16,
) -> tuple[int, ...]:
    if not ratios:
        return ()

    usable = (
        total
        - gap * (len(ratios) - 1)
    )
    raw_total = sum(ratios)
    widths = [
        max(
            min_width,
            usable * ratio // raw_total,
        )
        for ratio in ratios
    ]

    overflow = (
        sum(widths) - usable
    )
    while overflow > 0:
        index = max(
            range(len(widths)),
            key=lambda i: widths[i],
        )
        if widths[index] <= min_width:
            break
        widths[index] -= 1
        overflow -= 1

    while sum(widths) < usable:
        widths[-1] += 1

    return tuple(widths)


def render_columns(
    columns: list[list[str]],
    widths: tuple[int, ...],
    *,
    gap: int = 3,
) -> list[str]:
    rows = max(
        (len(column) for column in columns),
        default=0,
    )
    result = []

    for row in range(rows):
        cells = []
        for index, column in enumerate(
            columns
        ):
            value = (
                column[row]
                if row < len(column)
                else ""
            )
            cells.append(
                pad(
                    value,
                    widths[index],
                )
            )
        result.append(
            (" " * gap).join(cells)
        )

    return result


def command_bar(
    commands: list[tuple[str, str]],
) -> None:
    print(rule())
    parts = [
        f"{key} {label}"
        for key, label in commands
    ]
    print(
        f"{GRAY}"
        + " · ".join(parts)
        + f"{RESET}"
    )
