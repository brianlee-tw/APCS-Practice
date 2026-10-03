from __future__ import annotations

import datetime as dt
import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from tools import apcs_control as control
from tools.reading_runtime import (
    FORMAL_END,
    FORMAL_START,
    create_reading_scratch,
    formal_response_ready,
)
from tools.remote_writeback import (
    build_remote_writeback_bundle,
    notion_projection,
)


def placement(*, method_confirmation_required=False):
    return types.SimpleNamespace(
        placement_uid="PL-PB-143-L-FND-01",
        pb_uid="PB-143",
        problem_id="ZJ-d050",
        title="妳那裡現在幾點了？",
        url="https://zerojudge.tw/ShowProblem?problemid=d050",
        primary_skill="S01_IO",
        supporting_skills=(),
        role="Guided Drill",
        lesson_uid="L-FND-01",
        method_confirmation_required=method_confirmation_required,
        evidence_level_cap=2,
    )


class ReadingRuntimeV23Test(unittest.TestCase):
    def test_response_first_scratch_is_bound_to_placement(self):
        with tempfile.TemporaryDirectory() as temp:
            path = create_reading_scratch(
                Path(temp),
                placement(),
                action="review",
                today=dt.date(2026, 10, 3),
            )

            self.assertEqual(path.suffix, ".md")
            self.assertIn(
                "reading/review/2026-10-03",
                path.as_posix(),
            )
            self.assertIn(
                "__PL-PB-143-L-FND-01.md",
                path.name,
            )

            text = path.read_text(encoding="utf-8")
            self.assertIn(FORMAL_START, text)
            self.assertIn(FORMAL_END, text)
            self.assertIn("先 reason / trace，再驗證", text)
            self.assertFalse(formal_response_ready(path))

            text = text.replace(
                FORMAL_START + "\n\n" + FORMAL_END,
                FORMAL_START
                + "\n\n我先建立時差轉換 invariant，並手算兩個 boundary case。\n\n"
                + FORMAL_END,
            )
            path.write_text(text, encoding="utf-8")
            self.assertTrue(formal_response_ready(path))

    def test_runtime_path_encodes_track_and_record_action(self):
        self.assertEqual(
            control.runtime_scratch_context(
                Path(".apcs/runtime/reading/review/2026-10-03/x__PL.md")
            ),
            ("Reading", "review"),
        )
        self.assertEqual(
            control.runtime_scratch_context(
                Path(".apcs/runtime/review/2026-10-03/x__PL.cpp")
            ),
            ("Implementation", "review"),
        )
        self.assertEqual(
            control.runtime_scratch_context(
                Path(".apcs/runtime/learn/2026-10-03/x__PL.cpp")
            ),
            ("Implementation", "finish"),
        )

    def test_published_runtime_record_actions_do_not_depend_on_legacy_progress(self):
        finish = control.record_action_state(
            {
                "published_runtime": True,
                "runtime_track": "Reading",
                "runtime_action": "finish",
                "state": None,
            }
        )
        review = control.record_action_state(
            {
                "published_runtime": True,
                "runtime_track": "Implementation",
                "runtime_action": "review",
                "state": None,
            }
        )

        self.assertEqual(finish[:2], (True, False))
        self.assertIn("Reading", finish[2])
        self.assertEqual(review[:2], (False, True))
        self.assertIn("Implementation", review[3])

    def test_reading_envelope_uses_na_and_reading_outcome(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "x__PL-PB-143-L-FND-01.md"
            path.write_text("formal response", encoding="utf-8")
            p = placement(method_confirmation_required=True)
            problem = {
                "id": "zj-d050",
                "path": path,
            }

            envelope = control.attempt_envelope_for_record(
                action="review",
                problem=problem,
                result="N/A",
                minutes=6,
                assistance=1,
                independent=True,
                novelty="delayed_retest",
                timed=False,
                placement=p,
                method_confirmed=None,
                track="Reading",
                evidence_outcome="PARTIAL",
                finished_at=dt.datetime(
                    2026, 10, 3, 16, 30,
                    tzinfo=dt.timezone(dt.timedelta(hours=8)),
                ),
            )

        self.assertEqual(envelope.attempt.judge_result, "N/A")
        self.assertEqual(envelope.attempt.language, "unknown")
        self.assertEqual(envelope.attempt.activity, "Review")
        self.assertEqual(len(envelope.evidence), 1)
        claim = envelope.evidence[0]
        self.assertEqual(claim.track, "Reading")
        self.assertEqual(claim.outcome, "PARTIAL")
        self.assertEqual(claim.skill_uid, "S01_IO")

    def test_remote_projection_maps_reading_to_rec_unknown_but_ev_na(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "x__PL-PB-143-L-FND-01.md"
            problem = {
                "id": "ZJ-d050",
                "path": path,
            }
            envelope = control.attempt_envelope_for_record(
                action="finish",
                problem=problem,
                result="N/A",
                minutes=5,
                assistance=1,
                independent=True,
                novelty="new",
                timed=False,
                placement=placement(),
                track="Reading",
                evidence_outcome="PASS",
                finished_at=dt.datetime(
                    2026, 10, 3, 16, 30,
                    tzinfo=dt.timezone(dt.timedelta(hours=8)),
                ),
            )

        bundle = build_remote_writeback_bundle(envelope)
        projection = notion_projection(bundle)

        self.assertEqual(
            projection["rec"]["properties"]["最新提交結果"],
            "未提交/未知",
        )
        self.assertEqual(
            projection["evidence"][0]["properties"]["Judge Result"],
            "N/A",
        )
        self.assertEqual(
            projection["evidence"][0]["properties"]["Track"],
            "Reading",
        )

    def test_current_problem_preserves_reading_review_identity(self):
        fake = placement()
        curriculum = mock.Mock()
        curriculum.placement_by_uid.return_value = fake
        path = Path(
            ".apcs/runtime/reading/review/2026-10-03/"
            "ZJ-d050__PL-PB-143-L-FND-01.md"
        )

        with mock.patch.object(control, "CURRICULUM", curriculum):
            problem = control.current_problem(str(path))

        self.assertTrue(problem["published_runtime"])
        self.assertEqual(problem["runtime_track"], "Reading")
        self.assertEqual(problem["runtime_action"], "review")
        self.assertEqual(problem["placement_uid"], "PL-PB-143-L-FND-01")

    def test_worker_contract_accepts_na_without_writing_na_to_rec_result(self):
        root = Path(__file__).resolve().parents[1]
        source = (
            root / "cloudflare" / "worker" / "src" / "index.mjs"
        ).read_text(encoding="utf-8")

        self.assertIn(
            'REMOTE_RESULTS = /* @__PURE__ */ new Set(["N/A",',
            source,
        )
        self.assertIn(
            'a.judgeResult === "N/A" ? "未提交/未知" : a.judgeResult',
            source,
        )


if __name__ == "__main__":
    unittest.main()
