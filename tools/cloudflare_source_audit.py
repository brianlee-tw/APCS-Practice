#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


AUDIT_SCHEMA_VERSION = "cloudflare-source-audit-v1"

EXCLUDED_DIRS = {
    ".git",
    ".wrangler",
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".cache",
}

SECRET_BASENAMES = {
    ".dev.vars",
    ".env",
}

SECRET_PREFIXES = (
    ".env.",
)

REQUIRED_FILES = (
    "src/index.ts",
    "src/routing.ts",
    "wrangler.jsonc",
    "package.json",
)

FORBIDDEN_TEST_MARKERS = (
    "V23_TEST_WRITE_KEY",
    "/api/v23-system-test",
    "api/v23-system-test",
)

SOURCE_SUFFIXES = {
    ".ts",
    ".tsx",
    ".js",
    ".mjs",
    ".cjs",
}

ROUTE_LITERAL_RE = re.compile(
    r"""(?P<quote>["'`])(?P<route>/[^"'\`\r\n]*?)(?P=quote)"""
)

ENV_REFERENCE_RE = re.compile(
    r"""\benv\.([A-Z][A-Z0-9_]*)\b"""
)

JSON_STRING_FIELD_PATTERNS = {
    "name": re.compile(
        r'''"name"\s*:\s*"([^"]+)"'''
    ),
    "compatibility_date": re.compile(
        r'''"compatibility_date"\s*:\s*"([^"]+)"'''
    ),
}

COMPAT_FLAGS_RE = re.compile(
    r'''"compatibility_flags"\s*:\s*\[([^\]]*)\]''',
    re.S,
)

ASSET_BINDING_RE = re.compile(
    r'''"binding"\s*:\s*"([A-Z][A-Z0-9_]*)"'''
)


@dataclass(frozen=True)
class IncludedFile:
    relative_path: str
    size: int
    sha256: str


def _is_secret_path(path: Path) -> bool:
    name = path.name

    if name in SECRET_BASENAMES:
        return True

    return any(
        name.startswith(prefix)
        for prefix in SECRET_PREFIXES
    )


def _iter_project_files(
    project: Path,
) -> Iterable[Path]:
    for path in project.rglob("*"):
        if not path.is_file():
            continue

        relative = path.relative_to(
            project
        )

        if any(
            part in EXCLUDED_DIRS
            for part in relative.parts[:-1]
        ):
            continue

        if _is_secret_path(relative):
            continue

        yield path


def _secret_file_names(
    project: Path,
) -> list[str]:
    rows: list[str] = []

    for path in project.rglob("*"):
        if not path.is_file():
            continue

        relative = path.relative_to(
            project
        )

        if any(
            part in EXCLUDED_DIRS
            for part in relative.parts[:-1]
        ):
            continue

        if _is_secret_path(relative):
            rows.append(
                relative.as_posix()
            )

    return sorted(rows)


def _file_sha256(data: bytes) -> str:
    return hashlib.sha256(
        data
    ).hexdigest()


def build_inventory(
    project: Path,
) -> tuple[list[IncludedFile], str]:
    rows: list[IncludedFile] = []

    for path in sorted(
        _iter_project_files(project),
        key=lambda item: (
            item.relative_to(
                project
            ).as_posix()
        ),
    ):
        relative = path.relative_to(
            project
        ).as_posix()
        data = path.read_bytes()
        rows.append(
            IncludedFile(
                relative_path=relative,
                size=len(data),
                sha256=_file_sha256(
                    data
                ),
            )
        )

    digest = hashlib.sha256()

    for row in rows:
        # This deliberately hashes path + size + file digest instead of raw
        # concatenated file bytes.  The algorithm is explicit and versioned,
        # so future audits can reproduce it without depending on archive
        # metadata or filesystem ordering.
        digest.update(
            row.relative_path.encode(
                "utf-8"
            )
        )
        digest.update(b"\0")
        digest.update(
            str(row.size).encode(
                "ascii"
            )
        )
        digest.update(b"\0")
        digest.update(
            bytes.fromhex(
                row.sha256
            )
        )
        digest.update(b"\n")

    return rows, digest.hexdigest()


