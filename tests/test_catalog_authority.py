import csv
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

EXCLUDE = {
    ".git",
    ".github",
    ".vscode",
    "tools",
    "tests",
    "docs",
    "data",
    "notes",
    "build",
    "Build",
    "__pycache__",
}

LEGACY_HEADER_RE = re.compile(
    r"^\s*(?://|#)\s*APCS\s+[^:]+:\s*.*$",
    re.I,
)


def catalog_paths():
    with (
        ROOT
        / "data"
        / "solutions.csv"
    ).open(
        encoding="utf-8",
        newline="",
    ) as f:
        return {
            row["path"]
            for row in csv.DictReader(f)
        }


def disk_solution_paths():
    result = set()

    for path in ROOT.rglob("*"):
        if (
            not path.is_file()
            or path.suffix.lower()
            not in {".cpp", ".py"}
        ):
            continue

        relative = path.relative_to(
            ROOT
        )

        if any(
            part in EXCLUDE
            or part == ".cph"
            for part in relative.parts[:-1]
        ):
            continue

        if "tempCodeRunner" in path.name:
            continue

        result.add(
            relative.as_posix()
        )

    return result


class CatalogAuthorityTest(
    unittest.TestCase
):
    def test_every_solution_source_is_catalog_registered(self):
        self.assertEqual(
            disk_solution_paths(),
            catalog_paths(),
        )

    def test_registered_solutions_have_no_legacy_headers(self):
        offenders = []

        for relative in sorted(
            catalog_paths()
        ):
            path = ROOT / relative

            for number, line in enumerate(
                path.read_text(
                    encoding="utf-8",
                    errors="ignore",
                ).splitlines(),
                start=1,
            ):
                if LEGACY_HEADER_RE.match(
                    line
                ):
                    offenders.append(
                        f"{relative}:{number}: {line}"
                    )

        self.assertEqual(
            offenders,
            [],
        )


if __name__ == "__main__":
    unittest.main()
