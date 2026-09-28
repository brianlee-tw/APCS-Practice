#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import shutil
from collections import defaultdict
from pathlib import Path


OLD_PROGRESS = [
    "problem_id",
    "verdict",
    "solved",
    "reviewed",
    "recall",
]

OLD_REVIEWS = [
    "problem_id",
    "date",
    "score",
    "minutes",
    "result",
    "note",
]

NEW_PROGRESS = [
    "problem_id",
    "solved_on",
    "last_review_on",
    "last_result",
    "recall",
]

NEW_REVIEWS = [
    "problem_id",
    "event_type",
    "date",
    "score",
    "minutes",
    "result",
    "note",
]


def read_csv(path: Path):
    if not path.exists():
        return [], []

    with path.open(
        encoding="utf-8",
        newline="",
    ) as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open(
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


def normalize_id(value: str | None) -> str:
    return (value or "").strip().lower()


def migrate(
    data_dir: Path,
    *,
    drop_ids: set[str],
    backup_dir: Path | None = None,
):
    progress_path = data_dir / "progress.csv"
    reviews_path = data_dir / "reviews.csv"

    p_fields, p_rows = read_csv(progress_path)
    r_fields, r_rows = read_csv(reviews_path)

    drop_ids = {x.lower() for x in drop_ids}

    if backup_dir:
        backup_dir.mkdir(parents=True, exist_ok=True)

        if progress_path.exists():
            shutil.copy2(
                progress_path,
                backup_dir / "progress.csv",
            )

        if reviews_path.exists():
            shutil.copy2(
                reviews_path,
                backup_dir / "reviews.csv",
            )

    p_rows = [
        row
        for row in p_rows
        if normalize_id(row.get("problem_id"))
        not in drop_ids
    ]

    r_rows = [
        row
        for row in r_rows
        if normalize_id(row.get("problem_id"))
        not in drop_ids
    ]

    # Already migrated: only clean requested fixture IDs.
    if p_fields == NEW_PROGRESS and r_fields == NEW_REVIEWS:
        write_csv(
            progress_path,
            NEW_PROGRESS,
            p_rows,
        )
        write_csv(
            reviews_path,
            NEW_REVIEWS,
            r_rows,
        )

        return {
            "progress": len(p_rows),
            "events": len(r_rows),
            "already_v21": True,
        }

    if p_fields and p_fields != OLD_PROGRESS:
        raise SystemExit(
            f"Unknown progress schema: {p_fields}"
        )

    if r_fields and r_fields != OLD_REVIEWS:
        raise SystemExit(
            f"Unknown reviews schema: {r_fields}"
        )

    old_progress = {
        normalize_id(row.get("problem_id")): row
        for row in p_rows
        if normalize_id(row.get("problem_id"))
    }

    grouped_events = defaultdict(list)

    for row in r_rows:
        pid = normalize_id(row.get("problem_id"))

        if pid:
            grouped_events[pid].append(row)

    new_events = []
    review_summary = {}

    for pid, events in grouped_events.items():
        progress = old_progress.get(pid, {})
        solved_on = (progress.get("solved") or "").strip()

        finish_assigned = False
        migrated = []

        for index, row in enumerate(events):
            date = (row.get("date") or "").strip()
            result = (row.get("result") or "AC").upper()

            # Best-effort semantic migration:
            # the earliest event matching solved_on is the original finish.
            if (
                not finish_assigned
                and solved_on
                and date == solved_on
            ):
                event_type = "finish"
                finish_assigned = True
            elif (
                not finish_assigned
                and not solved_on
                and index == 0
                and result == "AC"
            ):
                event_type = "finish"
                finish_assigned = True
                solved_on = date
            else:
                event_type = "review"

            migrated_row = {
                "problem_id": pid,
                "event_type": event_type,
                "date": date,
                "score": row.get("score", ""),
                "minutes": row.get("minutes", ""),
                "result": result,
                "note": row.get("note", ""),
            }

            migrated.append(migrated_row)
            new_events.append(migrated_row)

        reviews = [
            row
            for row in migrated
            if row["event_type"] == "review"
        ]

        if reviews:
            last = reviews[-1]

            review_summary[pid] = {
                "last_review_on": last["date"],
                "last_result": last["result"],
            }

    new_progress = []

    for pid in sorted(old_progress):
        row = old_progress[pid]

        solved_on = (row.get("solved") or "").strip()
        summary = review_summary.get(pid)

        if summary:
            last_review_on = summary["last_review_on"]
            last_result = summary["last_result"]
        else:
            last_review_on = ""
            last_result = (
                "AC"
                if solved_on
                else (row.get("verdict") or "").upper()
            )

        new_progress.append(
            {
                "problem_id": pid,
                "solved_on": solved_on,
                "last_review_on": last_review_on,
                "last_result": last_result,
                "recall": row.get("recall", ""),
            }
        )

    write_csv(
        progress_path,
        NEW_PROGRESS,
        new_progress,
    )

    write_csv(
        reviews_path,
        NEW_REVIEWS,
        new_events,
    )

    return {
        "progress": len(new_progress),
        "events": len(new_events),
        "already_v21": False,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Migrate APCS learning data to v2.1"
    )

    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
    )

    parser.add_argument(
        "--drop-id",
        action="append",
        default=[],
    )

    parser.add_argument(
        "--backup-dir",
        type=Path,
    )

    args = parser.parse_args()

    result = migrate(
        args.data_dir,
        drop_ids=set(args.drop_id),
        backup_dir=args.backup_dir,
    )

    print("APCS learning-data migration")
    print(
        "Schema : "
        + (
            "already v2.1"
            if result["already_v21"]
            else "v2 → v2.1"
        )
    )
    print(f"Progress: {result['progress']} rows")
    print(f"Events  : {result['events']} rows")


if __name__ == "__main__":
    main()
