"""Persistent Skill x Track adaptive-memory cache for APCS v2.3.

Authoritative learner facts live in durable evidence envelopes.  This store is
derived state and can be rebuilt from those envelopes.

Key properties:
- atomic persistence;
- idempotent event processing;
- automatic rebuild on policy-version change;
- automatic rebuild if late/out-of-order evidence arrives;
- incomplete evidence is skipped rather than guessed.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

try:
    from .adaptive_memory import (
        MemoryPolicy,
        MemoryState,
        next_due_on,
        retrievability,
        update_memory,
    )
    from .evidence_outbox import (
        EvidenceOutboxError,
        OutboxEnvelope,
        memory_evidence,
    )
except ImportError:
    from adaptive_memory import (
        MemoryPolicy,
        MemoryState,
        next_due_on,
        retrievability,
        update_memory,
    )
    from evidence_outbox import (
        EvidenceOutboxError,
        OutboxEnvelope,
        memory_evidence,
    )


SCHEMA_VERSION = "v2.3-skill-memory-1"


@dataclass(frozen=True)
class ReconcileReport:
    applied_events: int
    skipped_envelopes: int
    rebuilt: bool
    states: int


class SkillMemoryStore:
    def __init__(
        self,
        path: Path,
        *,
        policy: MemoryPolicy = MemoryPolicy(),
    ):
        self.path = Path(path)
        self.policy = policy

    def _empty(self) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "policy_version": self.policy.version,
            "processed_event_ids": [],
            "states": [],
        }

    @staticmethod
    def _key(
        skill_uid: str,
        track: str,
    ) -> str:
        return f"{skill_uid}::{track}"

    @staticmethod
    def _state_to_dict(
        state: MemoryState,
    ) -> dict:
        value = asdict(state)
        value["last_evidence_on"] = (
            state.last_evidence_on.isoformat()
        )
        return value

    @staticmethod
    def _state_from_dict(
        value: dict,
    ) -> MemoryState:
        return MemoryState(
            skill_uid=str(
                value["skill_uid"]
            ),
            track=str(
                value["track"]
            ),
            stability_days=float(
                value["stability_days"]
            ),
            last_evidence_on=dt.date.fromisoformat(
                value["last_evidence_on"]
            ),
            evidence_count=int(
                value.get(
                    "evidence_count",
                    0,
                )
            ),
            successful_retrievals=int(
                value.get(
                    "successful_retrievals",
                    0,
                )
            ),
            lapses=int(
                value.get(
                    "lapses",
                    0,
                )
            ),
            last_outcome=str(
                value.get(
                    "last_outcome",
                    "PASS",
                )
            ),
            policy_version=str(
                value.get(
                    "policy_version",
                    "",
                )
            ),
        )

    def load_raw(self) -> dict:
        if not self.path.exists():
            return self._empty()

        try:
            value = json.loads(
                self.path.read_text(
                    encoding="utf-8"
                )
            )
        except (
            OSError,
            json.JSONDecodeError,
        ) as exc:
            raise ValueError(
                f"invalid skill memory store: {exc}"
            ) from exc

        if not isinstance(value, dict):
            raise ValueError(
                "skill memory store must be a JSON object"
            )

        if value.get("schema_version") != SCHEMA_VERSION:
            raise ValueError(
                "unsupported skill memory schema: "
                f"{value.get('schema_version')!r}"
            )

        return value

    def load_states(
        self,
    ) -> dict[tuple[str, str], MemoryState]:
        raw = self.load_raw()
        result: dict[
            tuple[str, str],
            MemoryState,
        ] = {}

        for item in raw.get("states") or []:
            state = self._state_from_dict(
                item
            )
            result[
                (
                    state.skill_uid,
                    state.track,
                )
            ] = state

        return result

    def _atomic_write(
        self,
        value: dict,
    ) -> None:
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        payload = (
            json.dumps(
                value,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")

        temp = self.path.with_name(
            self.path.name
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
                self.path,
            )

        finally:
            temp.unlink(
                missing_ok=True
            )

    def _serialize(
        self,
        states: dict[
            tuple[str, str],
            MemoryState,
        ],
        processed_event_ids: set[str],
    ) -> dict:
        ordered_states = sorted(
            states.values(),
            key=lambda item: (
                item.skill_uid,
                item.track,
            ),
        )

        return {
            "schema_version": SCHEMA_VERSION,
            "policy_version": (
                self.policy.version
            ),
            "processed_event_ids": sorted(
                processed_event_ids
            ),
            "states": [
                self._state_to_dict(
                    state
                )
                for state
                in ordered_states
            ],
        }

    @staticmethod
    def _ordered_events(
        envelopes: Iterable[
            OutboxEnvelope
        ],
    ) -> list[
        tuple[
            dt.date,
            str,
            object,
        ]
    ]:
        result = []

        for envelope in envelopes:
            try:
                evidence_items = (
                    memory_evidence(
                        envelope
                    )
                )
            except EvidenceOutboxError:
                continue

            for claim, evidence in zip(
                envelope.evidence,
                evidence_items,
            ):
                result.append(
                    (
                        evidence.occurred_on,
                        claim.event_id,
                        evidence,
                    )
                )

        result.sort(
            key=lambda item: (
                item[0],
                item[1],
            )
        )
        return result

    def rebuild(
        self,
        envelopes: Iterable[
            OutboxEnvelope
        ],
    ) -> ReconcileReport:
        states: dict[
            tuple[str, str],
            MemoryState,
        ] = {}
        processed: set[str] = set()

        events = self._ordered_events(
            envelopes
        )

        for _, event_id, evidence in events:
            key = (
                evidence.skill_uid,
                evidence.track,
            )

            states[key] = update_memory(
                states.get(key),
                evidence,
                policy=self.policy,
            )
            processed.add(
                event_id
            )

        self._atomic_write(
            self._serialize(
                states,
                processed,
            )
        )

        total_envelopes = len(
            tuple(envelopes)
        ) if not isinstance(
            envelopes,
            tuple,
        ) else len(envelopes)

        eligible_envelopes = len(
            {
                event_id.split(
                    ".ev",
                    1,
                )[0]
                for _, event_id, _
                in events
            }
        )

        return ReconcileReport(
            applied_events=len(events),
            skipped_envelopes=max(
                0,
                total_envelopes
                - eligible_envelopes,
            ),
            rebuilt=True,
            states=len(states),
        )

    def reconcile(
        self,
        envelopes: Iterable[
            OutboxEnvelope
        ],
    ) -> ReconcileReport:
        envelopes = tuple(
            envelopes
        )

        try:
            raw = self.load_raw()
            states = self.load_states()
        except ValueError:
            return self.rebuild(
                envelopes
            )

        if (
            raw.get("policy_version")
            != self.policy.version
        ):
            return self.rebuild(
                envelopes
            )

        processed = set(
            raw.get(
                "processed_event_ids"
            )
            or []
        )

        events = self._ordered_events(
            envelopes
        )
        pending = [
            item
            for item in events
            if item[1] not in processed
        ]

        rebuild_needed = False

        for occurred_on, _, evidence in pending:
            existing = states.get(
                (
                    evidence.skill_uid,
                    evidence.track,
                )
            )

            if (
                existing is not None
                and occurred_on
                < existing.last_evidence_on
            ):
                rebuild_needed = True
                break

        if rebuild_needed:
            return self.rebuild(
                envelopes
            )

        applied = 0

        for _, event_id, evidence in pending:
            key = (
                evidence.skill_uid,
                evidence.track,
            )

            states[key] = update_memory(
                states.get(key),
                evidence,
                policy=self.policy,
            )

            processed.add(
                event_id
            )
            applied += 1

        if applied:
            self._atomic_write(
                self._serialize(
                    states,
                    processed,
                )
            )

        eligible_event_ids = {
            event_id
            for _, event_id, _
            in events
        }

        eligible_writebacks = {
            event_id.split(
                ".ev",
                1,
            )[0]
            for event_id
            in eligible_event_ids
        }

        return ReconcileReport(
            applied_events=applied,
            skipped_envelopes=max(
                0,
                len(envelopes)
                - len(
                    eligible_writebacks
                ),
            ),
            rebuilt=False,
            states=len(states),
        )

    def due_states(
        self,
        *,
        on_date: dt.date,
    ) -> tuple[
        tuple[
            MemoryState,
            float,
            dt.date,
        ],
        ...,
    ]:
        result = []

        for state in self.load_states().values():
            due_on = next_due_on(
                state,
                policy=self.policy,
            )

            if due_on > on_date:
                continue

            result.append(
                (
                    state,
                    retrievability(
                        state,
                        on_date,
                    ),
                    due_on,
                )
            )

        result.sort(
            key=lambda item: (
                item[1],
                item[2],
                item[0].skill_uid,
                item[0].track,
            )
        )

        return tuple(result)
