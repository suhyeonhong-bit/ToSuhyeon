import unittest

from collector.errors import CollectorError
from collector.transform import merge_monthly


class MergeMonthlyTests(unittest.TestCase):
    def test_merges_month_union_in_chronological_order(self):
        ecos_values = {
            "2026-05": "2.5",
            "2026-06": "2.5",
        }
        fred_values = {
            "2026-04": "355.2",
            "2026-05": "359.100",
        }

        rows = merge_monthly(ecos_values, fred_values)

        self.assertEqual(
            rows,
            [
                {
                    "month": "2026-04",
                    "korea_base_rate_percent": "",
                    "us_steel_ppi_index": "355.2",
                },
                {
                    "month": "2026-05",
                    "korea_base_rate_percent": "2.5",
                    "us_steel_ppi_index": "359.100",
                },
                {
                    "month": "2026-06",
                    "korea_base_rate_percent": "2.5",
                    "us_steel_ppi_index": "",
                },
            ],
        )

    def test_none_becomes_empty_csv_value(self):
        rows = merge_monthly(
            {"2026-06": None},
            {"2026-06": "361.439"},
        )

        self.assertEqual(rows[0]["korea_base_rate_percent"], "")
        self.assertEqual(rows[0]["us_steel_ppi_index"], "361.439")

    def test_empty_inputs_are_rejected(self):
        with self.assertRaises(CollectorError):
            merge_monthly({}, {})


if __name__ == "__main__":
    unittest.main()
