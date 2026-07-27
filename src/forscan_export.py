"""FORScan Log export automation isolated from parsing and analysis."""

import time
from pathlib import Path

from forscan_reader import (
    ForscanDependencyError,
    RectangleInfo,
    find_open_forscan_window,
    inspect_open_forscan,
)
from history import DEFAULT_DATA_DIR


SAVE_LOG_BUTTON_RECT = RectangleInfo(248, 1070, 294, 1102)
SAVE_LOG_BUTTON_TOLERANCE = 18


class ForscanExportError(RuntimeError):
    """Base error for FORScan export automation."""


class ForscanLogTabUnavailableError(ForscanExportError):
    """Raised when the expected Log tab toolbar cannot be confirmed."""


class ForscanSaveDialogError(ForscanExportError):
    """Raised when the Windows Save As dialog never appears."""


class ForscanSaveTimeoutError(ForscanExportError):
    """Raised when an exported FORScan file is not written in time."""


class ForscanClearLogDetectedError(ForscanExportError):
    """Raised when FORScan opened a clear-log confirmation instead of Save."""


def build_incoming_scan_path(data_dir=None, filename="latest_forscan.txt"):
    """Return the controlled temporary export path in the incoming folder."""
    data_dir = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
    return data_dir / "incoming" / filename


def export_open_forscan_log(destination_path, timeout_seconds=15, backend="win32"):
    """Export the current FORScan Log tab to a controlled file path."""
    destination_path = Path(destination_path)
    destination_path.parent.mkdir(parents=True, exist_ok=True)

    inspection = inspect_open_forscan(backend=backend, max_controls=2000)
    save_button = find_save_log_button(inspection)
    window = find_open_forscan_window(backend=backend)

    _focus_forscan_window(window)
    _click_save_log_button(save_button)

    desktop, keyboard = _load_desktop_and_keyboard()
    dialog = _wait_for_export_dialog(desktop, keyboard, timeout_seconds)
    _enter_save_path(dialog, destination_path)
    _confirm_save(dialog, keyboard)
    _confirm_overwrite_if_needed(desktop, keyboard, timeout_seconds)
    _wait_for_written_file(destination_path, timeout_seconds)

    return destination_path


def find_save_log_button(inspection):
    """Return the bottom-toolbar control that best matches Save Log."""
    candidates = [
        control
        for control in inspection.small_bottom_controls
        if _looks_like_toolbar_button(control.relative_rectangle)
    ]
    if not candidates:
        raise ForscanLogTabUnavailableError(
            "FORScan was found, but the Log tab toolbar buttons were not available."
        )

    ordered_buttons = _distinct_toolbar_buttons(candidates)
    if len(ordered_buttons) >= 4:
        return ordered_buttons[3]

    return min(
        ordered_buttons,
        key=lambda control: _save_button_distance(control.relative_rectangle),
    )


def cleanup_incoming_scan(path):
    """Best-effort cleanup for the temporary incoming export file."""
    path = Path(path)
    try:
        if path.exists():
            path.unlink()
    except OSError:
        return False
    return True


def _looks_like_toolbar_button(rectangle):
    return (
        30 <= rectangle.width <= 60
        and 24 <= rectangle.height <= 40
        and rectangle.top >= SAVE_LOG_BUTTON_RECT.top - SAVE_LOG_BUTTON_TOLERANCE
        and rectangle.bottom <= SAVE_LOG_BUTTON_RECT.bottom + SAVE_LOG_BUTTON_TOLERANCE
    )


def _save_button_distance(rectangle):
    return (
        abs(rectangle.left - SAVE_LOG_BUTTON_RECT.left)
        + abs(rectangle.top - SAVE_LOG_BUTTON_RECT.top)
        + abs(rectangle.width - SAVE_LOG_BUTTON_RECT.width)
        + abs(rectangle.height - SAVE_LOG_BUTTON_RECT.height)
    )


def _focus_forscan_window(window):
    _safe_call(window, "set_focus")


