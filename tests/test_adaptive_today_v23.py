import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tools.adaptive_memory import MemoryPolicy
from tools.evidence_outbox import (
    EvidenceOutbox,
    build_envelope,
)
from tools.runtime_curriculum import (
    PlacementContext,
    RuntimeCurriculum,
)
from tools.skill_memory_store import (
    SkillMemoryStore,
)
import tools.apcs_control as control


TZ = dt.timezone(dt.timedelta(hours=8))
DAY0 = dt.datetime(2026, 9, 1, 18, 0, tzinfo=TZ)


def make_envelope(
    *,
    writeback_id,
    problem_id,
    skill_uid,
    finished_at,
):
    return build_envelope(
        problem_id=problem_id,
        pb_uid=f"PB-{problem_id}",
        started_at=None,
        finished_at=finished_at,
        language="cpp",
        judge_result="AC",
        assistance=0,
        independent=True,
        attempt_count=1,
        active_minutes=12,
        timed=False,
        novelty="transfer",
        activity="Core Independent",
        evidence=[
            (
                skill_uid,
                "Implementation",
                "PASS",
                "",
            )
        ],
        attempt_id=f"att_{writeback_id}",
        writeback_id=writeback_id,
        created_at=finished_at,
    )


class AdaptiveTodayV23Test(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.runtime = self.root / ".apcs" / "runtime"
        self.snapshot = self.root / "published.v23.json"

        self.outbox = EvidenceOutbox(
            self.runtime
        )
        self.memory = SkillMemoryStore(
            self.runtime
            / "skill_memory.json"
        )

    def tearDown(self):
        self.temp.cleanup()

    def write_curriculum(self):
        self.snapshot.write_text(
            json.dumps(
                {
                    "schema_version": "v2.3-published-1",
                    "contract_version": "v2.3-draft-0",
                    "curriculum_version": "fixture",
                    "skills": [
                        {
                            "uid": "S22_Prefix_Sum",
                            "name": "Prefix Sum",
                            "unit": "U-PFX",
                            "path_stage": "Bridge",
                            "path_order": 22,
                            "relevance": {
                                "3+3": "Required",
                                "5+5": "Required",
                            },
                        }
                    ],
                    "problems": [
                        {
                            "pb_uid": "PB-a693",
                            "problem_id": "a693",
                            "title": "Prefix Sum A",
                            "url": "https://example.invalid/a693",
                            "difficulty": "D2",
                        },
                        {
                            "pb_uid": "PB-b001",
                            "problem_id": "b001",
                            "title": "Prefix Sum Transfer",
                            "url": "https://example.invalid/b001",
                            "difficulty": "D2",
                        },
                    ],
                    "placements": [
                        {
                            "placement_uid": "PL-OLD",
                            "pb_uid": "PB-a693",
                            "primary_skill": "S22_Prefix_Sum",
                            "supporting_skills": [],
                            "role": "Core Independent",
                            "lesson_uid": "L-PFX-01",
                            "lesson_order": 1,
                        },
                        {
                            "placement_uid": "PL-FRESH",
                            "pb_uid": "PB-b001",
                            "primary_skill": "S22_Prefix_Sum",
                            "supporting_skills": [],
                            "role": "Transfer Challenge",
                            "lesson_uid": "L-PFX-01",
                            "lesson_order": 2,
                        },
                    ],
                    "stats": {},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def test_missing_published_curriculum_surfaces_new_learning_blocker(self):
        missing = RuntimeCurriculum(
            self.root / "missing-published.v23.json"
        )

        with (
            patch.object(
                control,
                "OUTBOX",
                self.outbox,
            ),
            patch.object(
                control,
                "MEMORY",
                self.memory,
            ),
            patch.object(
                control,
                "CURRICULUM",
                missing,
            ),
        ):
            snapshot = (
                control.adaptive_today_snapshot(
                    on_date=dt.date(
                        2026,
                        10,
                        1,
                    ),
                    total_capacity_minutes=60,
                )
            )

        self.assertEqual(
            snapshot[
                "curriculum_blocker"
            ],
            "Published curriculum snapshot 尚未建立。",
        )
        self.assertEqual(
            snapshot[
                "plan"
            ].budget_minutes,
            18,
        )

    def test_today_surfaces_new_learning_even_without_memory(self):
        self.write_curriculum()

        with (
            patch.object(
                control,
                "OUTBOX",
                self.outbox,
            ),
            patch.object(
                control,
                "MEMORY",
                self.memory,
            ),
            patch.object(
                control,
                "CURRICULUM",
                RuntimeCurriculum(
                    self.snapshot
                ),
            ),
        ):
            snapshot = (
                control.adaptive_today_snapshot(
                    on_date=dt.date(
                        2026,
                        10,
                        1,
                    ),
                    total_capacity_minutes=60,
                )
            )

        self.assertEqual(
            snapshot["memory_count"],
            0,
        )
        self.assertIsNotNone(
            snapshot["new_learning"],
        )
        self.assertEqual(
            snapshot[
                "new_learning"
            ].skill.uid,
            "S22_Prefix_Sum",
        )
        self.assertEqual(
            snapshot[
                "new_learning"
            ].status,
            "Ready",
        )
        self.assertIsNone(
            snapshot[
                "curriculum_blocker"
            ]
        )

    def test_adaptive_today_reconciles_evidence_and_selects_due_skill(self):
        self.write_curriculum()

        self.outbox.enqueue(
            make_envelope(
                writeback_id="wb1",
                problem_id="a693",
                skill_uid="S22_Prefix_Sum",
                finished_at=DAY0,
            )
        )

        with (
            patch.object(
                control,
                "OUTBOX",
                self.outbox,
            ),
            patch.object(
                control,
                "MEMORY",
                self.memory,
            ),
            patch.object(
                control,
                "CURRICULUM",
                RuntimeCurriculum(
                    self.snapshot
                ),
            ),
        ):
            snapshot = (
                control.adaptive_today_snapshot(
                    on_date=dt.date(
                        2026,
                        10,
                        1,
                    ),
                    total_capacity_minutes=60,
                )
            )

        self.assertEqual(
            snapshot["due_count"],
            1,
        )
        self.assertEqual(
            snapshot["memory_count"],
            1,
        )
        self.assertEqual(
            snapshot["plan"].budget_minutes,
            18,
        )
        self.assertEqual(
            len(
                snapshot[
                    "plan"
                ].selected
            ),
            1,
        )
        self.assertEqual(
            snapshot[
                "plan"
            ].selected[0].importance,
            "required",
        )
        self.assertIsNone(
            snapshot[
                "curriculum_blocker"
            ]
        )

    def test_review_placement_prefers_unattempted_transfer(self):
        self.write_curriculum()

        self.outbox.enqueue(
            make_envelope(
                writeback_id="wb_old",
                problem_id="a693",
                skill_uid="S22_Prefix_Sum",
                finished_at=DAY0,
            )
        )

        with (
            patch.object(
                control,
                "OUTBOX",
                self.outbox,
            ),
            patch.object(
                control,
                "CURRICULUM",
                RuntimeCurriculum(
                    self.snapshot
                ),
            ),
        ):
            placement = (
                control
                .review_placement_for_skill(
                    "S22_Prefix_Sum",
                    track="Implementation",
                )
            )

        self.assertIsNotNone(
            placement
        )
        self.assertEqual(
            placement.problem_id,
            "b001",
        )
        self.assertEqual(
            placement.role,
            "Transfer Challenge",
        )

    def test_review_scratch_is_blank_and_keeps_placement_identity(self):
        placement = PlacementContext(
            placement_uid="PL-FRESH",
            pb_uid="PB-b001",
            problem_id="b001",
            title="Prefix Sum Transfer",
            url="https://example.invalid/b001",
            difficulty="D2",
            primary_skill="S22_Prefix_Sum",
            supporting_skills=(),
            role="Transfer Challenge",
            lesson_uid="L-PFX-01",
            lesson_order=2,
        )

        with patch.object(
            control,
            "RUNTIME_DIR",
            self.runtime,
        ):
            path = (
                control.create_review_scratch(
                    placement
                )
            )

        text = path.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "S22_Prefix_Sum",
            text,
        )
        self.assertIn(
            "https://example.invalid/b001",
            text,
        )
        self.assertIn(
            "int main()",
            text,
        )
        self.assertNotIn(
            "Prefix Sum solution",
            text,
        )
        self.assertIn(
            "__PL-FRESH.cpp",
            path.name,
        )

    def test_current_problem_preserves_review_scratch_and_placement(self):
        folder = self.runtime / "review" / "2026-10-01"
        folder.mkdir(
            parents=True,
            exist_ok=True,
        )
        scratch = (
            folder
            / "b001__PL-FRESH.cpp"
        )
        scratch.write_text(
            "int main() {}\n",
            encoding="utf-8",
        )

        historical = (
            self.root
            / "solutions"
            / "b001.cpp"
        )

        primary = SimpleNamespace(
            path=historical,
            title="Prefix Sum Transfer",
        )
        solution = SimpleNamespace(
            path=historical,
        )

        row = (
            "b001",
            [solution],
            primary,
            None,
            None,
            None,
        )

        with patch.object(
            control,
            "all_rows",
            return_value=[row],
        ):
            current = control.current_problem(
                str(scratch)
            )

        self.assertEqual(
            current["id"],
            "b001",
        )
        self.assertEqual(
            current["placement_uid"],
            "PL-FRESH",
        )
        self.assertEqual(
            Path(
                current["path"]
            ).resolve(),
            scratch.resolve(),
        )

    def test_session_capacity_is_bounded(self):
        with patch.dict(
            "os.environ",
            {
                "APCS_SESSION_MINUTES": "5",
            },
            clear=False,
        ):
            self.assertEqual(
                control.session_capacity_minutes(),
                15,
            )

        with patch.dict(
            "os.environ",
            {
                "APCS_SESSION_MINUTES": "999",
            },
            clear=False,
        ):
            self.assertEqual(
                control.session_capacity_minutes(),
                240,
            )

        with patch.dict(
            "os.environ",
            {
                "APCS_SESSION_MINUTES": "bad",
            },
            clear=False,
        ):
            self.assertEqual(
                control.session_capacity_minutes(),
                60,
            )


if __name__ == "__main__":
    unittest.main()
