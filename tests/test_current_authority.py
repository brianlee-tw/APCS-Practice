from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools.current_authority import (
    AUTHORITY_PATH,
    CURRENT_MD_PATH,
    END,
    README_PATH,
    START,
    V23_ARCH_PATH,
    WORKER_AUTHORITY_PATH,
    load_current_authority,
    render_full,
    render_summary,
)


class CurrentAuthorityTest(unittest.TestCase):
    def test_current_authority_matches_worker_authority(self):
        authority = load_current_authority()
        worker = json.loads(
            WORKER_AUTHORITY_PATH.read_text(encoding="utf-8")
        )

        production = authority["production"]
        self.assertEqual(production["worker"], worker["worker"])
        self.assertEqual(
            production["version_number"],
            worker["production_version_number"],
        )
        self.assertEqual(
            production["version_id"],
            worker["production_version_id"],
        )
        self.assertEqual(
            production["deployment_id"],
            worker["deployment_id"],
        )
        self.assertEqual(authority["product"]["learner_readiness"], "NOT_ASSESSED")

    def test_generated_human_readable_authority_is_current(self):
        authority = load_current_authority()
        self.assertEqual(
            CURRENT_MD_PATH.read_text(encoding="utf-8"),
            render_full(authority),
        )

    def test_readme_projection_is_current(self):
        authority = load_current_authority()
        text = README_PATH.read_text(encoding="utf-8")
        body = text.split(START, 1)[1].split(END, 1)[0].strip()
        self.assertEqual(body, render_summary(authority, from_docs=False))

    def test_v23_architecture_projection_is_current(self):
        authority = load_current_authority()
        text = V23_ARCH_PATH.read_text(encoding="utf-8")
        body = text.split(START, 1)[1].split(END, 1)[0].strip()
        self.assertEqual(body, render_summary(authority, from_docs=True))
        self.assertIn("歷史架構契約", text)
        self.assertNotIn("Status: **Draft 0 / Gate 0**", text)

    def test_machine_readable_authority_path_exists(self):
        self.assertTrue(AUTHORITY_PATH.is_file())


if __name__ == "__main__":
    unittest.main()
