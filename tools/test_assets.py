#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "apcs-test-bundle-v1"

PROVENANCE_OFFICIAL = "OFFICIAL"
PROVENANCE_AI = "AI_GENERATED"
PROVENANCE_MANUAL = "MANUAL"
PROVENANCE_ORACLE = "ORACLE"

TRUST_OFFICIAL = "OFFICIAL"
TRUST_CANDIDATE = "CANDIDATE"
TRUST_ORACLE_VERIFIED = "ORACLE_VERIFIED"
TRUST_DIFFERENTIAL_VERIFIED = "DIFFERENTIAL_VERIFIED"

SUITE_FAST = "fast"
SUITE_FULL = "full"

VISIBILITY_OFFICIAL = "official"
VISIBILITY_PRACTICE = "practice"
VISIBILITY_POST_ATTEMPT = "post_attempt"

VALID_PROVENANCE = {
    PROVENANCE_OFFICIAL,
    PROVENANCE_AI,
    PROVENANCE_MANUAL,
    PROVENANCE_ORACLE,
}
VALID_TRUST = {
    TRUST_OFFICIAL,
    TRUST_CANDIDATE,
    TRUST_ORACLE_VERIFIED,
    TRUST_DIFFERENTIAL_VERIFIED,
}
VALID_SUITE = {
    SUITE_FAST,
    SUITE_FULL,
}
VALID_VISIBILITY = {
    VISIBILITY_OFFICIAL,
    VISIBILITY_PRACTICE,
    VISIBILITY_POST_ATTEMPT,
}


class TestAssetError(ValueError):
    pass


@dataclass(frozen=True)
class TestCase:
    case_id: str
    name: str
    input_text: str
    expected_output: str | None
    provenance: str
    trust: str
    suite: str
    visibility: str

    @property
    def runnable(self) -> bool:
        return (
            self.expected_output is not None
            and self.verified
        )

    @property
    def verified(self) -> bool:
        return self.trust in {
            TRUST_OFFICIAL,
            TRUST_ORACLE_VERIFIED,
            TRUST_DIFFERENTIAL_VERIFIED,
        }


@dataclass(frozen=True)
class TestBundle:
    source: str
    external_id: str
    canonical_url: str
    cases: tuple[TestCase, ...]
    oracle_path: Path | None = None

    @property
    def official_count(self) -> int:
        return sum(
            1
            for item in self.cases
            if item.provenance == PROVENANCE_OFFICIAL
        )

    @property
    def verified_count(self) -> int:
        return sum(
            1
            for item in self.cases
            if item.verified
        )

    @property
    def candidate_count(self) -> int:
        return sum(
            1
            for item in self.cases
            if item.trust == TRUST_CANDIDATE
        )


def normalize_output(text: str) -> str:
    lines = str(text).replace("\r\n", "\n").replace("\r", "\n").split("\n")
    while lines and lines[-1].strip() == "":
        lines.pop()
    return "\n".join(line.rstrip() for line in lines)


def same_output(actual: str, expected: str) -> bool:
    return normalize_output(actual) == normalize_output(expected)


