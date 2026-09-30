#!/usr/bin/env python3
from __future__ import annotations

import csv
import datetime as dt
from dataclasses import dataclass
from pathlib import Path


VALID_RESULTS = {"AC", "WA", "TLE", "MLE", "RE", "CE"}
EVENT_FINISH = "finish"
EVENT_REVIEW = "review"

PROGRESS_FIELDS = [
    "problem_id",
    "solved_on",
    "last_review_on",
    "last_result",
    "recall",
]

REVIEW_FIELDS = [
    "problem_id",
    "event_type",
    "date",
    "score",
    "minutes",
    "result",
    "note",
]


class LearningError(ValueError):
    pass


@dataclass
class ProgressState:
    problem_id: str
    solved_on: dt.date | None = None
    last_review_on: dt.date | None = None
    last_result: str = ""
    recall: int | None = None


@dataclass
class ReviewEvent:
    problem_id: str
    event_type: str
    date: dt.date
    score: int
    result: str = "AC"
    minutes: int | None = None
    note: str = ""


@dataclass
class DueItem:
    problem_id: str
    due_on: dt.date
    recall: int | None
    days_overdue: int


def parse_date(value: str | None) -> dt.date | None:
    value = (value or "").strip()
    return dt.date.fromisoformat(value) if value else None


def date_text(value: dt.date | None) -> str:
    return value.isoformat() if value else ""


def validate_score(score: int) -> None:
    if score not in {0, 1, 2, 3}:
        raise LearningError("Recall 必須介於 0–3。")


def validate_result(result: str) -> str:
    result = result.upper()

    if result not in VALID_RESULTS:
        raise LearningError(f"不支援的結果：{result}")

    return result


