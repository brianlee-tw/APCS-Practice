#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

try:
    from .problem_intelligence import (
        CANDIDATE,
        L1,
        ProblemIntelligenceError,
        ProblemIntelligenceStore,
    )
except ImportError:
    from problem_intelligence import (
        CANDIDATE,
        L1,
        ProblemIntelligenceError,
        ProblemIntelligenceStore,
    )

SCHEMA_VERSION = "apcs-problem-enrichment-v1"

AI_CANDIDATE = "AI_CANDIDATE"
COMPILE_VERIFIED = "COMPILE_VERIFIED"
SAMPLE_VERIFIED = "SAMPLE_VERIFIED"
DIFFERENTIAL_VERIFIED = "DIFFERENTIAL_VERIFIED"
OJ_ACCEPTED = "OJ_ACCEPTED"

NOT_RUN = "NOT_RUN"
PASS = "PASS"
FAIL = "FAIL"

TRUST_ORDER = {
    AI_CANDIDATE: 0,
    COMPILE_VERIFIED: 1,
    SAMPLE_VERIFIED: 2,
    DIFFERENTIAL_VERIFIED: 3,
    OJ_ACCEPTED: 4,
}

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE_DIR = ROOT / "data" / "problem_intelligence"
DEFAULT_ENRICHMENT_DIR = ROOT / "data" / "problem_enrichment"


class ProblemEnrichmentError(ValueError):
    pass


def _text(value: Any) -> str:
    return str(value or "").strip()


def _string_list(value: Any, name: str) -> list[str]:
    if not isinstance(value, list):
        raise ProblemEnrichmentError(f"{name} 必須是陣列")
    return [_text(x) for x in value if _text(x)]


def _case_list(value: Any, name: str, *, require_output: bool) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise ProblemEnrichmentError(f"{name} 必須是陣列")

    result = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise ProblemEnrichmentError(f"{name}[{index}] 必須是 object")

        allowed = {"input", "output"} if require_output else {"input", "output"}
        if set(item) - allowed:
            raise ProblemEnrichmentError(f"{name}[{index}] 含未知欄位")

        input_text = str(item.get("input", ""))
        output_text = str(item.get("output", ""))
        if not input_text:
            raise ProblemEnrichmentError(f"{name}[{index}] 缺少 input")
        if require_output and not output_text:
            raise ProblemEnrichmentError(f"{name}[{index}] 缺少 output")

        row = {"input": input_text}
        if output_text:
            row["output"] = output_text
        result.append(row)

    return result


def _same_output(actual: str, expected: str) -> bool:
    def normalize(text: str) -> list[str]:
        return [line.rstrip() for line in text.strip().splitlines()]

    return normalize(actual) == normalize(expected)