class TestAssetStore:
    def __init__(
        self,
        data_dir: Path,
        runtime_dir: Path | None = None,
    ):
        self.data_dir = Path(data_dir)
        self.runtime_dir = (
            Path(runtime_dir)
            if runtime_dir is not None
            else None
        )

    @staticmethod
    def _clean_identity(value: str) -> str:
        value = str(value or "").strip()
        if not value:
            raise TestAssetError("test bundle identity 不得為空")
        if any(part in {"..", ""} for part in Path(value).parts):
            raise TestAssetError("test bundle identity 不合法")
        return value

    def problem_dir(
        self,
        source: str,
        external_id: str,
    ) -> Path:
        source = self._clean_identity(source).casefold()
        external_id = self._clean_identity(external_id)
        return (
            self.data_dir
            / source
            / external_id
        )

    def tests_path(
        self,
        source: str,
        external_id: str,
    ) -> Path:
        return (
            self.problem_dir(source, external_id)
            / "tests.json"
        )

    def package_path(
        self,
        source: str,
        external_id: str,
    ) -> Path:
        return (
            self.problem_dir(source, external_id)
            / "package.json"
        )

    def candidate_path(
        self,
        source: str,
        external_id: str,
    ) -> Path | None:
        if self.runtime_dir is None:
            return None
        return (
            self.runtime_dir
            / "test_candidates"
            / source.casefold()
            / external_id
            / "tests.json"
        )

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        try:
            payload = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )
        except (
            OSError,
            json.JSONDecodeError,
        ) as exc:
            raise TestAssetError(
                f"{path}: 測資 JSON 無法讀取：{exc}"
            ) from exc
        if not isinstance(payload, dict):
            raise TestAssetError(
                f"{path}: 測資根節點必須是 object"
            )
        return payload

    @staticmethod
    def _case_from_payload(
        payload: dict[str, Any],
        *,
        index: int,
    ) -> TestCase:
        if not isinstance(payload, dict):
            raise TestAssetError(
                f"case #{index}: 必須是 object"
            )

        case_id = str(
            payload.get("id")
            or f"T{index}"
        ).strip()
        name = str(
            payload.get("name")
            or case_id
        ).strip()
        input_text = str(
            payload.get("input")
            or ""
        )
        raw_expected = payload.get(
            "expected_output"
        )
        expected = (
            None
            if raw_expected is None
            else str(raw_expected)
        )
        provenance = str(
            payload.get("provenance")
            or PROVENANCE_MANUAL
        ).strip().upper()
        trust = str(
            payload.get("trust")
            or TRUST_CANDIDATE
        ).strip().upper()
        suite = str(
            payload.get("suite")
            or SUITE_FULL
        ).strip().lower()
        visibility = str(
            payload.get("visibility")
            or VISIBILITY_PRACTICE
        ).strip().lower()

        if not case_id:
            raise TestAssetError(
                f"case #{index}: id 不得為空"
            )
        if provenance not in VALID_PROVENANCE:
            raise TestAssetError(
                f"{case_id}: provenance 不合法"
            )
        if trust not in VALID_TRUST:
            raise TestAssetError(
                f"{case_id}: trust 不合法"
            )
        if suite not in VALID_SUITE:
            raise TestAssetError(
                f"{case_id}: suite 必須是 fast/full"
            )
        if visibility not in VALID_VISIBILITY:
            raise TestAssetError(
                f"{case_id}: visibility 不合法"
            )
        if (
            trust != TRUST_CANDIDATE
            and expected is None
        ):
            raise TestAssetError(
                f"{case_id}: verified test 必須有 expected_output"
            )

        return TestCase(
            case_id=case_id,
            name=name,
            input_text=input_text,
            expected_output=expected,
            provenance=provenance,
            trust=trust,
            suite=suite,
            visibility=visibility,
        )

    def _load_dedicated(
        self,
        source: str,
        external_id: str,
    ) -> TestBundle | None:
        path = self.tests_path(
            source,
            external_id,
        )
        if not path.is_file():
            return None

        payload = self._read_json(path)
        if payload.get("schema_version") != SCHEMA_VERSION:
            raise TestAssetError(
                f"{path}: schema_version 不支援"
            )
        identity = payload.get("identity")
        if not isinstance(identity, dict):
            raise TestAssetError(
                f"{path}: identity 缺失"
            )

        cases_payload = payload.get("cases")
        if not isinstance(cases_payload, list):
            raise TestAssetError(
                f"{path}: cases 必須是 array"
            )

        cases = tuple(
            self._case_from_payload(
                item,
                index=index,
            )
            for index, item
            in enumerate(
                cases_payload,
                start=1,
            )
        )

        seen = set()
        for case in cases:
            if case.case_id in seen:
                raise TestAssetError(
                    f"{path}: 重複 case id {case.case_id}"
                )
            seen.add(case.case_id)

        oracle = self.problem_dir(
            source,
            external_id,
        ) / "oracle.cpp"

        return TestBundle(
            source=str(
                identity.get("source")
                or source
            ).strip().casefold(),
            external_id=str(
                identity.get("external_id")
                or external_id
            ).strip(),
            canonical_url=str(
                identity.get("canonical_url")
                or ""
            ).strip(),
            cases=cases,
            oracle_path=(
                oracle
                if oracle.is_file()
                else None
            ),
        )

    def _load_legacy_package(
        self,
        source: str,
        external_id: str,
    ) -> TestBundle | None:
        path = self.package_path(
            source,
            external_id,
        )
        if not path.is_file():
            return None

        payload = self._read_json(path)
        identity = payload.get("identity")
        tests = payload.get("tests")

        if (
            not isinstance(identity, dict)
            or not isinstance(tests, dict)
        ):
            return None

        result: list[TestCase] = []

        for index, item in enumerate(
            tests.get("official_samples") or [],
            start=1,
        ):
            if not isinstance(item, dict):
                continue
            result.append(
                TestCase(
                    case_id=f"S{index}",
                    name=f"官方範例 {index}",
                    input_text=str(
                        item.get("input")
                        or ""
                    ),
                    expected_output=str(
                        item.get("output")
                        or ""
                    ),
                    provenance=PROVENANCE_OFFICIAL,
                    trust=TRUST_OFFICIAL,
                    suite=SUITE_FAST,
                    visibility=VISIBILITY_OFFICIAL,
                )
            )

        verification = payload.get(
            "verification"
        ) or {}
        differential_ok = (
            verification.get("differential")
            == "PASS"
        )
        oracle = self.problem_dir(
            source,
            external_id,
        ) / "oracle.cpp"

        for index, item in enumerate(
            tests.get("generated_cases") or [],
            start=1,
        ):
            if not isinstance(item, dict):
                continue
            expected = item.get("output")
            result.append(
                TestCase(
                    case_id=f"G{index}",
                    name=f"本地測資 {index}",
                    input_text=str(
                        item.get("input")
                        or ""
                    ),
                    expected_output=(
                        None
                        if expected is None
                        else str(expected)
                    ),
                    provenance=PROVENANCE_AI,
                    trust=(
                        TRUST_DIFFERENTIAL_VERIFIED
                        if (
                            differential_ok
                            and expected is not None
                        )
                        else TRUST_CANDIDATE
                    ),
                    suite=SUITE_FULL,
                    visibility=VISIBILITY_PRACTICE,
                )
            )

        return TestBundle(
            source=str(
                identity.get("source")
                or source
            ).strip().casefold(),
            external_id=str(
                identity.get("external_id")
                or external_id
            ).strip(),
            canonical_url=str(
                identity.get("canonical_url")
                or ""
            ).strip(),
            cases=tuple(result),
            oracle_path=(
                oracle
                if oracle.is_file()
                else None
            ),
        )

    def _candidate_cases(
        self,
        source: str,
        external_id: str,
    ) -> tuple[TestCase, ...]:
        path = self.candidate_path(
            source,
            external_id,
        )
        if path is None or not path.is_file():
            return ()

        payload = self._read_json(path)
        raw = payload.get("cases")
        if not isinstance(raw, list):
            return ()

        result = []
        for index, item in enumerate(
            raw,
            start=1,
        ):
            case = self._case_from_payload(
                item,
                index=index,
            )
            result.append(
                TestCase(
                    case_id=case.case_id,
                    name=case.name,
                    input_text=case.input_text,
                    expected_output=case.expected_output,
                    provenance=case.provenance,
                    trust=TRUST_CANDIDATE,
                    suite=SUITE_FULL,
                    visibility=VISIBILITY_PRACTICE,
                )
            )
        return tuple(result)

    def _discover_sources(
        self,
        external_id: str,
    ) -> list[str]:
        if not self.data_dir.is_dir():
            return []

        matches = []
        for source_dir in sorted(
            self.data_dir.iterdir()
        ):
            if not source_dir.is_dir():
                continue
            candidate = (
                source_dir
                / external_id
            )
            if candidate.is_dir():
                matches.append(
                    source_dir.name
                )
        return matches

    def load(
        self,
        source: str | None,
        external_id: str,
        *,
        include_candidates: bool = True,
    ) -> TestBundle | None:
        external_id = self._clean_identity(
            external_id
        )
        sources = (
            [source]
            if source
            else self._discover_sources(
                external_id
            )
        )

        for candidate_source in sources:
            if not candidate_source:
                continue
            bundle = self._load_dedicated(
                candidate_source,
                external_id,
            )
            if bundle is None:
                bundle = self._load_legacy_package(
                    candidate_source,
                    external_id,
                )
            if bundle is None:
                continue

            if include_candidates:
                candidates = self._candidate_cases(
                    candidate_source,
                    external_id,
                )
                if candidates:
                    bundle = TestBundle(
                        source=bundle.source,
                        external_id=bundle.external_id,
                        canonical_url=bundle.canonical_url,
                        cases=(
                            *bundle.cases,
                            *candidates,
                        ),
                        oracle_path=bundle.oracle_path,
                    )
            return bundle

        return None

    def validate_all(self) -> list[str]:
        errors: list[str] = []

        if not self.data_dir.is_dir():
            return errors

        for path in sorted(
            self.data_dir.glob("*/*/tests.json")
        ):
            try:
                source = path.parent.parent.name
                external_id = path.parent.name
                bundle = self._load_dedicated(
                    source,
                    external_id,
                )
                if bundle is None:
                    errors.append(
                        f"{path}: 無法載入"
                    )
                    continue

                # A durable bundle may contain candidates for curation, but
                # they must never masquerade as verified cases.
                for case in bundle.cases:
                    if (
                        case.trust
                        == TRUST_CANDIDATE
                        and case.suite
                        == SUITE_FAST
                    ):
                        errors.append(
                            f"{path}: {case.case_id} CANDIDATE "
                            "不得進 fast suite"
                        )

            except TestAssetError as exc:
                errors.append(
                    str(exc)
                )

        return errors


    @staticmethod
    def visible_cases(
        bundle: TestBundle,
        *,
        mode: str,
        activity: str | None,
        post_attempt: bool,
        suite: str,
    ) -> tuple[TestCase, ...]:
        strict = (
            mode == "exam"
            or activity
            in {
                "Transfer Challenge",
                "Mock",
            }
        )

        result = []
        for case in bundle.cases:
            if suite == SUITE_FAST:
                if case.suite != SUITE_FAST:
                    continue
            elif suite == SUITE_FULL:
                if case.suite not in {
                    SUITE_FAST,
                    SUITE_FULL,
                }:
                    continue
            else:
                raise TestAssetError(
                    "suite 必須是 fast/full"
                )

            if strict and not post_attempt:
                if (
                    case.provenance
                    != PROVENANCE_OFFICIAL
                ):
                    continue

            if (
                case.visibility
                == VISIBILITY_POST_ATTEMPT
                and not post_attempt
            ):
                continue

            if (
                mode == "exam"
                and case.visibility
                != VISIBILITY_OFFICIAL
                and not post_attempt
            ):
                continue

            result.append(case)

        return tuple(result)

    @staticmethod
    def inventory(
        bundle: TestBundle | None,
    ) -> dict[str, int]:
        if bundle is None:
            return {
                "official": 0,
                "verified": 0,
                "candidate": 0,
                "total": 0,
            }
        return {
            "official": bundle.official_count,
            "verified": bundle.verified_count,
            "candidate": bundle.candidate_count,
            "total": len(bundle.cases),
        }