class LearningStore:
    """
    v2.2 learning state storage.

    progress snapshot 與 review event 採 rollback-safe paired update。
    測試時只需傳入 tempfile 路徑，完全不接觸正式 data/。
    """

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.progress_path = self.data_dir / "progress.csv"
        self.reviews_path = self.data_dir / "reviews.csv"

    def ensure(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)

        if not self.progress_path.exists():
            self._write_csv(
                self.progress_path,
                PROGRESS_FIELDS,
                [],
            )

        if not self.reviews_path.exists():
            self._write_csv(
                self.reviews_path,
                REVIEW_FIELDS,
                [],
            )

    @staticmethod
    def _write_csv(
        path: Path,
        fields: list[str],
        rows: list[dict[str, str]],
    ) -> None:
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temp = path.with_name(
            path.name + ".tmp"
        )

        try:
            with temp.open(
                "w",
                encoding="utf-8",
                newline="",
            ) as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=fields,
                    lineterminator="\n",
                )
                writer.writeheader()
                writer.writerows(rows)

            temp.replace(path)

        finally:
            temp.unlink(
                missing_ok=True
            )

    @staticmethod
    def _restore_bytes(
        path: Path,
        payload: bytes | None,
    ) -> None:
        rollback = path.with_name(
            path.name + ".rollback.tmp"
        )

        try:
            if payload is None:
                path.unlink(
                    missing_ok=True
                )
                return

            path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            rollback.write_bytes(
                payload
            )
            rollback.replace(
                path
            )

        finally:
            rollback.unlink(
                missing_ok=True
            )

    @staticmethod
    def _progress_rows(
        states: dict[str, ProgressState],
    ) -> list[dict[str, str]]:
        rows = []

        for pid in sorted(states):
            state = states[pid]

            rows.append(
                {
                    "problem_id": pid,
                    "solved_on": date_text(
                        state.solved_on
                    ),
                    "last_review_on": date_text(
                        state.last_review_on
                    ),
                    "last_result": state.last_result,
                    "recall": (
                        ""
                        if state.recall is None
                        else str(state.recall)
                    ),
                }
            )

        return rows

    @staticmethod
    def _event_row(
        event: ReviewEvent,
    ) -> dict[str, str]:
        return {
            "problem_id": event.problem_id,
            "event_type": event.event_type,
            "date": event.date.isoformat(),
            "score": str(event.score),
            "minutes": (
                ""
                if event.minutes is None
                else str(event.minutes)
            ),
            "result": event.result,
            "note": event.note,
        }

    @classmethod
    def _event_rows(
        cls,
        events: list[ReviewEvent],
    ) -> list[dict[str, str]]:
        return [
            cls._event_row(event)
            for event in events
        ]

    def load_progress(self) -> dict[str, ProgressState]:
        self.ensure()
        result: dict[str, ProgressState] = {}

        with self.progress_path.open(
            encoding="utf-8",
            newline="",
        ) as f:
            for row in csv.DictReader(f):
                pid = row["problem_id"].strip().lower()
                if not pid:
                    continue

                recall = (
                    int(row["recall"])
                    if row["recall"].strip()
                    else None
                )

                result[pid] = ProgressState(
                    problem_id=pid,
                    solved_on=parse_date(row["solved_on"]),
                    last_review_on=parse_date(
                        row["last_review_on"]
                    ),
                    last_result=row["last_result"].upper(),
                    recall=recall,
                )

        return result

    def save_progress(
        self,
        states: dict[str, ProgressState],
    ) -> None:
        self._write_csv(
            self.progress_path,
            PROGRESS_FIELDS,
            self._progress_rows(states),
        )

    def load_events(self) -> list[ReviewEvent]:
        self.ensure()
        events = []

        with self.reviews_path.open(
            encoding="utf-8",
            newline="",
        ) as f:
            for row in csv.DictReader(f):
                if not row["problem_id"].strip():
                    continue

                events.append(
                    ReviewEvent(
                        problem_id=row["problem_id"]
                        .strip()
                        .lower(),
                        event_type=row["event_type"].strip(),
                        date=dt.date.fromisoformat(row["date"]),
                        score=int(row["score"]),
                        minutes=(
                            int(row["minutes"])
                            if row["minutes"].strip()
                            else None
                        ),
                        result=row["result"].upper(),
                        note=row["note"],
                    )
                )

        return events

    def append_event(
        self,
        event: ReviewEvent,
    ) -> None:
        events = self.load_events()
        events.append(event)

        self._write_csv(
            self.reviews_path,
            REVIEW_FIELDS,
            self._event_rows(events),
        )

    @staticmethod
    def _consistency_errors(
        states: dict[str, ProgressState],
        events: list[ReviewEvent],
    ) -> list[str]:
        errors: list[str] = []

        by_problem: dict[
            str,
            list[ReviewEvent],
        ] = {}

        for event in events:
            by_problem.setdefault(
                event.problem_id,
                [],
            ).append(event)

        problem_ids = (
            set(states)
            | set(by_problem)
        )

        for pid in sorted(problem_ids):
            state = states.get(pid)
            history = by_problem.get(
                pid,
                [],
            )

            finishes = [
                event
                for event in history
                if event.event_type
                == EVENT_FINISH
            ]

            reviews = [
                event
                for event in history
                if event.event_type
                == EVENT_REVIEW
            ]

            solved = bool(
                state
                and state.solved_on
            )

            if solved and not finishes:
                errors.append(
                    f"{pid}: progress 已完成，"
                    "但缺少 Finish event"
                )

            if finishes and not solved:
                errors.append(
                    f"{pid}: 存在 Finish event，"
                    "但 progress 未標記完成"
                )

            if reviews and not finishes:
                errors.append(
                    f"{pid}: 存在 Review event，"
                    "但缺少 Finish event"
                )

            if len(finishes) != 1:
                # Duplicate Finish is validated separately.
                # Without exactly one Finish, snapshot
                # reconstruction is ambiguous.
                continue

            finish = finishes[0]

            if (
                state is None
                or state.solved_on is None
            ):
                continue

            if state.solved_on != finish.date:
                errors.append(
                    f"{pid}: solved_on="
                    f"{state.solved_on} "
                    "與 Finish date="
                    f"{finish.date} 不一致"
                )

            for review in reviews:
                if review.date < finish.date:
                    errors.append(
                        f"{pid}: Review date="
                        f"{review.date} "
                        "早於 Finish date="
                        f"{finish.date}"
                    )

            if reviews:
                latest = reviews[-1]
                expected_review = latest.date
            else:
                latest = finish
                expected_review = None

            if (
                state.last_review_on
                != expected_review
            ):
                errors.append(
                    f"{pid}: last_review_on="
                    f"{state.last_review_on} "
                    "與 event history="
                    f"{expected_review} 不一致"
                )

            if state.last_result != latest.result:
                errors.append(
                    f"{pid}: last_result="
                    f"{state.last_result!r} "
                    "與最新 event result="
                    f"{latest.result!r} 不一致"
                )

            if state.recall != latest.score:
                errors.append(
                    f"{pid}: recall="
                    f"{state.recall} "
                    "與最新 event score="
                    f"{latest.score} 不一致"
                )

        return errors

    def validate_consistency(
        self,
    ) -> list[str]:
        return self._consistency_errors(
            self.load_progress(),
            self.load_events(),
        )

    def save_transaction(
        self,
        states: dict[str, ProgressState],
        events: list[ReviewEvent],
    ) -> None:
        self.ensure()

        errors = self._consistency_errors(
            states,
            events,
        )

        if errors:
            raise LearningError(
                "learning snapshot/event "
                "inconsistency: "
                + "; ".join(errors)
            )

        progress_rows = self._progress_rows(
            states
        )
        review_rows = self._event_rows(
            events
        )

        snapshots = {
            self.progress_path:
                self.progress_path.read_bytes()
                if self.progress_path.exists()
                else None,
            self.reviews_path:
                self.reviews_path.read_bytes()
                if self.reviews_path.exists()
                else None,
        }

        try:
            self._write_csv(
                self.progress_path,
                PROGRESS_FIELDS,
                progress_rows,
            )
            self._write_csv(
                self.reviews_path,
                REVIEW_FIELDS,
                review_rows,
            )

        except BaseException as exc:
            rollback_errors = []

            for path, payload in snapshots.items():
                try:
                    self._restore_bytes(
                        path,
                        payload,
                    )
                except Exception as rollback_exc:
                    rollback_errors.append(
                        f"{path.name}: "
                        f"{rollback_exc}"
                    )

            if rollback_errors:
                raise LearningError(
                    "learning transaction failed "
                    "and rollback also failed: "
                    + "; ".join(
                        rollback_errors
                    )
                ) from exc

            raise


