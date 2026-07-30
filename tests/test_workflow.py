import unittest
from pathlib import Path


WORKFLOW_PATH = (
    Path(__file__).parents[1]
    / ".github"
    / "workflows"
    / "collect-weekly.yml"
)


class WorkflowContractTests(unittest.TestCase):
    def test_workflow_has_schedule_secrets_and_minimal_commit_scope(self):
        text = WORKFLOW_PATH.read_text(encoding="utf-8")

        self.assertIn('cron: "0 11 * * 1"', text)
        self.assertIn('timezone: "Asia/Seoul"', text)
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("contents: write", text)
        self.assertNotIn("pull_request:", text)
        self.assertIn(
            "FRED_API_KEY: ${{ secrets.FRED_API_KEY }}",
            text,
        )
        self.assertIn(
            "ECOS_API_KEY: ${{ secrets.ECOS_API_KEY }}",
            text,
        )
        self.assertIn(
            "git add -- data/raw "
            "data/processed/monthly_indicators.csv",
            text,
        )
        self.assertNotIn("git add .", text)


if __name__ == "__main__":
    unittest.main()
