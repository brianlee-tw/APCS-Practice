import csv
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ApcsCatalogRuntimeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data = Path(self.temp.name) / "data"
        self.data.mkdir()

        (self.data / "progress.csv").write_text(
            "problem_id,solved_on,last_review_on,last_result,recall\n",
            encoding="utf-8",
        )
        (self.data / "reviews.csv").write_text(
            "problem_id,event_type,date,score,minutes,result,note\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp.cleanup()

    def write_catalog(self, problem_row, solution_row):
        with (self.data / "problems.csv").open(
            "w",
            encoding="utf-8",
            newline="",
        ) as f:
            writer = csv.writer(f, lineterminator="\n")
            writer.writerow(
                ["problem_id", "title", "source", "difficulty", "tags"]
            )
            writer.writerow(problem_row)

        with (self.data / "solutions.csv").open(
            "w",
            encoding="utf-8",
            newline="",
        ) as f:
            writer = csv.writer(f, lineterminator="\n")
            writer.writerow(
                ["problem_id", "path", "language", "complexity"]
            )
            writer.writerow(solution_row)

    def run_code(self, code):
        env = os.environ.copy()
        env["APCS_DATA_DIR"] = str(self.data)

        return subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_catalog_overrides_source_header_and_drops_notion(self):
        self.write_catalog(
            ["b130", "CATALOG TITLE", "", "4", "CatalogTag"],
            [
                "b130",
                "01_Basic_Syntax_Optimization/b130_Random_Number.cpp",
                "cpp",
                "O(CATALOG)",
            ],
        )

        result = self.run_code(
            "import tools.apcs as a; "
            "rows,w=a.build(); r=rows[0]; "
            "print(r[2].title); "
            "print(r[2].complexity); "
            "print(','.join(r[2].tags)); "
            "print('Notion' in a.render_index(rows)); "
            "print(len(w))"
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.strip().splitlines(),
            [
                "CATALOG TITLE",
                "O(CATALOG)",
                "CatalogTag",
                "False",
                "0",
            ],
        )

    def test_blank_difficulty_is_not_invented(self):
        self.write_catalog(
            ["1621", "Distinct Values", "", "", "Set"],
            [
                "1621",
                "02_Data_Structures/1621_Distinct_Values.cpp",
                "cpp",
                "O(N log N)",
            ],
        )

        result = self.run_code(
            "import tools.apcs as a; "
            "rows,w=a.build(); "
            "r=rows[0]; "
            "print(r[2].difficulty is None); "
            "print(a.render_index(rows).splitlines()[-1])"
        )

        self.assertEqual(
            result.returncode,
            0,
            result.stderr,
        )

        lines = result.stdout.strip().splitlines()

        self.assertEqual(
            lines[0],
            "True",
        )

        self.assertIn(
            "`O(N log N)` | — |",
            lines[1],
        )


    def test_numeric_problem_id_is_runtime_compatible(self):
        self.write_catalog(
            ["1621", "Distinct Values", "", "2", "Set"],
            [
                "1621",
                "02_Data_Structures/1621_Distinct_Values.cpp",
                "cpp",
                "O(N log N)",
            ],
        )

        result = self.run_code(
            "import tools.apcs as a; "
            "print(a.norm('1621')); "
            "print('1621' in a.known_problem_ids())"
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.strip().splitlines(),
            ["1621", "True"],
        )

    def test_missing_catalog_is_hard_failure(self):
        result = self.run_code(
            """import tools.apcs as a
from tools.catalog_store import CatalogError

try:
    a.build()
except CatalogError as exc:
    print("CATALOG_REQUIRED")
    print("catalog file missing" in str(exc))
else:
    print("FALLBACK_USED")
"""
        )

        self.assertEqual(
            result.returncode,
            0,
            result.stderr,
        )

        self.assertEqual(
            result.stdout.strip().splitlines(),
            [
                "CATALOG_REQUIRED",
                "True",
            ],
        )


if __name__ == "__main__":
    unittest.main()
