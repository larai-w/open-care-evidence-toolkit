"""Benchmark mathematics, ground truth, and replay tested on synthetic inputs."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from benchmarks.quality_benchmark import (
    baseline, build_benchmark, detection_metrics, digest, evaluate_case,
    inject, select_rows, signal_summary,
)

ROOT = Path(__file__).resolve().parents[1]


class BenchmarkTests(unittest.TestCase):
    def test_confusion_matrix_against_hand_calculation(self):
        m = detection_metrics(10, {1, 2, 3}, {2, 3, 4, 5})
        self.assertEqual([m[k] for k in ('tp', 'fp', 'fn', 'tn')], [2, 2, 1, 5])
        self.assertEqual(m['precision'], 0.5)
        self.assertAlmostEqual(m['recall'], 2 / 3)
        self.assertAlmostEqual(m['false_positive_rate'], 2 / 7)
        self.assertEqual(m['retained_fraction'], 0.6)

    def test_undefined_rates_are_null_not_perfect_scores(self):
        m = detection_metrics(4, set(), set())
        self.assertIsNone(m['recall'])
        self.assertIsNone(m['precision'])
        self.assertEqual(m['false_positive_rate'], 0)
        self.assertIsNone(detection_metrics(4, {0, 1, 2, 3}, set())['false_positive_rate'])
        self.assertIsNone(signal_summary([])['observed_fraction_among_known'])
        with self.assertRaises(ValueError):
            detection_metrics(4, {4}, set())

    def test_injection_truth_is_separate_from_validator_and_input_is_preserved(self):
        events = baseline(16)
        original = deepcopy(events)
        corrupted, changes = inject(events, 'duplicate_id', [1, 4])
        self.assertEqual(events, original)
        self.assertEqual([c['row_index'] for c in changes], [1, 4])
        self.assertEqual(corrupted[1]['event_id'], events[0]['event_id'])
        self.assertEqual(corrupted[4]['event_id'], events[0]['event_id'])
        self.assertEqual(changes[0]['before']['event_id'], events[1]['event_id'])
        self.assertEqual([i for i, (a, b) in enumerate(zip(events, corrupted)) if a != b], [1, 4])

    def test_patterns_select_same_count_but_different_eligible_locations(self):
        events = baseline(120)
        eligible = [i for i, e in enumerate(events) if i > 0 and e['status'] == 'observed']
        scattered = select_rows(events, .3, 'scattered', 7)
        block = select_rows(events, .3, 'block', 7)
        self.assertEqual(len(scattered), int(len(eligible) * .3))
        self.assertEqual(len(block), len(scattered))
        start = eligible.index(block[0])
        self.assertEqual(block, eligible[start:start + len(block)])
        self.assertNotEqual(scattered, block)
        self.assertNotEqual(scattered, select_rows(events, .3, 'scattered', 19))
        self.assertEqual(select_rows(events, 0, 'scattered', 7), [])
        self.assertEqual(select_rows(events, 1, 'block', 7), eligible)

    def test_clean_challenge_surfaces_phrase_false_alarm(self):
        events = baseline(16)
        result, predictions = evaluate_case(events, set(), signal_summary(events))
        self.assertEqual(result['detection']['fp'], 1)
        self.assertEqual(predictions, [{'row_index': 0, 'rules': ['observation_interpretation']}])
        self.assertEqual(result['raw_absolute_error'], 0)
        self.assertGreater(result['retained_absolute_error'], 0)

    def test_silent_change_is_missed_and_changes_the_aggregate(self):
        events = baseline(16)
        corrupted, _ = inject(events, 'false_non_occurrence', [1, 4])
        result, _ = evaluate_case(corrupted, {1, 4}, signal_summary(events))
        self.assertEqual(result['detection']['fn'], 2)
        self.assertEqual(result['detection']['tp'], 0)
        # Baseline: 8 positives / 14 known. Two positives become negative.
        self.assertAlmostEqual(result['raw']['observed_fraction_among_known'], 6 / 14)
        self.assertAlmostEqual(result['raw_absolute_error'], 2 / 14)

    def test_detected_corruption_can_worsen_selection_bias(self):
        events = baseline(16)
        corrupted, _ = inject(events, 'missing_source', [1, 4])
        result, _ = evaluate_case(corrupted, {1, 4}, signal_summary(events))
        self.assertEqual(result['detection']['tp'], 2)
        self.assertEqual(result['raw_absolute_error'], 0)
        self.assertGreater(result['retained_absolute_error'], 0)
        self.assertEqual(result['retained']['rows'], 13)

    def test_evidence_reconstructs_every_input_and_metric(self):
        report, evidence = build_benchmark(32, [.3], [7])
        self.assertEqual(len(report['cases']), 12)
        self.assertEqual(len({c['id'] for c in report['cases']}), 12)
        self.assertEqual(report['evidence_sha256'], digest(evidence))
        for case, proof in zip(report['cases'], evidence['cases']):
            events = deepcopy(evidence['baseline'])
            truth = {c['row_index'] for c in proof['changes']}
            for change in proof['changes']:
                self.assertEqual({k: events[change['row_index']][k] for k in change['before']}, change['before'])
                events[change['row_index']].update(change['after'])
            self.assertEqual(case['input_sha256'], digest(events))
            measured, predictions = evaluate_case(events, truth, report['reference'])
            self.assertEqual(case['detection'], measured['detection'])
            self.assertEqual(proof['predictions'], predictions)
        second = build_benchmark(32, [.3], [7])
        self.assertEqual((report, evidence), second)

    def test_existing_false_alarm_is_not_credited_as_new_detection(self):
        report, _ = build_benchmark(32, [1], [7])
        for case in report['cases']:
            if case['scenario'] == 'duplicate_id':
                self.assertEqual(case['incremental_detection']['newly_flagged_injected'], 0)
                self.assertEqual(case['incremental_detection']['already_flagged_injected'], 1)
                self.assertEqual(case['detection']['tp'], 1)

    def test_cli_exports_reproducible_results_without_overwriting(self):
        with tempfile.TemporaryDirectory() as directory:
            outputs = []
            for name in ('first', 'second'):
                output = Path(directory) / name
                command = [sys.executable, str(ROOT / 'benchmarks/quality_benchmark.py'),
                           '--size', '16', '--rates', '0', '1', '--seeds', '7', '--output', str(output)]
                result = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                outputs.append(output)
            for name in ('metrics.json', 'evidence.json', 'REPORT.md'):
                self.assertEqual((outputs[0] / name).read_bytes(), (outputs[1] / name).read_bytes())
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn('already exists', result.stderr)
            self.assertGreaterEqual(json.loads((outputs[0] / 'run.json').read_text())['elapsed_seconds_generation_and_evaluation'], 0)

    def test_checked_in_example_matches_current_sources(self):
        directory = ROOT / 'examples/benchmark-v1'
        saved = json.loads((ROOT / 'examples/field-contract-v1/benchmark-metrics.json').read_text())
        config = saved['configuration']
        report, evidence = build_benchmark(config['size'], config['rates'], config['seeds'])
        self.assertEqual(saved, report, 'Current field-contract snapshot must match source hashes')
        historical = json.loads((directory / 'metrics.json').read_text())
        self.assertEqual({k: v for k, v in historical.items() if k != 'source_sha256'},
                         {k: v for k, v in report.items() if k != 'source_sha256'})
        self.assertEqual(json.loads((directory / 'evidence.json').read_text()), evidence)

    def test_invalid_parameters_are_rejected(self):
        for rates in ([], [0.1, 0.1], [-0.1], [1.1], [float('nan')]):
            with self.subTest(rates=rates), self.assertRaises(ValueError):
                build_benchmark(32, rates, [7])
        with self.assertRaises(ValueError):
            build_benchmark(32, [0.1], [])
        with self.assertRaises(ValueError):
            build_benchmark(0, [0.1], [7])


if __name__ == '__main__':
    unittest.main()
