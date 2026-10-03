import json
import tempfile
import unittest
from pathlib import Path

from tools.cloudflare_source_audit import (
    audit_project,
)


class CloudflareSourceAuditV23Test(
    unittest.TestCase
):
    def make_project(
        self,
        root: Path,
        *,
        forbidden: bool = False,
    ) -> Path:
        project = (
            root
            / "worker"
        )
        (
            project
            / "src"
        ).mkdir(
            parents=True
        )
        (
            project
            / "public"
        ).mkdir()
        (
            project
            / "node_modules"
        ).mkdir()

        (
            project
            / "wrangler.jsonc"
        ).write_text(
            """{
  // production worker
  "name": "apcs-rec-writeback",
  "compatibility_date": "2026-08-25",
  "compatibility_flags": ["nodejs_compat"],
  "assets": {
    "directory": "./public",
    "binding": "ASSETS",
  },
}
""",
            encoding="utf-8",
        )
        (
            project
            / "package.json"
        ).write_text(
            json.dumps(
                {
                    "name": (
                        "apcs-rec-writeback"
                    ),
                    "version": "1.0.0",
                    "scripts": {
                        "deploy": (
                            "wrangler deploy"
                        ),
                        "dry": (
                            "wrangler deploy "
                            "--dry-run"
                        ),
                    },
                }
            ),
            encoding="utf-8",
        )

        marker = (
            "\nconst bad = "
            "'V23_TEST_WRITE_KEY';"
            if forbidden
            else ""
        )
        (
            project
            / "src"
            / "index.ts"
        ).write_text(
            """
export default {
  async fetch(request, env) {
    const path = "/api/record";
    const health = "/api/health";
    void env.NOTION_API_TOKEN;
    void env.WRITE_KEY;
    return new Response(path + health);
  }
};
"""
            + marker,
            encoding="utf-8",
        )
        (
            project
            / "src"
            / "routing.ts"
        ).write_text(
            (
                'export const route = '
                '"/learn/dat/array-vector";\n'
            ),
            encoding="utf-8",
        )
        (
            project
            / "public"
            / "index.html"
        ).write_text(
            "<!doctype html>",
            encoding="utf-8",
        )

        # Excluded content must not affect the audit fingerprint.
        (
            project
            / "node_modules"
            / "noise.txt"
        ).write_text(
            "noise",
            encoding="utf-8",
        )
        (
            project
            / ".dev.vars"
        ).write_text(
            "WRITE_KEY=secret",
            encoding="utf-8",
        )

        return project

    def test_audit_inventory_and_contract(self):
        with tempfile.TemporaryDirectory() as temp:
            project = self.make_project(
                Path(temp)
            )
            result = audit_project(
                project
            )

        self.assertEqual(
            result["status"],
            "WARN",
        )
        self.assertEqual(
            result["wrangler"]["name"],
            "apcs-rec-writeback",
        )
        self.assertEqual(
            result["wrangler"][
                "compatibility_date"
            ],
            "2026-08-25",
        )
        self.assertIn(
            "nodejs_compat",
            result["wrangler"][
                "compatibility_flags"
            ],
        )
        self.assertIn(
            "ASSETS",
            result["wrangler"][
                "config_bindings"
            ],
        )
        self.assertIn(
            "/api/record",
            result["source"][
                "route_literals"
            ],
        )
        self.assertIn(
            "NOTION_API_TOKEN",
            result["source"][
                "env_references"
            ],
        )
        self.assertIn(
            "WRITE_KEY",
            result["source"][
                "env_references"
            ],
        )
        self.assertEqual(
            result["fingerprint"][
                "secret_files_excluded"
            ],
            [".dev.vars"],
        )

    def test_excluded_content_does_not_change_fingerprint(self):
        with tempfile.TemporaryDirectory() as temp:
            project = self.make_project(
                Path(temp)
            )
            first = audit_project(
                project
            )["fingerprint"][
                "tree_sha256"
            ]

            (
                project
                / "node_modules"
                / "noise.txt"
            ).write_text(
                "changed",
                encoding="utf-8",
            )
            (
                project
                / ".dev.vars"
            ).write_text(
                "WRITE_KEY=changed-secret",
                encoding="utf-8",
            )

            second = audit_project(
                project
            )["fingerprint"][
                "tree_sha256"
            ]

        self.assertEqual(
            first,
            second,
        )

    def test_included_source_change_changes_fingerprint(self):
        with tempfile.TemporaryDirectory() as temp:
            project = self.make_project(
                Path(temp)
            )
            first = audit_project(
                project
            )["fingerprint"][
                "tree_sha256"
            ]

            (
                project
                / "src"
                / "routing.ts"
            ).write_text(
                (
                    'export const route = '
                    '"/learn/dat/vector";\n'
                ),
                encoding="utf-8",
            )

            second = audit_project(
                project
            )["fingerprint"][
                "tree_sha256"
            ]

        self.assertNotEqual(
            first,
            second,
        )

    def test_forbidden_test_marker_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            project = self.make_project(
                Path(temp),
                forbidden=True,
            )
            result = audit_project(
                project
            )

        self.assertEqual(
            result["status"],
            "FAIL",
        )
        self.assertTrue(
            result["source"][
                "forbidden_test_hits"
            ],
        )


if __name__ == "__main__":
    unittest.main()
