"""Read-only inspection helpers for an open FORScan window."""

from dataclasses import dataclass


FORSCAN_LOG_MARKERS = ("vehicle:", "found module:", "dtcs in ")


class ForscanReaderError(RuntimeError):
    """Base error for FORScan window inspection."""


class ForscanNotFoundError(ForscanReaderError):
    """Raised when no open FORScan window can be found."""


class ForscanDependencyError(ForscanReaderError):
    """Raised when the Windows inspection dependency is unavailable."""


@dataclass
class RectangleInfo:
    """Safe rectangle details for a window or control."""

    left: int = 0
    top: int = 0
    right: int = 0
    bottom: int = 0

    @property
    def width(self):
        return max(0, self.right - self.left)

    @property
    def height(self):
        return max(0, self.bottom - self.top)

    def relative_to(self, other):
        return RectangleInfo(
            left=self.left - other.left,
            top=self.top - other.top,
            right=self.right - other.left,
            bottom=self.bottom - other.top,
        )

    def is_small(self, max_width=120, max_height=60):
        return self.width <= max_width and self.height <= max_height


@dataclass
class ControlInfo:
    """Safe diagnostic information exposed by one Windows control."""

    index: int
    control_type: str
    class_name: str
    automation_id: str
    name: str
    text: str
    rectangle: RectangleInfo
    relative_rectangle: RectangleInfo

    @property
    def contains_log_data(self):
        return looks_like_forscan_log(self.text)

    @property
    def label(self):
        return self.name or " ".join(self.text.split())[:80] or "(no text)"


@dataclass
class ForscanInspection:
    """Read-only snapshot of one FORScan window's exposed controls."""

    backend: str
    window_title: str
    window_rectangle: RectangleInfo
    total_descendants: int
    controls: list

    @property
    def log_candidates(self):
        return [control for control in self.controls if control.contains_log_data]

    @property
    def controls_near_bottom(self):
        cutoff = max(0, self.window_rectangle.height - 140)
        return [
            control
            for control in self.controls
            if control.relative_rectangle.bottom >= cutoff
        ]

    @property
    def small_bottom_controls(self):
        cutoff = max(0, self.window_rectangle.height - 100)
        return [
            control
            for control in self.controls
            if control.relative_rectangle.top >= cutoff
            and control.rectangle.is_small()
        ]


def is_forscan_window_title(title):
    """Return True for a likely FORScan top-level window title."""
    normalized = (title or "").strip().casefold()
    return "forscan" in normalized and "obd-insight" not in normalized


def looks_like_forscan_log(text):
    """Return True when exposed text contains a useful FORScan Log marker."""
    normalized = (text or "").casefold()
    return any(marker in normalized for marker in FORSCAN_LOG_MARKERS)


def inspect_open_forscan(backend="uia", max_controls=2000):
    """Inspect controls exposed by an open FORScan window without clicking it."""
    window = find_open_forscan_window(backend=backend)
    window_title = _safe_control_text(window) or "FORScan"
    window_rectangle = _extract_rectangle(window)
    descendants = list(window.descendants())
    total_descendants = len(descendants)
    controls = []

    for index, control in enumerate(descendants[:max_controls], start=1):
        element = getattr(control, "element_info", None)
        rectangle = _extract_rectangle(control)
        controls.append(
            ControlInfo(
                index=index,
                control_type=_safe_attribute(element, "control_type"),
                class_name=_safe_attribute(element, "class_name"),
                automation_id=_safe_attribute(element, "automation_id"),
                name=_safe_attribute(element, "name"),
                text=_extract_control_text(control),
                rectangle=rectangle,
                relative_rectangle=rectangle.relative_to(window_rectangle),
            )
        )

    return ForscanInspection(
        backend=backend,
        window_title=window_title,
        window_rectangle=window_rectangle,
        total_descendants=total_descendants,
        controls=controls,
    )


def find_open_forscan_window(backend="uia"):
    """Return the first matching open FORScan top-level window."""
    Desktop = _load_desktop()
    desktop = Desktop(backend=backend)
    windows = [
        window
        for window in desktop.windows()
        if is_forscan_window_title(_safe_control_text(window))
    ]
    if not windows:
        raise ForscanNotFoundError(
            f"No open FORScan window was found with the {backend!r} backend."
        )
    return windows[0]


def _load_desktop():
    try:
        from pywinauto import Desktop
    except ImportError as error:
        raise ForscanDependencyError(
            "pywinauto is not installed. Run: pip install -r requirements.txt"
        ) from error
    return Desktop


def _extract_control_text(control):
    values = []

    window_text = _safe_call(control, "window_text")
    if window_text:
        values.append(window_text)

    texts = _safe_call(control, "texts")
    if isinstance(texts, (list, tuple)):
        values.extend(text for text in texts if isinstance(text, str) and text)

    legacy_properties = _safe_call(control, "legacy_properties")
    if isinstance(legacy_properties, dict):
        legacy_value = legacy_properties.get("Value")
        if legacy_value:
            values.append(str(legacy_value))

    unique_values = []
    for value in values:
        cleaned = str(value).strip()
        if cleaned and cleaned not in unique_values:
            unique_values.append(cleaned)

    return "\n".join(unique_values)


def _safe_control_text(control):
    return _safe_call(control, "window_text") or ""


def _extract_rectangle(control):
    rectangle = _safe_call(control, "rectangle")
    if not rectangle:
        return RectangleInfo()

    return RectangleInfo(
        left=_safe_int_attribute(rectangle, "left"),
        top=_safe_int_attribute(rectangle, "top"),
        right=_safe_int_attribute(rectangle, "right"),
        bottom=_safe_int_attribute(rectangle, "bottom"),
    )


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
