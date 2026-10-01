import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCATOR = (
    ROOT
    / "curriculum"
    / "migration"
    / "notion_extract_locator.v23.json"
)


class NotionExtractLocatorV23Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(
            LOCATOR.read_text(encoding="utf-8")
        )

    def test_locator_is_migration_only(self):
        self.assertIn(
            "not runtime curriculum truth",
            self.data["purpose"].lower(),
        )

    def test_main_lesson_inventory_is_exactly_52(self):
        lessons = self.data["lessons"]
        self.assertEqual(len(lessons), 52)
        self.assertEqual(
            self.data["main_lesson_count"],
            52,
        )
        for lesson_uid in lessons:
            self.assertRegex(
                lesson_uid,
                r"^L-[A-Z]{2,3}-\d{2}$",
            )
            self.assertNotIn("-X", lesson_uid)

    def test_problem_page_ids_are_unique(self):
        page_ids = [
            page_id
            for ids in self.data[
                "lessons"
            ].values()
            for page_id in ids
        ]
        self.assertEqual(
            len(page_ids),
            self.data[
                "candidate_page_count"
            ],
        )
        self.assertEqual(len(page_ids), 126)
        self.assertEqual(
            len(page_ids),
            len(set(page_ids)),
        )
        for page_id in page_ids:
            self.assertRegex(
                page_id,
                (
                    r"^[0-9a-f]{8}-"
                    r"[0-9a-f]{4}-"
                    r"[0-9a-f]{4}-"
                    r"[0-9a-f]{4}-"
                    r"[0-9a-f]{12}$"
                ),
            )

    def test_mix04_has_no_formal_oj_locator(self):
        self.assertEqual(
            self.data["lessons"][
                "L-MIX-04"
            ],
            [],
        )


if __name__ == "__main__":
    unittest.main()
