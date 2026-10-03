from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_PATH = ROOT / "docs" / "CURRENT_AUTHORITY.json"
WORKER_AUTHORITY_PATH = ROOT / "cloudflare" / "worker" / "source-authority.json"
CURRENT_MD_PATH = ROOT / "docs" / "CURRENT_AUTHORITY.md"
README_PATH = ROOT / "README.md"
V23_ARCH_PATH = ROOT / "docs" / "ARCHITECTURE_V23.md"

START = "<!-- APCS_CURRENT_AUTHORITY_START -->"
END = "<!-- APCS_CURRENT_AUTHORITY_END -->"


class CurrentAuthorityError(ValueError):
    pass


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CurrentAuthorityError(
            f"無法讀取 {path.relative_to(ROOT)}：{exc}"
        ) from exc


def load_current_authority() -> dict:
    authority = _load_json(AUTHORITY_PATH)
    worker = _load_json(WORKER_AUTHORITY_PATH)
    validate_authority(authority, worker)
    return authority


def validate_authority(authority: dict, worker: dict) -> None:
    if authority.get("schema_version") != "apcs-current-authority-v1":
        raise CurrentAuthorityError(
            "CURRENT_AUTHORITY schema_version 不正確"
        )

    product = authority.get("product") or {}
    curriculum = authority.get("curriculum") or {}
    production = authority.get("production") or {}

    required_product = {
        "stable_runtime",
        "stable_runtime_status",
        "next_version",
        "next_version_status",
        "next_version_contract",
        "learner_readiness",
    }
    missing = sorted(required_product - set(product))
    if missing:
        raise CurrentAuthorityError(
            f"product 缺欄位：{', '.join(missing)}"
        )

    if product["learner_readiness"] not in {"NOT_ASSESSED", "ASSESSED"}:
        raise CurrentAuthorityError(
            "learner_readiness 值不合法"
        )

    for field in ("main_lessons", "units", "skills"):
        if not isinstance(curriculum.get(field), int) or curriculum[field] <= 0:
            raise CurrentAuthorityError(
                f"curriculum.{field} 必須是正整數"
            )

    checks = {
        "worker": worker.get("worker"),
        "version_number": worker.get("production_version_number"),
        "version_id": worker.get("production_version_id"),
        "deployment_id": worker.get("deployment_id"),
    }
    for field, expected in checks.items():
        if production.get(field) != expected:
            raise CurrentAuthorityError(
                f"production.{field} 與 cloudflare/worker/source-authority.json 不一致"
            )

    if worker.get("preview_urls_status") != "DISABLED_POST_RELEASE":
        raise CurrentAuthorityError(
            "Worker Preview / Version URLs 並非已關閉"
        )

    if production.get("preview_urls") != "DISABLED":
        raise CurrentAuthorityError(
            "CURRENT_AUTHORITY preview_urls 必須為 DISABLED"
        )

    if production.get("system_audit") != "PASS_CLEAN":
        raise CurrentAuthorityError(
            "production system_audit 不是 PASS_CLEAN"
        )

    if int(production.get("exceptions", -1)) != 0:
        raise CurrentAuthorityError(
            "production exceptions 必須為 0"
        )

    if int(production.get("warnings", -1)) != 0:
        raise CurrentAuthorityError(
            "production warnings 必須為 0"
        )


def render_summary(authority: dict) -> str:
    product = authority["product"]
    curriculum = authority["curriculum"]
    production = authority["production"]
    current_work = authority["current_work"]

    return "\n".join(
        [
            "## 目前正式狀態（自動產生）",
            "",
            "> 本區塊由 `docs/CURRENT_AUTHORITY.json` 產生；不要手動修改。",
            "",
            f"- 穩定學習執行環境：**{product['stable_runtime']}**，狀態 `{product['stable_runtime_status']}`。",
            f"- 下一版本：**{product['next_version']}**，目前階段 **{current_work['gate']}｜{current_work['goal']}**。",
            (
                "- 正式課程："
                f"**{curriculum['main_lessons']} Lessons / {curriculum['units']} Units / "
                f"{curriculum['skills']} Skills**；未有真實 Evidence 前不擴張主線。"
            ),
            (
                "- Production Worker："
                f"**#{production['version_number']} @100%** "
                f"`{production['version_id']}`；"
                f"system-audit = **{production['system_audit']}**；"
                "Preview / Version URLs = **DISABLED**。"
            ),
            "- 日常主要介面：**VS Code Control Center**。",
            (
                "- 學習準備度："
                f"`LEARNER_READINESS = {product['learner_readiness']}`。"
            ),
            "- v2.4 正式契約：[`docs/V24_PRODUCT_ARCHITECTURE_CONTRACT.md`](./docs/V24_PRODUCT_ARCHITECTURE_CONTRACT.md)。",
        ]
    )


