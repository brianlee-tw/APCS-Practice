import csv
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APCS = ROOT / "tools" / "apcs.py"


class ApcsIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data = Path(self.temp.name) / "data"

        self.production_files = [
            ROOT / "data" / "progress.csv",
            ROOT / "data" / "reviews.csv",
            ROOT / "README.md",
            ROOT / "docs" / "PROBLEM_INDEX.md",
            ROOT / "docs" / "REVIEW_QUEUE.md",
        ]

        self.before = {
            path: (
                path.read_bytes()
                if path.exists()
                else None
            )
            for path in self.production_files
        }

    def tearDown(self):
        self.temp.cleanup()

    def run_apcs(self, *args):
        env = os.environ.copy()
        env["APCS_DATA_DIR"] = str(self.data)
        env["APCS_DISABLE_SYNC"] = "1"

        return subprocess.run(
            [
                sys.executable,
                str(APCS),
                *args,
            ],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
        )

    def read_csv(self, name):
        with (self.data / name).open(
            encoding="utf-8",
            newline="",
        ) as f:
            return list(csv.DictReader(f))

    def assert_production_unchanged(self):
        for path, before in self.before.items():
            after = (
                path.read_bytes()
                if path.exists()
                else None
            )

            self.assertEqual(
                before,
                after,
                f"production file changed: {path}",
            )

    def test_finish_and_review_end_to_end(self):
        finish = self.run_apcs(
            "finish",
            "a001",
            "2",
            "--minutes",
            "18",
        )

        self.assertEqual(
            finish.returncode,
            0,
            finish.stderr,
        )

        review = self.run_apcs(
            "review",
            "a001",
            "1",
            "--result",
            "WA",
            "--minutes",
            "11",
        )

        self.assertEqual(
            review.returncode,
            0,
            review.stderr,
        )

        progress = self.read_csv(
            "progress.csv"
        )[0]

        events = self.read_csv(
            "reviews.csv"
        )

        self.assertTrue(progress["solved_on"])
        self.assertTrue(progress["last_review_on"])

        self.assertEqual(
            progress["last_result"],
            "WA",
        )

        self.assertEqual(
            progress["recall"],
            "1",
        )

        self.assertEqual(
            [event["event_type"] for event in events],
            ["finish", "review"],
        )

        self.assertEqual(
            events[0]["minutes"],
            "18",
        )

        self.assertEqual(
            events[1]["minutes"],
            "11",
        )

        self.assertEqual(
            events[1]["result"],
            "WA",
        )

        self.assert_production_unchanged()

    def test_minutes_are_event_specific(self):
        self.run_apcs(
            "finish",
            "a001",
            "2",
            "--minutes",
            "20",
        )

        self.run_apcs(
            "review",
            "a001",
            "3",
            "--result",
            "AC",
            "--minutes",
            "8",
        )

        events = self.read_csv(
            "reviews.csv"
        )

        self.assertEqual(
            events[0]["minutes"],
            "20",
        )

        self.assertEqual(
            events[1]["minutes"],
            "8",
        )

        self.assert_production_unchanged()

    def test_second_finish_rejected(self):
        first = self.run_apcs(
            "finish",
            "a001",
            "2",
        )

        self.assertEqual(
            first.returncode,
            0,
        )

        second = self.run_apcs(
            "finish",
            "a001",
            "3",
        )

        self.assertNotEqual(
            second.returncode,
            0,
        )

        self.assertIn(
            "已完成",
            second.stderr + second.stdout,
        )

        self.assert_production_unchanged()

    def test_review_unsolved_rejected(self):
        result = self.run_apcs(
            "review",
            "a006",
            "2",
        )

        self.assertNotEqual(
            result.returncode,
            0,
        )

        self.assertIn(
            "尚未完成",
            result.stderr + result.stdout,
        )

        self.assert_production_unchanged()

    def test_failed_review_cannot_be_recall_3(self):
        finish = self.run_apcs(
            "finish",
            "a001",
            "2",
        )

        self.assertEqual(
            finish.returncode,
            0,
        )

        review = self.run_apcs(
            "review",
            "a001",
            "3",
            "--result",
            "WA",
        )

        self.assertNotEqual(
            review.returncode,
            0,
        )

        self.assertIn(
            "Recall 3",
            review.stderr + review.stdout,
        )

        self.assert_production_unchanged()


if __name__ == "__main__":
    unittest.main()
