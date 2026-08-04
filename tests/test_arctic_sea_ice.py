import unittest
from pathlib import Path

from arctic_collector.errors import ArcticCollectorError
from arctic_collector.sea_ice import parse_nsidc_csv


FIXTURE = Path(__file__).parent / "fixtures" / "nsidc_sea_ice.csv"


class SeaIceTests(unittest.TestCase):
    def test_parses_units_latest_and_sorted_daily_rows(self):
        result = parse_nsidc_csv(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(result["latest"]["date"], "2026-08-02")
        self.assertEqual(result["latest"]["extent"], 6.123)
        self.assertEqual(result["latest"]["unit"], "10^6 sq km")
        self.assertEqual([row["date"] for row in result["daily"]], ["2025-12-31", "2026-01-01", "2026-08-02"])
        self.assertNotIn("nsr", result)

    def test_retains_latest_observation_count(self):
        result = parse_nsidc_csv(FIXTURE.read_text(encoding="utf-8"), retain_days=2)
        self.assertEqual([row["date"] for row in result["daily"]], ["2026-01-01", "2026-08-02"])

    def test_rejects_duplicate_and_non_numeric_rows(self):
        base = FIXTURE.read_text(encoding="utf-8")
        with self.assertRaises(ArcticCollectorError):
            parse_nsidc_csv(base + "2026, 08, 02, 6.100, 0.000, duplicate\n")
        with self.assertRaises(ArcticCollectorError):
            parse_nsidc_csv(base.replace("6.123", "not-a-number"))


if __name__ == "__main__":
    unittest.main()
