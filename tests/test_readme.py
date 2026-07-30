import unittest
from pathlib import Path


README_PATH = Path(__file__).parents[1] / "README.md"


class ReadmeContractTests(unittest.TestCase):
    def test_readme_contains_beginner_local_and_github_instructions(self):
        text = README_PATH.read_text(encoding="utf-8")
        required_phrases = (
            "python3 collect_data.py",
            "python3 -m unittest discover -s tests -v",
            "data/raw",
            "data/processed/monthly_indicators.csv",
            "FRED_API_KEY",
            "ECOS_API_KEY",
            "suhyeonhong-bit/ToSuhyeon",
            "매주 월요일 오전 11시",
            "Run workflow",
            "Actions secrets",
            "자동으로 GitHub에 올라가지 않습니다",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