def _click_save_log_button(control):
    _, _, mouse = _load_pywinauto_components()
    center_x = control.rectangle.left + int(control.rectangle.width * 0.75)
    center_y = control.rectangle.top + (control.rectangle.height // 2)
    mouse.click(button="left", coords=(center_x, center_y))


def _wait_for_export_dialog(desktop, keyboard, timeout_seconds):
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        clear_dialog = _find_clear_log_dialog(desktop)
        if clear_dialog is not None:
            _dismiss_dialog(clear_dialog, keyboard, {"no", "&no", "cancel", "&cancel"})
            raise ForscanClearLogDetectedError(
                "FORScan opened a clear-log confirmation instead of Save Log. "
                "OBD-Insight cancelled it so your log was not cleared."
            )

        dialog = _find_save_dialog(desktop)
        if dialog is not None:
            return dialog
        time.sleep(0.2)

    raise ForscanSaveDialogError(
        "FORScan Save to file did not appear. Keep FORScan open on the Log tab and try again."
    )


def _find_save_dialog(desktop):
    for window in desktop.windows():
        if _is_probable_save_dialog(window):
            return window
    return None


def _enter_save_path(dialog, destination_path):
    _safe_call(dialog, "set_focus")
    edit = _find_filename_edit(dialog)
    if edit is not None:
        set_edit_text = getattr(edit, "set_edit_text", None)
        if callable(set_edit_text):
            try:
                set_edit_text(str(destination_path))
                return
            except Exception:
                pass
        set_window_text = getattr(edit, "set_window_text", None)
        if callable(set_window_text):
            try:
                set_window_text(str(destination_path))
                return
            except Exception:
                pass
        type_keys = getattr(edit, "type_keys", None)
        if callable(type_keys):
            try:
                type_keys("^a{BACKSPACE}", set_foreground=False)
                type_keys(str(destination_path), with_spaces=True, set_foreground=False)
                return
            except Exception:
                pass

    _click_filename_box(dialog)
    _, keyboard, _ = _load_pywinauto_components()
    keyboard.send_keys("^a", pause=0.05)
    time.sleep(0.1)
    keyboard.send_keys(str(destination_path), with_spaces=True, pause=0.01)


def _find_filename_edit(dialog):
    descendants = _safe_call(dialog, "descendants") or []
    edit_controls = []
    for control in descendants:
        element = getattr(control, "element_info", None)
        class_name = _safe_attribute(element, "class_name").casefold()
        control_type = _safe_attribute(element, "control_type").casefold()
        if class_name == "edit" or control_type == "edit":
            edit_controls.append(control)
    if not edit_controls:
        return None

    scored_controls = []
    for control in edit_controls:
        rectangle = _control_rectangle(control)
        score = (
            1 if rectangle.width >= 180 else 0,
            1 if rectangle.top >= 180 else 0,
            -rectangle.top,
            rectangle.width,
        )
        scored_controls.append((score, control))

    scored_controls.sort(reverse=True, key=lambda item: item[0])
    return scored_controls[0][1]


def _click_filename_box(dialog):
    dialog_rect = _control_rectangle(dialog)
    _, _, mouse = _load_pywinauto_components()
    target_x = dialog_rect.left + max(120, int(dialog_rect.width * 0.36))
    target_y = dialog_rect.top + max(220, int(dialog_rect.height * 0.83))
    mouse.click(button="left", coords=(target_x, target_y))
    time.sleep(0.1)


def _confirm_save(dialog, keyboard):
    _safe_call(dialog, "set_focus")
    save_button = _find_dialog_button(dialog, {"save", "&save", "ok", "&ok"})
    if save_button is not None:
        _safe_call(save_button, "click")
        return

    keyboard.send_keys("{ENTER}", pause=0.05)


def _confirm_overwrite_if_needed(desktop, keyboard, timeout_seconds):
    deadline = time.monotonic() + min(timeout_seconds, 5)
    while time.monotonic() < deadline:
        dialog = _find_overwrite_dialog(desktop)
        if dialog is None:
            time.sleep(0.1)
            continue

        yes_button = _find_dialog_button(dialog, {"yes", "&yes", "replace"})
        if yes_button is not None:
            _safe_call(yes_button, "click")
        else:
            keyboard.send_keys("%y", pause=0.05)
        return


def _find_overwrite_dialog(desktop):
    overwrite_titles = {
        "confirm save as",
        "confirm file replace",
        "save as",
    }
    for window in desktop.windows():
        title = (_safe_call(window, "window_text") or "").strip().casefold()
        if title in overwrite_titles:
            buttons = _dialog_button_texts(window)
            if {"yes", "&yes", "replace"}.intersection(buttons):
                return window
    return None


def _find_clear_log_dialog(desktop):
    for window in desktop.windows():
        title = (_safe_call(window, "window_text") or "").strip().casefold()
        if "clear" in title and "log" in title:
            return window
        texts = _dialog_texts(window)
        if any("clear the log" in text for text in texts):
            return window
    return None


def _is_probable_save_dialog(window):
    title = (_safe_call(window, "window_text") or "").strip().casefold()
    class_name = _window_class_name(window).casefold()
    if title in ("save as", "save log", "save", "save to file"):
        return True
    if "save" in title and _dialog_has_file_controls(window):
        return True
    if class_name == "#32770" and _dialog_has_file_controls(window):
        return True
    return False


def _dialog_has_file_controls(window):
    descendants = _safe_call(window, "descendants") or []
    has_edit = False
    has_button = False

    for control in descendants:
        element = getattr(control, "element_info", None)
        class_name = _safe_attribute(element, "class_name").casefold()
        control_type = _safe_attribute(element, "control_type").casefold()
        title = _safe_attribute(element, "name").strip().casefold()

        if class_name == "edit" or control_type == "edit":
            has_edit = True
        if class_name == "button" or control_type == "button":
            has_button = True
        if title in {"file name:", "&file name:", "save", "&save"}:
            return True

    return has_edit and has_button


def _find_dialog_button(dialog, accepted_titles):
    for control in _safe_call(dialog, "descendants") or []:
        element = getattr(control, "element_info", None)
        title = _safe_attribute(element, "name").strip().casefold()
        class_name = _safe_attribute(element, "class_name").casefold()
        control_type = _safe_attribute(element, "control_type").casefold()
        if title in accepted_titles and (class_name == "button" or control_type == "button"):
            return control
    return None


def _dialog_button_texts(dialog):
    titles = set()
    for control in _safe_call(dialog, "descendants") or []:
        element = getattr(control, "element_info", None)
        if _safe_attribute(element, "class_name").casefold() != "button":
            continue
        title = _safe_attribute(element, "name").strip().casefold()
        if title:
            titles.add(title)
    return titles


def _dialog_texts(dialog):
    texts = set()
    for control in _safe_call(dialog, "descendants") or []:
        element = getattr(control, "element_info", None)
        title = _safe_attribute(element, "name").strip().casefold()
        if title:
            texts.add(title)
    return texts


def _dismiss_dialog(dialog, keyboard, button_titles):
    button = _find_dialog_button(dialog, button_titles)
    if button is not None:
        _safe_call(button, "click")
        return
    keyboard.send_keys("{ESC}", pause=0.05)


def _distinct_toolbar_buttons(candidates):
    ordered = []
    seen_positions = []
    for control in sorted(candidates, key=lambda item: item.relative_rectangle.left):
        left = control.relative_rectangle.left
        top = control.relative_rectangle.top
        if any(abs(left - seen_left) <= 12 and abs(top - seen_top) <= 8 for seen_left, seen_top in seen_positions):
            continue
        seen_positions.append((left, top))
        ordered.append(control)
    return ordered


def _window_class_name(window):
    element = getattr(window, "element_info", None)
    return _safe_attribute(element, "class_name")


def _control_rectangle(control):
    rectangle = _safe_call(control, "rectangle")
    if rectangle is None:
        return RectangleInfo()

    return RectangleInfo(
        left=_safe_int_attribute(rectangle, "left"),
        top=_safe_int_attribute(rectangle, "top"),
        right=_safe_int_attribute(rectangle, "right"),
        bottom=_safe_int_attribute(rectangle, "bottom"),
    )


def _wait_for_written_file(destination_path, timeout_seconds):
    deadline = time.monotonic() + timeout_seconds
    last_size = None
    stable_reads = 0
    while time.monotonic() < deadline:
        if destination_path.exists():
            current_size = destination_path.stat().st_size
            if current_size > 0 and current_size == last_size:
                stable_reads += 1
            else:
                stable_reads = 0
            last_size = current_size
            if current_size > 0 and stable_reads >= 2:
                return
        time.sleep(0.2)

    raise ForscanSaveTimeoutError(
        f"FORScan did not finish saving {destination_path.name} before timeout."
    )


def _load_desktop_and_keyboard():
    desktop, keyboard, _ = _load_pywinauto_components()
    return desktop, keyboard


def _load_pywinauto_components():
    try:
        from pywinauto import Desktop, keyboard, mouse
    except ImportError as error:
        raise ForscanDependencyError(
            "pywinauto is not installed in this Python environment."
        ) from error
    return Desktop(backend="win32"), keyboard, mouse


def _safe_call(value, method_name):
    try:
        method = getattr(value, method_name, None)
        return method() if method else None
    except Exception:
        return None


def _safe_attribute(value, attribute_name):
    try:
        return str(getattr(value, attribute_name, "") or "")
    except Exception:
        return ""


def _safe_int_attribute(value, attribute_name):
    try:
        return int(getattr(value, attribute_name, 0) or 0)
    except Exception:
        return 0
