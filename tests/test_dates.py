import unittest
from datetime import date

from collector.dates import CollectionRange, calculate_collection_range


class CollectionRangeTests(unittest.TestCase):
    def test_calculates_inclusive_five_year_range(self):
        result = calculate_collection_range(date(2026, 7, 30))

        self.assertEqual(
            result,
            CollectionRange(
                start_month="202107",
                end_month="202607",
                start_date="2021-07-01",
                end_date="2026-07-30",
            ),
        )

    def test_handles_january_without_month_rollover(self):
        result = calculate_collection_range(date(2026, 1, 5))

        self.assertEqual(result.start_month, "202101")
        self.assertEqual(result.end_month, "202601")
        self.assertEqual(result.start_date, "2021-01-01")
        self.assertEqual(result.end_date, "2026-01-05")


if __name__ == "__main__":
    unittest.main()
