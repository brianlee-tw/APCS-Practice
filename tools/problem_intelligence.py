#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qs, urlparse

SCHEMA_VERSION = "apcs-problem-intelligence-v1"
L0 = "L0_INDEXED"
L1 = "L1_CLASSIFIED"
UNCLASSIFIED = "UNCLASSIFIED"
CANDIDATE = "CANDIDATE"
NEEDS_QA = "NEEDS_QA"
CONFIDENCE_THRESHOLD = 0.80

ZEROJUDGE_ID = re.compile(r"^(?:[a-z]\d+|\d+)$", re.I)
ZEROJUDGE_HOSTS = {"zerojudge.tw", "www.zerojudge.tw"}

VALID_DIFFICULTY = {"D1", "D2", "D3", "D4", "D5"}
VALID_ROLE = {
    "Worked Example",
    "Guided Drill",
    "Core Independent",
    "Transfer Challenge",
    "Mock",
}
VALID_ALT_RISK = {"Low", "Medium", "High"}
VALID_EVIDENCE = {"Reading", "Implementation", "Both", "Not Suitable"}
VALID_CLASSIFIER = {"AI_CANDIDATE", "HUMAN_CURATOR"}
VALID_METADATA_SOURCE = {
    "URL_ONLY",
    "SOURCE_PAGE",
    "AI_EXTRACTED_FROM_SOURCE",
}

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "data" / "problem_intelligence"


class ProblemIntelligenceError(ValueError):
    pass


@dataclass(frozen=True)
class Identity:
    source: str
    external_id: str
    canonical_url: str

    @property
    def key(self) -> str:
        return f"{self.source}:{self.external_id}"


@dataclass(frozen=True)
class ImportSummary:
    added: tuple[str, ...]
    existing: tuple[str, ...]
    errors: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors


def _text(value: Any) -> str:
    return str(value or "").strip()


def _string_list(value: Any, name: str) -> list[str]:
    if not isinstance(value, list):
        raise ProblemIntelligenceError(f"{name} 必須是陣列")
    return sorted({_text(x) for x in value if _text(x)})


def normalize_problem_url(raw_url: str) -> Identity:
    raw = _text(raw_url)
    if not raw:
        raise ProblemIntelligenceError("題目網址不可為空")

    parsed = urlparse(raw if "://" in raw else "https://" + raw)
    host = parsed.netloc.lower().split("@")[-1].split(":")[0]
    if host not in ZEROJUDGE_HOSTS:
        raise ProblemIntelligenceError(
            f"目前 C1 只支援 ZeroJudge，無法匯入：{raw_url}"
        )
    if parsed.path.rstrip("/").lower() != "/showproblem":
        raise ProblemIntelligenceError("ZeroJudge 網址必須是 ShowProblem 題目頁")

    values = None
    for key, items in parse_qs(parsed.query).items():
        if key.lower() == "problemid":
            values = items
            break
    external_id = _text(values[0]).lower() if values else ""
    if not ZEROJUDGE_ID.fullmatch(external_id):
        raise ProblemIntelligenceError(
            f"ZeroJudge problemid 格式不合法：{external_id!r}"
        )

    return Identity(
        "zerojudge",
        external_id,
        f"https://zerojudge.tw/ShowProblem?problemid={external_id}",
    )


def empty_record(identity: Identity) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "identity": {
            "source": identity.source,
            "external_id": identity.external_id,
            "canonical_url": identity.canonical_url,
        },
        "lifecycle": L0,
        "source_metadata": {
            "title": "",
            "statement_summary": "",
            "constraints": [],
            "metadata_source": "URL_ONLY",
        },
        "classification": {
            "status": UNCLASSIFIED,
            "confidence": None,
            "primary_skill_candidate": None,
            "supporting_skill_candidates": [],
            "difficulty_candidate": None,
            "prerequisite_candidates": [],
            "expected_complexity_candidate": None,
            "role_candidate": None,
            "alternate_solution_risk_candidate": None,
            "evidence_suitability_candidate": None,
            "rationale": "",
            "qa_reasons": [],
            "classification_source": None,
        },
        "integration": {
            "pb_uid": None,
            "runtime_eligible": False,
        },
    }


