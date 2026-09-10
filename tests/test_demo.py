import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class DemoTests(unittest.TestCase):
    def test_demo_is_self_contained_and_offline(self):
        html = (ROOT / "demo.html").read_text(encoding="utf-8")
        self.assertIn("FileReader", html)
        self.assertIn("STATUSES", html)
        self.assertNotIn("http://", html)
        self.assertNotIn("https://", html)

    def test_demo_contains_all_required_fields(self):
        html = (ROOT / "demo.html").read_text(encoding="utf-8")
        for field in ("event_id", "observed_at", "timezone", "source", "recorder_role", "observation", "interpretation", "status", "corrects", "schema_version"):
            self.assertIn(field, html)

    def test_english_readme_states_same_safety_boundary(self):
        readme = (ROOT / "README.en.md").read_text(encoding="utf-8")
        for phrase in ("synthetic", "offline", "medical", "not_recorded", "not_occurring"):
            self.assertIn(phrase, readme)

    def test_one_minute_example_is_synthetic_and_reproducible(self):
        example = (ROOT / "examples" / "README.md").read_text(encoding="utf-8")
        self.assertIn("合成データ", example)
        self.assertIn("問題数: 0", example)
        self.assertIn("問題数: 4", example)
        self.assertIn("not_recorded", example)

    def test_demo_has_accessible_result_region_and_focus_style(self):
        html = (ROOT / "demo.html").read_text(encoding="utf-8")
        self.assertIn("<main>", html)
        self.assertIn('role="region"', html)
        self.assertIn('role="status"', html)
        self.assertIn('aria-describedby="privacy-note"', html)
        self.assertIn('aria-describedby="sample-hint"', html)
        self.assertIn(':focus-visible', html)

    def test_rule_registry_matches_the_six_rules(self):
        import json
        registry = json.loads((ROOT / "rules.json").read_text(encoding="utf-8"))
        html = (ROOT / "demo.html").read_text(encoding="utf-8")
        self.assertEqual([item["id"] for item in registry], [
            "required_fields", "timestamp_timezone", "observation_interpretation",
            "provenance", "missingness_status", "correction_reference"
        ])
        for item in registry:
            self.assertIn(item["severity"], {"high", "medium", "low"})
            self.assertIsInstance(item["machine_readable"], bool)
            self.assertIn("area", item)
        for item in registry:
            self.assertIn(f'"id":"{item["id"]}"', html)

    def test_demo_has_language_toggle_and_bilingual_copy(self):
        html = (ROOT / "demo.html").read_text(encoding="utf-8")
        self.assertIn('aria-pressed="false"', html)
        self.assertIn("setLanguage", html)
        self.assertIn("English", html)
        self.assertIn("This local demo processes files", html)
