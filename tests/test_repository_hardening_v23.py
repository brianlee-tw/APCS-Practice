import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RepositoryHardeningV23Test(unittest.TestCase):
    def test_precommit_uses_full_quality_gate(self):
        text = (
            ROOT
            / ".pre-commit-config.yaml"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "entry: python tools/quality_gate.py",
            text,
        )
        self.assertNotIn(
            "entry: python tools/apcs.py validate",
            text,
        )

    def test_validate_workflow_exposes_stable_required_checks(self):
        text = (
            ROOT
            / ".github"
            / "workflows"
            / "validate.yml"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "  metadata:",
            text,
        )
        self.assertIn(
            "  changed-solutions:",
            text,
        )

    def test_enforcement_contract_excludes_post_main_sync(self):
        text = (
            ROOT
            / "docs"
            / "REPOSITORY_ENFORCEMENT_V23.md"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "- `metadata`",
            text,
        )
        self.assertIn(
            "- `changed-solutions`",
            text,
        )
        self.assertIn(
            "Do **not** require:",
            text,
        )
        self.assertIn(
            "`sync`",
            text,
        )


if __name__ == "__main__":
    unittest.main()
