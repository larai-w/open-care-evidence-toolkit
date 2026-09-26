"""Arrival-cutoff and correction semantics, using only synthetic histories."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from care_history import snapshot

ROOT = Path(__file__).resolve().parents[1]


def at(time):
    return f'2026-01-01T{time}:00+00:00'


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads((ROOT / 'fixtures/history.json').read_text())

    def test_before_any_arrival_has_no_imputed_negatives(self):
        result = snapshot(self.payload, at('09:00'))
        self.assertEqual(result['events'], [])
        self.assertEqual(result['summary']['known_records'], 0)
        self.assertIsNone(result['summary']['observed_fraction_among_known'])
        self.assertEqual(result['excluded_after_cutoff'], 5)

    def test_late_observation_is_not_available_just_because_it_happened(self):
        result = snapshot(self.payload, at('10:00'))
        self.assertEqual([e['event_id'] for e in result['events']], ['synthetic-a', 'synthetic-c'])
        self.assertEqual(result['summary']['observed_fraction_among_known'], 1)
        self.assertEqual(result['summary']['not_recorded'], 1)

    def test_authored_but_not_received_correction_does_not_replace_original(self):
        result = snapshot(self.payload, at('10:20'))
        self.assertEqual(result['events'][0]['event_id'], 'synthetic-a')
        self.assertEqual(result['superseded_event_ids'], [])

    def test_exact_arrival_boundary_includes_correction_once(self):
        result = snapshot(self.payload, at('10:30'))
        self.assertEqual([e['event_id'] for e in result['events']], ['synthetic-a-r1', 'synthetic-c'])
        self.assertEqual(result['summary']['observed_fraction_among_known'], 0)
        self.assertEqual(result['superseded_event_ids'], ['synthetic-a'])
        self.assertEqual(result['visible_versions'], 3)

    def test_late_arrival_changes_denominator_at_receipt(self):
        before, after = snapshot(self.payload, at('10:59')), snapshot(self.payload, at('11:00'))
        self.assertEqual(before['summary']['known_records'], 1)
        self.assertEqual(after['summary']['known_records'], 2)
        self.assertEqual(after['summary']['not_recorded'], 1)

    def test_correction_chain_preserves_lineage_without_double_counting(self):
        result = snapshot(self.payload, at('12:00'))
        self.assertEqual(result['lineage'][0]['chain'], ['synthetic-a', 'synthetic-a-r1', 'synthetic-a-r2'])
        self.assertEqual(result['summary']['records'], 3)
        self.assertEqual(result['visible_versions'], 5)
        self.assertEqual(result['summary']['observed_fraction_among_known'], .5)

    def test_future_content_cannot_change_visible_records_or_summary(self):
        expected = snapshot(self.payload, at('10:00'))
        for event in self.payload['events']:
            if event['received_at'] > at('10:00'):
                event.clear()
                event.update({'received_at': at('15:00'), 'status': ['invalid'], 'corrects': 'unknown'})
        actual = snapshot(self.payload, at('10:00'))
        self.assertEqual(actual, expected)

    def test_input_order_does_not_change_snapshot(self):
        expected = snapshot(self.payload, at('12:00'))
        self.payload['events'].reverse()
        self.assertEqual(snapshot(self.payload, at('12:00')), expected)

    def test_equivalent_offsets_produce_same_cutoff(self):
        self.assertEqual(snapshot(self.payload, '2026-01-01T23:00:00+13:00'), snapshot(self.payload, at('10:00')))

    def test_input_is_unchanged_and_output_is_not_an_alias(self):
        before = deepcopy(self.payload)
        result = snapshot(self.payload, at('12:00'))
        result['events'][0]['corrects'].append('changed')
        self.assertEqual(self.payload, before)

    def test_missing_predecessor_never_silently_applies(self):
        self.payload['events'][3]['corrects'] = ['outside-file']
        with self.assertRaisesRegex(ValueError, 'predecessor is not available'):
            snapshot(self.payload, at('10:30'))
        # The bad correction has not arrived at the earlier cutoff.
        self.assertEqual(snapshot(self.payload, at('10:00'))['summary']['observed'], 1)

    def test_future_predecessor_is_unavailable(self):
        self.payload['events'][0]['received_at'] = at('11:00')
        with self.assertRaisesRegex(ValueError, 'predecessor is not available'):
            snapshot(self.payload, at('10:30'))

    def test_fork_is_rejected_only_when_both_branches_are_visible(self):
        self.payload['events'][4]['corrects'] = ['synthetic-a']
        snapshot(self.payload, at('11:00'))
        with self.assertRaisesRegex(ValueError, 'ambiguous correction branch'):
            snapshot(self.payload, at('12:00'))

    def test_duplicate_visible_id_rejected(self):
        self.payload['events'][1]['event_id'] = 'synthetic-a'
        snapshot(self.payload, at('10:00'))
        with self.assertRaisesRegex(ValueError, 'duplicate visible event_id'):
            snapshot(self.payload, at('12:00'))

    def test_cycle_and_self_reference_rejected(self):
        for self_reference in (False, True):
            with self.subTest(self_reference=self_reference):
                a = deepcopy(self.payload['events'][0])
                a.update(received_at=at('10:00'), corrected_at=at('10:00'), corrects=['a' if self_reference else 'b'], event_id='a')
                b = deepcopy(a)
                b.update(event_id='b', corrects=['a'])
                with self.assertRaisesRegex(ValueError, 'cycle'):
                    snapshot({'history_schema_version': 1, 'events': [a] if self_reference else [a, b]}, at('10:00'))

    def test_invalid_temporal_order_is_rejected(self):
        changes = [
            (0, 'observed_at', at('09:06'), 'observation cannot'),
            (3, 'corrected_at', at('10:31'), 'between observation and receipt'),
            (3, 'corrected_at', at('09:01'), 'predates receipt'),
            (3, 'observed_at', at('09:01'), 'preserve the observation instant'),
            (0, 'corrected_at', at('09:04'), 'original records'),
        ]
        for index, field, value, error in changes:
            with self.subTest(field=field, value=value):
                payload = deepcopy(self.payload)
                payload['events'][index][field] = value
                with self.assertRaisesRegex(ValueError, error):
                    snapshot(payload, at('12:00'))

    def test_invalid_correction_cardinality_and_types(self):
        for value in (None, '', [], ['synthetic-a', 'synthetic-b'], [3], {'id': 'synthetic-a'}):
            with self.subTest(value=value):
                payload = deepcopy(self.payload)
                payload['events'][3]['corrects'] = value
                with self.assertRaises(ValueError):
                    snapshot(payload, at('12:00'))

    def test_naive_cutoff_and_missing_receipt_cannot_be_guessed(self):
        with self.assertRaises(ValueError):
            snapshot(self.payload, '2026-01-01T10:00:00')
        self.payload['events'][4].pop('received_at')
        with self.assertRaisesRegex(ValueError, 'received_at'):
            snapshot(self.payload, at('10:00'))

    def test_string_reference_and_equivalent_observation_instant(self):
        self.payload['events'][3]['corrects'] = 'synthetic-a'
        self.payload['events'][3]['observed_at'] = '2026-01-01T22:00:00+13:00'
        result = snapshot(self.payload, at('10:30'))
        self.assertEqual(result['events'][0]['event_id'], 'synthetic-a-r1')

    def test_long_chain_is_iterative(self):
        rows = [deepcopy(self.payload['events'][0])]
        rows[0].update(event_id='e0', received_at=at('10:00'))
        for i in range(1, 1200):
            event = deepcopy(rows[0])
            event.update(event_id=f'e{i}', corrects=[f'e{i-1}'], corrected_at=at('10:00'))
            rows.append(event)
        result = snapshot({'history_schema_version': 1, 'events': rows}, at('10:00'))
        self.assertEqual(result['events'][0]['event_id'], 'e1199')
        self.assertEqual(len(result['lineage'][0]['chain']), 1200)

    def test_cli_reports_errors_without_partial_stdout(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic.json'
            for content in ('{', '{}', '{"history_schema_version": true, "events": []}'):
                path.write_text(content)
                run = subprocess.run([sys.executable, str(ROOT / 'care_history.py'), str(path), '--as-of', at('10:00')], capture_output=True, text=True)
                self.assertEqual(run.returncode, 2)
                self.assertEqual(run.stdout, '')
                self.assertIn('History error:', run.stderr)
                self.assertNotIn('Traceback', run.stderr)

    def test_empty_archive_is_valid_but_malformed_wrapper_is_not(self):
        self.assertEqual(snapshot({'history_schema_version': 1, 'events': []}, at('10:00'))['events'], [])
        for payload in (None, [], {'history_schema_version': True, 'events': []},
                        {'history_schema_version': 1, 'events': None}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                snapshot(payload, at('10:00'))

    def test_invalid_visible_status_and_types_are_rejected(self):
        for field, value in [('status', []), ('source', ''), ('schema_version', True),
                             ('observation', 3), ('received_at', '2026-01-01T09:05:00')]:
            with self.subTest(field=field):
                payload = deepcopy(self.payload)
                payload['events'][0][field] = value
                with self.assertRaises(ValueError):
                    snapshot(payload, at('10:00'))

    def test_utc_conversion_overflow_is_a_validation_error(self):
        for cutoff in ('0001-01-01T00:00:00+14:00', '9999-12-31T23:59:59-14:00'):
            with self.subTest(cutoff=cutoff), self.assertRaises(ValueError):
                snapshot(self.payload, cutoff)

    def test_replay_report_matches_independently_expected_timeline(self):
        from benchmarks.history_replay import build_report
        report = build_report()
        self.assertEqual([s['summary']['observed_fraction_among_known'] for s in report['snapshots']],
                         [None, 1, 1, 0, 0, .5])
        self.assertEqual(report['comparison']['absolute_fraction_difference'], .5)
        saved = json.loads((ROOT / 'examples/field-contract-v1/history-results.json').read_text())
        self.assertEqual(report, saved, 'Current snapshot must match history and validator sources')
        historical = json.loads((ROOT / 'examples/history-v1/results.json').read_text())
        self.assertEqual({k: v for k, v in report.items() if k != 'source_sha256'},
                         {k: v for k, v in historical.items() if k != 'source_sha256'})

    def test_cli_json_and_markdown(self):
        for fmt in ('json', 'markdown'):
            run = subprocess.run([sys.executable, str(ROOT / 'care_history.py'), str(ROOT / 'fixtures/history.json'), '--as-of', at('10:00'), '--format', fmt], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            if fmt == 'json':
                self.assertEqual(json.loads(run.stdout)['summary']['observed'], 1)
            else:
                self.assertIn('As-of observation history', run.stdout)
                self.assertIn('100.00%', run.stdout)


if __name__ == '__main__':
    unittest.main()
