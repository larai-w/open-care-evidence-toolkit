#!/usr/bin/env python3
"""Measure the existing validator against controlled synthetic changes, offline."""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from care_evidence import check_event

VERSION = 1
SCENARIOS = {
    'missing_source': 'Erase the record source.',
    'naive_timestamp': 'Remove the explicit timestamp offset.',
    'missingness_contradiction': 'Mark an observation not_recorded but retain its text.',
    'duplicate_id': 'Reuse the first record ID on another record.',
    'invalid_timezone': 'Replace the timezone with a nonexistent IANA name.',
    'false_non_occurrence': 'Silently relabel an observed signal as not_occurring and erase its text.',
}


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def baseline(size: int) -> list[dict]:
    """Independent data specification; does not call the validator."""
    if not 16 <= size <= 10000:
        raise ValueError('size must be between 16 and 10000')
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    events = []
    for index in range(size):
        status = 'observed' if index % 4 < 2 else 'not_recorded' if index % 8 == 7 else 'not_occurring'
        text = ''
        if status == 'observed':
            text = 'The synthetic indicator was on.'
            if index % 16 == 0:
                # The quoted word is directly observed, not the recorder's inference.
                text = 'The synthetic indicator was on; its display read "maybe".'
        events.append({
            'event_id': f'synthetic-event-{index:05d}',
            'observed_at': (start + timedelta(minutes=index)).isoformat(),
            'timezone': 'UTC', 'source': 'generated-synthetic-indicator',
            'recorder_role': 'synthetic-recorder', 'observation': text,
            'interpretation': '', 'status': status, 'corrects': [], 'schema_version': 1,
        })
    return events


def select_rows(events: list[dict], rate: float, pattern: str, seed: int) -> list[int]:
    """Rates refer to eligible positive observations, not all records."""
    if not 0 <= rate <= 1:
        raise ValueError('rates must be between 0 and 1')
    if pattern not in ('scattered', 'block'):
        raise ValueError('unknown injection pattern')
    eligible = [i for i, event in enumerate(events) if i > 0 and event['status'] == 'observed']
    count = int(len(eligible) * rate)
    if pattern == 'scattered':
        # Stable hash ranking avoids dependence on random.sample implementations.
        return sorted(sorted(eligible, key=lambda i: digest([seed, i]))[:count])
    start = int(digest([seed, 'block']), 16) % (len(eligible) - count + 1)
    return eligible[start:start + count]


def inject(events: list[dict], scenario: str, rows: list[int]) -> tuple[list[dict], list[dict]]:
    if scenario not in SCENARIOS:
        raise ValueError('unknown scenario')
    result = deepcopy(events)
    changes = []
    for index in rows:
        event = result[index]
        if scenario == 'missing_source':
            after = {'source': ''}
        elif scenario == 'naive_timestamp':
            after = {'observed_at': datetime.fromisoformat(event['observed_at']).replace(tzinfo=None).isoformat()}
        elif scenario == 'missingness_contradiction':
            after = {'status': 'not_recorded'}
        elif scenario == 'duplicate_id':
            after = {'event_id': events[0]['event_id']}
        elif scenario == 'invalid_timezone':
            after = {'timezone': 'Invalid/SyntheticZone'}
        else:
            after = {'status': 'not_occurring', 'observation': '', 'interpretation': ''}
        changes.append({'row_index': index, 'before': {key: event[key] for key in after}, 'after': after})
        event.update(after)
    return result, changes


def ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def detection_metrics(total: int, injected: set[int], flagged: set[int]) -> dict:
    universe = set(range(total))
    if not injected <= universe or not flagged <= universe:
        raise ValueError('metric indexes outside dataset')
    tp, fp = len(injected & flagged), len(flagged - injected)
    fn, tn = len(injected - flagged), len(universe - injected - flagged)
    return {'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn,
            'precision': ratio(tp, tp + fp), 'recall': ratio(tp, tp + fn),
            'false_positive_rate': ratio(fp, fp + tn), 'retained_fraction': ratio(total - len(flagged), total)}