def _read_text_safely(
    path: Path,
) -> str:
    try:
        return path.read_text(
            encoding="utf-8"
        )
    except (
        UnicodeDecodeError,
        OSError,
    ):
        return ""


def _wrangler_summary(
    project: Path,
) -> dict:
    path = project / "wrangler.jsonc"

    if not path.is_file():
        return {
            "present": False,
        }

    text = _read_text_safely(
        path
    )
    result = {
        "present": True,
        "name": None,
        "compatibility_date": None,
        "compatibility_flags": [],
        "config_bindings": [],
    }

    for key, pattern in (
        JSON_STRING_FIELD_PATTERNS.items()
    ):
        match = pattern.search(
            text
        )

        if match:
            result[key] = match.group(1)

    flags_match = COMPAT_FLAGS_RE.search(
        text
    )

    if flags_match:
        result[
            "compatibility_flags"
        ] = sorted(
            set(
                re.findall(
                    r'"([^"]+)"',
                    flags_match.group(1),
                )
            )
        )

    result["config_bindings"] = sorted(
        set(
            ASSET_BINDING_RE.findall(
                text
            )
        )
    )

    return result


def _package_summary(
    project: Path,
) -> dict:
    path = project / "package.json"

    if not path.is_file():
        return {
            "present": False,
            "scripts": [],
        }

    try:
        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except (
        json.JSONDecodeError,
        UnicodeDecodeError,
        OSError,
    ) as exc:
        return {
            "present": True,
            "parse_error": str(exc),
            "scripts": [],
        }

    scripts = payload.get(
        "scripts"
    )

    if not isinstance(
        scripts,
        dict,
    ):
        scripts = {}

    return {
        "present": True,
        "name": payload.get("name"),
        "version": payload.get(
            "version"
        ),
        "scripts": sorted(
            str(key)
            for key in scripts
        ),
    }


def _source_texts(
    project: Path,
) -> list[tuple[str, str]]:
    rows: list[
        tuple[str, str]
    ] = []

    src = project / "src"

    if not src.is_dir():
        return rows

    for path in sorted(
        src.rglob("*")
    ):
        if (
            not path.is_file()
            or path.suffix.lower()
            not in SOURCE_SUFFIXES
        ):
            continue

        text = _read_text_safely(
            path
        )
        rows.append(
            (
                path.relative_to(
                    project
                ).as_posix(),
                text,
            )
        )

    return rows


def _source_summary(
    project: Path,
) -> dict:
    texts = _source_texts(
        project
    )

    routes: set[str] = set()
    env_refs: set[str] = set()
    forbidden_hits: list[dict] = []

    for relative, text in texts:
        for match in (
            ROUTE_LITERAL_RE.finditer(
                text
            )
        ):
            route = match.group(
                "route"
            )

            # Keep only route-like literals.  CSS selectors, regex fragments,
            # and protocol-relative URLs are not useful here.
            if (
                route.startswith("//")
                or " " in route
            ):
                continue

            routes.add(
                route
            )

        env_refs.update(
            ENV_REFERENCE_RE.findall(
                text
            )
        )

        for marker in (
            FORBIDDEN_TEST_MARKERS
        ):
            if marker in text:
                forbidden_hits.append(
                    {
                        "file": relative,
                        "marker": marker,
                    }
                )

    return {
        "source_files": len(
            texts
        ),
        "route_literals": sorted(
            routes
        ),
        "env_references": sorted(
            env_refs
        ),
        "forbidden_test_hits": (
            forbidden_hits
        ),
    }


def _area_stats(
    rows: list[IncludedFile],
    prefix: str,
) -> dict:
    selected = [
        row
        for row in rows
        if row.relative_path.startswith(
            prefix
        )
    ]

    return {
        "files": len(selected),
        "bytes": sum(
            row.size
            for row in selected
        ),
    }


