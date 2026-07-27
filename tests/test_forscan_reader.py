"""Tests for read-only FORScan window detection helpers."""

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from forscan_reader import ControlInfo, ForscanInspection, RectangleInfo  # noqa: E402
from forscan_reader import is_forscan_window_title, looks_like_forscan_log  # noqa: E402


class ForscanReaderTests(unittest.TestCase):
    def test_forscan_window_title_is_recognized(self):
        self.assertTrue(is_forscan_window_title("FORScan 2.3.64 release"))
        self.assertFalse(is_forscan_window_title("OBD-Insight"))
        self.assertFalse(is_forscan_window_title("Notepad"))

    def test_log_markers_are_recognized(self):
        self.assertTrue(looks_like_forscan_log("Vehicle: Lincoln MKX"))
        self.assertTrue(looks_like_forscan_log("Found module: APIM - Interface"))
        self.assertTrue(looks_like_forscan_log("DTCs in DSM: B2312-60"))
        self.assertFalse(looks_like_forscan_log("Connection established"))

    def test_inspection_returns_only_log_candidates(self):
        window = RectangleInfo(100, 100, 900, 700)
        log_control = ControlInfo(
            1,
            "Document",
            "",
            "log",
            "",
            "Vehicle: MKX",
            RectangleInfo(120, 140, 880, 600),
            RectangleInfo(20, 40, 780, 500),
        )
        button_control = ControlInfo(
            2,
            "Button",
            "",
            "scan",
            "Scan",
            "Scan",
            RectangleInfo(120, 630, 180, 660),
            RectangleInfo(20, 530, 80, 560),
        )
        inspection = ForscanInspection("uia", "FORScan", window, 2, [log_control, button_control])

        self.assertEqual(inspection.log_candidates, [log_control])

    def test_bottom_toolbar_filters_use_relative_position_and_size(self):
        window = RectangleInfo(50, 50, 850, 650)
        toolbar_button = ControlInfo(
            1,
            "Button",
            "FXWindow",
            "",
            "",
            "",
            RectangleInfo(60, 575, 110, 605),
            RectangleInfo(10, 525, 60, 555),
        )
        large_bottom_panel = ControlInfo(
            2,
            "Pane",
            "FXWindow",
            "",
            "",
            "",
            RectangleInfo(55, 560, 845, 640),
            RectangleInfo(5, 510, 795, 590),
        )
        upper_control = ControlInfo(
            3,
            "Pane",
            "FXWindow",
            "",
            "",
            "",
            RectangleInfo(60, 120, 260, 300),
            RectangleInfo(10, 70, 210, 250),
        )
        inspection = ForscanInspection(
            "win32",
            "FORScan",
            window,
            3,
            [toolbar_button, large_bottom_panel, upper_control],
        )

        self.assertEqual(
            inspection.controls_near_bottom,
            [toolbar_button, large_bottom_panel],
        )
        self.assertEqual(inspection.small_bottom_controls, [toolbar_button])


if __name__ == "__main__":
    unittest.main()
