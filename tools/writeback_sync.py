#!/usr/bin/env python3
"""Inspect and synchronize APCS v2.3 durable remote-writeback bundles."""

from __future__ import annotations

import argparse
import getpass
import json
from pathlib import Path

try:
    from .evidence_outbox import (
        EvidenceOutbox,
        EvidenceOutboxError,
    )
    from .remote_transport import (
        DEFAULT_TIMEOUT_SECONDS,
        KEY_FILE,
        PRODUCTION_ENDPOINT,
        WritebackTransportError,
        credential_source,
        install_write_key,
        sync_bundle,
    )
    from .remote_writeback import (
        RemoteWritebackError,
        build_remote_writeback_bundle,
        notion_projection,
    )
except ImportError:
    from evidence_outbox import (
        EvidenceOutbox,
        EvidenceOutboxError,
    )
    from remote_transport import (
        DEFAULT_TIMEOUT_SECONDS,
        KEY_FILE,
        PRODUCTION_ENDPOINT,
        WritebackTransportError,
        credential_source,
        install_write_key,
        sync_bundle,
    )
    from remote_writeback import (
        RemoteWritebackError,
        build_remote_writeback_bundle,
        notion_projection,
    )


ROOT = Path(
    __file__
).resolve().parents[1]

RUNTIME_DIR = (
    ROOT
    / ".apcs"
    / "runtime"
)


def store() -> EvidenceOutbox:
    return EvidenceOutbox(
        RUNTIME_DIR
    )


def classify_pending(
    outbox: EvidenceOutbox,
):
    eligible = []
    blocked = []

    for envelope in outbox.pending():
        try:
            bundle = (
                build_remote_writeback_bundle(
                    envelope
                )
            )
        except RemoteWritebackError as exc:
            blocked.append(
                (
                    envelope,
                    str(exc),
                )
            )
            continue

        eligible.append(
            bundle
        )

    return eligible, blocked


def status_cmd() -> int:
    outbox = store()

    try:
        all_items = outbox.all_envelopes()
        pending = outbox.pending()
        eligible, blocked = classify_pending(
            outbox
        )
    except (
        EvidenceOutboxError,
        OSError,
        ValueError,
    ) as exc:
        print(
            f"REMOTE WRITEBACK · ERROR · {exc}"
        )
        return 2

    acknowledged = (
        len(all_items)
        - len(pending)
    )
    source = (
        credential_source()
        or "missing"
    )

    print(
        "REMOTE WRITEBACK · PRODUCTION TRANSPORT"
    )
    print(
        f"endpoint={PRODUCTION_ENDPOINT}"
    )
    print(
        f"credential={source}"
    )
    print(
        f"all={len(all_items)}"
        f" pending={len(pending)}"
        f" eligible={len(eligible)}"
        f" blocked={len(blocked)}"
        f" acknowledged={acknowledged}"
    )

    for bundle in eligible:
        print(
            "READY "
            f"{bundle.writeback_id}"
            f" · {bundle.attempt.pb_uid}"
            f" · EV={len(bundle.evidence)}"
        )

    for envelope, reason in blocked:
        print(
            "BLOCKED "
            f"{envelope.writeback_id}"
            f" · {reason}"
        )

    return 0


