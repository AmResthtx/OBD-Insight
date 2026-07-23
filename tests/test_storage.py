"""Tests for the Telegram bot's cross-scan history tracking."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "telegram_bot"))

from storage import is_premium, record_scan, set_premium  # noqa: E402


class StorageTests(unittest.TestCase):
    def setUp(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(path)
        self.db_path = path

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_first_scan_marks_everything_new(self):
        dtcs = [{"module": "PCM", "code": "P0300"}]
        tracked = record_scan(self.db_path, 1, "vin123", dtcs)
        self.assertEqual(tracked[0]["status"], "new")

    def test_code_seen_in_consecutive_scans_is_repeated(self):
        dtcs = [{"module": "PCM", "code": "P0300"}]
        record_scan(self.db_path, 1, "vin123", dtcs)
        tracked = record_scan(self.db_path, 1, "vin123", dtcs)
        self.assertEqual(tracked[0]["status"], "repeated")

    def test_code_missing_then_reappearing_is_returning(self):
        dtcs = [{"module": "PCM", "code": "P0300"}]
        other = [{"module": "BdyCM", "code": "B1000"}]
        record_scan(self.db_path, 1, "vin123", dtcs)
        record_scan(self.db_path, 1, "vin123", other)
        tracked = record_scan(self.db_path, 1, "vin123", dtcs)
        self.assertEqual(tracked[0]["status"], "returning")

    def test_different_users_have_independent_history(self):
        dtcs = [{"module": "PCM", "code": "P0300"}]
        record_scan(self.db_path, 1, "vin123", dtcs)
        tracked = record_scan(self.db_path, 2, "vin123", dtcs)
        self.assertEqual(tracked[0]["status"], "new")

    def test_different_vehicles_for_same_user_are_independent(self):
        dtcs = [{"module": "PCM", "code": "P0300"}]
        record_scan(self.db_path, 1, "vinA", dtcs)
        tracked = record_scan(self.db_path, 1, "vinB", dtcs)
        self.assertEqual(tracked[0]["status"], "new")

    def test_premium_status_defaults_false_then_activates(self):
        self.assertFalse(is_premium(self.db_path, 42))
        set_premium(self.db_path, 42, days=30)
        self.assertTrue(is_premium(self.db_path, 42))

    def test_premium_status_expires_in_the_past(self):
        set_premium(self.db_path, 7, days=-1)
        self.assertFalse(is_premium(self.db_path, 7))


if __name__ == "__main__":
    unittest.main()
