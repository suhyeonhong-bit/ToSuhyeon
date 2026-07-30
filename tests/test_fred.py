import json
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from collector.dates import CollectionRange
from collector.errors import CollectorError
from collector.fred import fetch_fred, parse_fred


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "fred_observations.json"


class FakeResponse:
    def __init__(self, body: bytes):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return self.body


class FredTests(unittest.TestCase):
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

        payload, raw_text = fetch_fred(
            "fred-test-key",
            self.date_range,
            opener=fake_opener,
        )

        query = parse_qs(urlparse(captured["url"]).query)
        self.assertEqual(query["series_id"], ["WPU1017"])
        self.assertEqual(query["file_type"], ["json"])
        self.assertEqual(query["observation_start"], ["2021-07-01"])
        self.assertEqual(query["observation_end"], ["2026-07-30"])
        self.assertEqual(query["sort_order"], ["asc"])
        self.assertEqual(query["api_key"], ["fred-test-key"])
        self.assertEqual(captured["timeout"], 30)
        self.assertEqual(payload["observations"][0]["date"], "2026-05-01")
        self.assertEqual(raw_text, fixture_bytes.decode("utf-8"))

    def test_parse_keeps_numeric_text_and_marks_dot_as_missing(self):
        payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

        values = parse_fred(payload)

        self.assertEqual(
            values,
            {
                "2026-05": "359.100",
                "2026-06": None,
            },
        )

    def test_api_error_does_not_expose_provider_message(self):
        secret = "fred-secret-in-provider-message"
        body = json.dumps(
            {
                "error_code": 400,
                "error_message": f"invalid key {secret}",
            }
        ).encode("utf-8")

        with self.assertRaises(CollectorError) as raised:
            fetch_fred(
                secret,
                self.date_range,
                opener=lambda url, timeout: FakeResponse(body),
            )

        message = str(raised.exception)
        self.assertIn("FRED", message)
        self.assertIn("400", message)
        self.assertNotIn(secret, message)

    def test_invalid_numeric_value_is_rejected(self):
        payload = {
            "observations": [
                {
                    "date": "2026-06-01",
                    "value": "not-a-number",
                }
            ]
        }

        with self.assertRaisesRegex(CollectorError, "숫자"):
            parse_fred(payload)


if __name__ == "__main__":
    unittest.main()
