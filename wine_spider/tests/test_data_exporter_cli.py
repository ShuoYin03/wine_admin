from __future__ import annotations

import unittest
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.data_exporter.data_exporter import resolve_date_filters


class DataExporterCliTests(unittest.TestCase):
    def test_missing_end_date_does_not_default_to_now(self):
        start_date, end_date = resolve_date_filters(None, None)

        self.assertIsNone(start_date)
        self.assertIsNone(end_date)

    def test_explicit_dates_are_parsed(self):
        start_date, end_date = resolve_date_filters("2020-01-01", "2020-12-31")

        self.assertEqual(start_date, datetime(2020, 1, 1))
        self.assertEqual(end_date, datetime(2020, 12, 31))


if __name__ == "__main__":
    unittest.main()