class LearningEngine:
    def __init__(self, store: LearningStore):
        self.store = store

    def state(self, problem_id: str) -> ProgressState:
        pid = problem_id.lower()
        return self.store.load_progress().get(
            pid,
            ProgressState(problem_id=pid),
        )

    def finish(
        self,
        problem_id: str,
        score: int,
        *,
        when: dt.date | None = None,
        minutes: int | None = None,
        note: str = "",
    ) -> ProgressState:
        validate_score(score)
        pid = problem_id.lower()
        when = when or dt.date.today()

        states = self.store.load_progress()
        events = self.store.load_events()
        old = states.get(pid)

        if old and old.solved_on:
            raise LearningError(
                "此題已完成；後續請使用 Review。"
            )

        state = ProgressState(
            problem_id=pid,
            solved_on=when,
            last_review_on=None,
            last_result="AC",
            recall=score,
        )

        states[pid] = state

        events.append(
            ReviewEvent(
                problem_id=pid,
                event_type=EVENT_FINISH,
                date=when,
                score=score,
                minutes=minutes,
                result="AC",
                note=note,
            )
        )

        self.store.save_transaction(
            states,
            events,
        )

        return state

    def review(
        self,
        problem_id: str,
        score: int,
        *,
        result: str = "AC",
        when: dt.date | None = None,
        minutes: int | None = None,
        note: str = "",
    ) -> ProgressState:
        validate_score(score)
        result = validate_result(result)
        pid = problem_id.lower()
        when = when or dt.date.today()

        states = self.store.load_progress()
        events = self.store.load_events()
        state = states.get(pid)

        if not state or not state.solved_on:
            raise LearningError(
                "此題尚未完成，不能建立 Review。"
            )

        if when < state.solved_on:
            raise LearningError(
                "Review 日期不能早於首次完成日期。"
            )

        if (
            state.last_review_on
            and when < state.last_review_on
        ):
            raise LearningError(
                "Review 日期不能早於最近 Review 日期。"
            )

        if result != "AC" and score == 3:
            raise LearningError(
                "未 AC 的 Review 不能評為 Recall 3。"
            )

        # solved_on 永遠保存，不受 Review 結果影響。
        state.last_review_on = when
        state.last_result = result
        state.recall = score

        states[pid] = state

        events.append(
            ReviewEvent(
                problem_id=pid,
                event_type=EVENT_REVIEW,
                date=when,
                score=score,
                minutes=minutes,
                result=result,
                note=note,
            )
        )

        self.store.save_transaction(
            states,
            events,
        )

        return state

    def review_streak_3(self, problem_id: str) -> int:
        """
        只計：
        - event_type=review
        - AC
        - Recall=3
        - 不同日期
        - 從最近日期往回連續

        同一天有多個 Review 時，只採最後一筆。
        """
        pid = problem_id.lower()

        events = [
            e
            for e in self.store.load_events()
            if (
                e.problem_id == pid
                and e.event_type == EVENT_REVIEW
            )
        ]

        latest_by_date: dict[dt.date, ReviewEvent] = {}

        # CSV 順序即事件發生順序；
        # 同日後面的 event 覆蓋前面。
        for event in events:
            latest_by_date[event.date] = event

        streak = 0

        for date in sorted(
            latest_by_date,
            reverse=True,
        ):
            event = latest_by_date[date]

            if event.result == "AC" and event.score == 3:
                streak += 1
            else:
                break

        return streak

    def next_due(
        self,
        problem_id: str,
    ) -> dt.date | None:
        state = self.state(problem_id)

        if not state.solved_on:
            return None

        anchor = (
            state.last_review_on
            or state.solved_on
        )

        if state.recall is None:
            return anchor

        if state.recall == 0:
            days = 1

        elif state.recall == 1:
            days = 3

        elif state.recall == 2:
            days = 7

        else:
            streak = self.review_streak_3(
                problem_id
            )

            if streak >= 3:
                days = 90
            elif streak >= 2:
                days = 60
            else:
                days = 30

        return anchor + dt.timedelta(days=days)

    def mastery(self, problem_id: str) -> str:
        state = self.state(problem_id)

        if not state.solved_on:
            return "NEW"

        if state.recall is not None and state.recall <= 1:
            return "LEARNING"

        if (
            state.recall == 3
            and state.last_result == "AC"
            and self.review_streak_3(problem_id) >= 3
        ):
            return "MASTERED"

        return "PRACTICING"

    def due_queue(
        self,
        *,
        on: dt.date | None = None,
    ) -> list[DueItem]:
        on = on or dt.date.today()
        states = self.store.load_progress()

        items = []

        for pid, state in states.items():
            if not state.solved_on:
                continue

            due = self.next_due(pid)

            if due is None or due > on:
                continue

            items.append(
                DueItem(
                    problem_id=pid,
                    due_on=due,
                    recall=state.recall,
                    days_overdue=(on - due).days,
                )
            )

        # 最逾期 → Recall 最低 → due → ID
        return sorted(
            items,
            key=lambda item: (
                -item.days_overdue,
                (
                    item.recall
                    if item.recall is not None
                    else -1
                ),
                item.due_on,
                item.problem_id,
            ),
        )
