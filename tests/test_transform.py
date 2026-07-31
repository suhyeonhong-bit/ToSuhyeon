import unittest

from collector.errors import CollectorError
from collector.transform import calculate_target_rate, merge_monthly


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
        fed_values = {"2026-05": "4.125"}

        rows = merge_monthly(ecos_values, fred_values, fed_values)

        self.assertEqual(
            rows,
            [
                {
                    "month": "2026-04",
                    "korea_base_rate_percent": "",
                    "us_steel_ppi_index": "355.2",
                    "us_fed_target_rate_percent": "",
                },
                {
                    "month": "2026-05",
                    "korea_base_rate_percent": "2.5",
                    "us_steel_ppi_index": "359.100",
                    "us_fed_target_rate_percent": "4.125",
                },
                {
                    "month": "2026-06",
                    "korea_base_rate_percent": "2.5",
                    "us_steel_ppi_index": "",
                    "us_fed_target_rate_percent": "",
                },
            ],
        )

    def test_none_becomes_empty_csv_value(self):
        rows = merge_monthly(
            {"2026-06": None},
            {"2026-06": "361.439"},
            {"2026-06": None},
        )

        self.assertEqual(rows[0]["korea_base_rate_percent"], "")
        self.assertEqual(rows[0]["us_steel_ppi_index"], "361.439")
        self.assertEqual(rows[0]["us_fed_target_rate_percent"], "")

    def test_empty_inputs_are_rejected(self):
        with self.assertRaises(CollectorError):
            merge_monthly({}, {}, {})


class TargetRateTests(unittest.TestCase):
    def test_calculates_midpoints_for_months_present_in_both_bounds(self):
        self.assertEqual(
            calculate_target_rate(
                {"2026-05": "4.25", "2026-06": "4.125"},
                {"2026-05": "4.00", "2026-06": "4.000"},
            ),
            {"2026-05": "4.125", "2026-06": "4.0625"},
        )

    def test_missing_bound_produces_none(self):
        self.assertEqual(
            calculate_target_rate(
                {"2026-05": "4.25", "2026-06": None},
                {"2026-05": "4.00", "2026-06": "4.00"},
            ),
            {"2026-05": "4.125", "2026-06": None},
        )

    def test_empty_usable_result_is_rejected(self):
        with self.assertRaises(CollectorError):
            calculate_target_rate({"2026-05": None}, {"2026-05": None})


if __name__ == "__main__":
    unittest.main()
