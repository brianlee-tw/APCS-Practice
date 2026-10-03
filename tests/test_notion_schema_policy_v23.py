import datetime as dt
import json
import unittest
from pathlib import Path

from tools.evidence_outbox import build_envelope
from tools.notion_schema_policy import (
    forbidden_projection_fields,
    validate_projection_fields,
)
from tools.remote_writeback import (
    build_remote_writeback_bundle,
    notion_projection,
)


ROOT = Path(__file__).resolve().parents[1]
TZ = dt.timezone(dt.timedelta(hours=8))
FINISHED = dt.datetime(
    2026,
    10,
    3,
    9,
    30,
    tzinfo=TZ,
)


class NotionSchemaPolicyV23Test(unittest.TestCase):
    def test_policy_declares_forbidden_write_boundaries(self):
        self.assertTrue(
            {
                "進度狀態",
                "複習日期",
            }.issubset(
                forbidden_projection_fields(
                    "rec"
                )
            )
        )
        self.assertEqual(
            forbidden_projection_fields(
                "ev"
            ),
            frozenset(
                {
                    "Delay Days",
                    "Valid for Gate",
                }
            ),
        )

    def test_policy_validator_fails_closed(self):
        with self.assertRaisesRegex(
            ValueError,
            "forbidden Notion field",
        ):
            validate_projection_fields(
                surface="rec",
                properties={
                    "Writeback ID": "wb-test",
                    "進度狀態": "已完成",
                },
            )

    def test_current_remote_projection_respects_policy(self):
        envelope = build_envelope(
            problem_id="ZJ-d067",
            pb_uid="PB-182",
            started_at=None,
            finished_at=FINISHED,
            language="cpp",
            judge_result="AC",
            assistance=0,
            independent=True,
            active_minutes=8,
            timed=False,
            novelty="new",
            activity="Core Independent",
            evidence=[
                (
                    "S02_Conditionals",
                    "Implementation",
                    "PASS",
                    "condition logic",
                )
            ],
            attempt_id="att-schema-policy",
            writeback_id="wb-schema-policy",
            created_at=FINISHED,
        )
        projection = notion_projection(
            build_remote_writeback_bundle(
                envelope
            )
        )

        rec_fields = set(
            projection["rec"][
                "properties"
            ]
        )
        self.assertFalse(
            rec_fields
            & forbidden_projection_fields(
                "rec"
            )
        )

        for row in projection["evidence"]:
            self.assertFalse(
                set(row["properties"])
                & forbidden_projection_fields(
                    "ev"
                )
            )

    def test_published_skill_contract_excludes_manual_learner_state(self):
        published = json.loads(
            (
                ROOT
                / "curriculum"
                / "published.v23.json"
            ).read_text(
                encoding="utf-8"
            )
        )
        forbidden = {
            "RM",
            "IM",
            "Skill Status",
            "Reading Milestone",
            "Implementation Milestone",
        }

        for skill in published["skills"]:
            self.assertFalse(
                forbidden
                & set(skill)
            )


if __name__ == "__main__":
    unittest.main()
