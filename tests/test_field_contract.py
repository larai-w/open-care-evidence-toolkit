"""Shared synthetic field contract: exact ordered rule IDs, both languages."""
import json
from pathlib import Path
import unittest
from care_evidence import check_event

CASES = json.loads((Path(__file__).resolve().parents[1] / 'fixtures/field-contract.json').read_text())

class FieldContractTests(unittest.TestCase):
    def test_shared_rule_expectations(self):
        for case in CASES:
            for language in ('en', 'ja'):
                with self.subTest(case=case['name'], language=language):
                    self.assertEqual([issue['rule'] for issue in check_event(case['event'], language)], case['rules'])
