import tempfile
import unittest
from pathlib import Path

from tools.apcs_control import (
    add_solution_asset,
    create_problem_assets,
    finish_with_optional_complexity,
    missing_finish_complexity,
    next_solution_path,
    normalize_problem_id,
    solution_template,
)
from tools.catalog_store import (
    CatalogError,
    CatalogStore,
    ProblemMeta,
    SolutionMeta,
)


class ApcsControlCatalogTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data = self.root / "data"
        self.data.mkdir()

        (self.data / "problems.csv").write_text(
            "problem_id,title,source,difficulty,tags\n"
            "a001,Hello,,1,Basic Syntax\n",
            encoding="utf-8",
        )
        (self.data / "solutions.csv").write_text(
            "problem_id,path,language,complexity\n"
            "a001,solutions/a001_old.cpp,cpp,O(1)\n",
            encoding="utf-8",
        )
        self.store = CatalogStore(self.data)

    def tearDown(self):
        self.temp.cleanup()

    def test_normalize_problem_id_supports_numeric(self):
        self.assertEqual(normalize_problem_id("B130"), "b130")
        self.assertEqual(normalize_problem_id("1621"), "1621")

        with self.assertRaises(CatalogError):
            normalize_problem_id("bad-id")

    def test_solution_templates_are_metadata_free(self):
        cpp = solution_template("cpp")
        py = solution_template("python")

        self.assertNotIn("APCS ", cpp)
        self.assertNotIn("APCS ", py)
        self.assertIn("int main()", cpp)
        self.assertIn("def main()", py)

    def test_next_solution_path_avoids_overwrite(self):
        folder = self.root / "solutions"
        folder.mkdir()
        (folder / "1621.cpp").write_text("", encoding="utf-8")

        target = next_solution_path(
            "1621",
            "cpp",
            root=self.root,
        )

        self.assertEqual(
            target.relative_to(self.root).as_posix(),
            "solutions/1621_2.cpp",
        )

    def test_create_problem_assets_updates_catalog_and_file(self):
        target = create_problem_assets(
            ProblemMeta(
                "b130",
                "Random Number",
                "ZeroJudge",
                "2",
                "Sorting, Set",
            ),
            "cpp",
            "O(N log N)",
            root=self.root,
            store=self.store,
        )

        self.assertTrue(target.is_file())
        self.assertNotIn(
            "APCS ",
            target.read_text(encoding="utf-8"),
        )

        problems = self.store.load_problems()
        solutions = self.store.load_solutions()

        self.assertEqual(problems["b130"].title, "Random Number")
        self.assertTrue(
            any(
                item.problem_id == "b130"
                and item.path == "solutions/b130.cpp"
                for item in solutions
            )
        )

    def test_create_problem_assets_rolls_back_source_on_catalog_error(self):
        with self.assertRaises(CatalogError):
            create_problem_assets(
                ProblemMeta("a001", "Duplicate"),
                "python",
                root=self.root,
                store=self.store,
            )

        self.assertFalse(
            (self.root / "solutions" / "a001.py").exists()
        )

    def test_add_solution_asset_updates_existing_problem(self):
        target = add_solution_asset(
            "a001",
            "python",
            "O(N)",
            root=self.root,
            store=self.store,
        )

        self.assertTrue(target.is_file())

        solutions = self.store.load_solutions()

        self.assertTrue(
            any(
                item.problem_id == "a001"
                and item.path == "solutions/a001.py"
                and item.complexity == "O(N)"
                for item in solutions
            )
        )



    def test_missing_finish_complexity_detects_blank(self):
        self.store.update_solution(
            SolutionMeta(
                "a001",
                "solutions/a001_old.cpp",
                "cpp",
                "",
            )
        )

        problem = {
            "path": str(
                self.root
                / "solutions"
                / "a001_old.cpp"
            )
        }

        solution = missing_finish_complexity(
            problem,
            store=self.store,
            root=self.root,
        )

        self.assertIsNotNone(solution)
        self.assertEqual(
            solution.path,
            "solutions/a001_old.cpp",
        )

    def test_missing_finish_complexity_skips_existing(self):
        problem = {
            "path": str(
                self.root
                / "solutions"
                / "a001_old.cpp"
            )
        }

        self.assertIsNone(
            missing_finish_complexity(
                problem,
                store=self.store,
                root=self.root,
            )
        )

    def test_finish_complexity_is_saved_on_success(self):
        self.store.update_solution(
            SolutionMeta(
                "a001",
                "solutions/a001_old.cpp",
                "cpp",
                "",
            )
        )

        original = next(
            item
            for item in self.store.load_solutions()
            if item.path
            == "solutions/a001_old.cpp"
        )

        calls = []

        def runner(pid, score, *, minutes=None):
            calls.append(
                (pid, score, minutes)
            )
            return 0

        result = finish_with_optional_complexity(
            "a001",
            2,
            minutes=17,
            complexity_solution=original,
            complexity="O(N)",
            store=self.store,
            finish_runner=runner,
        )

        self.assertEqual(result, 0)
        self.assertEqual(
            calls,
            [("a001", 2, 17)],
        )

        updated = next(
            item
            for item in self.store.load_solutions()
            if item.path
            == "solutions/a001_old.cpp"
        )

        self.assertEqual(
            updated.complexity,
            "O(N)",
        )

    def test_finish_failure_rolls_back_complexity(self):
        self.store.update_solution(
            SolutionMeta(
                "a001",
                "solutions/a001_old.cpp",
                "cpp",
                "",
            )
        )

        original = next(
            item
            for item in self.store.load_solutions()
            if item.path
            == "solutions/a001_old.cpp"
        )

        def runner(pid, score, *, minutes=None):
            raise SystemExit(
                "simulated Finish failure"
            )

        with self.assertRaises(SystemExit):
            finish_with_optional_complexity(
                "a001",
                2,
                minutes=10,
                complexity_solution=original,
                complexity="O(N log N)",
                store=self.store,
                finish_runner=runner,
            )

        rolled_back = next(
            item
            for item in self.store.load_solutions()
            if item.path
            == "solutions/a001_old.cpp"
        )

        self.assertEqual(
            rolled_back.complexity,
            "",
        )


if __name__ == "__main__":
    unittest.main()