class ProblemEnrichmentStore:
    def __init__(
        self,
        profile_store: ProblemIntelligenceStore | None = None,
        data_dir: Path = DEFAULT_ENRICHMENT_DIR,
    ):
        self.profile_store = profile_store or ProblemIntelligenceStore(
            DEFAULT_PROFILE_DIR
        )
        self.data_dir = Path(data_dir)

    def problem_dir(self, source: str, external_id: str) -> Path:
        return self.data_dir / source / external_id

    def package_path(self, source: str, external_id: str) -> Path:
        return self.problem_dir(source, external_id) / "package.json"

    def solution_path(self, source: str, external_id: str) -> Path:
        return self.problem_dir(source, external_id) / "solution.cpp"

    def oracle_path(self, source: str, external_id: str) -> Path:
        return self.problem_dir(source, external_id) / "oracle.cpp"

    @staticmethod
    def _write_json(path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(path.name + ".tmp")
        try:
            temp.write_text(
                json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            temp.replace(path)
        finally:
            temp.unlink(missing_ok=True)

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ProblemEnrichmentError(f"{path}: JSON 無法讀取：{exc}") from exc
        if not isinstance(data, dict):
            raise ProblemEnrichmentError(f"{path}: package 必須是 object")
        return data

    def all_packages(self) -> list[Path]:
        if not self.data_dir.exists():
            return []
        return sorted(self.data_dir.glob("*/*/package.json"))

    def _eligible_profile(self, source: str, external_id: str) -> dict[str, Any]:
        try:
            profile = self.profile_store.load(source, external_id)
        except ProblemIntelligenceError as exc:
            raise ProblemEnrichmentError(str(exc)) from exc

        if profile["lifecycle"] != L1:
            raise ProblemEnrichmentError("只有 L1 已分類題目可以進入 C2")
        if profile["classification"]["status"] != CANDIDATE:
            raise ProblemEnrichmentError(
                "NEEDS_QA 題目必須先完成分類確認，不能直接產生 L2"
            )
        return profile

    def create(
        self,
        source: str,
        external_id: str,
        payload: dict[str, Any],
        solution_code: str,
        *,
        replace: bool = False,
    ) -> dict[str, Any]:
        profile = self._eligible_profile(source, external_id)
        package_path = self.package_path(source, external_id)

        if package_path.exists() and not replace:
            raise ProblemEnrichmentError(
                "L2 package 已存在；若確定要重建請使用 replace"
            )

        allowed = {
            "problem_model",
            "key_observation",
            "correctness_reasoning",
            "invariant",
            "time_complexity",
            "space_complexity",
            "common_pitfalls",
            "edge_cases",
            "hints",
            "alternate_approaches",
            "transfer_signals",
            "official_samples",
            "generated_cases",
            "generation_source",
        }
        unknown = sorted(set(payload) - allowed)
        if unknown:
            raise ProblemEnrichmentError(
                "L2 輸入含未知欄位：" + ", ".join(unknown)
            )

        required_text = {
            name: _text(payload.get(name))
            for name in (
                "problem_model",
                "key_observation",
                "correctness_reasoning",
                "invariant",
                "time_complexity",
                "space_complexity",
            )
        }
        missing = [name for name, value in required_text.items() if not value]
        if missing:
            raise ProblemEnrichmentError(
                "L2 缺少必要內容：" + ", ".join(missing)
            )

        hints = payload.get("hints")
        if not isinstance(hints, dict) or set(hints) != {"A1", "A2", "A3", "A4", "A5"}:
            raise ProblemEnrichmentError("hints 必須完整包含 A1–A5")
        hints = {key: _text(value) for key, value in hints.items()}
        if any(not value for value in hints.values()):
            raise ProblemEnrichmentError("A1–A5 提示不得為空")

        solution_code = str(solution_code or "")
        if not solution_code.strip():
            raise ProblemEnrichmentError("solution.cpp 不得為空")

        identity = profile["identity"]
        package = {
            "schema_version": SCHEMA_VERSION,
            "identity": {
                "source": identity["source"],
                "external_id": identity["external_id"],
                "canonical_url": identity["canonical_url"],
            },
            "teaching": {
                **required_text,
                "common_pitfalls": _string_list(
                    payload.get("common_pitfalls", []), "common_pitfalls"
                ),
                "edge_cases": _string_list(
                    payload.get("edge_cases", []), "edge_cases"
                ),
                "hints": hints,
                "alternate_approaches": _string_list(
                    payload.get("alternate_approaches", []),
                    "alternate_approaches",
                ),
                "transfer_signals": _string_list(
                    payload.get("transfer_signals", []), "transfer_signals"
                ),
            },
            "tests": {
                "official_samples": _case_list(
                    payload.get("official_samples", []),
                    "official_samples",
                    require_output=True,
                ),
                "generated_cases": _case_list(
                    payload.get("generated_cases", []),
                    "generated_cases",
                    require_output=False,
                ),
            },
            "verification": {
                "trust_status": AI_CANDIDATE,
                "compile": NOT_RUN,
                "samples": NOT_RUN,
                "differential": NOT_RUN,
                "oj": NOT_RUN,
                "oj_reference": None,
            },
            "provenance": {
                "generation_source": _text(
                    payload.get("generation_source")
                )
                or "AI_CANDIDATE",
            },
        }

        self.validate_package(package, package_path)
        problem_dir = self.problem_dir(source, external_id)
        problem_dir.mkdir(parents=True, exist_ok=True)
        self.solution_path(source, external_id).write_text(
            solution_code,
            encoding="utf-8",
        )
        self._write_json(package_path, package)
        return package

    def load(self, source: str, external_id: str) -> dict[str, Any]:
        path = self.package_path(source, external_id)
        if not path.is_file():
            raise ProblemEnrichmentError(
                f"找不到 L2 package：{source}:{external_id}"
            )
        data = self._read_json(path)
        self.validate_package(data, path)
        return data

    @staticmethod
    def _compile(source_path: Path, output_path: Path) -> tuple[bool, str]:
        compiler = shutil.which("g++")
        if compiler is None:
            raise ProblemEnrichmentError("找不到 g++，無法做 C++ 編譯驗證")

        result = subprocess.run(
            [
                compiler,
                "-std=c++17",
                "-O2",
                "-pipe",
                str(source_path),
                "-o",
                str(output_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        detail = (result.stderr or result.stdout or "").strip()
        return result.returncode == 0, detail

    @staticmethod
    def _run(executable: Path, input_text: str) -> tuple[bool, str, str]:
        try:
            result = subprocess.run(
                [str(executable)],
                input=input_text,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return False, "", "TIMEOUT"

        return (
            result.returncode == 0,
            result.stdout,
            (result.stderr or "").strip(),
        )

    def _save_verification(
        self,
        source: str,
        external_id: str,
        package: dict[str, Any],
    ) -> None:
        self.validate_package(
            package,
            self.package_path(source, external_id),
        )
        self._write_json(
            self.package_path(source, external_id),
            package,
        )

    def verify_compile(self, source: str, external_id: str) -> dict[str, Any]:
        package = self.load(source, external_id)
        solution = self.solution_path(source, external_id)

        with tempfile.TemporaryDirectory() as temp:
            executable = Path(temp) / "solution"
            ok, _ = self._compile(solution, executable)

        package["verification"]["compile"] = PASS if ok else FAIL
        if ok:
            package["verification"]["trust_status"] = COMPILE_VERIFIED
        else:
            package["verification"]["trust_status"] = AI_CANDIDATE
            package["verification"]["samples"] = NOT_RUN
            package["verification"]["differential"] = NOT_RUN

        self._save_verification(source, external_id, package)
        return package

    def verify_samples(self, source: str, external_id: str) -> dict[str, Any]:
        package = self.load(source, external_id)
        samples = package["tests"]["official_samples"]
        if not samples:
            raise ProblemEnrichmentError("沒有 official sample，不能做 Sample Verified")

        with tempfile.TemporaryDirectory() as temp:
            executable = Path(temp) / "solution"
            ok, _ = self._compile(
                self.solution_path(source, external_id),
                executable,
            )
            package["verification"]["compile"] = PASS if ok else FAIL
            if not ok:
                package["verification"]["samples"] = NOT_RUN
                package["verification"]["trust_status"] = AI_CANDIDATE
            else:
                all_pass = True
                for case in samples:
                    ran, output, _ = self._run(executable, case["input"])
                    if not ran or not _same_output(output, case["output"]):
                        all_pass = False
                        break
                package["verification"]["samples"] = PASS if all_pass else FAIL
                package["verification"]["trust_status"] = (
                    SAMPLE_VERIFIED if all_pass else COMPILE_VERIFIED
                )

        self._save_verification(source, external_id, package)
        return package

    def verify_differential(
        self,
        source: str,
        external_id: str,
        oracle_code: str,
    ) -> dict[str, Any]:
        package = self.load(source, external_id)
        cases = package["tests"]["generated_cases"]
        if not cases:
            raise ProblemEnrichmentError(
                "沒有 generated case，不能做差分驗證"
            )
        if not str(oracle_code or "").strip():
            raise ProblemEnrichmentError("oracle.cpp 不得為空")

        oracle_path = self.oracle_path(source, external_id)
        oracle_path.parent.mkdir(parents=True, exist_ok=True)
        oracle_path.write_text(oracle_code, encoding="utf-8")

        with tempfile.TemporaryDirectory() as temp:
            candidate = Path(temp) / "candidate"
            oracle = Path(temp) / "oracle"
            candidate_ok, _ = self._compile(
                self.solution_path(source, external_id), candidate
            )
            oracle_ok, _ = self._compile(oracle_path, oracle)

            package["verification"]["compile"] = PASS if candidate_ok else FAIL
            if not candidate_ok or not oracle_ok:
                package["verification"]["differential"] = FAIL
                package["verification"]["trust_status"] = (
                    COMPILE_VERIFIED if candidate_ok else AI_CANDIDATE
                )
            else:
                all_pass = True
                for case in cases:
                    c_ok, c_out, _ = self._run(candidate, case["input"])
                    o_ok, o_out, _ = self._run(oracle, case["input"])
                    if not c_ok or not o_ok or not _same_output(c_out, o_out):
                        all_pass = False
                        break

                package["verification"]["differential"] = PASS if all_pass else FAIL
                if all_pass:
                    package["verification"]["trust_status"] = DIFFERENTIAL_VERIFIED
                elif package["verification"]["samples"] == PASS:
                    package["verification"]["trust_status"] = SAMPLE_VERIFIED
                else:
                    package["verification"]["trust_status"] = COMPILE_VERIFIED

        self._save_verification(source, external_id, package)
        return package

    def mark_oj_accepted(
        self,
        source: str,
        external_id: str,
        reference: str,
    ) -> dict[str, Any]:
        reference = _text(reference)
        if not reference:
            raise ProblemEnrichmentError(
                "OJ Accepted 必須附外部判題 reference"
            )

        package = self.load(source, external_id)
        package["verification"]["oj"] = PASS
        package["verification"]["oj_reference"] = reference
        package["verification"]["trust_status"] = OJ_ACCEPTED
        self._save_verification(source, external_id, package)
        return package

    def validate_package(
        self,
        package: dict[str, Any],
        path: Path | None = None,
    ) -> None:
        if set(package) != {
            "schema_version",
            "identity",
            "teaching",
            "tests",
            "verification",
            "provenance",
        }:
            raise ProblemEnrichmentError("L2 package 頂層 schema 不一致")
        if package["schema_version"] != SCHEMA_VERSION:
            raise ProblemEnrichmentError("L2 schema_version 不正確")

        identity = package["identity"]
        if not isinstance(identity, dict) or set(identity) != {
            "source", "external_id", "canonical_url"
        }:
            raise ProblemEnrichmentError("L2 identity schema 不一致")

        profile = self._eligible_profile(
            _text(identity["source"]),
            _text(identity["external_id"]),
        )
        if identity != profile["identity"]:
            raise ProblemEnrichmentError("L2 identity 與 L1 profile 不一致")

        if path is not None:
            expected = self.package_path(
                identity["source"], identity["external_id"]
            )
            if path.resolve() != expected.resolve():
                raise ProblemEnrichmentError("L2 package 路徑與 identity 不一致")

        teaching = package["teaching"]
        required_teaching = {
            "problem_model",
            "key_observation",
            "correctness_reasoning",
            "invariant",
            "time_complexity",
            "space_complexity",
            "common_pitfalls",
            "edge_cases",
            "hints",
            "alternate_approaches",
            "transfer_signals",
        }
        if not isinstance(teaching, dict) or set(teaching) != required_teaching:
            raise ProblemEnrichmentError("teaching schema 不一致")

        for field in (
            "problem_model",
            "key_observation",
            "correctness_reasoning",
            "invariant",
            "time_complexity",
            "space_complexity",
        ):
            if not _text(teaching[field]):
                raise ProblemEnrichmentError(f"teaching.{field} 不得為空")

        for field in (
            "common_pitfalls",
            "edge_cases",
            "alternate_approaches",
            "transfer_signals",
        ):
            _string_list(teaching[field], f"teaching.{field}")

        hints = teaching["hints"]
        if not isinstance(hints, dict) or set(hints) != {"A1", "A2", "A3", "A4", "A5"}:
            raise ProblemEnrichmentError("teaching.hints 必須完整包含 A1–A5")
        if any(not _text(value) for value in hints.values()):
            raise ProblemEnrichmentError("A1–A5 提示不得為空")

        tests = package["tests"]
        if not isinstance(tests, dict) or set(tests) != {
            "official_samples", "generated_cases"
        }:
            raise ProblemEnrichmentError("tests schema 不一致")
        _case_list(tests["official_samples"], "official_samples", require_output=True)
        _case_list(tests["generated_cases"], "generated_cases", require_output=False)

        verification = package["verification"]
        if not isinstance(verification, dict) or set(verification) != {
            "trust_status", "compile", "samples", "differential", "oj", "oj_reference"
        }:
            raise ProblemEnrichmentError("verification schema 不一致")

        trust = verification["trust_status"]
        if trust not in TRUST_ORDER:
            raise ProblemEnrichmentError("trust_status 不合法")
        for field in ("compile", "samples", "differential", "oj"):
            if verification[field] not in {NOT_RUN, PASS, FAIL}:
                raise ProblemEnrichmentError(f"verification.{field} 不合法")

        if trust in {
            COMPILE_VERIFIED,
            SAMPLE_VERIFIED,
            DIFFERENTIAL_VERIFIED,
        } and verification["compile"] != PASS:
            raise ProblemEnrichmentError(
                "本機驗證狀態必須有 compile PASS"
            )
        if (
            trust == SAMPLE_VERIFIED
            and verification["samples"] != PASS
        ):
            raise ProblemEnrichmentError(
                "Sample Verified 必須有 samples PASS"
            )
        if (
            trust == DIFFERENTIAL_VERIFIED
            and verification["differential"] != PASS
        ):
            raise ProblemEnrichmentError(
                "Differential Verified 必須有 differential PASS"
            )
        if trust == OJ_ACCEPTED and (
            verification["oj"] != PASS
            or not _text(verification["oj_reference"])
        ):
            raise ProblemEnrichmentError(
                "OJ Accepted 必須有外部判題 reference"
            )

        if not isinstance(package["provenance"], dict) or set(package["provenance"]) != {
            "generation_source"
        }:
            raise ProblemEnrichmentError("provenance schema 不一致")
        if not _text(package["provenance"]["generation_source"]):
            raise ProblemEnrichmentError("generation_source 不得為空")

        solution = self.solution_path(identity["source"], identity["external_id"])
        if path is not None and not solution.is_file():
            raise ProblemEnrichmentError("缺少 solution.cpp")

    def validate_all(self) -> list[str]:
        errors = []
        for path in self.all_packages():
            try:
                self.validate_package(self._read_json(path), path)
            except ProblemEnrichmentError as exc:
                errors.append(f"{path}: {exc}")
        return errors


def _payload(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProblemEnrichmentError(f"無法讀取 JSON：{exc}") from exc
    if not isinstance(data, dict):
        raise ProblemEnrichmentError("輸入 JSON 必須是 object")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="APCS v2.4 C2 深度教學資料工具")
    parser.add_argument("--profile-dir", type=Path, default=DEFAULT_PROFILE_DIR, help=argparse.SUPPRESS)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_ENRICHMENT_DIR, help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create")
    create.add_argument("source")
    create.add_argument("external_id")
    create.add_argument("--input", type=Path, required=True)
    create.add_argument("--solution", type=Path, required=True)
    create.add_argument("--replace", action="store_true")

    for name in ("verify-compile", "verify-samples"):
        p = sub.add_parser(name)
        p.add_argument("source")
        p.add_argument("external_id")

    diff = sub.add_parser("verify-differential")
    diff.add_argument("source")
    diff.add_argument("external_id")
    diff.add_argument("--oracle", type=Path, required=True)

    oj = sub.add_parser("mark-oj-accepted")
    oj.add_argument("source")
    oj.add_argument("external_id")
    oj.add_argument("--reference", required=True)

    sub.add_parser("validate")
    args = parser.parse_args(argv)
    store = ProblemEnrichmentStore(
        ProblemIntelligenceStore(args.profile_dir),
        args.data_dir,
    )

    try:
        if args.command == "create":
            package = store.create(
                args.source,
                args.external_id,
                _payload(args.input),
                args.solution.read_text(encoding="utf-8"),
                replace=args.replace,
            )
            print(
                f"已建立 L2：{package['identity']['source']}:"
                f"{package['identity']['external_id']}｜AI_CANDIDATE"
            )
            return 0

        if args.command == "verify-compile":
            package = store.verify_compile(args.source, args.external_id)
        elif args.command == "verify-samples":
            package = store.verify_samples(args.source, args.external_id)
        elif args.command == "verify-differential":
            package = store.verify_differential(
                args.source,
                args.external_id,
                args.oracle.read_text(encoding="utf-8"),
            )
        elif args.command == "mark-oj-accepted":
            package = store.mark_oj_accepted(
                args.source, args.external_id, args.reference
            )
        else:
            errors = store.validate_all()
            for error in errors:
                print(f"錯誤：{error}")
            print(
                f"L2 驗證 {'PASS' if not errors else 'FAIL'}｜"
                f"{len(store.all_packages())} 個 package"
            )
            return 1 if errors else 0

        print(
            f"驗證狀態：{package['verification']['trust_status']}"
        )
        return 0

    except (ProblemEnrichmentError, OSError) as exc:
        print(f"錯誤：{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