def render_full(authority: dict) -> str:
    product = authority["product"]
    curriculum = authority["curriculum"]
    runtime = authority["learner_runtime"]
    production = authority["production"]
    records = authority["durable_records"]
    work = authority["current_work"]

    lines = [
        "# APCS C++ Learning System｜目前正式狀態",
        "",
        "> 自動由 `docs/CURRENT_AUTHORITY.json` 產生；這份 Markdown 只供人閱讀，JSON 才是目前狀態的機器可讀來源。",
        "",
        "## 版本",
        "",
        f"- 穩定執行環境：**{product['stable_runtime']}**（{product['stable_runtime_status']}）",
        f"- 下一版本：**{product['next_version']}**（{product['next_version_status']}）",
        f"- 目前階段：**{work['gate']}｜{work['goal']}**",
        "",
        "## 正式課程",
        "",
        f"- 主線 Lessons：**{curriculum['main_lessons']}**",
        f"- Units：**{curriculum['units']}**",
        f"- Skills：**{curriculum['skills']}**",
        f"- Hosted UI：**{curriculum['hosted_ui_version']}**",
        "- 主線擴張：除非真實 Evidence 證明 coverage 缺口，否則保持凍結。",
        "",
        "## 日常學習",
        "",
        f"- 主要介面：**{runtime['default_surface']}**",
        f"- Tracks：{', '.join(runtime['tracks'])}",
        f"- Today：{runtime['today_policy']}",
        f"- Evidence authority：{runtime['evidence_authority']}",
        "",
        "## Production",
        "",
        f"- Worker：**{production['worker']} #{production['version_number']} @100%**",
        f"- Version：`{production['version_id']}`",
        f"- Deployment：`{production['deployment_id']}`",
        f"- System audit：**{production['system_audit']}**",
        f"- Exceptions / warnings：**{production['exceptions']} / {production['warnings']}**",
        f"- Preview / Version URLs：**{production['preview_urls']}**",
        "",
        "## Durable records",
        "",
        f"- Canonical REC：**{records['canonical_rec_count']}**",
        f"- Canonical EV：**{records['canonical_ev_count']}**",
        f"- Remote writeback：**{records['remote_writeback_status']}**",
        "",
        "## 尚未關閉但不阻塞 Production",
        "",
    ]

    for item in work["open_nonblocking"]:
        lines.append(
            f"- GitHub issue #{item['issue']}：{item['scope']}"
        )

    lines += [
        "",
        "## Readiness",
        "",
        f"`LEARNER_READINESS = {product['learner_readiness']}`",
        "",
        "工程完成、Production PASS、教材完成都不能自動取代真實 learner Evidence。",
        "",
    ]
    return "\n".join(lines)


def replace_between(text: str, start: str, end: str, body: str) -> str:
    if start in text and end in text:
        before, rest = text.split(start, 1)
        _, after = rest.split(end, 1)
        return before + start + "\n" + body + "\n" + end + after
    return text.rstrip() + f"\n\n{start}\n{body}\n{end}\n"


def sync_current_authority() -> None:
    authority = load_current_authority()
    summary = render_summary(authority)

    for path in (README_PATH, V23_ARCH_PATH):
        current = path.read_text(encoding="utf-8")
        path.write_text(
            replace_between(current, START, END, summary),
            encoding="utf-8",
        )

    CURRENT_MD_PATH.write_text(
        render_full(authority),
        encoding="utf-8",
    )


if __name__ == "__main__":
    sync_current_authority()
    print("已同步目前正式狀態。")
