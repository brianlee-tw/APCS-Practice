import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from pathlib import Path

from tools import apcs_control as ui


class TagSelectorUiTest(unittest.TestCase):
    def test_group_toggle_keeps_cursor_and_can_save(self):
        selected = {"Basic Syntax"}
        kept = set()

        keys = iter([
            "DOWN",
            "ENTER",
            "ENTER",
            "s",
        ])

        with (
            patch.object(ui, "read_key", side_effect=lambda: next(keys)),
            patch.object(ui, "clear"),
            redirect_stdout(io.StringIO()),
        ):
            result = ui._tag_group_menu(
                "基礎",
                ["Basic Syntax", "I/O"],
                selected,
                kept,
            )

        self.assertEqual(result, "save")
        self.assertEqual(selected, {"Basic Syntax"})

    def test_selector_has_explicit_save_entry(self):
        keys = iter(["7", "ENTER"])

        with (
            patch.object(ui, "read_key", side_effect=lambda: next(keys)),
            patch.object(ui, "clear"),
            redirect_stdout(io.StringIO()),
        ):
            result = ui.tag_selector(
                "Basic Syntax",
                required=True,
            )

        self.assertEqual(result, "Basic Syntax")

    def test_selector_save_shortcut(self):
        keys = iter(["s"])

        with (
            patch.object(ui, "read_key", side_effect=lambda: next(keys)),
            patch.object(ui, "clear"),
            redirect_stdout(io.StringIO()),
        ):
            result = ui.tag_selector(
                "Basic Syntax, Math Theory"
            )

        self.assertEqual(
            result,
            "Basic Syntax, Math Theory",
        )


    def test_save_semantics_are_explicit(self):
        source = Path(
            "tools/apcs_control.py"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "完成 Tags 選擇",
            source,
        )
        self.assertIn(
            "以上內容尚未寫入 Catalog",
            source,
        )
        self.assertIn(
            "確認儲存全部 metadata？",
            source,
        )
        self.assertIn(
            "metadata 已成功寫入 Catalog",
            source,
        )
        self.assertNotIn(
            "S 完成並儲存",
            source,
        )



if __name__ == "__main__":
    unittest.main()
