import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path

from arctic_collector.errors import ArcticCollectorError
from arctic_collector.manifest import SourceResult, empty_dashboard
from arctic_collector.storage import save_dashboard
from collect_arctic_data import run


NOW = datetime(2026, 8, 4, 3, 0, tzinfo=timezone.utc)


def eia_result():
    point = lambda value, unit: [{"period": "2026", "value": value, "unit": unit, "kind": "forecast", "source": "EIA STEO"}]
    return SourceResult(
        data={
            "usLngExports": point(17.5, "billion cubic feet per day"),
            "usDryGasProduction": point(107.2, "billion cubic feet per day"),
            "henryHub": point(4.1, "dollars per million Btu"),
        },
        content_hash="sha256:" + "a" * 64,
        data_through="2026",
        public_url="https://www.eia.gov/outlooks/steo/",
        edition="2026-08",
    )


def sanctions_result(source):
    return SourceResult(
        data={watch_id: [] for watch_id in ["novatek", "yamal-lng", "leonid-mikhelson", "gennady-timchenko"]},
        content_hash="sha256:" + ("b" if source == "ofac" else "c") * 64,
        data_through="2026-08-04",
        public_url=(
            "https://ofac.treasury.gov/sanctions-list-service"
            if source == "ofac"
            else "https://data.europa.eu/data/datasets/consolidated-list-of-persons-groups-and-entities-subject-to-eu-financial-sanctions?locale=en"
        ),
    )


def nsidc_result():
    row = {"date": "2026-08-02", "extent": 6.123, "unit": "10^6 sq km", "missing": 0.0, "source": "NSIDC Sea Ice Index v4"}
    return SourceResult(
        data={"latest": row, "daily": [row]},
        content_hash="sha256:" + "d" * 64,
        data_through="2026-08-02",
        public_url="https://noaadata.apps.nsidc.org/NOAA/G02135/north/daily/data/N_seaice_extent_daily_v4.0.csv",
    )


class CollectArcticDataTests(unittest.TestCase):
    def test_eia_group_requires_key_and_writes_only_eia_branch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.joinpath(".env").write_text("EIA_API_KEY=fake-key\n", encoding="utf-8")
            code = run(root, "eia", now=NOW, fetchers={"eia": eia_result})
            document = json.loads(root.joinpath("data/processed/arctic_dashboard.json").read_text())
        self.assertEqual(code, 0)
        self.assertTrue(document["sources"]["eia"]["hasData"])
        self.assertFalse(document["sources"]["ofac"]["hasData"])

    def test_daily_partial_failure_publishes_successes_and_marks_stale(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            save_dashboard(root / "data/processed/arctic_dashboard.json", empty_dashboard(), secrets=())

            def fail_eu():
                raise ArcticCollectorError("eu", "network", "failed")

            code = run(
                root,
                "daily",
                now=NOW,
                fetchers={"ofac": lambda: sanctions_result("ofac"), "eu": fail_eu, "nsidc": nsidc_result},
            )
            document = json.loads(root.joinpath("data/processed/arctic_dashboard.json").read_text())
        self.assertEqual(code, 0)
        self.assertEqual(document["sources"]["ofac"]["status"], "fresh")
        self.assertEqual(document["sources"]["eu"]["status"], "stale")
        self.assertEqual(document["sources"]["nsidc"]["status"], "fresh")

    def test_all_requested_failures_preserve_existing_file_and_hide_exception_text(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "data/processed/arctic_dashboard.json"
            save_dashboard(path, empty_dashboard(), secrets=())
            before = path.read_text(encoding="utf-8")

            def fail():
                raise RuntimeError("must-not-print-secret")

            stderr = io.StringIO()
            stdout = io.StringIO()
            with redirect_stderr(stderr), redirect_stdout(stdout):
                code = run(root, "daily", now=NOW, fetchers={"ofac": fail, "eu": fail, "nsidc": fail})
            after = path.read_text(encoding="utf-8")
        self.assertEqual(code, 1)
        self.assertEqual(after, before)
        self.assertNotIn("must-not-print-secret", stderr.getvalue() + stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
