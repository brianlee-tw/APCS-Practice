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
L0_INDEXED = "L0_INDEXED"
L1_CLASSIFIED = "L1_CLASSIFIED"

CLASS_UNCLASSIFIED = "UNCLASSIFIED"
CLASS_CANDIDATE = "CANDIDATE"
CLASS_NEEDS_QA = "NEEDS_QA"

CLASSIFICATION_CONFIDENCE_THRESHOLD = 0.80

SOURCE_ZEROJUDGE = "zerojudge"
SUPPORTED_SOURCES = {SOURCE_ZEROJUDGE}

ZEROJUDGE_HOSTS = {
    "zerojudge.tw",
    "www.zerojudge.tw",
}
ZEROJUDGE_ID_RE = re.compile(r"^(?:[a-z]\d+|\d+)$", re.IGNORECASE)

VALID_DIFFICULTIES = {
    "D1",
    "D2",
    "D3",
    "D4",
    "D5",
}

VALID_ROLES = {
    "Worked Example",
    "Guided Drill",
    "Core Independent",
    "Transfer Challenge",
    "Mock",
}

VALID_EVIDENCE_SUITABILITY = {
    "Reading",
    "Implementation",
    "Both",
    "Not Suitable",
}

VALID_ALTERNATE_SOLUTION_RISK = {
    "Low",
    "Medium",
    "High",
}

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "data" / "problem_intelligence"


class ProblemIntelligenceError(ValueError):
    pass


@dataclass(frozen=True)
class ExternalIdentity:
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


def _clean_string(value: Any) -> str:
    return str(value or "").strip()


def normalize_problem_url(raw_url: str) -> ExternalIdentity:
    """將支援的外部 OJ 網址轉成穩定 identity。

    C1 只正式支援 ZeroJudge。其他來源必須明確拒絕，避免系統
    猜測來源或建立錯誤 identity。
    """

    raw = _clean_string(raw_url)
    if not raw:
        raise ProblemIntelligenceError("題目網址不可為空")

    candidate = raw
    if "://" not in candidate:
        candidate = "https://" + candidate

    parsed = urlparse(candidate)
    host = parsed.netloc.lower().split("@")[-1].split(":")[0]

    if host not in ZEROJUDGE_HOSTS:
        raise ProblemIntelligenceError(
            f"目前 C1 只支援 ZeroJudge，無法匯入：{raw_url}"
        )

    if parsed.path.rstrip("/").lower() != "/showproblem":
        raise ProblemIntelligenceError(
            "ZeroJudge 網址必須是 ShowProblem 題目頁"
        )

    query = parse_qs(parsed.query)
    values = query.get("problemid") or query.get("problemId")

    if not values:
        # parse_qs preserves exact key case; tolerate arbitrary case without
        # silently accepting unrelated query fields.
        for key, items in query.items():
            if key.lower() == "problemid":
                values = items
                break

    if not values:
        raise ProblemIntelligenceError(
            "ZeroJudge 網址缺少 problemid"
        )

    external_id = _clean_string(values[0]).lower()

    if not ZEROJUDGE_ID_RE.fullmatch(external_id):
        raise ProblemIntelligenceError(
            f"ZeroJudge problemid 格式不合法：{external_id!r}"
        )

    canonical_url = (
        "https://zerojudge.tw/ShowProblem"
        f"?problemid={external_id}"
    )

    return ExternalIdentity(
        source=SOURCE_ZEROJUDGE,
        external_id=external_id,
        canonical_url=canonical_url,
    )


def empty_record(identity: ExternalIdentity) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "identity": {
            "source": identity.source,
            "external_id": identity.external_id,
            "canonical_url": identity.canonical_url,
        },
        "lifecycle": L0_INDEXED,
        "source_metadata": {
            "title": "",
            "statement_summary": "",
            "constraints": [],
            "metadata_source": "URL_ONLY",
        },
        "classification": {
            "status": CLASS_UNCLASSIFIED,
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
            "problem_bank_status": "UNLINKED",
            "pb_uid": None,
            "runtime_eligible": False,
        },
    }


