import json
import unittest
from pathlib import Path

from arctic_collector.sanctions import (
    parse_eu_csv,
    parse_ofac_csv,
    resolve_eu_csv_url,
)


FIXTURES = Path(__file__).parent / "fixtures"


class SanctionsTests(unittest.TestCase):
    def test_ofac_matches_exact_aliases_and_splits_programs(self):
        matches = parse_ofac_csv(
            (FIXTURES / "ofac_sdn.csv").read_text(encoding="utf-8"),
            "SDN",
        )
        self.assertEqual(len(matches["gennady-timchenko"]), 1)
        match = matches["gennady-timchenko"][0]
        self.assertEqual(match["officialId"], "16666")
        self.assertEqual(match["programs"], ["RUSSIA-EO14024", "UKRAINE-EO13661"])
        self.assertEqual(matches["novatek"], [])
        self.assertEqual(matches["yamal-lng"], [])

    def test_ofac_non_sdn_matches_bounded_company_aliases(self):
        matches = parse_ofac_csv(
            (FIXTURES / "ofac_non_sdn.csv").read_text(encoding="utf-8"),
            "Non-SDN",
        )
        self.assertEqual(matches["novatek"][0]["officialName"], "PAO NOVATEK")
        self.assertEqual(matches["yamal-lng"][0]["officialName"], "YAMAL LNG JSC")

    def test_ofac_accepts_the_official_trailing_dos_eof_marker(self):
        text = (FIXTURES / "ofac_sdn.csv").read_text(encoding="utf-8") + "\x1a\n"
        matches = parse_ofac_csv(text, "SDN")
        self.assertEqual(len(matches["gennady-timchenko"]), 1)

    def test_eu_deduplicates_rows_and_avoids_similar_names(self):
        matches, data_through = parse_eu_csv(
            (FIXTURES / "eu_sanctions.csv").read_text(encoding="utf-8-sig")
        )
        self.assertEqual(data_through, "2026-07-31")
        self.assertEqual(len(matches["gennady-timchenko"]), 1)
        self.assertEqual(len(matches["leonid-mikhelson"]), 1)
        self.assertEqual(matches["novatek"], [])

    def test_eu_resolver_chooses_official_csv_1_1(self):
        payload = json.loads((FIXTURES / "eu_distributions.json").read_text())
        self.assertEqual(
            resolve_eu_csv_url(payload),
            "https://webgate.ec.europa.eu/safe-tokenized-download",
        )


if __name__ == "__main__":
    unittest.main()
