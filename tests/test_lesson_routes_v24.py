import io
import json
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import tools.apcs_control as control
from tools.lesson_routes import (
    LessonRouteError,
    LessonRouteStore,
    NOTION_PAGE_URL_RE,
)
from tools.runtime_curriculum import RuntimeCurriculum


ROOT = Path(__file__).resolve().parents[1]
ROUTES_PATH = ROOT / "curriculum" / "lesson_routes.v24.json"
PUBLISHED_PATH = ROOT / "curriculum" / "published.v23.json"


def placement(
    *,
    lesson_uid="L-FND-01",
    role="Guided Drill",
    placement_uid="PL-TEST-L-FND-01",
):
    return types.SimpleNamespace(
        placement_uid=placement_uid,
        pb_uid="PB-TEST",
        problem_id="d050",
        title="測試題",
        url="https://zerojudge.tw/ShowProblem?problemid=d050",
        difficulty="D1",
        primary_skill="S01_IO",
        supporting_skills=(),
        role=role,
        lesson_uid=lesson_uid,
        lesson_order=1,
    )


def route(p):
    return types.SimpleNamespace(
        skill=types.SimpleNamespace(
            uid="S01_IO",
            name="I/O、型別與運算式",
            unit="U-FND",
            path_stage="Foundation",
        ),
        placement=p,
        status="NEW",
        skill_evidence=None,
        why_now="Published Curriculum 的下一個 ready Skill。",
        prerequisites=(),
        blocked_skill=None,
        blocked_by=(),
        route_complete=False,
    )


