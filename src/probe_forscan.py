"""Inspect what Windows exposes from an open FORScan application."""

from forscan_reader import ForscanReaderError, inspect_open_forscan


def format_rectangle(rectangle):
    return (
        f"({rectangle.left}, {rectangle.top}) - "
        f"({rectangle.right}, {rectangle.bottom}) "
        f"[{rectangle.width}x{rectangle.height}]"
    )


def print_control(control, indent="    "):
    print(
        f"{indent}#{control.index} "
        f"{control.control_type or 'Unknown'} | "
        f"{control.class_name or 'Unknown'} | "
        f"abs={format_rectangle(control.rectangle)} | "
        f"rel={format_rectangle(control.relative_rectangle)}"
    )
    print(f"{indent}  {control.label}")


def main():
    print("OBD-Insight FORScan read-only probe")
    print("This does not click or change anything in FORScan.\n")

    found_window = False
    for backend in ("uia", "win32"):
        print(f"Checking Windows backend: {backend}")
        try:
            inspection = inspect_open_forscan(backend=backend)
        except ForscanReaderError as error:
            print(f"  {error}\n")
            continue

        found_window = True
        print(f"  Window: {inspection.window_title}")
        print(f"  Window rectangle: {format_rectangle(inspection.window_rectangle)}")
        print(f"  Total descendants reported by Windows: {inspection.total_descendants}")
        print(f"  Controls inspected by this probe: {len(inspection.controls)}")
        print(f"  Possible log controls: {len(inspection.log_candidates)}")
        print(f"  Controls near bottom toolbar: {len(inspection.controls_near_bottom)}")
        print(f"  Small controls in bottom 100 px: {len(inspection.small_bottom_controls)}")

        for control in inspection.log_candidates:
            preview = " ".join(control.text.split())[:240]
            print(
                f"  Candidate #{control.index}: "
                f"type={control.control_type or 'Unknown'}, "
                f"class={control.class_name or 'Unknown'}"
            )
            print(f"    abs={format_rectangle(control.rectangle)}")
            print(f"    rel={format_rectangle(control.relative_rectangle)}")
            print(f"    {preview}")

        if not inspection.log_candidates:
            print("  No Vehicle, Found module, or DTC text was exposed.")

        print("  Controls near the bottom toolbar region:")
        for control in inspection.controls_near_bottom:
            print_control(control)

        print("  Small controls in the bottom 100 pixels:")
        for control in inspection.small_bottom_controls:
            print_control(control)

        print("  All inspected descendants:")
        for control in inspection.controls:
            print_control(control)
        print()

    if not found_window:
        print("Open FORScan, leave its Log tab visible, and run this probe again.")


if __name__ == "__main__":
    main()
