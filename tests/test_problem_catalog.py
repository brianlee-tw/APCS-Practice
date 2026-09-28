import csv
import tempfile
import unittest
from pathlib import Path

from tools.problem_catalog import (
    scan_repository,
    write_preview,
)


class ProblemCatalogTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        path.write_text(
            text,
            encoding="utf-8",
        )
        return path

    def rows(self, path):
        with path.open(
            encoding="utf-8",
            newline="",
        ) as handle:
            return list(
                csv.DictReader(handle)
            )

    def test_migrates_catalog_fields_and_drops_legacy_note(self):
        self.write(
            "solutions/b130_Random_Number.cpp",
            "// APCS Title: b130. 明明的隨機數\n"
            "// APCS Complexity: O(N log N)\n"
            "// APCS Tag: Sorting, Set\n"
            "// APCS Difficulty: 1\n"
            "// APCS Source: https://example.test/b130\n"
            "// APCS Note: https://notion.test/legacy\n"
            "// APCS Date: 26-07-01\n"
            "#include <iostream>\n",
        )

        problems, solutions, issues = scan_repository(
            self.root
        )

        self.assertEqual(len(problems), 1)
        self.assertEqual(len(solutions), 1)
        self.assertEqual(issues, [])

        self.assertEqual(
            problems[0],
            {
                "problem_id": "b130",
                "title": "明明的隨機數",
                "source": "https://example.test/b130",
                "difficulty": "1",
                "tags": "Sorting, Set",
            },
        )

        self.assertNotIn(
            "note_url",
            problems[0],
        )
        self.assertEqual(
            solutions[0]["complexity"],
            "O(N log N)",
        )

    def test_numeric_problem_id_is_supported(self):
        self.write(
            "legacy/1621_Distinct_Values.cpp",
            "#include <iostream>\n",
        )

        problems, solutions, issues = scan_repository(
            self.root
        )

        self.assertEqual(
            problems[0]["problem_id"],
            "1621",
        )
        self.assertEqual(
            solutions[0]["problem_id"],
            "1621",
        )
        self.assertEqual(issues, [])

    def test_title_id_mismatch_keeps_filename_id(self):
        self.write(
            "legacy/b965_Matrix.cpp",
            "// APCS Title: c291. 矩陣翻轉\n"
            "// APCS Complexity: O(N)\n",
        )

        problems, solutions, issues = scan_repository(
            self.root
        )

        self.assertEqual(
            problems[0]["problem_id"],
            "b965",
        )
        self.assertEqual(
            problems[0]["title"],
            "矩陣翻轉",
        )
        self.assertEqual(
            solutions[0]["problem_id"],
            "b965",
        )
        self.assertEqual(
            [x.code for x in issues],
            ["TITLE_ID_MISMATCH"],
        )

    def test_missing_metadata_remains_blank(self):
        self.write(
            "legacy/a038_Number_Reverse.cpp",
            "#include <iostream>\n",
        )

        problems, solutions, issues = scan_repository(
            self.root
        )

        self.assertEqual(
            problems[0]["title"],
            "",
        )
        self.assertEqual(
            problems[0]["difficulty"],
            "",
        )
        self.assertEqual(
            problems[0]["tags"],
            "",
        )
        self.assertEqual(
            solutions[0]["complexity"],
            "",
        )
        self.assertEqual(issues, [])

    def test_multiple_solutions_share_one_problem(self):
        self.write(
            "legacy/a010_Prime.cpp",
            "// APCS Title: a010. 因數分解\n"
            "// APCS Tag: Math\n"
            "// APCS Difficulty: 2\n"
            "// APCS Complexity: O(sqrt(N))\n",
        )
        self.write(
            "legacy/a010_Prime.py",
            "# APCS Title: a010. 因數分解\n"
            "# APCS Tag: Math\n"
            "# APCS Difficulty: 2\n"
            "# APCS Complexity: O(sqrt(N))\n",
        )

        problems, solutions, issues = scan_repository(
            self.root
        )

        self.assertEqual(len(problems), 1)
        self.assertEqual(len(solutions), 2)
        self.assertEqual(
            {x["language"] for x in solutions},
            {"cpp", "python"},
        )
        self.assertEqual(issues, [])

    def test_conflicting_problem_metadata_is_reported(self):
        self.write(
            "legacy/a010_A.cpp",
            "// APCS Title: a010. Alpha\n",
        )
        self.write(
            "legacy/a010_B.py",
            "# APCS Title: a010. Beta\n",
        )

        _, _, issues = scan_repository(
            self.root
        )

        self.assertEqual(
            [x.code for x in issues],
            ["PROBLEM_METADATA_CONFLICT"],
        )

    def test_preview_writes_only_requested_directory(self):
        self.write(
            "legacy/a001_Hello.cpp",
            "// APCS Title: a001. 哈囉\n"
            "// APCS Complexity: O(1)\n",
        )

        preview = self.root / "preview"

        counts = write_preview(
            self.root,
            preview,
        )

        self.assertEqual(
            counts,
            (1, 1, 0),
        )
        self.assertTrue(
            (preview / "problems.csv").is_file()
        )
        self.assertTrue(
            (preview / "solutions.csv").is_file()
        )
        self.assertTrue(
            (preview / "issues.txt").is_file()
        )

        self.assertEqual(
            self.rows(
                preview / "problems.csv"
            )[0]["problem_id"],
            "a001",
        )


if __name__ == "__main__":
    unittest.main()