def signal_summary(events: list[dict]) -> dict:
    counts = Counter(event['status'] for event in events)
    known = counts['observed'] + counts['not_occurring']
    return {'rows': len(events), 'observed': counts['observed'],
            'not_occurring': counts['not_occurring'], 'not_recorded': counts['not_recorded'],
            'known_rows': known, 'observed_fraction_among_known': ratio(counts['observed'], known)}


def error_from_reference(summary: dict, reference: dict) -> float | None:
    value, target = summary['observed_fraction_among_known'], reference['observed_fraction_among_known']
    return None if value is None or target is None else abs(value - target)


def evaluate_case(events: list[dict], injected: set[int], reference: dict) -> tuple[dict, list[dict]]:
    predictions = []
    for index, event in enumerate(events):
        rules = sorted({issue['rule'] for issue in check_event(event)})
        if rules:
            predictions.append({'row_index': index, 'rules': rules})
    flagged = {item['row_index'] for item in predictions}
    raw = signal_summary(events)
    retained = signal_summary([event for i, event in enumerate(events) if i not in flagged])
    result = {'detection': detection_metrics(len(events), injected, flagged),
              'raw': raw, 'retained': retained,
              'raw_absolute_error': error_from_reference(raw, reference),
              'retained_absolute_error': error_from_reference(retained, reference)}
    return result, predictions


def build_benchmark(size: int, rates: list[float], seeds: list[int]) -> tuple[dict, dict]:
    if not rates or not seeds or len(set(rates)) != len(rates) or len(set(seeds)) != len(seeds):
        raise ValueError('rates and seeds must be non-empty and unique')
    events = baseline(size)
    reference = signal_summary(events)
    clean, clean_predictions = evaluate_case(events, set(), reference)
    evidence = {'format_version': VERSION, 'baseline': events,
                'clean_predictions': clean_predictions, 'cases': []}
    cases = []
    for seed in seeds:
        for pattern in ('scattered', 'block'):
            for rate in rates:
                selected = select_rows(events, rate, pattern, seed)
                for scenario in SCENARIOS:
                    corrupted, changes = inject(events, scenario, selected)
                    measured, predictions = evaluate_case(corrupted, set(selected), reference)
                    case_id = f'{scenario}-{pattern}-rate{rate!r}-seed{seed}'
                    flagged = {p['row_index'] for p in predictions}
                    originally_flagged = {p['row_index'] for p in clean_predictions}
                    measured['incremental_detection'] = {
                        'newly_flagged_injected': len(set(selected) & (flagged - originally_flagged)),
                        'already_flagged_injected': len(set(selected) & flagged & originally_flagged),
                    }
                    cases.append({'id': case_id, 'scenario': scenario, 'pattern': pattern,
                                  'requested_rate': rate, 'seed': seed,
                                  'injected_rows': len(selected), 'input_sha256': digest(corrupted), **measured})
                    evidence['cases'].append({'id': case_id, 'changes': changes,
                                              'predictions': predictions})
    sources = ['care_evidence.py', 'rules.json', 'benchmarks/quality_benchmark.py']
    report = {'format_version': VERSION, 'synthetic_only': True,
              'configuration': {'size': size, 'rates': rates, 'seeds': seeds,
                                'eligible_rows': sum(i > 0 and e['status'] == 'observed' for i, e in enumerate(events))},
              'source_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in sources},
              'baseline_sha256': digest(events), 'evidence_sha256': digest(evidence),
              'reference': reference, 'clean_control': clean, 'cases': cases}
    return report, evidence


def display(value: float | None) -> str:
    return 'n/a' if value is None else f'{100 * value:.2f}%'


