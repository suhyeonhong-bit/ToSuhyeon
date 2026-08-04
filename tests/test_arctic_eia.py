import json
import unittest
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from arctic_collector.eia import fetch_eia_steo, parse_eia_steo
from arctic_collector.errors import ArcticCollectorError


FIXTURE = Path(__file__).parent / "fixtures" / "eia_steo_annual.json"


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.body


class EiaTests(unittest.TestCase):
    def setUp(self):
        self.raw = FIXTURE.read_bytes()
        self.payload = json.loads(self.raw)

    def test_parses_series_units_order_and_forecast_boundary(self):
        result = parse_eia_steo(self.payload, date(2026, 8, 4))
        self.assertEqual(list(result), ["usLngExports", "usDryGasProduction", "henryHub"])
        self.assertEqual(result["usLngExports"][0]["period"], "2016")
        self.assertEqual(result["usLngExports"][0]["kind"], "actual")
        self.assertEqual(result["usLngExports"][2]["kind"], "forecast")
        self.assertEqual(result["henryHub"][-1]["unit"], "dollars per million Btu")
        self.assertEqual(result["henryHub"][-1]["value"], 4.25)

    def test_rejects_unknown_series_and_duplicate_periods(self):
        payload = json.loads(self.raw)
        payload["response"]["data"][0]["seriesId"] = "UNKNOWN"
        with self.assertRaises(ArcticCollectorError):
            parse_eia_steo(payload, date(2026, 8, 4))

        payload = json.loads(self.raw)
        payload["response"]["data"].append(dict(payload["response"]["data"][0]))
        with self.assertRaises(ArcticCollectorError):
            parse_eia_steo(payload, date(2026, 8, 4))

    def test_fetch_builds_expected_request_and_safe_metadata(self):
        requests = []

        def opener(request, timeout):
            requests.append((request, timeout))
            return FakeResponse(self.raw)

        result = fetch_eia_steo("eia-secret", date(2026, 8, 4), opener=opener)
        parsed = urlparse(requests[0][0].full_url)
        query = parse_qs(parsed.query)
        self.assertEqual(parsed.path, "/v2/steo/data/")
        self.assertEqual(query["frequency"], ["annual"])
        self.assertEqual(query["api_key"], ["eia-secret"])
        self.assertEqual(set(query["facets[seriesId][]"]), {"NGEXPUS_LNG", "NGPRPUS", "NGHHUUS"})
        self.assertEqual(result.data_through, "2027")
        self.assertEqual(result.edition, "2026-08")
        self.assertRegex(result.content_hash, r"^sha256:[0-9a-f]{64}$")
        self.assertNotIn("eia-secret", result.public_url)

    def test_fetch_error_never_exposes_key_or_url(self):
        def opener(_request, _timeout):
            raise OSError("network failed at api_key=eia-secret")

        with self.assertRaises(ArcticCollectorError) as raised:
            fetch_eia_steo("eia-secret", date(2026, 8, 4), opener=opener)
        self.assertNotIn("eia-secret", str(raised.exception))
        self.assertNotIn("api.eia.gov", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
