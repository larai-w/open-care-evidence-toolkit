"""CLI behaviour with temporary synthetic inputs only; no network or real data."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CLIContractTests(unittest.TestCase):
    def run_cli(self, content, suffix='.json', *args):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ('synthetic' + suffix)
            path.write_text(content, encoding='utf-8')
            return subprocess.run(
                [sys.executable, str(ROOT / 'care_evidence.py'), str(path), *args],
                capture_output=True, text=True,
            )

    def test_default_report_is_english(self):
        result = self.run_cli((ROOT / 'fixtures/missing.json').read_text())
        self.assertEqual(result.returncode, 0)
        self.assertIn('Data quality summary', result.stdout)
        self.assertIn('Provenance', result.stdout)

    def test_language_does_not_change_findings(self):
        content = (ROOT / 'fixtures/missing.json').read_text()
        reports = []
        for language in ('en', 'ja'):
            result = self.run_cli(content, '.json', '--format', 'json', '--lang', language)
            self.assertEqual(result.returncode, 0, result.stderr)
            reports.append(json.loads(result.stdout))
        self.assertEqual(reports[0]['issues'], reports[1]['issues'])
        self.assertEqual([i['rule'] for i in reports[0]['results'][0]['issues']],
                         [i['rule'] for i in reports[1]['results'][0]['issues']])
        self.assertIn('source and recorder_role', reports[0]['results'][0]['issues'][1]['message'])
        self.assertIn('記録', reports[1]['results'][0]['issues'][1]['message'])

    def test_quality_gate_returns_one_and_preserves_json(self):
        result = self.run_cli((ROOT / 'fixtures/missing.json').read_text(), '.json',
                              '--format', 'json', '--fail-on-issues')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)['issues'], 4)
        self.assertEqual(result.stderr, '')

    def test_clean_quality_gate_returns_zero(self):
        result = self.run_cli((ROOT / 'fixtures/complete.json').read_text(), '.json', '--fail-on-issues')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_invalid_inputs_are_errors_without_partial_report(self):
        for content in ('{', 'null', '3', '"text"', '[null]', '{"events": {}}', '{"events": [2]}', '[]'):
            with self.subTest(content=content):
                result = self.run_cli(content, '.json', '--format', 'json')
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, '')
                self.assertIn('Input error:', result.stderr)
                self.assertNotIn('Traceback', result.stderr)

    def test_bom_and_quoted_newline_csv(self):
        import csv
        import io
        event = json.loads((ROOT / 'fixtures/complete.json').read_text())['events'][0]
        event['observation'] = 'Synthetic observation, first line\nsecond line'
        event['corrects'] = ''
        stream = io.StringIO(newline='')
        writer = csv.DictWriter(stream, fieldnames=event.keys())
        writer.writeheader()
        writer.writerow(event)
        result = self.run_cli('\ufeff' + stream.getvalue() + '\n', '.csv', '--format', 'json')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['issues'], 0)

    def test_ambiguous_csv_shape_is_rejected(self):
        for content in ('event_id,event_id\na,b\n', 'event_id,status\na,observed,extra\n',
                        'event_id,status\na\n', '', 'event_id,status\n', 'event_id,status\n"unclosed,observed\n'):
            with self.subTest(content=content):
                result = self.run_cli(content, '.csv', '--format', 'json')
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, '')
                self.assertNotIn('Traceback', result.stderr)

    def test_supported_json_shapes_and_bom(self):
        event = json.loads((ROOT / 'fixtures/complete.json').read_text())['events'][0]
        for payload in (event, [event], {'events': [event]}):
            with self.subTest(payload=type(payload).__name__):
                result = self.run_cli('\ufeff' + json.dumps(payload), '.json', '--format', 'json')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)['events'], 1)
                self.assertEqual(json.loads(result.stdout)['issues'], 0)

    def test_missing_file_is_an_input_error(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, str(ROOT / 'care_evidence.py'),
                                     str(Path(directory) / 'absent.json')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, '')
        self.assertIn('Input error:', result.stderr)
        self.assertNotIn('Traceback', result.stderr)

    def test_missing_csv_fields_are_quality_findings(self):
        result = self.run_cli('event_id,status\nsynthetic-1,observed\n', '.csv',
                              '--format', 'json', '--fail-on-issues')
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('required_fields', {i['rule'] for i in json.loads(result.stdout)['results'][0]['issues']})

    def test_non_string_status_is_reported_not_crashed(self):
        event = json.loads((ROOT / 'fixtures/complete.json').read_text())['events'][0]
        event['status'] = []
        result = self.run_cli(json.dumps(event), '.json', '--format', 'json')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('missingness_status', {i['rule'] for i in json.loads(result.stdout)['results'][0]['issues']})


if __name__ == '__main__':
    unittest.main()
