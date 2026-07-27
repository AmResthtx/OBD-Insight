"""Tests for local folder-based vehicle scan history."""

import json
import shutil
import sys
import unittest
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from history import save_scan_to_history  # noqa: E402


class HistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.real_log = (PROJECT_ROOT / "data" / "forscan.txt").read_text(
            encoding="utf-8"
        )

    def setUp(self):
        self.test_dir = PROJECT_ROOT / ".test-history-data" / self._testMethodName
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir(parents=True)

    def tearDown(self):
        test_root = PROJECT_ROOT / ".test-history-data"
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        if test_root.exists() and not any(test_root.iterdir()):
            test_root.rmdir()

    def test_scan_is_saved_under_its_vehicle(self):
        result = save_scan_to_history(
            self.real_log,
            data_dir=self.test_dir,
            scanned_at=datetime(2026, 7, 26, 19, 42, 9),
        )

        self.assertTrue(result.created)
        self.assertEqual(result.vehicle_folder.name, "Lincoln-MKX-18750")
        self.assertEqual(
            result.scan_path.parent,
            self.test_dir / "vehicles" / "Lincoln-MKX-18750" / "scans",
        )
        self.assertTrue(result.scan_path.name.startswith("2026-07-26_194209_"))
        self.assertTrue(result.scan_path.exists())
        self.assertTrue((self.test_dir / "incoming").is_dir())

        vehicle_data = json.loads(
            (result.vehicle_folder / "vehicle.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            vehicle_data["vehicle"],
            "Lincoln MKX TiVCT 3.7L 2012 ( 2012 MY )",
        )
        self.assertEqual(vehicle_data["vin"], "2LM*********18750")

    def test_same_scan_is_not_saved_twice(self):
        first = save_scan_to_history(
            self.real_log,
            data_dir=self.test_dir,
            scanned_at=datetime(2026, 7, 26, 19, 42, 9),
        )
        second = save_scan_to_history(
            self.real_log,
            data_dir=self.test_dir,
            scanned_at=datetime(2026, 7, 27, 12, 0, 0),
        )

        self.assertTrue(first.created)
        self.assertFalse(second.created)
        self.assertEqual(second.scan_path, first.scan_path)
        self.assertEqual(len(list(first.scan_path.parent.glob("*.txt"))), 1)


if __name__ == "__main__":
    unittest.main()
