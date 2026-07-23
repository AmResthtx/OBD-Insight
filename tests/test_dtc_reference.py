"""Tests for the Telegram bot's plain-English DTC explanations."""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "telegram_bot"))

from dtc_reference import explain  # noqa: E402


class DtcReferenceTests(unittest.TestCase):
    def test_known_code_returns_specific_explanation(self):
        self.assertIn("misfire", explain("P0300").lower())

    def test_known_code_with_suffix_matches_base_code(self):
        self.assertIn("Body Control Module", explain("B115E:55-0A"))

    def test_unknown_powertrain_code_falls_back_to_category(self):
        self.assertIn("Powertrain", explain("P0999"))

    def test_unknown_body_code_falls_back_to_category(self):
        self.assertIn("Body", explain("B9999"))

    def test_empty_code_returns_placeholder(self):
        self.assertEqual(explain(""), "No code provided.")


if __name__ == "__main__":
    unittest.main()
