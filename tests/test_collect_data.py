import io
import unittest
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

import collect_data
from collector.config import Config
from collector.dates import CollectionRange
from collector.errors import CollectorError


class CollectDataTests(unittest.TestCase):
    def test_run_orchestrates_sources_and_saves_outputs(self):
        project_root = Path("/tmp/tosuhyeon-test")
        date_range = CollectionRange(
            start_month="202107",
            end_month="202607",
            start_date="2021-07-01",
            end_date="2026-07-30",
        )
        fred_payload = {"observations": []}
        ecos_payload = {"StatisticSearch": {"row": []}}
        fred_values = {"2026-06": "361.439"}
        ecos_values = {"2026-06": "2.5"}
        merged_rows = [
            {
                "month": "2026-06",
                "korea_base_rate_percent": "2.5",
                "us_steel_ppi_index": "361.439",
                "us_fed_target_rate_percent": "4.125",
            }
        ]

        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    "collect_data.load_config",
                    return_value=Config("fred-secret", "ecos-secret"),
                )
            )
            stack.enter_context(
                patch(
                    "collect_data.calculate_collection_range",
                    return_value=date_range,
                )
            )
            fetch_fred = stack.enter_context(
                patch(
                    "collect_data.fetch_fred",
                    side_effect=[
                        (fred_payload, '{"observations": []}'),
                        (fred_payload, '{"observations": []}'),
                        (fred_payload, '{"observations": []}'),
                    ],
                )
            )
            stack.enter_context(
                patch(
                    "collect_data.parse_fred",
                    side_effect=[
                        fred_values,
                        {"2026-06": "4.25"},
                        {"2026-06": "4.00"},
                    ],
                )
            )
            stack.enter_context(
                patch(
                    "collect_data.calculate_target_rate",
                    return_value={"2026-06": "4.125"},
                )
            )
            stack.enter_context(
                patch(
                    "collect_data.fetch_ecos",
                    return_value=(
                        ecos_payload,
                        '{"StatisticSearch": {"row": []}}',
                    ),
                )
            )
            stack.enter_context(
                patch(
                    "collect_data.parse_ecos",
                    return_value=ecos_values,
                )
            )
            stack.enter_context(
                patch(
                    "collect_data.merge_monthly",
                    return_value=merged_rows,
                )
            )
            save_raw = stack.enter_context(
                patch(
                    "collect_data.save_raw_response",
                    side_effect=[
                        project_root / "data/raw/fred_steel.json",
                        project_root / "data/raw/fred_upper.json",
                        project_root / "data/raw/fred_lower.json",
                        project_root / "data/raw/ecos.json",
                    ],
                )
            )
            save_csv = stack.enter_context(
                patch(
                    "collect_data.save_csv",
                    return_value=project_root
                    / "data/processed/monthly_indicators.csv",
                )
            )
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = collect_data.run(
                    project_root,
                    today=date(2026, 7, 30),
                    now=datetime(2026, 7, 30, 2, 0, tzinfo=timezone.utc),
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(fetch_fred.call_count, 3)
        self.assertEqual(save_raw.call_count, 4)
        save_csv.assert_called_once_with(
            project_root / "data/processed/monthly_indicators.csv",
            merged_rows,
        )
        text = output.getvalue()
        self.assertIn("[1/6]", text)
        self.assertIn("FRED 철강 PPI 1건", text)
        self.assertIn("ECOS 기준금리 1건", text)
        self.assertIn("monthly_indicators.csv", text)
        self.assertNotIn("fred-secret", text)
        self.assertNotIn("ecos-secret", text)

    def test_main_returns_one_and_prints_safe_error(self):
        error_output = io.StringIO()
        with patch(
            "collect_data.run",
            side_effect=CollectorError("수집 실패: 안전한 오류"),
        ):
            with redirect_stderr(error_output):
                exit_code = collect_data.main()

        self.assertEqual(exit_code, 1)
        self.assertEqual(error_output.getvalue(), "수집 실패: 안전한 오류\n")

    def test_default_collection_date_uses_korean_calendar_month(self):
        project_root = Path("/tmp/tosuhyeon-test")
        korean_month_start = datetime(
            2026,
            7,
            31,
            15,
            30,
            tzinfo=timezone.utc,
        )

        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    "collect_data.load_config",
                    return_value=Config("fred-secret", "ecos-secret"),
                )
            )
            fetch_fred = stack.enter_context(
                patch(
                    "collect_data.fetch_fred",
                    side_effect=[
                        ({"observations": []}, "{}"),
                        ({"observations": []}, "{}"),
                        ({"observations": []}, "{}"),
                    ],
                )
            )
            stack.enter_context(
                patch("collect_data.parse_fred", return_value={"2026-06": "1"})
            )
            stack.enter_context(
                patch(
                    "collect_data.fetch_ecos",
                    return_value=({"StatisticSearch": {"row": []}}, "{}"),
                )
            )
            stack.enter_context(patch("collect_data.parse_ecos", return_value={}))
            stack.enter_context(patch("collect_data.merge_monthly", return_value=[]))
            stack.enter_context(patch("collect_data.save_raw_response"))
            stack.enter_context(patch("collect_data.save_csv"))

            collect_data.run(project_root, now=korean_month_start)

        self.assertEqual(
            fetch_fred.call_args.args[1],
            CollectionRange(
                start_month="202108",
                end_month="202608",
                start_date="2021-08-01",
                end_date="2026-08-01",
            ),
        )


if __name__ == "__main__":
    unittest.main()