def markdown(report: dict) -> str:
    config = report['configuration']
    clean = report['clean_control']['detection']
    lines = ['# Synthetic data-quality benchmark', '',
             'Generated by `benchmarks/quality_benchmark.py`. All records and injected problems are synthetic.', '',
             f"Configuration: {config['size']} rows, {config['eligible_rows']} eligible positive observations, "
             f"rates {config['rates']}, seeds {config['seeds']}.", '',
             f"Clean control: {clean['fp']} false alarms out of {config['size']} rows "
             f"({display(clean['false_positive_rate'])}). Recall is undefined because no problems were injected.", '',
             'Each row below is a separate paired experiment starting from the same baseline. Rates apply to eligible '
             'positive observations; block means consecutive eligible observations. Any validator finding flags a row, '
             'even if its rule does not identify the injected cause. New flags counts injected rows that were not flagged in the clean control. See evidence.json for exact rules and edits.', '',
             '| Scenario | Pattern | Rate | Seed | Injected | TP/FP/FN/TN | Precision | Recall | New flags | FPR | Retained | Raw error | Retained error |',
             '| --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for case in report['cases']:
        m = case['detection']
        counts = '/'.join(str(m[k]) for k in ('tp', 'fp', 'fn', 'tn'))
        lines.append(f"| {case['scenario']} | {case['pattern']} | {case['requested_rate']:g} | {case['seed']} | "
                     f"{case['injected_rows']} | {counts} | {display(m['precision'])} | {display(m['recall'])} | "
                     f"{case['incremental_detection']['newly_flagged_injected']} | {display(m['false_positive_rate'])} | {display(m['retained_fraction'])} | "
                     f"{display(case['raw_absolute_error'])} | {display(case['retained_absolute_error'])} |")
    lines += ['', '## Interpretation', '',
              '- Raw/retained error is the absolute difference in the observed-signal fraction among known statuses, '
              'relative to the clean baseline. Percentages in these error columns are percentage-point differences. '
              'This is a toy aggregation, not model accuracy or a clinical outcome.',
              '- The gate drops every flagged row; it does not repair data. Corruptions target positive observations '
              'deliberately, so dropping rows can increase selection bias. Retained rows and denominators are in metrics.json.',
              '- A literal display reading containing "maybe" is valid in this data specification. The current phrase '
              'heuristic flags it, exposing false alarms and incidental detections of otherwise undetected changes.',
              '- Silent relabelling cannot generally be discovered from a schema-valid row alone. Duplicate IDs require '
              'dataset context. These cases expose limits; their injected truth is available only to this evaluator.',
              '- No real-world detection rates, statistical confidence, learned-model performance, or clinical validity '
              'are established. Synthetic cases and rates were selected by the benchmark author.', '',
              '## Reproduction', '',
              'Use the configuration in metrics.json with the command in the benchmark guide. '
              'metrics.json and evidence.json are deterministic for the same configuration and source hashes. '
              'run.json records environment and elapsed time separately; timing is not a performance guarantee.', '']
    return '\n'.join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--size', type=int, default=120)
    parser.add_argument('--rates', type=float, nargs='+', default=[0.1, 0.3, 0.6])
    parser.add_argument('--seeds', type=int, nargs='+', default=[7, 19])
    parser.add_argument('--output', type=Path, required=True, help='new directory; existing paths are never overwritten')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('output already exists; choose a new directory')
    started = time.perf_counter()
    try:
        report, evidence = build_benchmark(args.size, args.rates, args.seeds)
    except ValueError as error:
        parser.error(str(error))
    elapsed = time.perf_counter() - started
    revision = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True)
    status = subprocess.run(['git', 'status', '--porcelain'], cwd=ROOT, capture_output=True, text=True)
    run = {'python': platform.python_version(), 'platform': platform.platform(),
           'elapsed_seconds_generation_and_evaluation': elapsed,
           'revision': revision.stdout.strip() if revision.returncode == 0 else None,
           'working_tree_dirty': bool(status.stdout) if status.returncode == 0 else None,
           'source_identity': 'Source SHA-256 values in metrics.json are authoritative, including uncommitted changes.'}
    args.output.mkdir(parents=True, exist_ok=False)
    for name, value in [('metrics.json', report), ('evidence.json', evidence), ('run.json', run)]:
        (args.output / name).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    (args.output / 'REPORT.md').write_text(markdown(report))
    print(f"Wrote {len(report['cases'])} synthetic cases and a clean control to {args.output}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
