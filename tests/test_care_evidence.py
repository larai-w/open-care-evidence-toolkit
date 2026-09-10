import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]


class ToolkitTests(unittest.TestCase):
    def run_tool(self, fixture):
        result = subprocess.run([sys.executable, str(ROOT / "care_evidence.py"), str(ROOT / "fixtures" / fixture), "--format", "json"], capture_output=True, text=True, check=True)
        return json.loads(result.stdout)

    def test_complete_fixture_passes(self):
        report = self.run_tool("complete.json")
        self.assertEqual(report["issues"], 0)

    def test_missing_fixture_exposes_multiple_boundaries(self):
        report = self.run_tool("missing.json")
        rules = {issue["rule"] for issue in report["results"][0]["issues"]}
        self.assertTrue({"timestamp_timezone", "provenance", "missingness_status"} <= rules)

    def test_correction_fixture_preserves_reference(self):
        report = self.run_tool("correction.json")
        self.assertEqual(report["issues"], 0)

    def test_csv_fixture_passes(self):
        report = self.run_tool("complete.csv")
        self.assertEqual(report["issues"], 0)

    def test_naive_timestamp_is_rejected(self):
        event = json.loads((ROOT / "fixtures" / "complete.json").read_text())['events'][0]
        event["observed_at"] = "2026-09-10T09:00:00"
        from care_evidence import check_event
        self.assertIn("timestamp_timezone", {issue["rule"] for issue in check_event(event)})


if __name__ == "__main__":
    unittest.main()
