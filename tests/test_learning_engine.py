import datetime as dt
import tempfile
import unittest
from pathlib import Path

from tools.learning_engine import (
    EVENT_FINISH,
    EVENT_REVIEW,
    LearningEngine,
    LearningError,
    LearningStore,
    ProgressState,
    ReviewEvent,
)


D0 = dt.date(2026, 9, 28)


class LearningEngineTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp.name) / "data"
        self.store = LearningStore(self.data_dir)
        self.engine = LearningEngine(self.store)

    def tearDown(self):
        self.temp.cleanup()

    def finish(self, pid="a001", score=2, day=D0):
        return self.engine.finish(
            pid,
            score,
            when=day,
        )

    def review(
        self,
        pid="a001",
        score=2,
        day=D0,
        result="AC",
    ):
        return self.engine.review(
            pid,
            score,
            when=day,
            result=result,
        )

    def test_01_finish_new_problem(self):
        state = self.finish()

        self.assertEqual(state.solved_on, D0)
        self.assertIsNone(state.last_review_on)
        self.assertEqual(state.last_result, "AC")
        self.assertEqual(state.recall, 2)

    def test_02_finish_twice_rejected(self):
        self.finish()

        with self.assertRaises(LearningError):
            self.finish()

    def test_03_review_unsolved_rejected(self):
        with self.assertRaises(LearningError):
            self.review()

    def test_04_review_ac_updates_last_review(self):
        self.finish()
        day = D0 + dt.timedelta(days=7)

        state = self.review(day=day)

        self.assertEqual(state.solved_on, D0)
        self.assertEqual(state.last_review_on, day)
        self.assertEqual(state.last_result, "AC")

    def test_05_failed_review_preserves_solved(self):
        self.finish()
        day = D0 + dt.timedelta(days=7)

        state = self.review(
            score=1,
            day=day,
            result="WA",
        )

        self.assertEqual(state.solved_on, D0)
        self.assertEqual(state.last_review_on, day)
        self.assertEqual(state.last_result, "WA")

    def test_06_recall_0_due_in_one_day(self):
        self.finish(score=0)

        self.assertEqual(
            self.engine.next_due("a001"),
            D0 + dt.timedelta(days=1),
        )

    def test_07_recall_1_due_in_three_days(self):
        self.finish(score=1)

        self.assertEqual(
            self.engine.next_due("a001"),
            D0 + dt.timedelta(days=3),
        )

    def test_08_recall_2_due_in_seven_days(self):
        self.finish(score=2)

        self.assertEqual(
            self.engine.next_due("a001"),
            D0 + dt.timedelta(days=7),
        )

    def test_09_finish_recall_3_due_in_30_days(self):
        self.finish(score=3)

        self.assertEqual(
            self.engine.next_due("a001"),
            D0 + dt.timedelta(days=30),
        )

    def test_10_first_review_3_due_in_30_days(self):
        self.finish(score=3)
        d1 = D0 + dt.timedelta(days=30)
        self.review(score=3, day=d1)

        self.assertEqual(
            self.engine.review_streak_3("a001"),
            1,
        )
        self.assertEqual(
            self.engine.next_due("a001"),
            d1 + dt.timedelta(days=30),
        )

    def test_11_second_distinct_review_3_due_in_60_days(self):
        self.finish(score=3)

        d1 = D0 + dt.timedelta(days=30)
        d2 = d1 + dt.timedelta(days=30)

        self.review(score=3, day=d1)
        self.review(score=3, day=d2)

        self.assertEqual(
            self.engine.review_streak_3("a001"),
            2,
        )
        self.assertEqual(
            self.engine.next_due("a001"),
            d2 + dt.timedelta(days=60),
        )

    def test_12_third_distinct_review_3_due_in_90_days(self):
        self.finish(score=3)

        d1 = D0 + dt.timedelta(days=30)
        d2 = d1 + dt.timedelta(days=30)
        d3 = d2 + dt.timedelta(days=60)

        self.review(score=3, day=d1)
        self.review(score=3, day=d2)
        self.review(score=3, day=d3)

        self.assertEqual(
            self.engine.review_streak_3("a001"),
            3,
        )
        self.assertEqual(
            self.engine.next_due("a001"),
            d3 + dt.timedelta(days=90),
        )

    def test_13_same_day_review_3_counts_once(self):
        self.finish(score=3)

        day = D0 + dt.timedelta(days=30)

        self.review(score=3, day=day)
        self.review(score=3, day=day)
        self.review(score=3, day=day)

        self.assertEqual(
            self.engine.review_streak_3("a001"),
            1,
        )

    def test_14_low_recall_breaks_streak(self):
        self.finish(score=3)

        d1 = D0 + dt.timedelta(days=30)
        d2 = d1 + dt.timedelta(days=30)
        d3 = d2 + dt.timedelta(days=60)

        self.review(score=3, day=d1)
        self.review(score=3, day=d2)
        self.review(score=1, day=d3)

        self.assertEqual(
            self.engine.review_streak_3("a001"),
            0,
        )
        self.assertEqual(
            self.engine.next_due("a001"),
            d3 + dt.timedelta(days=3),
        )

    def test_15_failed_review_breaks_streak(self):
        self.finish(score=3)

        d1 = D0 + dt.timedelta(days=30)
        d2 = d1 + dt.timedelta(days=30)

        self.review(score=3, day=d1)
        self.review(
            score=1,
            day=d2,
            result="WA",
        )

        self.assertEqual(
            self.engine.review_streak_3("a001"),
            0,
        )

    def test_16_mastery_states(self):
        self.assertEqual(
            self.engine.mastery("a001"),
            "NEW",
        )

        self.finish(score=1)
        self.assertEqual(
            self.engine.mastery("a001"),
            "LEARNING",
        )

        self.review(
            score=2,
            day=D0 + dt.timedelta(days=3),
        )
        self.assertEqual(
            self.engine.mastery("a001"),
            "PRACTICING",
        )

        d1 = D0 + dt.timedelta(days=10)
        d2 = D0 + dt.timedelta(days=40)
        d3 = D0 + dt.timedelta(days=100)

        self.review(score=3, day=d1)
        self.review(score=3, day=d2)
        self.review(score=3, day=d3)

        self.assertEqual(
            self.engine.mastery("a001"),
            "MASTERED",
        )

    def test_17_due_queue_prioritizes_more_overdue(self):
        self.engine.finish(
            "a001",
            2,
            when=D0,
        )
        self.engine.finish(
            "b001",
            1,
            when=D0 + dt.timedelta(days=5),
        )

        queue = self.engine.due_queue(
            on=D0 + dt.timedelta(days=10)
        )

        self.assertEqual(
            [x.problem_id for x in queue],
            ["a001", "b001"],
        )

    def test_review_before_solved_date_rejected(self):
        self.finish()

        with self.assertRaises(LearningError):
            self.review(
                day=D0 - dt.timedelta(days=1),
            )

    def test_failed_review_cannot_be_recall_3(self):
        self.finish()

        with self.assertRaises(LearningError):
            self.review(
                score=3,
                day=D0 + dt.timedelta(days=7),
                result="WA",
            )


    def test_18_test_store_is_isolated(self):
        self.finish()

        production = (
            Path.cwd()
            / "data"
            / "progress.csv"
        ).resolve()

        test_file = self.store.progress_path.resolve()

        self.assertNotEqual(
            test_file,
            production,
        )
        self.assertTrue(test_file.exists())



    def test_19_finish_transaction_rolls_back(self):
        self.store.ensure()

        before_progress = (
            self.store.progress_path.read_bytes()
        )
        before_reviews = (
            self.store.reviews_path.read_bytes()
        )

        original_write = self.store._write_csv
        calls = {"count": 0}

        def fail_second(path, fields, rows):
            calls["count"] += 1

            if calls["count"] == 2:
                raise OSError(
                    "simulated reviews write failure"
                )

            return original_write(
                path,
                fields,
                rows,
            )

        self.store._write_csv = fail_second

        with self.assertRaises(OSError):
            self.engine.finish(
                "a001",
                2,
                when=D0,
            )

        self.assertEqual(
            self.store.progress_path.read_bytes(),
            before_progress,
        )
        self.assertEqual(
            self.store.reviews_path.read_bytes(),
            before_reviews,
        )

    def test_20_review_transaction_rolls_back(self):
        self.finish()

        before_progress = (
            self.store.progress_path.read_bytes()
        )
        before_reviews = (
            self.store.reviews_path.read_bytes()
        )

        original_write = self.store._write_csv
        calls = {"count": 0}

        def fail_second(path, fields, rows):
            calls["count"] += 1

            if calls["count"] == 2:
                raise OSError(
                    "simulated reviews write failure"
                )

            return original_write(
                path,
                fields,
                rows,
            )

        self.store._write_csv = fail_second

        with self.assertRaises(OSError):
            self.engine.review(
                "a001",
                1,
                result="WA",
                when=D0 + dt.timedelta(days=7),
            )

        self.assertEqual(
            self.store.progress_path.read_bytes(),
            before_progress,
        )
        self.assertEqual(
            self.store.reviews_path.read_bytes(),
            before_reviews,
        )

    def test_21_valid_history_is_consistent(self):
        self.finish(
            score=2,
        )

        self.review(
            score=3,
            day=D0 + dt.timedelta(days=7),
        )

        self.assertEqual(
            self.store.validate_consistency(),
            [],
        )

    def test_22_progress_without_finish_is_detected(self):
        self.store.ensure()

        self.store.save_progress(
            {
                "a001": ProgressState(
                    problem_id="a001",
                    solved_on=D0,
                    last_result="AC",
                    recall=2,
                )
            }
        )

        errors = (
            self.store.validate_consistency()
        )

        self.assertTrue(
            any(
                "缺少 Finish event" in error
                for error in errors
            )
        )

    def test_23_finish_without_progress_is_detected(self):
        self.store.ensure()

        self.store.append_event(
            ReviewEvent(
                problem_id="a001",
                event_type=EVENT_FINISH,
                date=D0,
                score=2,
                result="AC",
            )
        )

        errors = (
            self.store.validate_consistency()
        )

        self.assertTrue(
            any(
                "progress 未標記完成" in error
                for error in errors
            )
        )

    def test_24_snapshot_latest_review_mismatch_detected(self):
        self.finish(
            score=2,
        )

        day = D0 + dt.timedelta(days=7)

        self.review(
            score=3,
            day=day,
        )

        states = self.store.load_progress()
        states["a001"].recall = 1

        self.store.save_progress(
            states
        )

        errors = (
            self.store.validate_consistency()
        )

        self.assertTrue(
            any(
                "最新 event score" in error
                for error in errors
            )
        )

    def test_25_review_without_finish_is_detected(self):
        self.store.ensure()

        self.store.append_event(
            ReviewEvent(
                problem_id="a001",
                event_type=EVENT_REVIEW,
                date=D0,
                score=2,
                result="AC",
            )
        )

        errors = (
            self.store.validate_consistency()
        )

        self.assertTrue(
            any(
                "Review event" in error
                and "缺少 Finish event" in error
                for error in errors
            )
        )

    def test_26_review_cannot_move_backward_in_time(self):
        self.finish()

        later = D0 + dt.timedelta(days=10)

        self.review(
            day=later,
        )

        before_progress = (
            self.store.progress_path.read_bytes()
        )
        before_reviews = (
            self.store.reviews_path.read_bytes()
        )

        with self.assertRaises(LearningError):
            self.review(
                day=D0 + dt.timedelta(days=5),
            )

        self.assertEqual(
            self.store.progress_path.read_bytes(),
            before_progress,
        )
        self.assertEqual(
            self.store.reviews_path.read_bytes(),
            before_reviews,
        )


if __name__ == "__main__":
    unittest.main()
