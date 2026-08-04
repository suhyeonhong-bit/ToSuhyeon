import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ArcticWorkflowTests(unittest.TestCase):
    def test_monthly_workflow_has_eia_schedule_secret_and_minimal_scope(self):
        workflow = (ROOT / ".github/workflows/collect-arctic-monthly.yml").read_text(encoding="utf-8")
        self.assertIn('cron: "30 9 15 * *"', workflow)
        self.assertIn('timezone: "Asia/Seoul"', workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("group: arctic-dashboard-data", workflow)
        self.assertIn("contents: write", workflow)
        self.assertIn("python3 collect_arctic_data.py --group eia", workflow)
        self.assertIn("EIA_API_KEY: ${{ secrets.EIA_API_KEY }}", workflow)
        self.assertIn("git add -- data/processed/arctic_dashboard.json", workflow)
        self.assertNotIn("pull_request:", workflow)
        self.assertNotIn("git add .", workflow)
        self.assertNotIn("VITE_", workflow)
        self.assertNotIn("NEXT_PUBLIC_", workflow)

    def test_daily_workflow_has_daily_schedule_no_secret_and_same_concurrency(self):
        workflow = (ROOT / ".github/workflows/collect-arctic-daily.yml").read_text(encoding="utf-8")
        self.assertIn('cron: "10 9 * * *"', workflow)
        self.assertIn('timezone: "Asia/Seoul"', workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("group: arctic-dashboard-data", workflow)
        self.assertIn("python3 collect_arctic_data.py --group daily", workflow)
        self.assertIn("git add -- data/processed/arctic_dashboard.json", workflow)
        self.assertNotIn("EIA_API_KEY", workflow)
        self.assertNotIn("secrets.", workflow)
        self.assertNotIn("data/raw", workflow)

    def test_both_workflows_run_tests_before_collection_and_rebase_before_push(self):
        for filename in ("collect-arctic-monthly.yml", "collect-arctic-daily.yml"):
            workflow = (ROOT / ".github/workflows" / filename).read_text(encoding="utf-8")
            self.assertLess(
                workflow.index("python3 -m unittest discover -s tests -v"),
                workflow.index("python3 collect_arctic_data.py"),
            )
            self.assertLess(workflow.index("git pull --rebase origin main"), workflow.index("git push origin HEAD:main"))
            self.assertIn("timeout-minutes: 15", workflow)
            self.assertIn('python-version: "3.9"', workflow)


if __name__ == "__main__":
    unittest.main()
