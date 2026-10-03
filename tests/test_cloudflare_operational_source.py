from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "cloudflare" / "worker"
RECOVERY = ROOT / "cloudflare" / "recovery" / "worker-51"
EXPECTED_SHA = "c4f2271c73a928a4dd757aaa160be303d3e555b0cfee80f156b2ca6956c7ba67"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_operational_source_matches_exact_worker51_baseline() -> None:
    operational = WORKER / "src" / "index.mjs"
    recovered = RECOVERY / "index.mjs"
    assert _sha256(operational) == EXPECTED_SHA
    assert operational.read_bytes() == recovered.read_bytes()


def test_operational_source_authority_contract() -> None:
    authority = json.loads((WORKER / "source-authority.json").read_text(encoding="utf-8"))
    assert authority["status"] == "EXACT_PRODUCTION_BASELINE"
    assert authority["production_version_number"] == 51
    assert authority["source_sha256"] == EXPECTED_SHA
    assert authority["original_typescript_status"] == "NOT_RECOVERED"

    config = (WORKER / "wrangler.jsonc").read_text(encoding="utf-8")
    assert '"name": "apcs-rec-writeback"' in config
    assert '"main": "src/index.mjs"' in config
    assert '"compatibility_date": "2026-08-25"' in config
    assert '"nodejs_compat"' in config
    assert '"directory": "../recovery/assets-51/public"' in config
    assert '"binding": "ASSETS"' in config
