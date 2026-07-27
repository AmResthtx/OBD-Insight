"""Tests for isolated FORScan Log export helpers."""

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from forscan_export import (  # noqa: E402
    ForscanClearLogDetectedError,
    ForscanLogTabUnavailableError,
    ForscanSaveTimeoutError,
    SAVE_LOG_BUTTON_RECT,
    _click_filename_box,
    _enter_save_path,
    _find_clear_log_dialog,
    _find_filename_edit,
    _is_probable_save_dialog,
    _wait_for_export_dialog,
    build_incoming_scan_path,
    cleanup_incoming_scan,
    find_save_log_button,
    _wait_for_written_file,
)
from forscan_reader import ControlInfo, ForscanInspection, RectangleInfo  # noqa: E402


class ForscanExportTests(unittest.TestCase):
    def test_build_incoming_scan_path_uses_incoming_folder(self):
        path = build_incoming_scan_path(
            data_dir=PROJECT_ROOT / ".test-export-data",
            filename="manual.txt",
        )

        self.assertEqual(
            path,
            PROJECT_ROOT / ".test-export-data" / "incoming" / "manual.txt",
        )

    def test_find_save_log_button_chooses_fourth_toolbar_button(self):
        inspection = ForscanInspection(
            "win32",
            "FORScan",
            RectangleInfo(0, 0, 1920, 1120),
            4,
            [
                self._toolbar_button(1, 96),
                self._toolbar_button(2, 144),
                self._toolbar_button(3, 200),
                self._toolbar_button(4, SAVE_LOG_BUTTON_RECT.left),
            ],
        )

        save_button = find_save_log_button(inspection)

        self.assertEqual(save_button.index, 4)
        self.assertEqual(
            save_button.relative_rectangle.left,
            SAVE_LOG_BUTTON_RECT.left,
        )

    def test_find_save_log_button_requires_bottom_toolbar_buttons(self):
        inspection = ForscanInspection(
            "win32",
            "FORScan",
            RectangleInfo(0, 0, 1920, 1120),
            1,
            [
                ControlInfo(
                    1,
                    "Pane",
                    "FXWindow",
                    "",
                    "",
                    "",
                    RectangleInfo(100, 100, 600, 300),
                    RectangleInfo(100, 100, 600, 300),
                )
            ],
        )

        with self.assertRaises(ForscanLogTabUnavailableError):
            find_save_log_button(inspection)

    def test_cleanup_incoming_scan_removes_existing_file(self):
        test_file = PROJECT_ROOT / ".test-export-data" / "incoming" / "latest_forscan.txt"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("scan text", encoding="utf-8")

        removed = cleanup_incoming_scan(test_file)

        self.assertTrue(removed)
        self.assertFalse(test_file.exists())

    def test_wait_for_written_file_times_out_when_file_never_appears(self):
        missing_file = PROJECT_ROOT / ".test-export-data" / "incoming" / "missing.txt"

        with self.assertRaises(ForscanSaveTimeoutError):
            _wait_for_written_file(missing_file, timeout_seconds=0.2)

    def test_probable_save_dialog_accepts_standard_dialog_class_with_file_controls(self):
        dialog = FakeWindow(
            title="",
            class_name="#32770",
            descendants=[
                FakeControl("Edit", "Edit", "File name:"),
                FakeControl("Button", "Button", "Save"),
            ],
        )

        self.assertTrue(_is_probable_save_dialog(dialog))

    def test_probable_save_dialog_rejects_unrelated_dialog(self):
        dialog = FakeWindow(
            title="Settings",
            class_name="#32770",
            descendants=[
                FakeControl("Static", "Text", "Theme"),
                FakeControl("Button", "Button", "Close"),
            ],
        )

        self.assertFalse(_is_probable_save_dialog(dialog))

    def test_probable_save_dialog_accepts_save_to_file_title(self):
        dialog = FakeWindow(
            title="Save to file",
            class_name="#32770",
            descendants=[
                FakeControl("Edit", "Edit", "File Name:"),
                FakeControl("Button", "Button", "OK"),
            ],
        )

        self.assertTrue(_is_probable_save_dialog(dialog))

    def test_enter_save_path_falls_back_to_keyboard_when_edit_not_actionable(self):
        dialog = FakeWindow(
            title="Save As",
            class_name="#32770",
            descendants=[FakeEditControl(visible=False)],
        )
        keyboard = FakeKeyboard()
        mouse = FakeMouse()

        original_loader = sys.modules["forscan_export"]._load_pywinauto_components
        sys.modules["forscan_export"]._load_pywinauto_components = (
            lambda: (None, keyboard, mouse)
        )
        try:
            _enter_save_path(dialog, PROJECT_ROOT / "tmp" / "latest_forscan.txt")
        finally:
            sys.modules["forscan_export"]._load_pywinauto_components = original_loader

        self.assertEqual(dialog.focus_calls, 1)
        self.assertEqual(mouse.clicks, [("left", (180, 290))])
        self.assertEqual(
            keyboard.calls,
            [
                ("^a", {"pause": 0.05}),
                (
                    str(PROJECT_ROOT / "tmp" / "latest_forscan.txt"),
                    {"with_spaces": True, "pause": 0.01},
                ),
            ],
        )

    def test_confirm_save_accepts_ok_button(self):
        dialog = FakeWindow(
            title="Save to file",
            class_name="#32770",
            descendants=[FakeControl("Button", "Button", "OK")],
        )
        keyboard = FakeKeyboard()

        sys.modules["forscan_export"]._confirm_save(dialog, keyboard)

        ok_button = dialog.descendants()[0]
        self.assertEqual(ok_button.clicked_buttons, ["OK"])
        self.assertEqual(keyboard.calls, [])

    def test_find_filename_edit_prefers_lower_wide_filename_field(self):
        directory_edit = FakeEditControl(visible=True, rect=(350, 810, 510, 838))
        file_name_edit = FakeEditControl(visible=True, rect=(275, 1020, 635, 1050))
        file_filter_edit = FakeEditControl(visible=True, rect=(365, 1058, 630, 1088))
        dialog = FakeWindow(
            title="Save to file",
            class_name="#32770",
            descendants=[directory_edit, file_name_edit, file_filter_edit],
        )

        chosen = _find_filename_edit(dialog)

        self.assertIs(chosen, file_name_edit)

    def test_click_filename_box_targets_lower_dialog_area(self):
        dialog = FakeWindow(
            title="Save to file",
            class_name="#32770",
            rect=(250, 750, 750, 1100),
        )
        mouse = FakeMouse()

        original_loader = sys.modules["forscan_export"]._load_pywinauto_components
        sys.modules["forscan_export"]._load_pywinauto_components = (
            lambda: (None, None, mouse)
        )
        try:
            _click_filename_box(dialog)
        finally:
            sys.modules["forscan_export"]._load_pywinauto_components = original_loader

        self.assertEqual(
            mouse.clicks,
            [("left", (430, 1040))],
        )

    def test_find_clear_log_dialog_matches_warning_text(self):
        desktop = FakeDesktop(
            [
                FakeWindow(
                    title="FORScan",
                    class_name="#32770",
                    descendants=[
                        FakeControl("Static", "Text", "This action will clear the log"),
                        FakeControl("Button", "Button", "No"),
                    ],
                )
            ]
        )

        dialog = _find_clear_log_dialog(desktop)

        self.assertIsNotNone(dialog)

    def test_wait_for_export_dialog_cancels_clear_log_confirmation(self):
        no_button = FakeControl("Button", "Button", "No")
        clear_dialog = FakeWindow(
            title="FORScan",
            class_name="#32770",
            descendants=[
                FakeControl("Static", "Text", "This action will clear the log"),
                no_button,
            ],
        )
        desktop = FakeDesktop([clear_dialog])
        keyboard = FakeKeyboard()

        with self.assertRaises(ForscanClearLogDetectedError):
            _wait_for_export_dialog(desktop, keyboard, timeout_seconds=0.1)

        self.assertEqual(no_button.clicked_buttons, ["No"])

    def _toolbar_button(self, index, relative_left):
        relative_rect = RectangleInfo(
            relative_left,
            SAVE_LOG_BUTTON_RECT.top,
            relative_left + SAVE_LOG_BUTTON_RECT.width,
            SAVE_LOG_BUTTON_RECT.bottom,
        )
        absolute_rect = RectangleInfo(
            relative_rect.left + 10,
            relative_rect.top + 10,
            relative_rect.right + 10,
            relative_rect.bottom + 10,
        )
        return ControlInfo(
            index,
            "Button",
            "FXWindow",
            "",
            "",
            "",
            absolute_rect,
            relative_rect,
        )