class ProblemIntelligenceStore:
    """v2.4 C1 的輕量題目智慧儲存層。

    一題一個 JSON。這些資料是外部題目的 index / classification
    artifact，不是 Problem Bank，也不具 Published Curriculum 權限。
    """

    def __init__(self, data_dir: Path = DEFAULT_DATA_DIR):
        self.data_dir = Path(data_dir)

    def record_path(self, identity: ExternalIdentity) -> Path:
        return (
            self.data_dir
            / identity.source
            / f"{identity.external_id}.json"
        )

    @staticmethod
    def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(path.name + ".tmp")
        try:
            temp.write_text(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            temp.replace(path)
        finally:
            temp.unlink(missing_ok=True)

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ProblemIntelligenceError(
                f"{path}: JSON 無法讀取：{exc}"
            ) from exc

        if not isinstance(value, dict):
            raise ProblemIntelligenceError(
                f"{path}: 題目智慧檔案必須是 JSON object"
            )
        return value

    def all_paths(self) -> list[Path]:
        if not self.data_dir.exists():
            return []
        return sorted(
            path
            for path in self.data_dir.rglob("*.json")
            if path.is_file()
        )

    def load(self, source: str, external_id: str) -> dict[str, Any]:
        source = _clean_string(source).lower()
        external_id = _clean_string(external_id).lower()
        if source not in SUPPORTED_SOURCES:
            raise ProblemIntelligenceError(
                f"不支援的來源：{source}"
            )

        identity = ExternalIdentity(
            source=source,
            external_id=external_id,
            canonical_url=(
                "https://zerojudge.tw/ShowProblem"
                f"?problemid={external_id}"
            )
            if source == SOURCE_ZEROJUDGE
            else ""
        )
        path = self.record_path(identity)
        if not path.is_file():
            raise ProblemIntelligenceError(
                f"找不到題目智慧資料：{identity.key}"
            )
        return self._read_json(path)

    def import_urls(self, urls: Iterable[str]) -> ImportSummary:
        added: list[str] = []
        existing: list[str] = []
        errors: list[str] = []
        seen_batch: set[str] = set()

        for raw in urls:
            raw = _clean_string(raw)
            if not raw:
                continue

            try:
                identity = normalize_problem_url(raw)
            except ProblemIntelligenceError as exc:
                errors.append(f"{raw} :: {exc}")
                continue

            if identity.key in seen_batch:
                if identity.key not in existing:
                    existing.append(identity.key)
                continue

            seen_batch.add(identity.key)
            path = self.record_path(identity)

            if path.exists():
                try:
                    record = self._read_json(path)
                    self.validate_record(record, path=path)
                except ProblemIntelligenceError as exc:
                    errors.append(
                        f"{identity.key} :: 現有資料無效：{exc}"
                    )
                    continue

                existing.append(identity.key)
                continue

            record = empty_record(identity)
            self.validate_record(record, path=path)
            self._atomic_write(path, record)
            added.append(identity.key)

        return ImportSummary(
            added=tuple(added),
            existing=tuple(existing),
            errors=tuple(errors),
        )

    def update_source_metadata(
        self,
        source: str,
        external_id: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        record = self.load(source, external_id)
        current = dict(record["source_metadata"])

        allowed = {
            "title",
            "statement_summary",
            "constraints",
            "metadata_source",
        }
        unknown = sorted(set(metadata) - allowed)
        if unknown:
            raise ProblemIntelligenceError(
                "source metadata 含未知欄位："
                + ", ".join(unknown)
            )

        if "title" in metadata:
            current["title"] = _clean_string(metadata["title"])

        if "statement_summary" in metadata:
            current["statement_summary"] = _clean_string(
                metadata["statement_summary"]
            )

        if "constraints" in metadata:
            constraints = metadata["constraints"]
            if not isinstance(constraints, list):
                raise ProblemIntelligenceError(
                    "constraints 必須是字串陣列"
                )
            current["constraints"] = [
                _clean_string(item)
                for item in constraints
                if _clean_string(item)
            ]

        if "metadata_source" in metadata:
            source_value = _clean_string(metadata["metadata_source"])
            if source_value not in {
                "URL_ONLY",
                "SOURCE_PAGE",
                "AI_EXTRACTED_FROM_SOURCE",
            }:
                raise ProblemIntelligenceError(
                    "metadata_source 值不合法"
                )
            current["metadata_source"] = source_value

        record["source_metadata"] = current
        identity = self.identity_from_record(record)
        path = self.record_path(identity)
        self.validate_record(record, path=path)
        self._atomic_write(path, record)
        return record

    def apply_classification(
        self,
        source: str,
        external_id: str,
        candidate: dict[str, Any],
    ) -> dict[str, Any]:
        """套用 L1 AI candidate，狀態由 deterministic rule 決定。

        AI 不能直接指定 Published，也不能自行把低信心分類升成
        CANDIDATE。
        """

        record = self.load(source, external_id)

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
                "classification 含未知欄位："
                + ", ".join(unknown)
            )

        confidence_raw = candidate.get("confidence")
        if isinstance(confidence_raw, bool):
            raise ProblemIntelligenceError(
                "confidence 必須是 0–1 的數字"
            )
        try:
            confidence = float(confidence_raw)
        except (TypeError, ValueError) as exc:
            raise ProblemIntelligenceError(
                "confidence 必須是 0–1 的數字"
            ) from exc

        if not 0.0 <= confidence <= 1.0:
            raise ProblemIntelligenceError(
                "confidence 必須介於 0–1"
            )

        primary_skill = _clean_string(
            candidate.get("primary_skill_candidate")
        ) or None

        supporting = candidate.get(
            "supporting_skill_candidates",
            [],
        )
        prerequisites = candidate.get(
            "prerequisite_candidates",
            [],
        )
        ambiguity = candidate.get(
            "ambiguity_notes",
            [],
        )

        for label, value in (
            ("supporting_skill_candidates", supporting),
            ("prerequisite_candidates", prerequisites),
            ("ambiguity_notes", ambiguity),
        ):
            if not isinstance(value, list):
                raise ProblemIntelligenceError(
                    f"{label} 必須是陣列"
                )

        supporting_clean = sorted(
            {
                _clean_string(item)
                for item in supporting
                if _clean_string(item)
            }
        )
        prerequisites_clean = sorted(
            {
                _clean_string(item)
                for item in prerequisites
                if _clean_string(item)
            }
        )
        ambiguity_clean = [
            _clean_string(item)
            for item in ambiguity
            if _clean_string(item)
        ]

        difficulty = _clean_string(
            candidate.get("difficulty_candidate")
        ) or None
        if difficulty and difficulty not in VALID_DIFFICULTIES:
            raise ProblemIntelligenceError(
                "difficulty_candidate 必須是 D1–D5"
            )

        role = _clean_string(
            candidate.get("role_candidate")
        ) or None
        if role and role not in VALID_ROLES:
            raise ProblemIntelligenceError(
                "role_candidate 值不合法"
            )

        alternate_risk = _clean_string(
            candidate.get("alternate_solution_risk_candidate")
        ) or None
        if (
            alternate_risk
            and alternate_risk not in VALID_ALTERNATE_SOLUTION_RISK
        ):
            raise ProblemIntelligenceError(
                "alternate_solution_risk_candidate 值不合法"
            )

        evidence_suitability = _clean_string(
            candidate.get("evidence_suitability_candidate")
        ) or None
        if (
            evidence_suitability
            and evidence_suitability not in VALID_EVIDENCE_SUITABILITY
        ):
            raise ProblemIntelligenceError(
                "evidence_suitability_candidate 值不合法"
            )

        qa_reasons: list[str] = []
        if confidence < CLASSIFICATION_CONFIDENCE_THRESHOLD:
            qa_reasons.append(
                "分類信心低於自動候選門檻 0.80"
            )
        if not primary_skill:
            qa_reasons.append(
                "缺少 Primary Skill candidate"
            )
        if not difficulty:
            qa_reasons.append(
                "缺少 difficulty candidate"
            )
        if ambiguity_clean:
            qa_reasons.extend(
                f"分類歧義：{note}"
                for note in ambiguity_clean
            )

        status = (
            CLASS_NEEDS_QA
            if qa_reasons
            else CLASS_CANDIDATE
        )

        classification_source = _clean_string(
            candidate.get("classification_source")
        ) or "AI_CANDIDATE"

        record["lifecycle"] = L1_CLASSIFIED
        record["classification"] = {
            "status": status,
            "confidence": confidence,
            "primary_skill_candidate": primary_skill,
            "supporting_skill_candidates": supporting_clean,
            "difficulty_candidate": difficulty,
            "prerequisite_candidates": prerequisites_clean,
            "expected_complexity_candidate": (
                _clean_string(
                    candidate.get("expected_complexity_candidate")
                )
                or None
            ),
            "role_candidate": role,
            "alternate_solution_risk_candidate": alternate_risk,
            "evidence_suitability_candidate": evidence_suitability,
            "rationale": _clean_string(
                candidate.get("rationale")
            ),
            "qa_reasons": qa_reasons,
            "classification_source": classification_source,
        }

        # C1 hard boundary: classification cannot publish a problem.
        record["integration"]["runtime_eligible"] = False

        identity = self.identity_from_record(record)
        path = self.record_path(identity)
        self.validate_record(record, path=path)
        self._atomic_write(path, record)
        return record

    @staticmethod
    def identity_from_record(record: dict[str, Any]) -> ExternalIdentity:
        identity = record.get("identity")
        if not isinstance(identity, dict):
            raise ProblemIntelligenceError(
                "identity 必須是 object"
            )

        source = _clean_string(identity.get("source")).lower()
        external_id = _clean_string(
            identity.get("external_id")
        ).lower()
        canonical_url = _clean_string(
            identity.get("canonical_url")
        )

        if source == SOURCE_ZEROJUDGE:
            normalized = normalize_problem_url(canonical_url)
            if normalized.external_id != external_id:
                raise ProblemIntelligenceError(
                    "external_id 與 canonical_url 不一致"
                )
            return normalized

        raise ProblemIntelligenceError(
            f"不支援的 source：{source}"
        )

    def validate_record(
        self,
        record: dict[str, Any],
        *,
        path: Path | None = None,
    ) -> None:
        expected_top = {
            "schema_version",
            "identity",
            "lifecycle",
            "source_metadata",
            "classification",
            "integration",
        }
        if set(record) != expected_top:
            unknown = sorted(set(record) - expected_top)
            missing = sorted(expected_top - set(record))
            detail = []
            if unknown:
                detail.append(
                    "未知欄位=" + ",".join(unknown)
                )
            if missing:
                detail.append(
                    "缺欄位=" + ",".join(missing)
                )
            raise ProblemIntelligenceError(
                "題目智慧頂層 schema 不一致"
                + (
                    "；" + "；".join(detail)
                    if detail
                    else ""
                )
            )

        if record.get("schema_version") != SCHEMA_VERSION:
            raise ProblemIntelligenceError(
                "schema_version 不正確"
            )

        identity = self.identity_from_record(record)

        if path is not None:
            expected = self.record_path(identity)
            try:
                same = path.resolve() == expected.resolve()
            except OSError:
                same = path == expected
            if not same:
                raise ProblemIntelligenceError(
                    "檔案路徑與 identity 不一致"
                )

        lifecycle = record.get("lifecycle")
        if lifecycle not in {
            L0_INDEXED,
            L1_CLASSIFIED,
        }:
            raise ProblemIntelligenceError(
                f"lifecycle 不合法：{lifecycle!r}"
            )

        metadata = record.get("source_metadata")
        if not isinstance(metadata, dict):
            raise ProblemIntelligenceError(
                "source_metadata 必須是 object"
            )

        expected_metadata = {
            "title",
            "statement_summary",
            "constraints",
            "metadata_source",
        }
        if set(metadata) != expected_metadata:
            raise ProblemIntelligenceError(
                "source_metadata schema 不一致"
            )

        if not isinstance(metadata.get("constraints"), list):
            raise ProblemIntelligenceError(
                "source_metadata.constraints 必須是陣列"
            )
        if any(
            not isinstance(item, str)
            or not item.strip()
            for item in metadata["constraints"]
        ):
            raise ProblemIntelligenceError(
                "constraints 只能包含非空字串"
            )

        if metadata.get("metadata_source") not in {
            "URL_ONLY",
            "SOURCE_PAGE",
            "AI_EXTRACTED_FROM_SOURCE",
        }:
            raise ProblemIntelligenceError(
                "metadata_source 值不合法"
            )

        for field in (
            "title",
            "statement_summary",
        ):
            if not isinstance(metadata.get(field), str):
                raise ProblemIntelligenceError(
                    f"source_metadata.{field} 必須是字串"
                )

        classification = record.get("classification")
        if not isinstance(classification, dict):
            raise ProblemIntelligenceError(
                "classification 必須是 object"
            )

        expected_classification = {
            "status",
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
            "qa_reasons",
            "classification_source",
        }
        if set(classification) != expected_classification:
            raise ProblemIntelligenceError(
                "classification schema 不一致"
            )

        for field in (
            "supporting_skill_candidates",
            "prerequisite_candidates",
            "qa_reasons",
        ):
            value = classification.get(field)
            if not isinstance(value, list):
                raise ProblemIntelligenceError(
                    f"classification.{field} 必須是陣列"
                )
            if any(
                not isinstance(item, str)
                or not item.strip()
                for item in value
            ):
                raise ProblemIntelligenceError(
                    f"classification.{field} 只能包含非空字串"
                )

        for field in (
            "primary_skill_candidate",
            "expected_complexity_candidate",
            "classification_source",
        ):
            value = classification.get(field)
            if value is not None and (
                not isinstance(value, str)
                or not value.strip()
            ):
                raise ProblemIntelligenceError(
                    f"classification.{field} 必須是非空字串或 null"
                )

        if not isinstance(classification.get("rationale"), str):
            raise ProblemIntelligenceError(
                "classification.rationale 必須是字串"
            )

        difficulty = classification.get(
            "difficulty_candidate"
        )
        if (
            difficulty is not None
            and difficulty not in VALID_DIFFICULTIES
        ):
            raise ProblemIntelligenceError(
                "difficulty_candidate 必須是 D1–D5 或 null"
            )

        role = classification.get("role_candidate")
        if (
            role is not None
            and role not in VALID_ROLES
        ):
            raise ProblemIntelligenceError(
                "role_candidate 值不合法"
            )

        alternate_risk = classification.get(
            "alternate_solution_risk_candidate"
        )
        if (
            alternate_risk is not None
            and alternate_risk not in VALID_ALTERNATE_SOLUTION_RISK
        ):
            raise ProblemIntelligenceError(
                "alternate_solution_risk_candidate 值不合法"
            )

        evidence_suitability = classification.get(
            "evidence_suitability_candidate"
        )
        if (
            evidence_suitability is not None
            and evidence_suitability not in VALID_EVIDENCE_SUITABILITY
        ):
            raise ProblemIntelligenceError(
                "evidence_suitability_candidate 值不合法"
            )

        status = classification.get("status")
        if lifecycle == L0_INDEXED:
            if status != CLASS_UNCLASSIFIED:
                raise ProblemIntelligenceError(
                    "L0 題目必須是 UNCLASSIFIED"
                )
        else:
            if status not in {
                CLASS_CANDIDATE,
                CLASS_NEEDS_QA,
            }:
                raise ProblemIntelligenceError(
                    "L1 題目必須是 CANDIDATE 或 NEEDS_QA"
                )

            confidence = classification.get("confidence")
            if (
                not isinstance(confidence, (int, float))
                or isinstance(confidence, bool)
                or not 0 <= float(confidence) <= 1
            ):
                raise ProblemIntelligenceError(
                    "L1 confidence 必須介於 0–1"
                )

            if (
                status == CLASS_CANDIDATE
                and classification.get("qa_reasons")
            ):
                raise ProblemIntelligenceError(
                    "CANDIDATE 不得同時存在 qa_reasons"
                )

            if (
                status == CLASS_NEEDS_QA
                and not classification.get("qa_reasons")
            ):
                raise ProblemIntelligenceError(
                    "NEEDS_QA 必須說明 qa_reasons"
                )

            if (
                status == CLASS_CANDIDATE
                and float(confidence)
                < CLASSIFICATION_CONFIDENCE_THRESHOLD
            ):
                raise ProblemIntelligenceError(
                    "CANDIDATE confidence 不得低於 0.80"
                )

            if (
                status == CLASS_CANDIDATE
                and not classification.get(
                    "primary_skill_candidate"
                )
            ):
                raise ProblemIntelligenceError(
                    "CANDIDATE 必須有 Primary Skill candidate"
                )

            if (
                status == CLASS_CANDIDATE
                and not classification.get(
                    "difficulty_candidate"
                )
            ):
                raise ProblemIntelligenceError(
                    "CANDIDATE 必須有 difficulty candidate"
                )

            if not classification.get(
                "classification_source"
            ):
                raise ProblemIntelligenceError(
                    "L1 classification_source 不得為空"
                )

        integration = record.get("integration")
        if not isinstance(integration, dict):
            raise ProblemIntelligenceError(
                "integration 必須是 object"
            )

        expected_integration = {
            "problem_bank_status",
            "pb_uid",
            "runtime_eligible",
        }
        if set(integration) != expected_integration:
            raise ProblemIntelligenceError(
                "integration schema 不一致"
            )

        if integration.get("runtime_eligible") is not False:
            raise ProblemIntelligenceError(
                "C1 題目智慧資料不得直接成為 runtime eligible"
            )

        if integration.get("problem_bank_status") not in {
            "UNLINKED",
            "LINKED",
        }:
            raise ProblemIntelligenceError(
                "problem_bank_status 不合法"
            )

        pb_uid = integration.get("pb_uid")
        if (
            integration.get("problem_bank_status") == "UNLINKED"
            and pb_uid is not None
        ):
            raise ProblemIntelligenceError(
                "UNLINKED 題目不得帶 pb_uid"
            )

        if (
            integration.get("problem_bank_status") == "LINKED"
            and not _clean_string(pb_uid)
        ):
            raise ProblemIntelligenceError(
                "LINKED 題目必須帶 pb_uid"
            )

    def validate_all(self) -> list[str]:
        errors: list[str] = []
        seen_keys: dict[str, Path] = {}
        seen_urls: dict[str, Path] = {}

        for path in self.all_paths():
            try:
                record = self._read_json(path)
                self.validate_record(record, path=path)
                identity = self.identity_from_record(record)
            except ProblemIntelligenceError as exc:
                errors.append(f"{path}: {exc}")
                continue

            if identity.key in seen_keys:
                errors.append(
                    f"{path}: duplicate identity {identity.key}; "
                    f"已存在 {seen_keys[identity.key]}"
                )
            else:
                seen_keys[identity.key] = path

            if identity.canonical_url in seen_urls:
                errors.append(
                    f"{path}: duplicate canonical_url；"
                    f"已存在 {seen_urls[identity.canonical_url]}"
                )
            else:
                seen_urls[identity.canonical_url] = path

        return errors


def _read_url_file(path: Path) -> list[str]:
    try:
        return [
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
    except OSError as exc:
        raise ProblemIntelligenceError(
            f"無法讀取 URL 檔案：{exc}"
        ) from exc


def _load_payload(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProblemIntelligenceError(
            f"無法讀取 JSON：{exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise ProblemIntelligenceError(
            "輸入 JSON 必須是 object"
        )
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="APCS v2.4 題目智慧 C1 工具"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=argparse.SUPPRESS,
    )

    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    import_parser = sub.add_parser(
        "import",
        help="匯入一題或一批題目網址",
    )
    import_parser.add_argument(
        "urls",
        nargs="*",
    )
    import_parser.add_argument(
        "--file",
        type=Path,
        help="每行一個題目網址",
    )

    metadata_parser = sub.add_parser(
        "metadata",
        help="寫入從來源頁可靠取得的 L0 metadata",
    )
    metadata_parser.add_argument("source")
    metadata_parser.add_argument("external_id")
    metadata_parser.add_argument(
        "--input",
        type=Path,
        required=True,
    )

    classify_parser = sub.add_parser(
        "classify",
        help="套用 L1 AI 候選分類",
    )
    classify_parser.add_argument("source")
    classify_parser.add_argument("external_id")
    classify_parser.add_argument(
        "--input",
        type=Path,
        required=True,
    )

    sub.add_parser(
        "validate",
        help="驗證全部題目智慧資料",
    )

    args = parser.parse_args(argv)
    store = ProblemIntelligenceStore(args.data_dir)

    try:
        if args.command == "import":
            urls = list(args.urls)
            if args.file:
                urls.extend(_read_url_file(args.file))
            if not urls:
                raise ProblemIntelligenceError(
                    "至少提供一個題目網址或 --file"
                )

            result = store.import_urls(urls)
            for key in result.added:
                print(f"新增：{key}")
            for key in result.existing:
                print(f"已存在：{key}")
            for error in result.errors:
                print(f"錯誤：{error}")

            print(
                f"完成：新增 {len(result.added)}｜"
                f"已存在 {len(result.existing)}｜"
                f"錯誤 {len(result.errors)}"
            )
            return 0 if result.ok else 1

        if args.command == "metadata":
            record = store.update_source_metadata(
                args.source,
                args.external_id,
                _load_payload(args.input),
            )
            identity = store.identity_from_record(record)
            print(f"已更新來源 metadata：{identity.key}")
            return 0

        if args.command == "classify":
            record = store.apply_classification(
                args.source,
                args.external_id,
                _load_payload(args.input),
            )
            identity = store.identity_from_record(record)
            status = record["classification"]["status"]
            print(f"已分類：{identity.key}｜{status}")
            if status == CLASS_NEEDS_QA:
                for reason in record["classification"]["qa_reasons"]:
                    print(f"需檢查：{reason}")
            return 0

        if args.command == "validate":
            errors = store.validate_all()
            if errors:
                for error in errors:
                    print(f"錯誤：{error}")
                print(f"題目智慧驗證失敗：{len(errors)} 個錯誤")
                return 1
            print(
                f"題目智慧驗證 PASS｜"
                f"{len(store.all_paths())} 個題目 artifact"
            )
            return 0

    except ProblemIntelligenceError as exc:
        print(f"錯誤：{exc}")
        return 1

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
