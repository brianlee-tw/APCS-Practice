import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from tools import apcs_control as ui


class MenuRenderingUiTest(unittest.TestCase):
    def test_cursor_move_redraw_clears_full_visible_terminal(self):
        keys = iter(["DOWN", "q"])
        output = io.StringIO()

        with (
            patch.object(ui, "read_key", side_effect=lambda: next(keys)),
            redirect_stdout(output),
        ):
            result = ui.choose_menu(
                "測試",
                [
                    {
                        "label": "較長的第一個選項",
                        "detail": "這一行刻意比下一個選項長，用來覆蓋殘影情境。",
                        "enabled": True,
                    },
                    {
                        "label": "短",
                        "detail": "短",
                        "enabled": True,
                    },
                ],
            )

        self.assertIsNone(result)
        rendered = output.getvalue()

        # Initial frame + redraw after DOWN.  Every frame must clear the
        # visible terminal before repainting; HOME-only redraw leaves stale
        # text when a previous frame wrapped/scrolled or had longer lines.
        self.assertEqual(
            rendered.count("\033[2J\033[H"),
            2,
        )
        self.assertEqual(
            rendered.count("\033[H"),
            2,
        )


if __name__ == "__main__":
    unittest.main()
