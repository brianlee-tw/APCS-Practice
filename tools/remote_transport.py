"""Fixed-origin HTTP transport for APCS v2.3 remote writeback.

The learner mutation is already durable before this module is called.
A transport failure therefore leaves the outbox envelope pending.  A local
receipt is persisted only after the server returns a complete, identity-matching
v2.3 receipt.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import socket
from typing import Any, Callable
import urllib.error
import urllib.request

try:
    from .evidence_outbox import EvidenceOutbox
    from .remote_writeback import (
        RemoteWritebackBundle,
        RemoteWritebackError,
        validate_remote_receipt,
    )
except ImportError:
    from evidence_outbox import EvidenceOutbox
    from remote_writeback import (
        RemoteWritebackBundle,
        RemoteWritebackError,
        validate_remote_receipt,
    )


PRODUCTION_ENDPOINT = (
    "https://apcs-rec-writeback.main-1h9k2.workers.dev/api/record"
)
WRITEBACK_URL_ENV = "APCS_WRITEBACK_URL"
WRITE_KEY_ENV = "APCS_WRITE_KEY"
DEFAULT_TIMEOUT_SECONDS = 20.0
KEY_FILE = (
    Path.home()
    / ".config"
    / "apcs"
    / "writeback.key"
)


class WritebackTransportError(RuntimeError):
    pass


def configured_endpoint() -> str:
    value = str(
        os.environ.get(
            WRITEBACK_URL_ENV,
            "",
        )
    ).strip()

    if not value:
        raise WritebackTransportError(
            f"missing {WRITEBACK_URL_ENV}; "
            "pending envelopes remain local"
        )

    if value != PRODUCTION_ENDPOINT:
        raise WritebackTransportError(
            f"{WRITEBACK_URL_ENV} must equal the approved "
            "production endpoint"
        )

    return value


def credential_source() -> str | None:
    if str(os.environ.get(WRITE_KEY_ENV, "")).strip():
        return "environment"

    if KEY_FILE.is_file():
        return "file"

    return None


def configured_write_key() -> str:
    env_value = str(
        os.environ.get(
            WRITE_KEY_ENV,
            "",
        )
    ).strip()

    if env_value:
        return env_value

    if KEY_FILE.is_file():
        try:
            mode = KEY_FILE.stat().st_mode & 0o777
        except OSError as exc:
            raise WritebackTransportError(
                f"cannot inspect writeback key file: {exc}"
            ) from exc

        if mode & 0o077:
            raise WritebackTransportError(
                "writeback key file permissions are too broad; "
                "run chmod 600 ~/.config/apcs/writeback.key"
            )

        try:
            value = KEY_FILE.read_text(
                encoding="utf-8"
            ).strip()
        except OSError as exc:
            raise WritebackTransportError(
                f"cannot read writeback key file: {exc}"
            ) from exc

        if value:
            return value

    raise WritebackTransportError(
        f"missing {WRITE_KEY_ENV} and {KEY_FILE}; "
        "pending envelopes remain local"
    )


def install_write_key(
    value: str,
) -> Path:
    value = str(value or "").strip()

    if not value:
        raise WritebackTransportError(
            "writeback key cannot be empty"
        )

    KEY_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
        mode=0o700,
    )

    temp = KEY_FILE.with_name(
        KEY_FILE.name + ".tmp"
    )

    try:
        temp.write_text(
            value + "\n",
            encoding="utf-8",
        )
        os.chmod(
            temp,
            0o600,
        )
        os.replace(
            temp,
            KEY_FILE,
        )
        os.chmod(
            KEY_FILE,
            0o600,
        )
    finally:
        temp.unlink(
            missing_ok=True,
        )

    return KEY_FILE


def post_bundle(
    bundle: RemoteWritebackBundle,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> dict[str, Any]:
    if timeout <= 0:
        raise WritebackTransportError(
            "timeout must be positive"
        )

    payload = json.dumps(
        bundle.to_dict(),
        ensure_ascii=False,
        separators=(
            ",",
            ":",
        ),
    ).encode(
        "utf-8"
    )

    request = urllib.request.Request(
        configured_endpoint(),
        data=payload,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": (
                "APCS-Practice-v2.3-writeback"
            ),
            "X-APCS-Write-Key": (
                configured_write_key()
            ),
        },
    )

    try:
        with opener(
            request,
            timeout=timeout,
        ) as response:
            status = int(
                getattr(
                    response,
                    "status",
                    response.getcode(),
                )
            )
            body = response.read()

    except urllib.error.HTTPError as exc:
        raise WritebackTransportError(
            "remote writeback HTTP "
            f"{exc.code}"
        ) from exc

    except (
        urllib.error.URLError,
        TimeoutError,
        socket.timeout,
        OSError,
    ) as exc:
        raise WritebackTransportError(
            "remote writeback transport failed: "
            f"{exc}"
        ) from exc

    if not 200 <= status < 300:
        raise WritebackTransportError(
            "remote writeback HTTP "
            f"{status}"
        )

    try:
        value = json.loads(
            body.decode(
                "utf-8"
            )
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise WritebackTransportError(
            "remote writeback returned invalid JSON"
        ) from exc

    if not isinstance(
        value,
        dict,
    ):
        raise WritebackTransportError(
            "remote writeback receipt must be an object"
        )

    try:
        return validate_remote_receipt(
            bundle,
            value,
        )
    except RemoteWritebackError as exc:
        raise WritebackTransportError(
            "remote writeback receipt rejected: "
            f"{exc}"
        ) from exc


def sync_bundle(
    outbox: EvidenceOutbox,
    bundle: RemoteWritebackBundle,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> tuple[
    dict[str, Any],
    bool,
]:
    receipt = post_bundle(
        bundle,
        timeout=timeout,
        opener=opener,
    )

    created = outbox.mark_sent(
        bundle.writeback_id,
        receipt,
    )

    return (
        receipt,
        created,
    )
