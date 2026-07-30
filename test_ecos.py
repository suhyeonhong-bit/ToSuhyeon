import json
import unittest
from pathlib import Path

from collector.dates import CollectionRange
from collector.ecos import fetch_ecos, parse_ecos
from collector.errors import CollectorError


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "ecos_base_rate.json"


class FakeResponse:
    def __init__(self, body: bytes):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return self.body


class EcosTests(unittest.TestCase):
    def setUp(self):
        self.date_range = CollectionRange(
            start_month="202107",
            end_month="202607",
            start_date="2021-07-01",
            end_date="2026-07-30",
        )

    def test_fetch_builds_expected_request_and_returns_raw_text(self):
        captured = {}
        fixture_bytes = FIXTURE_PATH.read_bytes()

        def fake_opener(url, timeout):
            captured["url"] = url
            captured["timeout"] = timeout
            return FakeResponse(fixture_bytes)

        payload, raw_text = fetch_ecos(
            "ecos-test-key",
            self.date_range,
            opener=fake_opener,
        )

        self.assertIn(
            "/StatisticSearch/ecos-test-key/json/kr/1/1000/"
            "722Y001/M/202107/202607/0101000",
            captured["url"],
        )
        self.assertEqual(captured["timeout"], 30)
        self.assertEqual(
            payload["StatisticSearch"]["row"][0]["ITEM_CODE1"],
            "0101000",
        )
        self.assertEqual(raw_text, fixture_bytes.decode("utf-8"))

    def test_parse_returns_monthly_base_rate(self):
        payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

        values = parse_ecos(payload)

        self.assertEqual(
            values,
            {
                "2026-05": "2.5",
                "2026-06": "2.5",
            },
        )

    def test_provider_error_does_not_expose_provider_message(self):
        secret = "ecos-secret-in-provider-message"
        payload = {
            "RESULT": {
                "CODE": "INFO-100",
                "MESSAGE": f"invalid key {secret}",
            }
        }

        with self.assertRaises(CollectorError) as raised:
            parse_ecos(payload)

        message = str(raised.exception)
        self.assertIn("ECOS", message)
        self.assertIn("INFO-100", message)
        self.assertNotIn(secret, message)

    def test_unexpected_item_code_is_rejected(self):
        payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        payload["StatisticSearch"]["row"][0]["ITEM_CODE1"] = "WRONG"

        with self.assertRaisesRegex(CollectorError, "항목"):
            parse_ecos(payload)

    def test_non_finite_numeric_values_are_rejected_safely(self):
        key = "ecos-key-that-must-not-appear"
        for raw_value in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(raw_value=raw_value):
                payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
                payload["api_key"] = key
                payload["StatisticSearch"]["row"][0]["DATA_VALUE"] = raw_value

                with self.assertRaises(CollectorError) as raised:
                    parse_ecos(payload)

                message = str(raised.exception)
                self.assertIn("숫자", message)
                self.assertNotIn(raw_value, message)
                self.assertNotIn(key, message)


if __name__ == "__main__":
    unittest.main()
