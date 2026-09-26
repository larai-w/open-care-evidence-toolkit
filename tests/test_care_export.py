from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from care_export import export_bundle

ROOT = Path(__file__).resolve().parents[1]


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.request = json.loads((ROOT / 'fixtures/integration-request.json').read_text())

    def test_gates_and_as_of_features(self):
        rows = {r['sample_id']: r for r in export_bundle(self.request)['rows']}
        self.assertEqual(rows['fit-at-10']['features'], {'observed_fraction': 1, 'known_count': 1, 'unknown_count': 1})
        self.assertEqual(rows['test-at-12']['features'], {'observed_fraction': .5, 'known_count': 2, 'unknown_count': 1})
        self.assertEqual(rows['fit-before-arrival']['decision'], 'insufficient_data')
        self.assertEqual(rows['test-at-10']['decision'], 'quality_rejected')
        self.assertIsNone(rows['test-at-10']['features'])
        self.assertIsNone(rows['fit-before-arrival']['features'])

    def test_future_changes_do_not_change_features_decision_or_visible_versions(self):
        original = self.request['samples'][0]
        before = export_bundle({'dataset_kind': 'synthetic', 'samples': [original]})['rows'][0]
        changed = deepcopy(original)
        changed['history']['events'][-1]['observation'] = 'future change'
        after = export_bundle({'dataset_kind': 'synthetic', 'samples': [changed]})['rows'][0]
        for key in ('features', 'decision', 'quality_issues'):
            self.assertEqual(before[key], after[key])
        self.assertEqual(before['audit']['selected_versions'], after['audit']['selected_versions'])
        self.assertNotEqual(before['audit']['history_sha256'], after['audit']['history_sha256'])

    def test_input_is_not_modified_and_replay_is_deterministic(self):
        before = deepcopy(self.request)
        self.assertEqual(export_bundle(self.request), export_bundle(self.request))
        self.assertEqual(self.request, before)

    def test_contract_rejects_unsupported_and_duplicate_inputs(self):
        for request in ({}, {'dataset_kind': 'research', 'samples': []},
                        {'dataset_kind': 'synthetic', 'samples': []},
                        {'dataset_kind': 'synthetic', 'samples': [self.request['samples'][0]] * 2}):
            with self.subTest(request=request.get('dataset_kind')), self.assertRaises(ValueError):
                export_bundle(request)

    def test_bad_history_is_not_exported_as_a_successful_quality_gate(self):
        self.request['samples'][0]['history']['events'][0]['received_at'] = 'invalid'
        with self.assertRaises(ValueError):
            export_bundle(self.request)

    def test_raw_text_and_future_archive_counts_are_not_features(self):
        bundle = export_bundle(self.request)
        for row in bundle['rows']:
            self.assertNotIn('excluded_after_cutoff', row)
            for event in row['audit']['selected_versions']:
                self.assertNotIn('observation', event)
            if row['features']:
                self.assertEqual(set(row['features']), set(bundle['feature_names']))

    def test_checked_in_bundle_matches_exporter(self):
        saved = json.loads((ROOT / 'examples/field-contract-v1/bundle.json').read_text())
        self.assertEqual(saved, export_bundle(self.request))
        historical = json.loads((ROOT / 'examples/integration-v1/bundle.json').read_text())
        historical['audit'].pop('source_sha256')
        current = deepcopy(saved)
        current['audit'].pop('source_sha256')
        self.assertEqual(historical, current)

    def test_cli_does_not_overwrite_or_write_on_validation_error(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'bundle.json'
            command = [sys.executable, str(ROOT / 'care_export.py'), str(ROOT / 'fixtures/integration-request.json'), '--output', str(output)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            saved = output.read_bytes()
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)
            self.assertEqual(output.read_bytes(), saved)
            invalid = Path(directory) / 'invalid.json'
            invalid.write_text('{}')
            new = Path(directory) / 'not-created.json'
            result = subprocess.run([sys.executable, str(ROOT / 'care_export.py'), str(invalid), '--output', str(new)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(new.exists())


if __name__ == '__main__':
    unittest.main()