class LessonRouteProjectionV24Test(unittest.TestCase):
    def test_projection_is_routing_only_and_covers_52_main_lessons(self):
        raw = json.loads(
            ROUTES_PATH.read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            set(raw),
            {
                "schema_version",
                "captured_on",
                "source_authority",
                "source_root",
                "purpose",
                "routes",
            },
        )
        self.assertEqual(
            raw["schema_version"],
            "apcs-lesson-routes-v1",
        )
        self.assertIn(
            "Routing-only projection",
            raw["purpose"],
        )
        self.assertIn(
            "Notion remains Lesson authority",
            raw["purpose"],
        )

        routes = raw["routes"]
        self.assertEqual(
            len(routes),
            52,
        )
        self.assertEqual(
            len(set(routes.values())),
            52,
        )
        self.assertIn(
            "L-MIX-04",
            routes,
        )

        for uid, url in routes.items():
            self.assertRegex(
                uid,
                r"^L-[A-Z]{2,3}-\d{2}$",
            )
            self.assertRegex(
                url,
                NOTION_PAGE_URL_RE,
            )

    def test_every_published_placement_lesson_resolves(self):
        store = LessonRouteStore(
            ROUTES_PATH
        )
        curriculum = RuntimeCurriculum(
            PUBLISHED_PATH
        )

        missing = sorted(
            {
                item.lesson_uid
                for item in curriculum.all_placements()
                if (
                    item.lesson_uid
                    and store.resolve(
                        item.lesson_uid
                    )
                    is None
                )
            }
        )

        self.assertEqual(
            missing,
            [],
        )

    def test_unknown_lesson_never_guesses_url(self):
        store = LessonRouteStore(
            ROUTES_PATH
        )

        self.assertIsNone(
            store.resolve(
                "L-FND-99"
            )
        )
        self.assertIsNone(
            store.resolve(
                "../../L-FND-01"
            )
        )

    def test_invalid_projection_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            path = (
                Path(temp)
                / "routes.json"
            )
            path.write_text(
                json.dumps(
                    {
                        "schema_version": (
                            "apcs-lesson-routes-v1"
                        ),
                        "routes": {
                            "L-FND-01": (
                                "https://example.invalid/"
                                "guessed"
                            )
                        },
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(
                LessonRouteError
            ):
                LessonRouteStore(
                    path
                ).load()


class LessonRouteWorkbenchV24Test(unittest.TestCase):
    def test_reading_new_learning_opens_canonical_notion_before_scratch(self):
        p = placement()
        lesson_url = (
            "https://app.notion.com/p/"
            "3c743be958cd81c6808dc1215f600a0c"
        )
        scratch = Path(
            "/tmp/reading-response.md"
        )

        with (
            patch.object(
                control.LESSON_ROUTES,
                "resolve",
                return_value=lesson_url,
            ),
            patch.object(
                control.webbrowser,
                "open",
                return_value=True,
            ) as open_browser,
            patch.object(
                control,
                "create_reading_scratch",
                return_value=scratch,
            ) as create_reading,
            patch.object(
                control,
                "open_in_vscode",
                return_value=True,
            ),
            patch.object(
                control,
                "pause",
            ),
            redirect_stdout(
                io.StringIO()
            ),
        ):
            result = (
                control._start_new_learning(
                    route(p),
                    "current.cpp",
                    track="Reading",
                )
            )

        open_browser.assert_called_once_with(
            lesson_url
        )
        create_reading.assert_called_once()
        self.assertEqual(
            result,
            str(scratch),
        )

    def test_reading_missing_lesson_route_fails_safe_without_guessing(self):
        p = placement(
            lesson_uid="L-FND-99"
        )

        output = io.StringIO()
        with (
            patch.object(
                control.LESSON_ROUTES,
                "resolve",
                return_value=None,
            ),
            patch.object(
                control.webbrowser,
                "open",
            ) as open_browser,
            patch.object(
                control,
                "create_reading_scratch",
            ) as create_reading,
            patch.object(
                control,
                "pause",
            ),
            redirect_stdout(output),
        ):
            result = (
                control._start_new_learning(
                    route(p),
                    "current.cpp",
                    track="Reading",
                )
            )

        open_browser.assert_not_called()
        create_reading.assert_not_called()
        self.assertEqual(
            result,
            "current.cpp",
        )
        rendered = output.getvalue()
        self.assertIn(
            "L-FND-99",
            rendered,
        )
        self.assertIn(
            "未猜測 URL",
            rendered,
        )
        self.assertIn(
            "Reading 已安全停止",
            rendered,
        )
        self.assertIn(
            "Implementation 仍可",
            rendered,
        )

    def test_implementation_continues_when_lesson_route_is_missing(self):
        p = placement()
        scratch = Path(
            "/tmp/implementation.cpp"
        )

        with (
            patch.object(
                control,
                "create_learning_scratch",
                return_value=scratch,
            ) as create_learning,
            patch.object(
                control,
                "open_in_vscode",
                return_value=True,
            ),
            patch.object(
                control,
                "pause",
            ),
            redirect_stdout(
                io.StringIO()
            ),
        ):
            result = (
                control._start_new_learning(
                    route(p),
                    "current.cpp",
                    track="Implementation",
                )
            )

        create_learning.assert_called_once_with(
            p
        )
        self.assertEqual(
            result,
            str(scratch),
        )

    def test_implementation_scratch_links_lesson_context_without_copying_content(self):
        p = placement()
        lesson_url = (
            "https://app.notion.com/p/"
            "3c743be958cd81c6808dc1215f600a0c"
        )

        with tempfile.TemporaryDirectory() as temp:
            with (
                patch.object(
                    control,
                    "RUNTIME_DIR",
                    Path(temp),
                ),
                patch.object(
                    control.LESSON_ROUTES,
                    "resolve",
                    return_value=lesson_url,
                ),
            ):
                scratch = (
                    control.create_learning_scratch(
                        p
                    )
                )

            text = scratch.read_text(
                encoding="utf-8"
            )

        self.assertIn(
            "// Lesson: L-FND-01",
            text,
        )
        self.assertIn(
            f"// Lesson context: {lesson_url}",
            text,
        )
        self.assertNotIn(
            "Worked Example",
            text,
        )

    def test_strict_spoiler_scratch_does_not_expose_lesson_route(self):
        p = placement(
            role="Transfer Challenge",
            placement_uid="PL-TRANSFER",
        )
        lesson_url = (
            "https://app.notion.com/p/"
            "3c743be958cd81c6808dc1215f600a0c"
        )

        with tempfile.TemporaryDirectory() as temp:
            with (
                patch.object(
                    control,
                    "RUNTIME_DIR",
                    Path(temp),
                ),
                patch.object(
                    control.LESSON_ROUTES,
                    "resolve",
                    return_value=lesson_url,
                ) as resolve,
            ):
                scratch = (
                    control.create_learning_scratch(
                        p
                    )
                )

            text = scratch.read_text(
                encoding="utf-8"
            )

        resolve.assert_not_called()
        self.assertNotIn(
            "Lesson context:",
            text,
        )
        self.assertNotIn(
            "L-FND-01",
            text,
        )


if __name__ == "__main__":
    unittest.main()
