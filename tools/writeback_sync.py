#!/usr/bin/env python3
"""Inspect/export APCS v2.3 durable remote-writeback bundles.

No network transport is implemented here.  The command is safe to run before
the Cloudflare Worker gains the v2.3 bundle variant.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .evidence_outbox import (
        EvidenceOutbox,
        EvidenceOutboxError,
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
        all_items = (
            outbox.all_envelopes()
        )
        pending = (
            outbox.pending()
        )
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

    acknowledged = (
        len(all_items)
        - len(pending)
    )

    print(
        "REMOTE WRITEBACK · CONTRACT READY / TRANSPORT DISABLED"
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


def main(
    argv: list[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect/export APCS v2.3 remote-writeback bundles. "
            "This tool performs no network writes."
        )
    )
    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    sub.add_parser(
        "status",
        help=(
            "Show pending / eligible / blocked envelope counts."
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
            "Print logical REC / EV Notion projection instead."
        ),
    )

    args = parser.parse_args(
        argv
    )

    if args.command == "status":
        return status_cmd()

    if args.command == "bundle":
        return bundle_cmd(
            args.writeback_id,
            projection=(
                args.projection
            ),
        )

    return 2


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
