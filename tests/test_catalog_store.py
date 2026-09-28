import csv
import tempfile
import unittest
from pathlib import Path

from tools.catalog_store import (
    CatalogError,
    CatalogStore,
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
