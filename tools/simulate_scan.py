"""Generate a synthetic FORScan log for a 2000 Ford F-250 7.3L Power Stroke.

Not connected to a real truck - this fabricates FORScan-formatted text so
OBD-Insight (and the Telegram bot) can be exercised end-to-end without a
vehicle attached. DTCs are real, verified 7.3L Power Stroke codes; the VIN,
timestamps, and adapter ID are placeholders.

Usage:
    python tools/simulate_scan.py                       # a representative mix
    python tools/simulate_scan.py --codes P0340,P1211    # pick specific codes
    python tools/simulate_scan.py --clean                # no DTCs at all
    python tools/simulate_scan.py --list                 # show the reference codes
    python tools/simulate_scan.py --out data/sim_run.txt  # write to a file
"""

import argparse
import sys
from datetime import datetime, timedelta

VEHICLE_LINE = "Ford F-250 Super Duty 7.3L Power Stroke DIT 2000 (2000 MY)"
VIN_PLACEHOLDER = "1FT******0YE12345"
ADAPTER_ID = "FTDI #1:D3C3XG6H"

# Real 7.3L Power Stroke DTCs, cross-checked against cararac.com, riffraffdiesel.com,
# and powerstrokenation.com. A 2000 F-250 is an early OBD-II truck - FORScan
# forum reports confirm it typically shows just PCM/OBD2_PCM, none of the
# body/seat/HVAC modules a modern CAN-bus Ford would have.
REFERENCE_DTCS = {
    "P0340": ("PCM", "Camshaft Position Sensor (CPS) circuit malfunction - the classic 7.3 gremlin; causes random stalling and can prevent a hot restart."),
    "P1210": ("PCM", "Injection Control Pressure (ICP) above expected level - the high-pressure oil system is building more pressure than commanded."),
    "P1211": ("PCM", "Injection Control Pressure (ICP) not controllable - pressure reading above or below desired. Check ICP sensor, IPR valve, and HPOP."),
    "P1212": ("PCM", "ICP sensor voltage not at expected level - points to the ICP sensor or its wiring rather than the oil pressure system itself."),
    "P0402": ("PCM", "EGR flow detected as excessive - check the EGR valve and related sensors."),
    "P0480": ("PCM", "Fan 1 control circuit fault - cooling fan clutch/relay circuit issue."),
    "P0500": ("PCM", "Vehicle Speed Sensor (VSS) circuit fault - no or incorrect signal reaching the PCM."),
    "P1000": ("PCM", "OBD-II monitor testing not complete (Not Present) - normal right after a battery disconnect or code clear; needs a drive cycle."),
}

DEFAULT_CODES = ["P0340", "P1211", "P1000"]

# Status text FORScan appends for codes that aren't currently active - e.g.
# P1000 is expected to show as stored/not-present right after a code clear.
CODE_STATUS_SUFFIX = {
    "P1000": " (Not Present)",
}


def build_log(codes):
    """Return FORScan-style log text containing the given DTC codes."""
    t = datetime(2000, 1, 1, 12, 0, 0, 0)
    lines = []

    def emit(status, text, step=timedelta(milliseconds=120)):
        nonlocal t
        t += step
        lines.append(f"({status}) [{t.strftime('%H:%M:%S.%f')[:-3]}] {text}")

    emit("OK", f"Checking {ADAPTER_ID}...")
    emit("OK", f"Connection to adapter has been established: {ADAPTER_ID}")
    emit("OK", "Connection to vehicle has been established")
    emit("OK", f"Vehicle: {VEHICLE_LINE}, VIN: {VIN_PLACEHOLDER}")
    emit("OK", "Found module:  OBD2_PCM - On Board Diagnostic II (PCM)")
    emit("OK", "Found module:  PCM - Powertrain Control Module")

    # Codes with a status annotation (e.g. "Not Present") get their own line.
    # severity.py classifies a DTC using the *entire* raw log line it came
    # from, so codes sharing a line with an annotated one would incorrectly
    # inherit that annotation's classification if combined together.
    plain_codes = [c for c in codes if c not in CODE_STATUS_SUFFIX]
    annotated_codes = [c for c in codes if c in CODE_STATUS_SUFFIX]

    if plain_codes:
        emit("WARN", f"DTCs in PCM: {', '.join(plain_codes)}")
    for code in annotated_codes:
        emit("WARN", f"DTCs in PCM: {code}{CODE_STATUS_SUFFIX[code]}")

    emit("OK", "Disconnected", step=timedelta(seconds=48))
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--codes", help="Comma-separated DTCs to include (default: a representative mix)")
    parser.add_argument("--clean", action="store_true", help="Generate a scan with no DTCs found")
    parser.add_argument("--list", action="store_true", help="List the available reference DTCs and exit")
    parser.add_argument("--out", help="Write the log to this file instead of stdout")
    args = parser.parse_args()

    if args.list:
        for code, (module, description) in REFERENCE_DTCS.items():
            print(f"{code} ({module}): {description}")
        return

    if args.clean:
        codes = []
    elif args.codes:
        codes = [c.strip().upper() for c in args.codes.split(",") if c.strip()]
        unknown = [c for c in codes if c not in REFERENCE_DTCS]
        if unknown:
            print(f"Unknown code(s), not in reference list: {', '.join(unknown)}", file=sys.stderr)
            print("Run with --list to see available codes.", file=sys.stderr)
            sys.exit(1)
    else:
        codes = DEFAULT_CODES

    log_text = build_log(codes)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(log_text)
        print(f"Wrote simulated scan ({len(codes)} DTC(s)) to {args.out}")
    else:
        print(log_text, end="")


if __name__ == "__main__":
    main()
