import csv
import tempfile
import unittest
from pathlib import Path

from tools.migrate_learning_v21 import migrate


class MigrationTest(unittest.TestCase):
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

    def read(self, name):
        with (self.data / name).open(
            encoding="utf-8",
            newline="",
        ) as f:
            return list(csv.DictReader(f))

    def test_finish_only(self):
        self.write(
            "progress.csv",
            "problem_id,verdict,solved,reviewed,recall\n"
            "a001,AC,2026-09-28,2026-09-28,2\n",
        )

        self.write(
            "reviews.csv",
            "problem_id,date,score,minutes,result,note\n"
            "a001,2026-09-28,2,,AC,\n",
        )

        migrate(
            self.data,
            drop_ids=set(),
        )

        p = self.read("progress.csv")[0]
        e = self.read("reviews.csv")[0]

        self.assertEqual(
            p["solved_on"],
            "2026-09-28",
        )
        self.assertEqual(
            p["last_review_on"],
            "",
        )
        self.assertEqual(
            e["event_type"],
            "finish",
        )

    def test_finish_then_review(self):
        self.write(
            "progress.csv",
            "problem_id,verdict,solved,reviewed,recall\n"
            "a001,AC,2026-09-28,2026-10-05,3\n",
        )

        self.write(
            "reviews.csv",
            "problem_id,date,score,minutes,result,note\n"
            "a001,2026-09-28,2,,AC,\n"
            "a001,2026-10-05,3,,AC,\n",
        )

        migrate(
            self.data,
            drop_ids=set(),
        )

        events = self.read("reviews.csv")
        progress = self.read("progress.csv")[0]

        self.assertEqual(
            [x["event_type"] for x in events],
            ["finish", "review"],
        )

        self.assertEqual(
            progress["last_review_on"],
            "2026-10-05",
        )

    def test_drop_test_fixtures(self):
        self.write(
            "progress.csv",
            "problem_id,verdict,solved,reviewed,recall\n"
            "a001,AC,2026-09-28,2026-09-28,3\n"
            "b001,AC,2026-09-20,2026-09-20,2\n",
        )

        self.write(
            "reviews.csv",
            "problem_id,date,score,minutes,result,note\n"
            "a001,2026-09-28,3,,AC,\n"
            "b001,2026-09-20,2,,AC,\n",
        )

        migrate(
            self.data,
            drop_ids={"a001"},
        )

        self.assertEqual(
            [x["problem_id"] for x in self.read("progress.csv")],
            ["b001"],
        )

        self.assertEqual(
            [x["problem_id"] for x in self.read("reviews.csv")],
            ["b001"],
        )

    def test_idempotent_v21(self):
        self.write(
            "progress.csv",
            "problem_id,solved_on,last_review_on,last_result,recall\n",
        )

        self.write(
            "reviews.csv",
            "problem_id,event_type,date,score,minutes,result,note\n",
        )

        first = migrate(
            self.data,
            drop_ids=set(),
        )

        second = migrate(
            self.data,
            drop_ids=set(),
        )

        self.assertTrue(
            first["already_v21"]
        )
        self.assertTrue(
            second["already_v21"]
        )


if __name__ == "__main__":
    unittest.main()
