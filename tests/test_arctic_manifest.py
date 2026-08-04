import copy
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from arctic_collector.errors import ArcticCollectorError
from arctic_collector.manifest import (
    SourceResult,
    empty_dashboard,
    merge_collection_results,
    validate_dashboard,
)


FIXTURE = Path(__file__).parent / "fixtures" / "arctic_dashboard_existing.json"
NOW = datetime(2026, 8, 4, tzinfo=timezone.utc)


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.previous = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_empty_dashboard_has_fixed_sources_and_watchlist(self):
        document = empty_dashboard()
        self.assertEqual(list(document["sources"]), ["eia", "ofac", "eu", "nsidc"])
        self.assertEqual(
            [item["id"] for item in document["sanctions"]["watchlist"]],
            ["novatek", "yamal-lng", "leonid-mikhelson", "gennady-timchenko"],
        )
        validate_dashboard(document)

    def test_success_replaces_owned_branch_and_preserves_unrequested_sources(self):
        result = SourceResult(
            data={
                "usLngExports": [{"period": "2026", "value": 17.5, "unit": "billion cubic feet per day", "kind": "forecast", "source": "EIA STEO"}],
                "usDryGasProduction": [{"period": "2026", "value": 107.2, "unit": "billion cubic feet per day", "kind": "forecast", "source": "EIA STEO"}],
                "henryHub": [{"period": "2026", "value": 4.1, "unit": "dollars per million Btu", "kind": "forecast", "source": "EIA STEO"}],
            },
            content_hash="sha256:" + "e" * 64,
            data_through="2026",
            public_url="https://www.eia.gov/outlooks/steo/",
            edition="2026-08",
        )
        merged = merge_collection_results(self.previous, ["eia"], {"eia": result}, {}, NOW)
        self.assertEqual(merged["energy"]["henryHub"][0]["value"], 4.1)
        self.assertEqual(merged["sources"]["eia"]["status"], "fresh")
        self.assertEqual(merged["sources"]["ofac"], self.previous["sources"]["ofac"])
        self.assertEqual(merged["sanctions"], self.previous["sanctions"])

    def test_partial_failure_keeps_prior_source_data_and_marks_only_it_stale(self):
        ofac = SourceResult(
            data={watch_id: [] for watch_id in ["novatek", "yamal-lng", "leonid-mikhelson", "gennady-timchenko"]},
            content_hash="sha256:" + "f" * 64,
            data_through="2026-08-04",
            public_url="https://ofac.treasury.gov/sanctions-list-service",
        )
        failure = ArcticCollectorError("eu", "network", "EU 데이터를 가져오지 못했습니다.")
        merged = merge_collection_results(self.previous, ["ofac", "eu"], {"ofac": ofac}, {"eu": failure}, NOW)
        self.assertEqual(merged["sources"]["ofac"]["status"], "fresh")
        self.assertEqual(merged["sources"]["eu"]["status"], "stale")
        mikhelson = merged["sanctions"]["watchlist"][2]
        self.assertTrue(mikhelson["eu"]["listed"])
        self.assertFalse(mikhelson["ofac"]["listed"])

    def test_all_requested_failures_do_not_create_replacement(self):
        with self.assertRaises(ArcticCollectorError):
            merge_collection_results(
                self.previous,
                ["nsidc"],
                {},
                {"nsidc": ArcticCollectorError("nsidc", "network", "failed")},
                NOW,
            )

    def test_validation_rejects_bad_hash_duplicate_period_and_latest_mismatch(self):
        broken = copy.deepcopy(self.previous)
        broken["sources"]["eia"]["contentHash"] = "bad"
        with self.assertRaises(ArcticCollectorError):
            validate_dashboard(broken)

        broken = copy.deepcopy(self.previous)
        broken["energy"]["henryHub"].append(dict(broken["energy"]["henryHub"][0]))
        with self.assertRaises(ArcticCollectorError):
            validate_dashboard(broken)

        broken = copy.deepcopy(self.previous)
        broken["seaIce"]["latest"]["extent"] = 9.9
        with self.assertRaises(ArcticCollectorError):
            validate_dashboard(broken)


if __name__ == "__main__":
    unittest.main()
