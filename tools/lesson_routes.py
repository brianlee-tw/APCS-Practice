"""Fail-closed canonical Notion Lesson routing for the v2.4 Workbench.

Notion remains the Lesson/content authority.  This module only reads the reviewed
Git projection needed by the offline VS Code runtime to open the correct page.
It never derives or guesses a Notion URL from a Lesson UID.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "apcs-lesson-routes-v1"
LESSON_UID_RE = re.compile(r"^L-[A-Z]{2,3}-\d{2}$")
NOTION_PAGE_URL_RE = re.compile(
    r"^https://app\.notion\.com/p/[0-9a-f]{32}$"
)


class LessonRouteError(ValueError):
    """Raised when the reviewed routing projection is unreadable or invalid."""


class LessonRouteStore:
    def __init__(self, path: Path):
        self.path = Path(path)

    def load(self) -> dict[str, Any]:
        try:
            data = json.loads(
                self.path.read_text(encoding="utf-8")
            )
        except FileNotFoundError as exc:
            raise LessonRouteError(
                "Lesson routing projection 不存在。"
            ) from exc
        except json.JSONDecodeError as exc:
            raise LessonRouteError(
                "Lesson routing projection JSON 損壞。"
            ) from exc
        except OSError as exc:
            raise LessonRouteError(
                f"無法讀取 Lesson routing projection：{exc}"
            ) from exc

        if not isinstance(data, dict):
            raise LessonRouteError(
                "Lesson routing projection top-level 必須是 object。"
            )

        if data.get("schema_version") != SCHEMA_VERSION:
            raise LessonRouteError(
                "Lesson routing projection schema 不相容："
                f"{data.get('schema_version')!r}"
            )

        routes = data.get("routes")
        if not isinstance(routes, dict):
            raise LessonRouteError(
                "Lesson routing projection routes 必須是 object。"
            )

        seen_urls: set[str] = set()
        for raw_uid, raw_url in routes.items():
            uid = str(raw_uid or "").strip()
            url = str(raw_url or "").strip()

            if not LESSON_UID_RE.fullmatch(uid):
                raise LessonRouteError(
                    f"非法 Lesson UID：{uid!r}"
                )

            if not NOTION_PAGE_URL_RE.fullmatch(url):
                raise LessonRouteError(
                    f"{uid}: canonical Notion URL 非法。"
                )

            if url in seen_urls:
                raise LessonRouteError(
                    f"{uid}: canonical Notion URL 重複。"
                )
            seen_urls.add(url)

        return data

    def resolve(
        self,
        lesson_uid: str | None,
    ) -> str | None:
        uid = str(
            lesson_uid or ""
        ).strip()

        if not uid:
            return None

        if not LESSON_UID_RE.fullmatch(uid):
            return None

        routes = self.load()["routes"]
        value = routes.get(uid)

        if value is None:
            return None

        return str(value).strip()
