import tempfile
import unittest
from pathlib import Path

from arctic_collector.config import load_arctic_config
from arctic_collector.errors import ArcticCollectorError


class ArcticConfigTests(unittest.TestCase):
    def test_reads_eia_key_from_env_file(self):
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text("EIA_API_KEY=eia-local-key\n", encoding="utf-8")
            config = load_arctic_config(env_path, require_eia=True, environ={})
        self.assertEqual(config.eia_api_key, "eia-local-key")

    def test_environment_overrides_file(self):
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text("EIA_API_KEY=eia-local-key\n", encoding="utf-8")
            config = load_arctic_config(
                env_path,
                require_eia=True,
                environ={"EIA_API_KEY": "eia-actions-key"},
            )
        self.assertEqual(config.eia_api_key, "eia-actions-key")

    def test_daily_group_does_not_require_eia_key(self):
        with tempfile.TemporaryDirectory() as directory:
            config = load_arctic_config(
                Path(directory) / ".env",
                require_eia=False,
                environ={},
            )
        self.assertIsNone(config.eia_api_key)

    def test_missing_monthly_key_is_safe(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ArcticCollectorError) as raised:
                load_arctic_config(
                    Path(directory) / ".env",
                    require_eia=True,
                    environ={},
                )
        self.assertIn("EIA_API_KEY", str(raised.exception))

    def test_whitespace_in_key_is_rejected_without_showing_key(self):
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text("EIA_API_KEY=secret key\n", encoding="utf-8")
            with self.assertRaises(ArcticCollectorError) as raised:
                load_arctic_config(env_path, require_eia=True, environ={})
        self.assertNotIn("secret key", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
