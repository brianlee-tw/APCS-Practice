"""Durable evidence outbox for APCS v2.3.

The outbox bridges the local VS Code runtime and durable Notion REC / Evidence
writeback without making a network request part of the learning mutation.

Design goals:
- capture attempt facts once;
- preserve unknown facts as unknown;
- one evidence claim = one Skill x Track observation;
- idempotent writeback keys;
- crash-tolerant local persistence;
- retries are safe when the remote writer also keys by writeback_id/event_id;
- no automatic promotion from problem tags to mastery evidence.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    from .adaptive_memory import Evidence as MemoryEvidence
except ImportError:
    from adaptive_memory import Evidence as MemoryEvidence


SCHEMA_VERSION = "v2.3-outbox-1"

VALID_JUDGE_RESULTS = {
    "AC",
    "WA",
    "TLE",
    "MLE",
    "RE",
    "CE",
}
VALID_EVIDENCE_OUTCOMES = {
    "PASS",
    "PARTIAL",
    "FAIL",
}
VALID_TRACKS = {
    "Reading",
    "Implementation",
}
VALID_NOVELTY = {
    "new",
    "seen",
    "delayed_retest",
    "transfer",
    "mixed",
    "same_problem_repeat",
}
VALID_ACTIVITIES = {
    "Concept Check",
    "Guided Drill",
    "Core Independent",
    "Transfer Challenge",
    "Review",
    "Diagnostic",
    "Mock",
}
ID_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")


class EvidenceOutboxError(ValueError):
    pass


def _aware_iso(value: dt.datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise EvidenceOutboxError(
            "timestamps must be timezone-aware"
        )

    return value.isoformat(timespec="seconds")


def _parse_aware_iso(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value)

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise EvidenceOutboxError(
            "timestamps must be timezone-aware"
        )

    return parsed


def _validate_id(value: str, label: str) -> str:
    value = str(value or "").strip()

    if not value:
        raise EvidenceOutboxError(
            f"{label} is required"
        )

    if not ID_RE.fullmatch(value):
        raise EvidenceOutboxError(
            f"{label} has invalid characters: {value!r}"
        )

    return value


@dataclass(frozen=True)
class EvidenceClaim:
    event_id: str
    skill_uid: str
    track: str
    outcome: str
    note: str = ""

    def __post_init__(self) -> None:
        _validate_id(self.event_id, "event_id")
        _validate_id(self.skill_uid, "skill_uid")

        if self.track not in VALID_TRACKS:
            raise EvidenceOutboxError(
                f"invalid track={self.track!r}"
            )

        if self.outcome not in VALID_EVIDENCE_OUTCOMES:
            raise EvidenceOutboxError(
                f"invalid evidence outcome={self.outcome!r}"
            )


@dataclass(frozen=True)
class AttemptFacts:
    attempt_id: str
    problem_id: str
    pb_uid: str | None
    started_at: str
    finished_at: str
    language: str
    judge_result: str
    assistance: int | None
    independent: bool | None
    attempt_count: int | None
    active_minutes: int | None
    novelty: str | None
    activity: str | None
    source: str = "vscode"
    note: str = ""

    def __post_init__(self) -> None:
        _validate_id(self.attempt_id, "attempt_id")

        if not str(self.problem_id or "").strip():
            raise EvidenceOutboxError(
                "problem_id is required"
            )

        if self.pb_uid is not None:
            _validate_id(self.pb_uid, "pb_uid")

        started = _parse_aware_iso(self.started_at)
        finished = _parse_aware_iso(self.finished_at)

        if finished < started:
            raise EvidenceOutboxError(
                "finished_at cannot be earlier than started_at"
            )

        if self.judge_result not in VALID_JUDGE_RESULTS:
            raise EvidenceOutboxError(
                f"invalid judge_result={self.judge_result!r}"
            )

        if self.assistance is not None and not (
            0 <= self.assistance <= 5
        ):
            raise EvidenceOutboxError(
                "assistance must be A0-A5 / integer 0-5"
            )

        if self.attempt_count is not None and self.attempt_count <= 0:
            raise EvidenceOutboxError(
                "attempt_count must be positive"
            )

        if self.active_minutes is not None and self.active_minutes < 0:
            raise EvidenceOutboxError(
                "active_minutes cannot be negative"
            )

        if (
            self.novelty is not None
            and self.novelty not in VALID_NOVELTY
        ):
            raise EvidenceOutboxError(
                f"invalid novelty={self.novelty!r}"
            )

        if (
            self.activity is not None
            and self.activity not in VALID_ACTIVITIES
        ):
            raise EvidenceOutboxError(
                f"invalid activity={self.activity!r}"
            )


@dataclass(frozen=True)
class OutboxEnvelope:
    schema_version: str
    writeback_id: str
    created_at: str
    attempt: AttemptFacts
    evidence: tuple[EvidenceClaim, ...]

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise EvidenceOutboxError(
                f"unsupported schema_version={self.schema_version!r}"
            )

        _validate_id(self.writeback_id, "writeback_id")
        _parse_aware_iso(self.created_at)

        seen: set[tuple[str, str]] = set()
        event_ids: set[str] = set()

        for claim in self.evidence:
            key = (
                claim.skill_uid,
                claim.track,
            )

            if key in seen:
                raise EvidenceOutboxError(
                    "one attempt may contain at most one evidence claim "
                    f"for {claim.skill_uid} x {claim.track}"
                )

            seen.add(key)

            if claim.event_id in event_ids:
                raise EvidenceOutboxError(
                    f"duplicate event_id={claim.event_id}"
                )

            event_ids.add(claim.event_id)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["evidence"] = [
            asdict(item)
            for item in self.evidence
        ]
        return value

    @classmethod
    def from_dict(
        cls,
        value: dict[str, Any],
    ) -> "OutboxEnvelope":
        if not isinstance(value, dict):
            raise EvidenceOutboxError(
                "outbox envelope must be an object"
            )

        attempt_raw = value.get("attempt")
        evidence_raw = value.get("evidence")

        if not isinstance(attempt_raw, dict):
            raise EvidenceOutboxError(
                "attempt must be an object"
            )

        if not isinstance(evidence_raw, list):
            raise EvidenceOutboxError(
                "evidence must be an array"
            )

        attempt = AttemptFacts(
            **attempt_raw
        )
        evidence = tuple(
            EvidenceClaim(**item)
            for item in evidence_raw
        )

        return cls(
            schema_version=value.get(
                "schema_version",
                "",
            ),
            writeback_id=value.get(
                "writeback_id",
                "",
            ),
            created_at=value.get(
                "created_at",
                "",
            ),
            attempt=attempt,
            evidence=evidence,
        )


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def build_envelope(
    *,
    problem_id: str,
    started_at: dt.datetime,
    finished_at: dt.datetime,
    language: str,
    judge_result: str,
    evidence: Iterable[
        tuple[str, str, str, str]
    ] = (),
    pb_uid: str | None = None,
    assistance: int | None = None,
    independent: bool | None = None,
    attempt_count: int | None = None,
    active_minutes: int | None = None,
    novelty: str | None = None,
    activity: str | None = None,
    note: str = "",
    attempt_id: str | None = None,
    writeback_id: str | None = None,
    created_at: dt.datetime | None = None,
) -> OutboxEnvelope:
    attempt_id = attempt_id or _new_id("att")
    writeback_id = writeback_id or _new_id("wb")
    created_at = created_at or finished_at

    claims: list[EvidenceClaim] = []

    for index, item in enumerate(evidence, start=1):
        if len(item) != 4:
            raise EvidenceOutboxError(
                "evidence tuple must be "
                "(skill_uid, track, outcome, note)"
            )

        skill_uid, track, outcome, claim_note = item

        claims.append(
            EvidenceClaim(
                event_id=(
                    f"{writeback_id}.ev{index}"
                ),
                skill_uid=skill_uid,
                track=track,
                outcome=outcome,
                note=claim_note,
            )
        )

    return OutboxEnvelope(
        schema_version=SCHEMA_VERSION,
        writeback_id=writeback_id,
        created_at=_aware_iso(created_at),
        attempt=AttemptFacts(
            attempt_id=attempt_id,
            problem_id=problem_id,
            pb_uid=pb_uid,
            started_at=_aware_iso(
                started_at
            ),
            finished_at=_aware_iso(
                finished_at
            ),
            language=str(language or "").strip(),
            judge_result=judge_result,
            assistance=assistance,
            independent=independent,
            attempt_count=attempt_count,
            active_minutes=active_minutes,
            novelty=novelty,
            activity=activity,
            note=note,
        ),
        evidence=tuple(claims),
    )


def memory_evidence(
    envelope: OutboxEnvelope,
) -> tuple[MemoryEvidence, ...]:
    """Convert complete explicit claims into adaptive-memory evidence.

    Unknown Assistance / Independent / Novelty facts are intentionally not
    guessed.  Such an attempt remains a valid durable REC candidate, but it
    cannot update the adaptive memory model until those facts are known.
    """

    attempt = envelope.attempt

    missing = []

    if attempt.assistance is None:
        missing.append("assistance")

    if attempt.independent is None:
        missing.append("independent")

    if attempt.novelty is None:
        missing.append("novelty")

    if missing:
        raise EvidenceOutboxError(
            "adaptive memory requires explicit "
            + ", ".join(missing)
        )

    occurred_on = _parse_aware_iso(
        attempt.finished_at
    ).date()

    return tuple(
        MemoryEvidence(
            skill_uid=claim.skill_uid,
            track=claim.track,
            occurred_on=occurred_on,
            outcome=claim.outcome,
            assistance=attempt.assistance,
            independent=attempt.independent,
            novelty=attempt.novelty,
            timed=(
                attempt.active_minutes
                is not None
            ),
            problem_id=attempt.problem_id,
        )
        for claim in envelope.evidence
    )


class EvidenceOutbox:
    """Append-only pending envelopes plus independent receipts.

    Remote writeback must use writeback_id and event_id as idempotency keys.
    A crash after remote success but before local receipt is therefore safe:
    the same pending envelope can be retried without duplicating durable
    records.
    """

    def __init__(self, runtime_dir: Path):
        self.runtime_dir = Path(runtime_dir)
        self.pending_dir = (
            self.runtime_dir
            / "outbox"
            / "pending"
        )
        self.receipt_dir = (
            self.runtime_dir
            / "outbox"
            / "receipts"
        )

    def ensure(self) -> None:
        self.pending_dir.mkdir(
            parents=True,
            exist_ok=True,
        )
        self.receipt_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    @staticmethod
    def _payload(
        value: dict[str, Any],
    ) -> bytes:
        return (
            json.dumps(
                value,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")

    @staticmethod
    def _atomic_write(
        path: Path,
        payload: bytes,
    ) -> None:
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temp = path.with_name(
            path.name
            + f".{uuid.uuid4().hex}.tmp"
        )

        try:
            with temp.open("wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(
                    handle.fileno()
                )

            os.replace(
                temp,
                path,
            )

        finally:
            temp.unlink(
                missing_ok=True,
            )

    def _pending_path(
        self,
        writeback_id: str,
    ) -> Path:
        _validate_id(
            writeback_id,
            "writeback_id",
        )
        return (
            self.pending_dir
            / f"{writeback_id}.json"
        )

    def _receipt_path(
        self,
        writeback_id: str,
    ) -> Path:
        _validate_id(
            writeback_id,
            "writeback_id",
        )
        return (
            self.receipt_dir
            / f"{writeback_id}.json"
        )

    def enqueue(
        self,
        envelope: OutboxEnvelope,
    ) -> bool:
        """Persist an envelope.

        Returns True when newly written, False when an identical envelope was
        already present.  A conflicting reuse of writeback_id is rejected.
        """

        self.ensure()

        path = self._pending_path(
            envelope.writeback_id
        )
        payload = self._payload(
            envelope.to_dict()
        )

        if path.exists():
            if path.read_bytes() == payload:
                return False

            raise EvidenceOutboxError(
                "writeback_id already exists with different payload: "
                f"{envelope.writeback_id}"
            )

        self._atomic_write(
            path,
            payload,
        )

        return True

    def load(
        self,
        writeback_id: str,
    ) -> OutboxEnvelope:
        path = self._pending_path(
            writeback_id
        )

        try:
            value = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )
        except FileNotFoundError as exc:
            raise EvidenceOutboxError(
                f"unknown writeback_id={writeback_id}"
            ) from exc
        except json.JSONDecodeError as exc:
            raise EvidenceOutboxError(
                f"corrupt outbox envelope: {path}"
            ) from exc

        return OutboxEnvelope.from_dict(
            value
        )

    def has_receipt(
        self,
        writeback_id: str,
    ) -> bool:
        return self._receipt_path(
            writeback_id
        ).exists()

    def pending(
        self,
    ) -> tuple[OutboxEnvelope, ...]:
        self.ensure()
        result = []

        for path in sorted(
            self.pending_dir.glob(
                "*.json"
            )
        ):
            writeback_id = path.stem

            if self.has_receipt(
                writeback_id
            ):
                continue

            result.append(
                self.load(
                    writeback_id
                )
            )

        return tuple(result)

    def mark_sent(
        self,
        writeback_id: str,
        receipt: dict[str, Any],
    ) -> bool:
        """Record remote acknowledgement independently from the envelope."""

        self.ensure()

        # Refuse receipts for envelopes that never existed locally.
        self.load(
            writeback_id
        )

        if not isinstance(receipt, dict):
            raise EvidenceOutboxError(
                "receipt must be an object"
            )

        payload_value = {
            "schema_version": (
                "v2.3-outbox-receipt-1"
            ),
            "writeback_id": writeback_id,
            "receipt": receipt,
        }

        payload = self._payload(
            payload_value
        )
        path = self._receipt_path(
            writeback_id
        )

        if path.exists():
            if path.read_bytes() == payload:
                return False

            raise EvidenceOutboxError(
                "writeback receipt already exists with different payload: "
                f"{writeback_id}"
            )

        self._atomic_write(
            path,
            payload,
        )

        return True

    def receipt(
        self,
        writeback_id: str,
    ) -> dict[str, Any] | None:
        path = self._receipt_path(
            writeback_id
        )

        if not path.exists():
            return None

        try:
            value = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )
        except json.JSONDecodeError as exc:
            raise EvidenceOutboxError(
                f"corrupt outbox receipt: {path}"
            ) from exc

        return value
