import codecs
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from collector.errors import CollectorError
from collector.storage import save_csv, save_raw_response


class StorageTests(unittest.TestCase):
    def test_saves_raw_response_with_deterministic_name(self):
        with tempfile.TemporaryDirectory() as directory:
            raw_dir = Path(directory) / "raw"

            output_path = save_raw_response(
                raw_dir=raw_dir,
                source="fred",
                raw_text='{"observations": []}',
                secrets=("fred-secret", "ecos-secret"),
                run_id="20260730T020000Z",
            )

            self.assertEqual(
                output_path.name,
                "fred_WPU1017_20260730T020000Z.json",
            )
            self.assertEqual(
                output_path.read_text(encoding="utf-8"),
                '{"observations": []}',
            )

    def test_refuses_to_store_a_secret(self):
        with tempfile.TemporaryDirectory() as directory:
            raw_dir = Path(directory) / "raw"

            with self.assertRaisesRegex(CollectorError, "비밀 키"):
                save_raw_response(
                    raw_dir=raw_dir,
                    source="ecos",
                    raw_text='{"message": "ecos-secret"}',
                    secrets=("fred-secret", "ecos-secret"),
                    run_id="20260730T020000Z",
                )

            self.assertFalse(raw_dir.exists())

    def test_csv_has_bom_header_and_missing_value(self):
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "monthly_indicators.csv"
            rows = [
                {
                    "month": "2026-06",
                    "korea_base_rate_percent": "2.5",
                    "us_steel_ppi_index": "",
                    "us_fed_target_rate_percent": "",
                }
            ]

            save_csv(output_path, rows)

            raw_bytes = output_path.read_bytes()
            self.assertTrue(raw_bytes.startswith(codecs.BOM_UTF8))
            self.assertEqual(
                raw_bytes.decode("utf-8-sig"),
                "month,korea_base_rate_percent,us_steel_ppi_index,us_fed_target_rate_percent\r\n"
                "2026-06,2.5,,\r\n",
            )

    def test_failed_replace_preserves_existing_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "monthly_indicators.csv"
            output_path.write_text("old-data\n", encoding="utf-8")

            with patch(
                "collector.storage.os.replace",
                side_effect=OSError("disk error"),
            ):
                with self.assertRaises(CollectorError):
                    save_csv(
                        output_path,
                        [
                            {
                                "month": "2026-06",
                                "korea_base_rate_percent": "2.5",
                                "us_steel_ppi_index": "361.439",
                                "us_fed_target_rate_percent": "",
                            }
                        ],
                    )

            self.assertEqual(
                output_path.read_text(encoding="utf-8"),
                "old-data\n",
            )


if __name__ == "__main__":
    unittest.main()