class ProblemIntelligenceStore:
    def __init__(self, data_dir: Path = DEFAULT_DATA_DIR):
        self.data_dir = Path(data_dir)

    def path_for(self, identity: Identity) -> Path:
        return self.data_dir / identity.source / f"{identity.external_id}.json"

    @staticmethod
    def _read(path: Path) -> dict[str, Any]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ProblemIntelligenceError(f"{path}: JSON 無法讀取：{exc}") from exc
        if not isinstance(data, dict):
            raise ProblemIntelligenceError(f"{path}: 必須是 JSON object")
        return data

    @staticmethod
    def _write(path: Path, data: dict[str, Any]) -> None:
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

    def all_paths(self) -> list[Path]:
        if not self.data_dir.exists():
            return []
        return sorted(self.data_dir.rglob("*.json"))

    def load(self, source: str, external_id: str) -> dict[str, Any]:
        source, external_id = _text(source).lower(), _text(external_id).lower()
        if source != "zerojudge":
            raise ProblemIntelligenceError(f"不支援的來源：{source}")
        if not ZEROJUDGE_ID.fullmatch(external_id):
            raise ProblemIntelligenceError(
                f"ZeroJudge problemid 格式不合法：{external_id!r}"
            )
        identity = Identity(
            source,
            external_id,
            f"https://zerojudge.tw/ShowProblem?problemid={external_id}",
        )
        path = self.path_for(identity)
        if not path.is_file():
            raise ProblemIntelligenceError(f"找不到題目智慧資料：{identity.key}")
        return self._read(path)

    def import_urls(self, urls: Iterable[str]) -> ImportSummary:
        added, existing, errors = [], [], []
        seen: set[str] = set()

        for raw in filter(None, (_text(x) for x in urls)):
            try:
                identity = normalize_problem_url(raw)
            except ProblemIntelligenceError as exc:
                errors.append(f"{raw} :: {exc}")
                continue

            if identity.key in seen:
                if identity.key not in existing:
                    existing.append(identity.key)
                continue
            seen.add(identity.key)

            path = self.path_for(identity)
            if path.exists():
                try:
                    self.validate_record(self._read(path), path)
                except ProblemIntelligenceError as exc:
                    errors.append(f"{identity.key} :: 現有資料無效：{exc}")
                    continue
                existing.append(identity.key)
                continue

            record = empty_record(identity)
            self.validate_record(record, path)
            self._write(path, record)
            added.append(identity.key)

        return ImportSummary(tuple(added), tuple(existing), tuple(errors))

    def update_source_metadata(
        self,
        source: str,
        external_id: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        allowed = {"title", "statement_summary", "constraints", "metadata_source"}
        unknown = sorted(set(metadata) - allowed)
        if unknown:
            raise ProblemIntelligenceError(
                "source metadata 含未知欄位：" + ", ".join(unknown)
            )

        record = self.load(source, external_id)
        current = dict(record["source_metadata"])
        if "title" in metadata:
            current["title"] = _text(metadata["title"])
        if "statement_summary" in metadata:
            current["statement_summary"] = _text(metadata["statement_summary"])
        if "constraints" in metadata:
            current["constraints"] = _string_list(
                metadata["constraints"], "constraints"
            )
        if "metadata_source" in metadata:
            value = _text(metadata["metadata_source"])
            if value not in VALID_METADATA_SOURCE:
                raise ProblemIntelligenceError("metadata_source 值不合法")
            current["metadata_source"] = value

        record["source_metadata"] = current
        identity = self.identity(record)
        path = self.path_for(identity)
        self.validate_record(record, path)
        self._write(path, record)
        return record

    def apply_classification(
        self,
        source: str,
        external_id: str,
        candidate: dict[str, Any],
    ) -> dict[str, Any]:
        allowed = {
            "confidence",
            "primary_skill_candidate",
            "supporting_skill_candidates",
            "difficulty_candidate",
            "prerequisite_candidates",
            "expected_complexity_candidate",
            "role_candidate",
            "alternate_solution_risk_candidate",
            "evidence_suitability_candidate",
            "rationale",
            "ambiguity_notes",
            "classification_source",
        }
        unknown = sorted(set(candidate) - allowed)
        if unknown:
            raise ProblemIntelligenceError(
                "classification 含未知欄位：" + ", ".join(unknown)
            )

        try:
            confidence = float(candidate.get("confidence"))
        except (TypeError, ValueError) as exc:
            raise ProblemIntelligenceError("confidence 必須是 0–1 的數字") from exc
        if isinstance(candidate.get("confidence"), bool) or not 0 <= confidence <= 1:
            raise ProblemIntelligenceError("confidence 必須介於 0–1")

        primary = _text(candidate.get("primary_skill_candidate")) or None
        difficulty = _text(candidate.get("difficulty_candidate")) or None
        role = _text(candidate.get("role_candidate")) or None
        alt_risk = _text(candidate.get("alternate_solution_risk_candidate")) or None
        evidence = _text(candidate.get("evidence_suitability_candidate")) or None
        classifier = _text(candidate.get("classification_source")) or "AI_CANDIDATE"

        if difficulty and difficulty not in VALID_DIFFICULTY:
            raise ProblemIntelligenceError("difficulty_candidate 必須是 D1–D5")
        if role and role not in VALID_ROLE:
            raise ProblemIntelligenceError("role_candidate 值不合法")
        if alt_risk and alt_risk not in VALID_ALT_RISK:
            raise ProblemIntelligenceError("alternate_solution_risk_candidate 值不合法")
        if evidence and evidence not in VALID_EVIDENCE:
            raise ProblemIntelligenceError("evidence_suitability_candidate 值不合法")
        if classifier not in VALID_CLASSIFIER:
            raise ProblemIntelligenceError("classification_source 值不合法")

        ambiguity = _string_list(candidate.get("ambiguity_notes", []), "ambiguity_notes")
        qa = []
        if confidence < CONFIDENCE_THRESHOLD:
            qa.append("分類信心低於自動候選門檻 0.80")
        if not primary:
            qa.append("缺少 Primary Skill candidate")
        if not difficulty:
            qa.append("缺少 difficulty candidate")
        qa.extend(f"分類歧義：{note}" for note in ambiguity)

        record = self.load(source, external_id)
        record["lifecycle"] = L1
        record["classification"] = {
            "status": NEEDS_QA if qa else CANDIDATE,
            "confidence": confidence,
            "primary_skill_candidate": primary,
            "supporting_skill_candidates": _string_list(
                candidate.get("supporting_skill_candidates", []),
                "supporting_skill_candidates",
            ),
            "difficulty_candidate": difficulty,
            "prerequisite_candidates": _string_list(
                candidate.get("prerequisite_candidates", []),
                "prerequisite_candidates",
            ),
            "expected_complexity_candidate": (
                _text(candidate.get("expected_complexity_candidate")) or None
            ),
            "role_candidate": role,
            "alternate_solution_risk_candidate": alt_risk,
            "evidence_suitability_candidate": evidence,
            "rationale": _text(candidate.get("rationale")),
            "qa_reasons": qa,
            "classification_source": classifier,
        }
        record["integration"]["runtime_eligible"] = False

        identity = self.identity(record)
        path = self.path_for(identity)
        self.validate_record(record, path)
        self._write(path, record)
        return record

    @staticmethod
    def identity(record: dict[str, Any]) -> Identity:
        raw = record.get("identity")
        if not isinstance(raw, dict):
            raise ProblemIntelligenceError("identity 必須是 object")
        source = _text(raw.get("source")).lower()
        external_id = _text(raw.get("external_id")).lower()
        canonical = _text(raw.get("canonical_url"))
        if source != "zerojudge":
            raise ProblemIntelligenceError(f"不支援的 source：{source}")
        normalized = normalize_problem_url(canonical)
        if normalized.external_id != external_id:
            raise ProblemIntelligenceError("external_id 與 canonical_url 不一致")
        return normalized

    def validate_record(self, record: dict[str, Any], path: Path | None = None) -> None:
        expected_top = {
            "schema_version", "identity", "lifecycle",
            "source_metadata", "classification", "integration",
        }
        if set(record) != expected_top:
            raise ProblemIntelligenceError("題目智慧頂層 schema 不一致")
        if record["schema_version"] != SCHEMA_VERSION:
            raise ProblemIntelligenceError("schema_version 不正確")

        identity = self.identity(record)
        if path is not None and path.resolve() != self.path_for(identity).resolve():
            raise ProblemIntelligenceError("檔案路徑與 identity 不一致")

        metadata = record["source_metadata"]
        if not isinstance(metadata, dict) or set(metadata) != {
            "title", "statement_summary", "constraints", "metadata_source"
        }:
            raise ProblemIntelligenceError("source_metadata schema 不一致")
        if not isinstance(metadata["title"], str) or not isinstance(
            metadata["statement_summary"], str
        ):
            raise ProblemIntelligenceError("title / statement_summary 必須是字串")
        _string_list(metadata["constraints"], "constraints")
        if metadata["metadata_source"] not in VALID_METADATA_SOURCE:
            raise ProblemIntelligenceError("metadata_source 值不合法")

        classification = record["classification"]
        expected_class = {
            "status", "confidence", "primary_skill_candidate",
            "supporting_skill_candidates", "difficulty_candidate",
            "prerequisite_candidates", "expected_complexity_candidate",
            "role_candidate", "alternate_solution_risk_candidate",
            "evidence_suitability_candidate", "rationale", "qa_reasons",
            "classification_source",
        }
        if not isinstance(classification, dict) or set(classification) != expected_class:
            raise ProblemIntelligenceError("classification schema 不一致")

        lifecycle, status = record["lifecycle"], classification["status"]
        if lifecycle == L0:
            if status != UNCLASSIFIED:
                raise ProblemIntelligenceError("L0 題目必須是 UNCLASSIFIED")
        elif lifecycle == L1:
            if status not in {CANDIDATE, NEEDS_QA}:
                raise ProblemIntelligenceError("L1 題目狀態不合法")
            confidence = classification["confidence"]
            if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
                raise ProblemIntelligenceError("L1 confidence 必須是數字")
            if not 0 <= float(confidence) <= 1:
                raise ProblemIntelligenceError("L1 confidence 必須介於 0–1")
            qa = _string_list(classification["qa_reasons"], "qa_reasons")
            if status == CANDIDATE and (
                qa
                or confidence < CONFIDENCE_THRESHOLD
                or not classification["primary_skill_candidate"]
                or not classification["difficulty_candidate"]
            ):
                raise ProblemIntelligenceError("CANDIDATE 不符合自動候選門檻")
            if status == NEEDS_QA and not qa:
                raise ProblemIntelligenceError("NEEDS_QA 必須有 qa_reasons")
            if classification["classification_source"] not in VALID_CLASSIFIER:
                raise ProblemIntelligenceError("classification_source 值不合法")
        else:
            raise ProblemIntelligenceError(f"lifecycle 不合法：{lifecycle!r}")

        integration = record["integration"]
        if not isinstance(integration, dict) or set(integration) != {
            "pb_uid", "runtime_eligible"
        }:
            raise ProblemIntelligenceError("integration schema 不一致")
        if integration["runtime_eligible"] is not False:
            raise ProblemIntelligenceError(
                "C1 題目智慧資料不得直接成為 runtime eligible"
            )
        if integration["pb_uid"] is not None and not _text(integration["pb_uid"]):
            raise ProblemIntelligenceError("pb_uid 必須是非空字串或 null")

    def validate_all(self) -> list[str]:
        errors, seen, urls = [], {}, {}
        for path in self.all_paths():
            try:
                record = self._read(path)
                self.validate_record(record, path)
                identity = self.identity(record)
            except ProblemIntelligenceError as exc:
                errors.append(f"{path}: {exc}")
                continue

            if identity.key in seen:
                errors.append(f"{path}: duplicate identity {identity.key}")
            else:
                seen[identity.key] = path
            if identity.canonical_url in urls:
                errors.append(f"{path}: duplicate canonical_url")
            else:
                urls[identity.canonical_url] = path
        return errors


def _read_url_file(path: Path) -> list[str]:
    try:
        return [
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
    except OSError as exc:
        raise ProblemIntelligenceError(f"無法讀取 URL 檔案：{exc}") from exc


def _payload(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProblemIntelligenceError(f"無法讀取 JSON：{exc}") from exc
    if not isinstance(data, dict):
        raise ProblemIntelligenceError("輸入 JSON 必須是 object")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="APCS v2.4 題目智慧 C1 工具")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR, help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="command", required=True)

    p_import = sub.add_parser("import", help="匯入一題或一批題目網址")
    p_import.add_argument("urls", nargs="*")
    p_import.add_argument("--file", type=Path, help="每行一個題目網址")

    for name, help_text in (
        ("metadata", "寫入來源 metadata"),
        ("classify", "套用 L1 AI 候選分類"),
    ):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("source")
        p.add_argument("external_id")
        p.add_argument("--input", type=Path, required=True)

    sub.add_parser("validate", help="驗證全部題目智慧資料")
    args = parser.parse_args(argv)
    store = ProblemIntelligenceStore(args.data_dir)

    try:
        if args.command == "import":
            urls = list(args.urls)
            if args.file:
                urls += _read_url_file(args.file)
            if not urls:
                raise ProblemIntelligenceError("至少提供一個題目網址或 --file")
            result = store.import_urls(urls)
            for key in result.added:
                print(f"新增：{key}")
            for key in result.existing:
                print(f"已存在：{key}")
            for error in result.errors:
                print(f"錯誤：{error}")
            print(
                f"完成：新增 {len(result.added)}｜已存在 {len(result.existing)}｜"
                f"錯誤 {len(result.errors)}"
            )
            return 0 if result.ok else 1

        if args.command == "metadata":
            record = store.update_source_metadata(
                args.source, args.external_id, _payload(args.input)
            )
            print(f"已更新來源 metadata：{store.identity(record).key}")
            return 0

        if args.command == "classify":
            record = store.apply_classification(
                args.source, args.external_id, _payload(args.input)
            )
            print(
                f"已分類：{store.identity(record).key}｜"
                f"{record['classification']['status']}"
            )
            for reason in record["classification"]["qa_reasons"]:
                print(f"需檢查：{reason}")
            return 0

        errors = store.validate_all()
        for error in errors:
            print(f"錯誤：{error}")
        print(
            f"題目智慧驗證 {'PASS' if not errors else 'FAIL'}｜"
            f"{len(store.all_paths())} 個題目"
        )
        return 1 if errors else 0

    except ProblemIntelligenceError as exc:
        print(f"錯誤：{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