if __name__ == "__main__":
    unittest.main()


class FakeElementInfo:
    def __init__(self, class_name="", control_type="", name=""):
        self.class_name = class_name
        self.control_type = control_type
        self.name = name


class FakeControl:
    def __init__(self, class_name="", control_type="", name=""):
        self.element_info = FakeElementInfo(class_name, control_type, name)
        self.clicked_buttons = []

    def click(self):
        self.clicked_buttons.append(self.element_info.name)


class FakeWindow(FakeControl):
    def __init__(self, title="", class_name="", descendants=None, rect=(0, 0, 500, 350)):
        super().__init__(class_name=class_name, control_type="Window", name=title)
        self._title = title
        self._descendants = list(descendants or [])
        self.rect = rect

    def window_text(self):
        return self._title

    def descendants(self):
        return list(self._descendants)

    def set_focus(self):
        self.focus_calls = getattr(self, "focus_calls", 0) + 1

    def rectangle(self):
        return FakeRectangle(*self.rect)


class FakeEditControl(FakeControl):
    def __init__(self, visible=True, rect=(0, 0, 240, 28)):
        super().__init__(class_name="Edit", control_type="Edit", name="File name:")
        self.visible = visible
        self.rect = rect

    def set_edit_text(self, value):
        if not self.visible:
            raise RuntimeError("ElementNotVisible")
        self.value = value

    def rectangle(self):
        return FakeRectangle(*self.rect)


class FakeRectangle:
    def __init__(self, left, top, right, bottom):
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom


class FakeKeyboard:
    def __init__(self):
        self.calls = []

    def send_keys(self, text, **kwargs):
        self.calls.append((text, kwargs))


class FakeDesktop:
    def __init__(self, windows):
        self._windows = list(windows)

    def windows(self):
        return list(self._windows)


class FakeMouse:
    def __init__(self):
        self.clicks = []

    def click(self, button="left", coords=None):
        self.clicks.append((button, coords))
