import csv
import tempfile
import unittest
from pathlib import Path

from tools.catalog_store import (
    CatalogError,
    CatalogStore,
    ProblemMeta,
    SolutionMeta,
)


class CatalogStoreTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data = Path(self.temp.name) / "data"
        self.data.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, text):
        (self.data / name).write_text(
            text,
            encoding="utf-8",
        )

    def valid_catalog(self):
        self.write(
            "problems.csv",
            "problem_id,title,source,difficulty,tags\n"
            'a001,Hello,,1,"Basic Syntax, IO"\n'
            "1621,Distinct Values,,,\n",
        )
        self.write(
            "solutions.csv",
            "problem_id,path,language,complexity\n"
            "a001,solutions/a001.cpp,cpp,O(1)\n"
            "1621,solutions/1621.cpp,cpp,\n",
        )

    def test_loads_valid_catalog(self):
        self.valid_catalog()
        store = CatalogStore(self.data)

        problems = store.load_problems()
        solutions = store.load_solutions()

        self.assertEqual(
            sorted(problems),
            ["1621", "a001"],
        )
        self.assertEqual(
            problems["a001"].tag_list,
            ["Basic Syntax", "IO"],
        )
        self.assertEqual(
            len(solutions),
            2,
        )

    def test_note_url_is_not_part_of_schema(self):
        self.write(
            "problems.csv",
            "problem_id,title,source,difficulty,tags,note_url\n"
            "a001,Hello,,1,Basic Syntax,https://example.com\n",
        )
        self.write(
            "solutions.csv",
            "problem_id,path,language,complexity\n",
        )

        with self.assertRaises(CatalogError):
            CatalogStore(self.data).load_problems()

    def test_duplicate_problem_rejected(self):
        self.write(
            "problems.csv",
            "problem_id,title,source,difficulty,tags\n"
            "a001,One,,1,\n"
            "a001,Two,,1,\n",
        )
        self.write(
            "solutions.csv",
            "problem_id,path,language,complexity\n",
        )

        with self.assertRaises(CatalogError):
            CatalogStore(self.data).load_problems()

    def test_unknown_problem_reference_reported(self):
        self.write(
            "problems.csv",
            "problem_id,title,source,difficulty,tags\n"
            "a001,Hello,,1,\n",
        )
        self.write(
            "solutions.csv",
            "problem_id,path,language,complexity\n"
            "b001,solutions/b001.cpp,cpp,O(1)\n",
        )

        errors = CatalogStore(self.data).validate()

        self.assertTrue(
            any(
                "unknown problem_id b001" in item
                for item in errors
            )
        )

    def test_missing_solution_reported(self):
        self.write(
            "problems.csv",
            "problem_id,title,source,difficulty,tags\n"
            "a001,Hello,,1,\n",
        )
        self.write(
            "solutions.csv",
            "problem_id,path,language,complexity\n",
        )

        errors = CatalogStore(self.data).validate()

        self.assertIn(
            "a001: no solution registered",
            errors,
        )

    def test_missing_solution_file_reported(self):
        self.valid_catalog()

        root = Path(self.temp.name) / "repo"
        root.mkdir()

        errors = CatalogStore(
            self.data
        ).validate(root=root)

        self.assertEqual(
            sum("solution file missing" in x for x in errors),
            2,
        )

    def test_create_problem_with_solution(self):
        self.valid_catalog()
        store = CatalogStore(self.data)

        store.create_problem_with_solution(
            ProblemMeta(
                "b130",
                "Random Number",
                "ZeroJudge",
                "2",
                " Sorting, Set, Sorting ",
            ),
            SolutionMeta(
                "b130",
                "solutions/b130.cpp",
                "CPP",
                "O(N log N)",
            ),
        )

        problems = store.load_problems()
        solutions = store.load_solutions()

        self.assertEqual(
            problems["b130"].tags,
            "Sorting, Set",
        )
        self.assertTrue(
            any(
                item.problem_id == "b130"
                and item.path == "solutions/b130.cpp"
                and item.language == "cpp"
                for item in solutions
            )
        )

    def test_create_rejects_duplicate_problem_without_mutation(self):
        self.valid_catalog()
        store = CatalogStore(self.data)
        before_problems = self.data.joinpath(
            "problems.csv"
        ).read_bytes()
        before_solutions = self.data.joinpath(
            "solutions.csv"
        ).read_bytes()

        with self.assertRaises(CatalogError):
            store.create_problem_with_solution(
                ProblemMeta("a001", "Duplicate"),
                SolutionMeta(
                    "a001",
                    "solutions/duplicate.cpp",
                    "cpp",
                ),
            )

        self.assertEqual(
            self.data.joinpath("problems.csv").read_bytes(),
            before_problems,
        )
        self.assertEqual(
            self.data.joinpath("solutions.csv").read_bytes(),
            before_solutions,
        )

    def test_create_rejects_mismatched_problem_id(self):
        self.valid_catalog()
        store = CatalogStore(self.data)

        with self.assertRaises(CatalogError):
            store.create_problem_with_solution(
                ProblemMeta("b001", "One"),
                SolutionMeta(
                    "b002",
                    "solutions/b001.cpp",
                    "cpp",
                ),
            )

    def test_invalid_difficulty_is_rejected(self):
        self.valid_catalog()
        store = CatalogStore(self.data)

        with self.assertRaises(CatalogError):
            store.create_problem_with_solution(
                ProblemMeta(
                    "b001",
                    "Bad",
                    difficulty="9",
                ),
                SolutionMeta(
                    "b001",
                    "solutions/b001.cpp",
                    "cpp",
                ),
            )

    def test_unsafe_solution_path_is_rejected(self):
        self.valid_catalog()
        store = CatalogStore(self.data)

        with self.assertRaises(CatalogError):
            store.create_problem_with_solution(
                ProblemMeta("b001", "Bad Path"),
                SolutionMeta(
                    "b001",
                    "../outside.cpp",
                    "cpp",
                ),
            )

    def test_update_problem_and_solution(self):
        self.valid_catalog()
        store = CatalogStore(self.data)

        store.update_problem(
            ProblemMeta(
                "a001",
                "Hello Updated",
                "ZeroJudge",
                "2",
                "Basic Syntax, IO",
            )
        )
        store.update_solution(
            SolutionMeta(
                "a001",
                "solutions/a001.cpp",
                "cpp",
                "O(N)",
            )
        )

        self.assertEqual(
            store.load_problems()["a001"].title,
            "Hello Updated",
        )

        solution = next(
            item
            for item in store.load_solutions()
            if item.path == "solutions/a001.cpp"
        )

        self.assertEqual(
            solution.complexity,
            "O(N)",
        )

    def test_add_solution_to_existing_problem(self):
        self.valid_catalog()
        store = CatalogStore(self.data)

        store.add_solution(
            SolutionMeta(
                "a001",
                "solutions/a001.py",
                "PYTHON",
                "O(1)",
            )
        )

        solutions = store.load_solutions()

        self.assertTrue(
            any(
                item.problem_id == "a001"
                and item.path == "solutions/a001.py"
                and item.language == "python"
                for item in solutions
            )
        )

    def test_add_solution_rejects_unknown_problem_without_mutation(self):
        self.valid_catalog()
        store = CatalogStore(self.data)
        before = self.data.joinpath("solutions.csv").read_bytes()

        with self.assertRaises(CatalogError):
            store.add_solution(
                SolutionMeta(
                    "z999",
                    "solutions/z999.cpp",
                    "cpp",
                )
            )

        self.assertEqual(
            self.data.joinpath("solutions.csv").read_bytes(),
            before,
        )

    def test_add_solution_rejects_duplicate_path_without_mutation(self):
        self.valid_catalog()
        store = CatalogStore(self.data)
        before = self.data.joinpath("solutions.csv").read_bytes()

        with self.assertRaises(CatalogError):
            store.add_solution(
                SolutionMeta(
                    "a001",
                    "solutions/a001.cpp",
                    "cpp",
                )
            )

        self.assertEqual(
            self.data.joinpath("solutions.csv").read_bytes(),
            before,
        )

    def test_load_rejects_invalid_problem_id(self):
        self.write(
            "problems.csv",
            "problem_id,title,source,difficulty,tags\n"
            "bad-id,Bad,,1,\n",
        )
        self.write(
            "solutions.csv",
            "problem_id,path,language,complexity\n",
        )

        with self.assertRaises(CatalogError):
            CatalogStore(
                self.data
            ).load_problems()

    def test_load_rejects_invalid_difficulty(self):
        self.write(
            "problems.csv",
            "problem_id,title,source,difficulty,tags\n"
            "a001,Bad,,9,\n",
        )
        self.write(
            "solutions.csv",
            "problem_id,path,language,complexity\n"
            "a001,solutions/a001.cpp,cpp,\n",
        )

        with self.assertRaises(CatalogError):
            CatalogStore(
                self.data
            ).load_problems()

    def test_load_rejects_language_extension_mismatch(self):
        self.write(
            "problems.csv",
            "problem_id,title,source,difficulty,tags\n"
            "a001,Hello,,1,\n",
        )
        self.write(
            "solutions.csv",
            "problem_id,path,language,complexity\n"
            "a001,solutions/a001.py,cpp,\n",
        )

        with self.assertRaises(CatalogError):
            CatalogStore(
                self.data
            ).load_solutions()

    def test_windows_absolute_solution_path_is_rejected(self):
        self.valid_catalog()
        store = CatalogStore(self.data)

        with self.assertRaises(CatalogError):
            store.add_solution(
                SolutionMeta(
                    "a001",
                    "C:/temp/a001.cpp",
                    "cpp",
                )
            )

    def test_create_pair_rolls_back_when_second_write_fails(self):
        self.valid_catalog()
        store = CatalogStore(self.data)

        before_problems = (
            store.problems_path.read_bytes()
        )
        before_solutions = (
            store.solutions_path.read_bytes()
        )

        original_write = store._write_rows
        calls = {"count": 0}

        def fail_second(path, fields, rows):
            calls["count"] += 1

            if calls["count"] == 2:
                raise OSError(
                    "simulated second write failure"
                )

            return original_write(
                path,
                fields,
                rows,
            )

        store._write_rows = fail_second

        with self.assertRaises(OSError):
            store.create_problem_with_solution(
                ProblemMeta(
                    "b001",
                    "Atomic Create",
                    difficulty="2",
                ),
                SolutionMeta(
                    "b001",
                    "solutions/b001.cpp",
                    "cpp",
                    "O(1)",
                ),
            )

        self.assertEqual(
            store.problems_path.read_bytes(),
            before_problems,
        )
        self.assertEqual(
            store.solutions_path.read_bytes(),
            before_solutions,
        )

    def test_update_pair_updates_both_catalogs(self):
        self.valid_catalog()
        store = CatalogStore(self.data)

        store.update_problem_with_solution(
            ProblemMeta(
                "a001",
                "Updated",
                "ZeroJudge",
                "3",
                "Basic Syntax, I/O",
            ),
            SolutionMeta(
                "a001",
                "solutions/a001.cpp",
                "cpp",
                "O(N)",
            ),
        )

        problem = (
            store.load_problems()["a001"]
        )
        solution = next(
            item
            for item in store.load_solutions()
            if item.path
            == "solutions/a001.cpp"
        )

        self.assertEqual(
            problem.title,
            "Updated",
        )
        self.assertEqual(
            problem.difficulty,
            "3",
        )
        self.assertEqual(
            solution.complexity,
            "O(N)",
        )

    def test_update_pair_rolls_back_when_second_write_fails(self):
        self.valid_catalog()
        store = CatalogStore(self.data)

        before_problems = (
            store.problems_path.read_bytes()
        )
        before_solutions = (
            store.solutions_path.read_bytes()
        )

        original_write = store._write_rows
        calls = {"count": 0}

        def fail_second(path, fields, rows):
            calls["count"] += 1

            if calls["count"] == 2:
                raise OSError(
                    "simulated second write failure"
                )

            return original_write(
                path,
                fields,
                rows,
            )

        store._write_rows = fail_second

        with self.assertRaises(OSError):
            store.update_problem_with_solution(
                ProblemMeta(
                    "a001",
                    "Should Roll Back",
                    difficulty="5",
                ),
                SolutionMeta(
                    "a001",
                    "solutions/a001.cpp",
                    "cpp",
                    "O(N^2)",
                ),
            )

        self.assertEqual(
            store.problems_path.read_bytes(),
            before_problems,
        )
        self.assertEqual(
            store.solutions_path.read_bytes(),
            before_solutions,
        )
