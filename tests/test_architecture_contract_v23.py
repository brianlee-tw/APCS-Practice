import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = (
    ROOT
    / "curriculum"
    / "architecture_contract.v23.json"
)


class ArchitectureContractV23Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(
            CONTRACT.read_text(
                encoding="utf-8"
            )
        )

    def test_vscode_is_single_default_daily_surface(self):
        self.assertEqual(
            self.data["daily_surface"],
            "vscode",
        )

    def test_runtime_does_not_depend_on_live_notion(self):
        publication = self.data[
            "publication"
        ]

        self.assertFalse(
            publication[
                "runtime_live_notion_dependency"
            ]
        )

        self.assertEqual(
            publication["flow"][-1],
            "vscode_runtime",
        )

        self.assertIn(
            "published_snapshot",
            publication["flow"],
        )

    def test_machine_contract_is_git_published(self):
        systems = self.data["systems"]

        self.assertIn(
            "published_learning_contract",
            systems["git"]["role"],
        )

        self.assertIn(
            "runtime_scheduler",
            systems["notion"]["forbidden"],
        )

        self.assertIn(
            "manual_mastery_truth_without_evidence",
            systems["notion"]["forbidden"],
        )

    def test_problem_role_is_placement_semantics(self):
        placement = self.data[
            "entities"
        ]["problem_placement"]

        self.assertEqual(
            placement["published_owner"],
            "git",
        )

        self.assertIn(
            "placement/activity",
            placement["policy"],
        )

    def test_mastery_and_memory_are_derived(self):
        entities = self.data[
            "entities"
        ]

        self.assertEqual(
            entities["mastery"][
                "authoring_owner"
            ],
            "system",
        )

        self.assertEqual(
            entities["memory_state"][
                "durable_owner"
            ],
            "derived",
        )

        self.assertIn(
            "rebuildable",
            entities["memory_state"][
                "policy"
            ],
        )

    def test_review_policy_has_no_fixed_graduation(self):
        review = self.data[
            "review_invariants"
        ]

        self.assertEqual(
            review["scheduler_unit"],
            "skill_x_track",
        )

        self.assertTrue(
            review[
                "fixed_review_sequence_forbidden"
            ]
        )

        self.assertTrue(
            review[
                "fixed_review_count_graduation_forbidden"
            ]
        )

        self.assertTrue(
            review[
                "new_learning_capacity_protected"
            ]
        )

        self.assertTrue(
            review[
                "deferred_reviews_are_not_debt"
            ]
        )

    def test_review_budget_is_bounded(self):
        budget = self.data[
            "review_invariants"
        ][
            "review_budget_fraction_default"
        ]

        self.assertGreater(
            budget["min"],
            0,
        )

        self.assertLess(
            budget["max"],
            1,
        )

        self.assertLessEqual(
            budget["min"],
            budget["max"],
        )


if __name__ == "__main__":
    unittest.main()
