"""Tests for the 2000 F-250 7.3L Power Stroke FORScan log simulator."""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from simulate_scan import DEFAULT_CODES, REFERENCE_DTCS, build_log  # noqa: E402
from parser import parse_scan_session  # noqa: E402
from severity import classify_severity  # noqa: E402


class SimulateScanTests(unittest.TestCase):
    def test_default_log_parses_into_expected_vehicle_and_modules(self):
        session = parse_scan_session(build_log(DEFAULT_CODES))
        self.assertEqual(session["vehicle"]["vehicle"], "Ford F-250 Super Duty 7.3L Power Stroke DIT 2000 (2000 MY)")
        self.assertEqual([m["id"] for m in session["modules"]], ["OBD2_PCM", "PCM"])

    def test_default_log_contains_expected_codes(self):
        session = parse_scan_session(build_log(DEFAULT_CODES))
        codes = {dtc["code"] for dtc in session["dtcs"]}
        self.assertEqual(codes, set(DEFAULT_CODES))

    def test_clean_log_has_no_dtcs(self):
        session = parse_scan_session(build_log([]))
        self.assertEqual(session["dtcs"], [])

    def test_annotated_code_does_not_contaminate_active_codes_on_same_scan(self):
        # P1000 carries a "(Not Present)" annotation; make sure it stays on
        # its own line and doesn't drag genuinely active codes down to
        # Informational just because they were generated in the same run.
        session = parse_scan_session(build_log(["P0340", "P1211", "P1000"]))
        severities = {
            dtc["code"]: classify_severity(dtc["module"], dtc["code"], raw_line=dtc["raw_line"])
            for dtc in session["dtcs"]
        }
        self.assertEqual(severities["P0340"], "Critical")
        self.assertEqual(severities["P1211"], "Critical")
        self.assertEqual(severities["P1000"], "Informational")

    def test_all_reference_codes_produce_parseable_dtcs(self):
        all_codes = list(REFERENCE_DTCS.keys())
        session = parse_scan_session(build_log(all_codes))
        self.assertEqual({dtc["code"] for dtc in session["dtcs"]}, set(all_codes))


if __name__ == "__main__":
    unittest.main()
