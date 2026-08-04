import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from arctic_collector.errors import ArcticCollectorError
from arctic_collector.storage import load_dashboard, save_dashboard


FIXTURE = Path(__file__).parent / "fixtures" / "arctic_dashboard_existing.json"


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.document = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_round_trips_valid_dashboard_with_stable_newline(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "arctic_dashboard.json"
            save_dashboard(path, self.document, secrets=("secret-key",))
            self.assertTrue(path.read_text(encoding="utf-8").endswith("\n"))
            self.assertEqual(load_dashboard(path), self.document)

    def test_secret_blocks_write(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "arctic_dashboard.json"
            document = dict(self.document)
            document["generatedAt"] = "secret-key"
            with self.assertRaises(ArcticCollectorError):
                save_dashboard(path, document, secrets=("secret-key",))
            self.assertFalse(path.exists())

    def test_failed_replace_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "arctic_dashboard.json"
            path.write_text("old-data\n", encoding="utf-8")
            with patch("arctic_collector.storage.os.replace", side_effect=OSError("disk")):
                with self.assertRaises(ArcticCollectorError):
                    save_dashboard(path, self.document, secrets=())
            self.assertEqual(path.read_text(encoding="utf-8"), "old-data\n")

    def test_invalid_existing_json_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "arctic_dashboard.json"
            path.write_text("not-json", encoding="utf-8")
            with self.assertRaises(ArcticCollectorError):
                load_dashboard(path)


if __name__ == "__main__":
    unittest.main()
