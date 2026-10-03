from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "cloudflare" / "worker"
RECOVERY = ROOT / "cloudflare" / "recovery" / "worker-51"
EXPECTED_BASELINE_SHA = (
    "c4f2271c73a928a4dd757aaa160be303"
    "d3e555b0cfee80f156b2ca6956c7ba67"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_immutable_recovery_snapshot_is_exact_worker51_baseline() -> None:
    recovered = RECOVERY / "index.mjs"
    assert _sha256(recovered) == EXPECTED_BASELINE_SHA


def test_operational_source_authority_contract() -> None:
    authority = json.loads(
        (WORKER / "source-authority.json").read_text(
            encoding="utf-8"
        )
    )
    assert authority["status"] == (
        "SCHEMA_COMPAT_PATCH_PENDING_DEPLOY"
    )
    assert authority["production_version_number"] == 51
    assert authority["baseline_source_sha256"] == (
        EXPECTED_BASELINE_SHA
    )
    assert authority["original_typescript_status"] == (
        "NOT_RECOVERED"
    )
    assert authority["pending_patch"][
        "deployment_status"
    ] == "NOT_DEPLOYED"

    config = (WORKER / "wrangler.jsonc").read_text(
        encoding="utf-8"
    )
    assert '"name": "apcs-rec-writeback"' in config
    assert '"main": "src/index.mjs"' in config
    assert '"compatibility_date": "2026-08-25"' in config
    assert '"nodejs_compat"' in config
    assert (
        '"directory": "../recovery/assets-51/public"'
        in config
    )
    assert '"binding": "ASSETS"' in config


def test_operational_source_does_not_write_removed_rec_fields() -> None:
    source = (WORKER / "src" / "index.mjs").read_text(
        encoding="utf-8"
    )

    # v2.3 remote REC path used a raw Chinese property key.
    assert '"進度狀態":' not in source

    # HTML Direct path used escaped property keys.
    assert (
        '"\\u9032\\u5EA6\\u72C0\\u614B":'
        not in source
    )
    assert (
        'properties["\\u8907\\u7FD2\\u65E5\\u671F"]'
        not in source
    )

    # Keep the intended contracts and learner-facing review-date
    # page-body behavior while removing only invalid property writes.
    assert (
        'REMOTE_WRITEBACK_SCHEMA = '
        '"v2.3-remote-writeback-1"'
        in source
    )
    assert (
        'REMOTE_RECEIPT_SCHEMA = '
        '"v2.3-remote-receipt-1"'
        in source
    )
    assert (
        "makePageBody(p, { result, assistance, independent, "
        "attempts, timeMin, stage, errors, takeaway, reviewDate })"
        in source
    )