def audit_project(
    project: Path,
    *,
    expected_name: str | None = (
        "apcs-rec-writeback"
    ),
) -> dict:
    project = project.expanduser().resolve()

    if not project.is_dir():
        raise ValueError(
            f"project directory does not exist: {project}"
        )

    rows, fingerprint = (
        build_inventory(
            project
        )
    )
    wrangler = _wrangler_summary(
        project
    )
    package = _package_summary(
        project
    )
    source = _source_summary(
        project
    )

    missing = [
        relative
        for relative in REQUIRED_FILES
        if not (
            project
            / relative
        ).is_file()
    ]

    errors: list[str] = []
    warnings: list[str] = []

    if missing:
        errors.append(
            "missing required file(s): "
            + ", ".join(missing)
        )

    if (
        expected_name
        and wrangler.get("name")
        and wrangler.get("name")
        != expected_name
    ):
        errors.append(
            "unexpected Wrangler project name: "
            f"{wrangler['name']!r}"
        )

    if source[
        "forbidden_test_hits"
    ]:
        errors.append(
            "forbidden test-only marker(s) "
            "present in source"
        )

    secret_files = _secret_file_names(
        project
    )

    if secret_files:
        warnings.append(
            "secret-bearing local files were "
            "excluded from inventory/fingerprint"
        )

    if not source["route_literals"]:
        warnings.append(
            "no route-like literals found under src/"
        )

    payload = {
        "schema_version": (
            AUDIT_SCHEMA_VERSION
        ),
        "status": (
            "FAIL"
            if errors
            else (
                "WARN"
                if warnings
                else "PASS"
            )
        ),
        "project": str(project),
        "fingerprint": {
            "algorithm": (
                "sha256-v1("
                "relative_path\\0"
                "decimal_size\\0"
                "sha256(file_bytes)\\n"
                "; sorted UTF-8 paths)"
            ),
            "tree_sha256": fingerprint,
            "included_files": len(rows),
            "included_bytes": sum(
                row.size
                for row in rows
            ),
            "excluded_directories": sorted(
                EXCLUDED_DIRS
            ),
            "secret_files_excluded": (
                secret_files
            ),
        },
        "areas": {
            "src": _area_stats(
                rows,
                "src/",
            ),
            "public": _area_stats(
                rows,
                "public/",
            ),
        },
        "required_files": {
            relative: (
                project
                / relative
            ).is_file()
            for relative in REQUIRED_FILES
        },
        "wrangler": wrangler,
        "package": package,
        "source": source,
        "errors": errors,
        "warnings": warnings,
    }

    return payload


def main(
    argv: list[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only inventory of the local "
            "Cloudflare Worker source authority."
        )
    )
    parser.add_argument(
        "project",
        type=Path,
        help=(
            "Path to the Wrangler project root."
        ),
    )
    parser.add_argument(
        "--expected-name",
        default="apcs-rec-writeback",
        help=(
            "Expected Wrangler project name "
            "(default: apcs-rec-writeback)."
        ),
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=None,
        help=(
            "Also write the audit payload to "
            "this JSON file."
        ),
    )
    args = parser.parse_args(
        argv
    )

    try:
        payload = audit_project(
            args.project,
            expected_name=(
                args.expected_name
            ),
        )
    except ValueError as exc:
        print(
            json.dumps(
                {
                    "schema_version": (
                        AUDIT_SCHEMA_VERSION
                    ),
                    "status": "FAIL",
                    "errors": [
                        str(exc)
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    rendered = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    print(rendered)

    if args.json is not None:
        args.json.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        args.json.write_text(
            rendered + "\n",
            encoding="utf-8",
        )

    return (
        0
        if payload["status"]
        in {
            "PASS",
            "WARN",
        }
        else 1
    )


if __name__ == "__main__":
    sys.exit(main())
