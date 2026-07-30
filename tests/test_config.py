import tempfile
import unittest
from pathlib import Path

from collector.config import load_config
from collector.errors import CollectorError


class LoadConfigTests(unittest.TestCase):
    def test_reads_keys_from_env_file(self):
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text(
                "# API keys\n"
                "\n"
                "FRED_API_KEY=fredtest123\n"
                "ECOS_API_KEY=ecostest456\n",
                encoding="utf-8",
            )

            config = load_config(env_path, environ={})

        self.assertEqual(config.fred_api_key, "fredtest123")
        self.assertEqual(config.ecos_api_key, "ecostest456")

    def test_environment_variables_work_without_env_file(self):
        with tempfile.TemporaryDirectory() as directory:
            missing_env_path = Path(directory) / ".env"

            config = load_config(
                missing_env_path,
                environ={
                    "FRED_API_KEY": "fredfromgithub",
                    "ECOS_API_KEY": "ecosfromgithub",
                },
            )

        self.assertEqual(config.fred_api_key, "fredfromgithub")
        self.assertEqual(config.ecos_api_key, "ecosfromgithub")

    def test_environment_variables_override_env_file(self):
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text(
                "FRED_API_KEY=fredlocal\nECOS_API_KEY=ecoslocal\n",
                encoding="utf-8",
            )

            config = load_config(
                env_path,
                environ={
                    "FRED_API_KEY": "fredgithub",
                    "ECOS_API_KEY": "ecosgithub",
                },
            )

        self.assertEqual(config.fred_api_key, "fredgithub")
        self.assertEqual(config.ecos_api_key, "ecosgithub")

    def test_missing_key_names_variable_without_exposing_other_key(self):
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text(
                "FRED_API_KEY=fred-secret-that-must-not-appear\n",
                encoding="utf-8",
            )

            with self.assertRaises(CollectorError) as raised:
                load_config(env_path, environ={})

        message = str(raised.exception)
        self.assertIn("ECOS_API_KEY", message)
        self.assertNotIn("fred-secret-that-must-not-appear", message)

    def test_whitespace_in_key_is_rejected_without_showing_key(self):
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text(
                "FRED_API_KEY=fred secret\nECOS_API_KEY=ecostest456\n",
                encoding="utf-8",
            )

            with self.assertRaises(CollectorError) as raised:
                load_config(env_path, environ={})

        message = str(raised.exception)
        self.assertIn("FRED_API_KEY", message)
        self.assertNotIn("fred secret", message)


if __name__ == "__main__":
    unittest.main()
