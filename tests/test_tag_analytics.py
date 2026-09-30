import datetime as dt
import unittest
from types import SimpleNamespace

from tools.tag_analytics import (
    build_tag_stats,
    display_tags,
    weakness_stats,
)


TODAY = dt.date(
    2026,
    9,
    30,
)


def make_row(
    pid,
    tags,
    *,
    solved=False,
    recall=None,
    due=None,
):
    primary = SimpleNamespace(
        meta={
            "tag": tags,
        }
    )

    state = SimpleNamespace(
        solved_on=(
            TODAY
            if solved
            else None
        ),
        recall=recall,
    )

    return (
        pid,
        [primary],
        primary,
        state,
        False,
        due,
        "",
    )


class TagAnalyticsTest(unittest.TestCase):
    def test_display_tags_marks_legacy(self):
        self.assertEqual(
            display_tags(
                "Array, Math Theory, IO"
            ),
            "I/O, Array, Math Theory (Legacy)",
        )

    def test_multi_tag_problem_counts_each_tag(self):
        rows = [
            make_row(
                "a001",
                "Array, Loops",
            )
        ]

        stats, legacy = build_tag_stats(
            rows,
            today=TODAY,
            mastery_by_pid={},
        )

        table = {
            stat.tag: stat
            for stat in stats
        }

        self.assertEqual(
            table["Loops"].total,
            1,
        )
        self.assertEqual(
            table["Array"].total,
            1,
        )
        self.assertEqual(
            legacy,
            [],
        )

    def test_stats_follow_taxonomy_order(self):
        rows = [
            make_row(
                "a001",
                "Array, Loops, Basic Syntax",
            )
        ]

        stats, _ = build_tag_stats(
            rows,
            today=TODAY,
            mastery_by_pid={},
        )

        self.assertEqual(
            [
                stat.tag
                for stat in stats
            ],
            [
                "Basic Syntax",
                "Loops",
                "Array",
            ],
        )

    def test_solved_mastered_and_low_recall(self):
        rows = [
            make_row(
                "a001",
                "Array",
                solved=True,
                recall=1,
            ),
            make_row(
                "a002",
                "Array",
                solved=True,
                recall=3,
            ),
        ]

        stats, _ = build_tag_stats(
            rows,
            today=TODAY,
            mastery_by_pid={
                "a001": "LEARNING",
                "a002": "MASTERED",
            },
        )

        stat = stats[0]

        self.assertEqual(
            stat.total,
            2,
        )
        self.assertEqual(
            stat.solved,
            2,
        )
        self.assertEqual(
            stat.mastered,
            1,
        )
        self.assertEqual(
            stat.low_recall,
            1,
        )

    def test_due_and_legacy_counts(self):
        rows = [
            make_row(
                "a001",
                "Loops, Math Theory",
                solved=True,
                recall=2,
                due=TODAY,
            ),
            make_row(
                "a002",
                "Math Theory",
            ),
        ]

        stats, legacy = build_tag_stats(
            rows,
            today=TODAY,
            mastery_by_pid={
                "a001": "PRACTICING",
            },
        )

        self.assertEqual(
            stats[0].tag,
            "Loops",
        )
        self.assertEqual(
            stats[0].due,
            1,
        )
        self.assertEqual(
            legacy,
            [
                ("Math Theory", 2),
            ],
        )

    def test_weakness_uses_observable_signals_only(self):
        rows = [
            make_row(
                "a001",
                "Array",
                solved=True,
                recall=1,
            ),
            make_row(
                "a002",
                "Loops",
                solved=True,
                recall=2,
                due=TODAY,
            ),
            make_row(
                "a003",
                "String",
                solved=True,
                recall=2,
            ),
        ]

        stats, _ = build_tag_stats(
            rows,
            today=TODAY,
            mastery_by_pid={
                "a001": "LEARNING",
                "a002": "PRACTICING",
                "a003": "PRACTICING",
            },
        )

        weak = weakness_stats(
            stats
        )

        self.assertEqual(
            [
                stat.tag
                for stat in weak
            ],
            [
                "Loops",
                "Array",
            ],
        )


if __name__ == "__main__":
    unittest.main()
