#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import json
import uuid
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME_DIR = ROOT / ".apcs" / "runtime"

SCHEMA_VERSION = "apcs-exam-session-v1"
VALID_RESULTS = {"AC", "WA", "TLE", "MLE", "RE", "CE", "N/A"}
POSTMORTEM_REASONS = {
    "NONE": "沒有主要失分",
    "KNOWLEDGE_GAP": "不會",
    "OVERTHINKING": "想太久",
    "CODING_SPEED": "寫太慢",
    "BUG": "bug",
    "MISREAD": "看錯題",
    "COMPLEXITY": "complexity 判斷錯",
    "TIME_ALLOCATION": "時間配置錯",
}


class ExamRuntimeError(ValueError):
    pass


def _now(value: dt.datetime | None = None) -> dt.datetime:
    value = value or dt.datetime.now().astimezone()
    if value.tzinfo is None or value.utcoffset() is None:
        raise ExamRuntimeError("timestamp 必須包含時區")
    return value


def _iso(value: dt.datetime | None = None) -> str:
    return _now(value).isoformat(timespec="seconds")


def _parse(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ExamRuntimeError("timestamp 必須包含時區")
    return parsed


class ExamSessionStore:
    """本機考試 telemetry；不等於 learner Evidence。"""

    def __init__(self, runtime_dir: Path = DEFAULT_RUNTIME_DIR):
        self.root = Path(runtime_dir) / "exam"
        self.active_path = self.root / "active.json"
        self.sessions_dir = self.root / "sessions"

    @staticmethod
    def _write(path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(path.name + ".tmp")
        try:
            temp.write_text(
                json.dumps(
                    data,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            temp.replace(path)
        finally:
            temp.unlink(missing_ok=True)

    @staticmethod
    def _read(path: Path) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ExamRuntimeError("目前沒有進行中的考試 session") from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise ExamRuntimeError(f"Exam session 無法讀取：{exc}") from exc
        if not isinstance(value, dict):
            raise ExamRuntimeError("Exam session 必須是 JSON object")
        return value

    @staticmethod
    def _clean_problem_ids(problem_ids: Iterable[str]) -> list[str]:
        result = []
        seen = set()
        for value in problem_ids:
            pid = str(value or "").strip().lower()
            if not pid or pid in seen:
                continue
            seen.add(pid)
            result.append(pid)
        return result

    def active(self) -> dict[str, Any] | None:
        if not self.active_path.is_file():
            return None
        session = self._read(self.active_path)
        self.validate(session)
        return session

    def start(
        self,
        problem_ids: Iterable[str],
        *,
        duration_minutes: int,
        started_at: dt.datetime | None = None,
    ) -> dict[str, Any]:
        if self.active_path.exists():
            raise ExamRuntimeError("已有進行中的考試 session")

        problems = self._clean_problem_ids(problem_ids)
        if not problems:
            raise ExamRuntimeError("考試至少需要一題")
        if not 15 <= int(duration_minutes) <= 240:
            raise ExamRuntimeError("考試時間必須介於 15–240 分鐘")

        when = _now(started_at)
        session = {
            "schema_version": SCHEMA_VERSION,
            "session_id": f"exam_{uuid.uuid4().hex}",
            "status": "ACTIVE",
            "started_at": _iso(when),
            "ended_at": None,
            "duration_minutes": int(duration_minutes),
            "problem_ids": problems,
            "selected_problem_id": None,
            "events": [
                {
                    "type": "START",
                    "at": _iso(when),
                },
                {
                    "type": "SCAN_START",
                    "at": _iso(when),
                },
            ],
            "postmortem_reason": None,
        }
        self.validate(session)
        self._write(self.active_path, session)
        return session

    def _mutate(
        self,
        event_type: str,
        *,
        problem_id: str | None = None,
        at: dt.datetime | None = None,
        **extra: Any,
    ) -> dict[str, Any]:
        session = self._read(self.active_path)
        self.validate(session)
        when = _iso(at)

        event: dict[str, Any] = {
            "type": event_type,
            "at": when,
        }
        if problem_id is not None:
            pid = str(problem_id).strip().lower()
            if pid not in session["problem_ids"]:
                raise ExamRuntimeError(
                    f"題目不在本次考試：{pid}"
                )
            event["problem_id"] = pid
        event.update(extra)
        session["events"].append(event)
        self.validate(session)
        self._write(self.active_path, session)
        return session

    def select(
        self,
        problem_id: str,
        *,
        at: dt.datetime | None = None,
    ) -> dict[str, Any]:
        session = self._read(self.active_path)
        self.validate(session)
        pid = str(problem_id).strip().lower()
        if pid not in session["problem_ids"]:
            raise ExamRuntimeError(f"題目不在本次考試：{pid}")

        previous = session["selected_problem_id"]
        event_type = "SELECT" if previous is None else "SWITCH"
        event = {
            "type": event_type,
            "at": _iso(at),
            "problem_id": pid,
        }
        if previous is not None:
            event["from_problem_id"] = previous

        session["selected_problem_id"] = pid
        session["events"].append(event)
        self.validate(session)
        self._write(self.active_path, session)
        return session

    def mark_compile(
        self,
        problem_id: str,
        *,
        success: bool,
        at: dt.datetime | None = None,
    ) -> bool:
        session = self.active()
        if session is None:
            return False
        pid = str(problem_id).strip().lower()
        if pid not in session["problem_ids"]:
            return False
        self._mutate(
            "COMPILE",
            problem_id=pid,
            at=at,
            success=bool(success),
        )
        return True

    def mark_submit(
        self,
        problem_id: str,
        *,
        result: str = "N/A",
        at: dt.datetime | None = None,
    ) -> dict[str, Any]:
        result = str(result or "N/A").strip().upper()
        if result not in VALID_RESULTS:
            raise ExamRuntimeError(f"不支援的 submit result：{result}")
        return self._mutate(
            "SUBMIT",
            problem_id=problem_id,
            at=at,
            result=result,
        )

    def end(
        self,
        *,
        postmortem_reason: str,
        ended_at: dt.datetime | None = None,
    ) -> dict[str, Any]:
        if postmortem_reason not in POSTMORTEM_REASONS:
            raise ExamRuntimeError("postmortem reason 不合法")

        session = self._read(self.active_path)
        self.validate(session)
        when = _now(ended_at)
        if when < _parse(session["started_at"]):
            raise ExamRuntimeError("ended_at 不能早於 started_at")

        session["status"] = "ENDED"
        session["ended_at"] = _iso(when)
        session["postmortem_reason"] = postmortem_reason
        session["events"].append(
            {
                "type": "END",
                "at": _iso(when),
            }
        )
        self.validate(session)

        destination = (
            self.sessions_dir
            / f"{session['session_id']}.json"
        )
        self._write(destination, session)
        self.active_path.unlink(missing_ok=True)
        return session

    def abort(
        self,
        *,
        aborted_at: dt.datetime | None = None,
    ) -> dict[str, Any]:
        """Close an accidental/abandoned exam without postmortem Evidence."""

        session = self._read(
            self.active_path
        )
        self.validate(session)
        when = _now(aborted_at)

        if when < _parse(
            session["started_at"]
        ):
            raise ExamRuntimeError(
                "aborted_at 不能早於 started_at"
            )

        session["status"] = "ABORTED"
        session["ended_at"] = _iso(when)
        session["postmortem_reason"] = None
        session["events"].append(
            {
                "type": "ABORT",
                "at": _iso(when),
            }
        )
        self.validate(session)

        destination = (
            self.sessions_dir
            / f"{session['session_id']}.json"
        )
        self._write(
            destination,
            session,
        )
        self.active_path.unlink(
            missing_ok=True
        )
        return session

    @staticmethod
    def validate(session: dict[str, Any]) -> None:
        expected = {
            "schema_version",
            "session_id",
            "status",
            "started_at",
            "ended_at",
            "duration_minutes",
            "problem_ids",
            "selected_problem_id",
            "events",
            "postmortem_reason",
        }
        if set(session) != expected:
            raise ExamRuntimeError("Exam session schema 不一致")
        if session["schema_version"] != SCHEMA_VERSION:
            raise ExamRuntimeError("Exam schema_version 不正確")
        if session["status"] not in {
            "ACTIVE",
            "ENDED",
            "ABORTED",
        }:
            raise ExamRuntimeError("Exam status 不合法")
        _parse(session["started_at"])

        if not isinstance(session["duration_minutes"], int):
            raise ExamRuntimeError("duration_minutes 必須是整數")
        if not 15 <= session["duration_minutes"] <= 240:
            raise ExamRuntimeError("duration_minutes 超出範圍")

        problems = session["problem_ids"]
        if (
            not isinstance(problems, list)
            or not problems
            or len(problems) != len(set(problems))
            or any(not isinstance(x, str) or not x for x in problems)
        ):
            raise ExamRuntimeError("problem_ids 不合法")

        selected = session["selected_problem_id"]
        if selected is not None and selected not in problems:
            raise ExamRuntimeError("selected_problem_id 不在題組")

        if not isinstance(session["events"], list):
            raise ExamRuntimeError("events 必須是陣列")
        for event in session["events"]:
            if not isinstance(event, dict):
                raise ExamRuntimeError("exam event 必須是 object")
            if not event.get("type") or not event.get("at"):
                raise ExamRuntimeError("exam event 缺 type / at")
            _parse(event["at"])
            pid = event.get("problem_id")
            if pid is not None and pid not in problems:
                raise ExamRuntimeError("exam event problem_id 不在題組")

        if session["status"] == "ACTIVE":
            if session["ended_at"] is not None:
                raise ExamRuntimeError(
                    "ACTIVE session 不得有 ended_at"
                )
            if session["postmortem_reason"] is not None:
                raise ExamRuntimeError(
                    "ACTIVE session 不得有 postmortem"
                )
        elif session["status"] == "ENDED":
            if not session["ended_at"]:
                raise ExamRuntimeError(
                    "ENDED session 必須有 ended_at"
                )
            _parse(session["ended_at"])
            if (
                session["postmortem_reason"]
                not in POSTMORTEM_REASONS
            ):
                raise ExamRuntimeError(
                    "ENDED session 缺 postmortem reason"
                )
        else:
            if not session["ended_at"]:
                raise ExamRuntimeError(
                    "ABORTED session 必須有 ended_at"
                )
            _parse(session["ended_at"])
            if session["postmortem_reason"] is not None:
                raise ExamRuntimeError(
                    "ABORTED session 不得有 postmortem"
                )

    @staticmethod
    def summary(session: dict[str, Any]) -> dict[str, Any]:
        ExamSessionStore.validate(session)
        start = _parse(session["started_at"])
        end = (
            _parse(session["ended_at"])
            if session["ended_at"]
            else dt.datetime.now().astimezone()
        )

        first_select = next(
            (
                _parse(event["at"])
                for event in session["events"]
                if event["type"] == "SELECT"
            ),
            None,
        )
        first_compile = next(
            (
                _parse(event["at"])
                for event in session["events"]
                if event["type"] == "COMPILE"
            ),
            None,
        )

        return {
            "session_id": session["session_id"],
            "status": session["status"],
            "elapsed_minutes": max(
                0,
                int((end - start).total_seconds() // 60),
            ),
            "scan_minutes": (
                max(
                    0,
                    int((first_select - start).total_seconds() // 60),
                )
                if first_select
                else None
            ),
            "first_compile_minutes": (
                max(
                    0,
                    int((first_compile - start).total_seconds() // 60),
                )
                if first_compile
                else None
            ),
            "compile_count": sum(
                event["type"] == "COMPILE"
                for event in session["events"]
            ),
            "submit_count": sum(
                event["type"] == "SUBMIT"
                for event in session["events"]
            ),
            "switch_count": sum(
                event["type"] == "SWITCH"
                for event in session["events"]
            ),
            "postmortem_reason": session["postmortem_reason"],
        }
