import tempfile
import unittest
from pathlib import Path

from tools.quality_gate import (
    compare_warning_multiset,
    extract_warnings,
    load_known_warnings,
)


class QualityGateTest(unittest.TestCase):
    def test_extracts_chinese_warnings(self):
        output = (
            "題目：58 | 錯誤：0 | 警告：2\n"
            "警告： a.cpp: missing A\n"
            "警告： b.cpp: missing B\n"
        )

        self.assertEqual(
            extract_warnings(output),
            [
                "a.cpp: missing A",
                "b.cpp: missing B",
            ],
        )

    def test_known_warning_set_passes(self):
        current = [
            "a",
            "b",
        ]
        known = [
            "a",
            "b",
        ]

        unexpected, resolved = (
            compare_warning_multiset(
                current,
                known,
            )
        )

        self.assertEqual(
            unexpected,
            [],
        )
        self.assertEqual(
            resolved,
            [],
        )

    def test_resolved_warning_is_allowed(self):
        unexpected, resolved = (
            compare_warning_multiset(
                ["a"],
                ["a", "b"],
            )
        )

        self.assertEqual(
            unexpected,
            [],
        )
        self.assertEqual(
            resolved,
            ["b"],
        )

    def test_new_warning_is_rejected(self):
        unexpected, resolved = (
            compare_warning_multiset(
                ["a", "new"],
                ["a", "old"],
            )
        )

        self.assertEqual(
            unexpected,
            ["new"],
        )
        self.assertEqual(
            resolved,
            ["old"],
        )

    def test_duplicate_known_warning_is_rejected(self):
        unexpected, _ = (
            compare_warning_multiset(
                ["a", "a"],
                ["a"],
            )
        )

        self.assertEqual(
            unexpected,
            ["a"],
        )

    def test_load_known_warnings_ignores_comments(self):
        with tempfile.TemporaryDirectory() as td:
            path = (
                Path(td)
                / "warnings.txt"
            )

            path.write_text(
                "# comment\n"
                "\n"
                "warning one\n"
                "warning two\n",
                encoding="utf-8",
            )

            self.assertEqual(
                load_known_warnings(
                    path
                ),
                [
                    "warning one",
                    "warning two",
                ],
            )


if __name__ == "__main__":
    unittest.main()
