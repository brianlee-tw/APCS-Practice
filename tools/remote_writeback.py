"""Canonical remote-writeback bundle for APCS v2.3.

This module is transport-independent on purpose.

The local EvidenceOutbox is already durable and authoritative for captured
attempt facts.  Remote synchronization must not depend on a particular
Cloudflare auth header, Notion page URL, or live connector.  Instead, this
module projects one immutable OutboxEnvelope into a deterministic bundle that
the remote writer can validate and apply idempotently.

Important boundaries:
- writeback_id identifies one REC attempt transaction;
- event_id identifies one EV-v1 event;
- PB / Skill relations are referenced by canonical UID and must be resolved
  remotely against the Notion SSOT;
- unknown facts remain null / omitted rather than guessed;
- Valid for Gate is intentionally NOT supplied by the client;
- the bundle does not claim RM / IM / RR / IR.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

try:
    from .evidence_outbox import (
        OutboxEnvelope,
    )
except ImportError:
    from evidence_outbox import (
        OutboxEnvelope,
    )


SCHEMA_VERSION = "v2.3-remote-writeback-1"

NOTION_SOURCE = "VS Code Direct"

NOVELTY_TO_NOTION = {
    "new": "New",
    "seen": "Seen",
    "delayed_retest": "Delayed Retest",
    "transfer": "Transfer",
    "mixed": "Mixed",
    "same_problem_repeat": "Same Problem Repeat",
}

LANGUAGE_TO_NOTION = {
    "cpp": "C++",
    "python": "Python",
}

REMOTE_JUDGE_RESULTS = {
    "AC",
    "WA",
    "TLE",
    "MLE",
    "RE",
    "CE",
}


class RemoteWritebackError(
    ValueError
):
    pass


@dataclass(frozen=True)
class RemoteAttempt:
    attempt_id: str
    writeback_id: str
    pb_uid: str
    problem_id: str
    started_at: str | None
    finished_at: str
    language: str
    notion_language: str | None
    judge_result: str
    assistance: str | None
    independent: bool | None
    attempt_count: int | None
    active_minutes: int | None
    timed: bool | None
    novelty: str | None
    notion_novelty: str | None
    activity: str | None
    source: str
    note: str


@dataclass(frozen=True)
class RemoteEvidence:
    event_id: str
    writeback_id: str
    pb_uid: str
    problem_id: str
    skill_uid: str
    track: str
    outcome: str
    occurred_at: str
    judge_result: str
    assistance: str | None
    independent: bool | None
    active_minutes: int | None
    timed: bool | None
    novelty: str | None
    notion_novelty: str | None
    activity: str | None
    note: str


@dataclass(frozen=True)
class RemoteWritebackBundle:
    schema_version: str
    writeback_id: str
    attempt: RemoteAttempt
    evidence: tuple[
        RemoteEvidence,
        ...,
    ]

    def to_dict(
        self,
    ) -> dict[str, Any]:
        raw = asdict(
            self
        )
        raw["evidence"] = [
            asdict(item)
            for item in self.evidence
        ]
        return raw


def assistance_label(
    assistance: int | None,
) -> str | None:
    if assistance is None:
        return None

    if not 0 <= assistance <= 5:
        raise RemoteWritebackError(
            "assistance must be A0-A5"
        )

    return f"A{assistance}"


def notion_novelty_label(
    novelty: str | None,
) -> str | None:
    if novelty is None:
        return None

    try:
        return NOVELTY_TO_NOTION[
            novelty
        ]
    except KeyError as exc:
        raise RemoteWritebackError(
            f"unsupported novelty={novelty!r}"
        ) from exc


def notion_language_label(
    language: str,
) -> str | None:
    value = str(
        language or ""
    ).strip().lower()

    if not value:
        return None

    return LANGUAGE_TO_NOTION.get(
        value
    )


def derive_rec_stage(
    *,
    activity: str | None,
    independent: bool | None,
    timed: bool | None,
) -> str | None:
    """Derive legacy learner-facing REC stage from explicit attempt facts.

    The stage is presentation metadata, not a capability axis.  Unknown or
    ambiguous input remains unknown.
    """

    if activity == "Review":
        return "複習驗證"

    if (
        activity == "Mock"
        or timed is True
    ):
        return "限時實戰"

    if (
        activity
        in {
            "Core Independent",
            "Transfer Challenge",
        }
        and independent is True
    ):
        return "獨立解題"

    if activity in {
        "Concept Check",
        "Guided Drill",
        "Core Independent",
        "Transfer Challenge",
        "Diagnostic",
    }:
        return "理解觀念"

    return None


def build_remote_writeback_bundle(
    envelope: OutboxEnvelope,
) -> RemoteWritebackBundle:
    attempt = envelope.attempt

    pb_uid = str(
        attempt.pb_uid
        or ""
    ).strip()

    if not pb_uid:
        raise RemoteWritebackError(
            "remote writeback requires Published PB UID; "
            "keep this envelope local until curriculum placement is known"
        )

    if (
        attempt.judge_result
        not in REMOTE_JUDGE_RESULTS
    ):
        raise RemoteWritebackError(
            "unsupported remote judge result="
            f"{attempt.judge_result!r}"
        )

    assistance = assistance_label(
        attempt.assistance
    )
    notion_novelty = (
        notion_novelty_label(
            attempt.novelty
        )
    )

    remote_attempt = RemoteAttempt(
        attempt_id=attempt.attempt_id,
        writeback_id=(
            envelope.writeback_id
        ),
        pb_uid=pb_uid,
        problem_id=attempt.problem_id,
        started_at=attempt.started_at,
        finished_at=attempt.finished_at,
        language=attempt.language,
        notion_language=(
            notion_language_label(
                attempt.language
            )
        ),
        judge_result=(
            attempt.judge_result
        ),
        assistance=assistance,
        independent=attempt.independent,
        attempt_count=attempt.attempt_count,
        active_minutes=(
            attempt.active_minutes
        ),
        timed=attempt.timed,
        novelty=attempt.novelty,
        notion_novelty=(
            notion_novelty
        ),
        activity=attempt.activity,
        source=NOTION_SOURCE,
        note=attempt.note,
    )

    evidence = tuple(
        RemoteEvidence(
            event_id=claim.event_id,
            writeback_id=(
                envelope.writeback_id
            ),
            pb_uid=pb_uid,
            problem_id=(
                attempt.problem_id
            ),
            skill_uid=claim.skill_uid,
            track=claim.track,
            outcome=claim.outcome,
            occurred_at=(
                attempt.finished_at
            ),
            judge_result=(
                attempt.judge_result
            ),
            assistance=assistance,
            independent=(
                attempt.independent
            ),
            active_minutes=(
                attempt.active_minutes
            ),
            timed=attempt.timed,
            novelty=attempt.novelty,
            notion_novelty=(
                notion_novelty
            ),
            activity=attempt.activity,
            note=claim.note,
        )
        for claim in envelope.evidence
    )

    return RemoteWritebackBundle(
        schema_version=(
            SCHEMA_VERSION
        ),
        writeback_id=(
            envelope.writeback_id
        ),
        attempt=remote_attempt,
        evidence=evidence,
    )


def notion_projection(
    bundle: RemoteWritebackBundle,
) -> dict[str, Any]:
    """Return logical Notion property + relation projection.

    This is deliberately not raw Notion REST JSON.  Scalar properties use the
    live REC / EV-v1 property names.  Relations remain canonical PB / Skill /
    writeback identities and must be resolved by the trusted remote writer.
    """

    attempt = bundle.attempt

    rec_properties: dict[str, Any] = {
        "Writeback ID": (
            attempt.writeback_id
        ),
        "PB UID": attempt.pb_uid,
        "Problem ID": (
            attempt.problem_id
        ),
        "最新提交結果": (
            attempt.judge_result
        ),
        "紀錄來源": (
            attempt.source
        ),
        "紀錄性質": "正式紀錄",
        "Attempt Finished At": (
            attempt.finished_at
        ),
    }

    if (
        attempt.notion_language
        is not None
    ):
        rec_properties[
            "使用語言"
        ] = [
            attempt.notion_language
        ]

    if attempt.assistance is not None:
        rec_properties[
            "Assistance"
        ] = attempt.assistance

    if (
        attempt.independent
        is not None
    ):
        rec_properties[
            "獨立完成"
        ] = attempt.independent

    if (
        attempt.attempt_count
        is not None
    ):
        rec_properties[
            "嘗試次數"
        ] = attempt.attempt_count

    if (
        attempt.active_minutes
        is not None
    ):
        rec_properties[
            "解題時間(分鐘)"
        ] = attempt.active_minutes

    stage = derive_rec_stage(
        activity=attempt.activity,
        independent=attempt.independent,
        timed=attempt.timed,
    )

    if stage is not None:
        rec_properties[
            "學習階段"
        ] = stage

    if attempt.note:
        rec_properties[
            "核心收穫"
        ] = attempt.note

    ev_rows = []

    for event in bundle.evidence:
        properties: dict[str, Any] = {
            "Event ID": (
                event.event_id
            ),
            "Track": event.track,
            "Outcome": event.outcome,
            "Judge Result": (
                event.judge_result
            ),
            "日期": event.occurred_at,
        }

        if (
            event.assistance
            is not None
        ):
            properties[
                "Assistance"
            ] = event.assistance

        if (
            event.independent
            is not None
        ):
            properties[
                "Independent"
            ] = event.independent

        if (
            event.active_minutes
            is not None
        ):
            properties[
                "Time min"
            ] = event.active_minutes

        if event.timed is not None:
            properties[
                "Timed"
            ] = event.timed

        if (
            event.notion_novelty
            is not None
        ):
            properties[
                "Novelty"
            ] = event.notion_novelty

        if event.activity is not None:
            properties[
                "Activity"
            ] = event.activity

        if event.note:
            properties[
                "Evidence Note"
            ] = event.note

        # Valid for Gate is intentionally absent.  It must be derived by the
        # versioned MEAS evaluator after the event has been durably written.

        ev_rows.append(
            {
                "event_id": (
                    event.event_id
                ),
                "properties": (
                    properties
                ),
                "relations": {
                    "problem_pb_uid": (
                        event.pb_uid
                    ),
                    "skill_uid": (
                        event.skill_uid
                    ),
                    "solve_writeback_id": (
                        event.writeback_id
                    ),
                },
            }
        )

    return {
        "rec": {
            "properties": (
                rec_properties
            ),
            "relations": {
                "problem_pb_uid": (
                    attempt.pb_uid
                ),
                "skill_uids": [
                    event.skill_uid
                    for event
                    in bundle.evidence
                ],
            },
        },
        "evidence": ev_rows,
    }


REMOTE_RECEIPT_SCHEMA = "v2.3-remote-receipt-1"


def validate_remote_receipt(
    bundle: RemoteWritebackBundle,
    receipt: dict[str, Any],
) -> dict[str, Any]:
    """Validate a complete remote receipt before local acknowledgement."""

    if not isinstance(
        receipt,
        dict,
    ):
        raise RemoteWritebackError(
            "remote receipt must be an object"
        )

    if (
        receipt.get(
            "schema_version"
        )
        != REMOTE_RECEIPT_SCHEMA
    ):
        raise RemoteWritebackError(
            "remote receipt schema mismatch"
        )

    if (
        receipt.get(
            "writeback_id"
        )
        != bundle.writeback_id
    ):
        raise RemoteWritebackError(
            "remote receipt writeback_id mismatch"
        )

    if receipt.get(
        "complete"
    ) is not True:
        raise RemoteWritebackError(
            "remote receipt is not complete"
        )

    rec = receipt.get(
        "rec"
    )

    if not isinstance(
        rec,
        dict,
    ):
        raise RemoteWritebackError(
            "remote receipt rec must be an object"
        )

    if not str(
        rec.get(
            "page_id",
            "",
        )
    ).strip():
        raise RemoteWritebackError(
            "remote receipt missing REC page_id"
        )

    raw_events = receipt.get(
        "evidence"
    )

    if not isinstance(
        raw_events,
        list,
    ):
        raise RemoteWritebackError(
            "remote receipt evidence must be an array"
        )

    expected = {
        item.event_id
        for item in bundle.evidence
    }

    seen: set[str] = set()

    for item in raw_events:
        if not isinstance(
            item,
            dict,
        ):
            raise RemoteWritebackError(
                "remote evidence receipt must be an object"
            )

        event_id = str(
            item.get(
                "event_id",
                "",
            )
        ).strip()

        if not event_id:
            raise RemoteWritebackError(
                "remote evidence receipt missing event_id"
            )

        if event_id in seen:
            raise RemoteWritebackError(
                "duplicate event_id in remote receipt: "
                f"{event_id}"
            )

        seen.add(
            event_id
        )

        if not str(
            item.get(
                "page_id",
                "",
            )
        ).strip():
            raise RemoteWritebackError(
                "remote evidence receipt missing page_id: "
                f"{event_id}"
            )

    if seen != expected:
        missing = sorted(
            expected - seen
        )
        unexpected = sorted(
            seen - expected
        )

        raise RemoteWritebackError(
            "remote receipt Evidence identity mismatch; "
            f"missing={missing} unexpected={unexpected}"
        )

    # Keep only JSON-compatible data supplied by the trusted transport.
    return receipt