def bundle_cmd(
    writeback_id: str,
    *,
    projection: bool,
) -> int:
    outbox = store()

    try:
        envelope = outbox.load(
            writeback_id
        )
        bundle = (
            build_remote_writeback_bundle(
                envelope
            )
        )
    except (
        EvidenceOutboxError,
        RemoteWritebackError,
        OSError,
        ValueError,
    ) as exc:
        print(
            f"REMOTE WRITEBACK · ERROR · {exc}"
        )
        return 2

    value = (
        notion_projection(
            bundle
        )
        if projection
        else bundle.to_dict()
    )

    print(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


def configure_key_cmd() -> int:
    try:
        first = getpass.getpass(
            "APCS write key: "
        )
        second = getpass.getpass(
            "Repeat write key: "
        )

        if first != second:
            raise WritebackTransportError(
                "writeback key confirmation mismatch"
            )

        path = install_write_key(
            first
        )

    except (
        WritebackTransportError,
        OSError,
    ) as exc:
        print(
            f"REMOTE WRITEBACK · ERROR · {exc}"
        )
        return 2

    print(
        "REMOTE WRITEBACK · CREDENTIAL STORED"
    )
    print(
        f"path={path}"
    )
    print(
        "mode=600"
    )

    return 0


def sync_cmd(
    writeback_id: str,
    *,
    timeout: float,
) -> int:
    outbox = store()

    try:
        if outbox.has_receipt(
            writeback_id
        ):
            print(
                "REMOTE WRITEBACK · ALREADY ACKNOWLEDGED · "
                f"{writeback_id}"
            )
            return 0

        bundle = (
            build_remote_writeback_bundle(
                outbox.load(
                    writeback_id
                )
            )
        )

        receipt, created = sync_bundle(
            outbox,
            bundle,
            timeout=timeout,
        )

    except (
        EvidenceOutboxError,
        RemoteWritebackError,
        WritebackTransportError,
        OSError,
        ValueError,
    ) as exc:
        print(
            "REMOTE WRITEBACK · PENDING · "
            f"{writeback_id} · {exc}"
        )
        return 2

    duplicate_events = sum(
        1
        for item in receipt.get(
            "evidence",
            [],
        )
        if item.get(
            "duplicate"
        ) is True
    )

    print(
        "REMOTE WRITEBACK · SENT · "
        f"{writeback_id}"
        f" · receipt={'new' if created else 'existing'}"
        f" · rec_duplicate="
        f"{receipt['rec'].get('duplicate') is True}"
        f" · ev={len(receipt.get('evidence', []))}"
        f" · ev_duplicates={duplicate_events}"
    )

    return 0


def sync_pending_cmd(
    *,
    timeout: float,
    limit: int | None,
) -> int:
    if (
        limit is not None
        and limit <= 0
    ):
        print(
            "REMOTE WRITEBACK · ERROR · "
            "--limit must be positive"
        )
        return 2

    outbox = store()

    try:
        eligible, blocked = (
            classify_pending(
                outbox
            )
        )
    except (
        EvidenceOutboxError,
        OSError,
        ValueError,
    ) as exc:
        print(
            f"REMOTE WRITEBACK · ERROR · {exc}"
        )
        return 2

    selected = (
        eligible
        if limit is None
        else eligible[:limit]
    )

    sent = 0

    for bundle in selected:
        try:
            sync_bundle(
                outbox,
                bundle,
                timeout=timeout,
            )
        except (
            EvidenceOutboxError,
            WritebackTransportError,
            OSError,
            ValueError,
        ) as exc:
            print(
                "PENDING "
                f"{bundle.writeback_id}"
                f" · {exc}"
            )
            print(
                "REMOTE WRITEBACK · STOPPED "
                f"sent={sent}"
                f" remaining={len(outbox.pending())}"
                f" blocked={len(blocked)}"
            )
            return 2

        sent += 1

        print(
            "SENT "
            f"{bundle.writeback_id}"
            f" · {bundle.attempt.pb_uid}"
            f" · EV={len(bundle.evidence)}"
        )

    print(
        "REMOTE WRITEBACK · SYNC COMPLETE "
        f"sent={sent}"
        f" remaining={len(outbox.pending())}"
        f" blocked={len(blocked)}"
    )

    for envelope, reason in blocked:
        print(
            "BLOCKED "
            f"{envelope.writeback_id}"
            f" · {reason}"
        )

    return 0


def main(
    argv: list[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect and synchronize APCS v2.3 "
            "durable remote-writeback bundles."
        )
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="HTTP timeout in seconds.",
    )

    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    sub.add_parser(
        "status",
        help=(
            "Show pending / eligible / blocked counts "
            "and credential state."
        ),
    )

    sub.add_parser(
        "configure-key",
        help=(
            "Securely store the local write key "
            f"at {KEY_FILE}."
        ),
    )

    bundle = sub.add_parser(
        "bundle",
        help=(
            "Print one canonical remote-writeback bundle."
        ),
    )
    bundle.add_argument(
        "writeback_id",
    )
    bundle.add_argument(
        "--projection",
        action="store_true",
        help=(
            "Print logical REC / EV Notion projection."
        ),
    )

    sync = sub.add_parser(
        "sync",
        help=(
            "Synchronize one pending envelope."
        ),
    )
    sync.add_argument(
        "writeback_id",
    )

    pending = sub.add_parser(
        "sync-pending",
        help=(
            "Synchronize eligible pending envelopes "
            "in durable order."
        ),
    )
    pending.add_argument(
        "--limit",
        type=int,
        help=(
            "Maximum number of eligible pending "
            "envelopes to send."
        ),
    )

    args = parser.parse_args(
        argv
    )

    if args.command == "status":
        return status_cmd()

    if args.command == "configure-key":
        return configure_key_cmd()

    if args.command == "bundle":
        return bundle_cmd(
            args.writeback_id,
            projection=args.projection,
        )

    if args.command == "sync":
        return sync_cmd(
            args.writeback_id,
            timeout=args.timeout,
        )

    if args.command == "sync-pending":
        return sync_pending_cmd(
            timeout=args.timeout,
            limit=args.limit,
        )

    return 2


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
