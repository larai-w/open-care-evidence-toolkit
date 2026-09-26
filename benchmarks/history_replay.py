#!/usr/bin/env python3
"""Reproduce the fixed synthetic arrival/correction example without network IO."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from care_history import snapshot, summarise, timestamp

CUTOFFS = [f'2026-01-01T{time}:00+00:00' for time in ('09:00', '10:00', '10:20', '10:30', '11:00', '12:00')]


def build_report() -> dict:
    payload = json.loads((ROOT / 'fixtures/history.json').read_text())
    snapshots = [snapshot(payload, cutoff) for cutoff in CUTOFFS]
    target = snapshots[1]
    cutoff = timestamp(target['as_of'], 'as_of')
    # Deliberately wrong: resolve at the last arrival, then filter by observation time only.
    naive = summarise([event for event in snapshots[-1]['events']
                       if timestamp(event['observed_at'], 'observed_at') <= cutoff])
    correct = target['summary']['observed_fraction_among_known']
    wrong = naive['observed_fraction_among_known']
    return {'synthetic_only': True, 'snapshots': snapshots,
            'comparison': {'target_cutoff': target['as_of'],
                           'incorrect_later_cutoff': snapshots[-1]['as_of'],
                           'as_of_summary': target['summary'], 'naive_latest_summary': naive,
                           'absolute_fraction_difference': abs(correct - wrong)},
            'source_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                              for name in ('care_history.py', 'care_evidence.py', 'fixtures/history.json', 'benchmarks/history_replay.py')}}


def render(report: dict) -> str:
    lines = ['# Synthetic history replay', '',
             'A fixed example of delayed arrival and two revisions. All records are generated synthetic data.', '',
             '| Cutoff (UTC) | Visible versions | Selected logical records | Known statuses | Observed fraction | Selected event IDs |',
             '| --- | ---: | ---: | ---: | ---: | --- |']
    for result in report['snapshots']:
        s = result['summary']
        fraction = s['observed_fraction_among_known']
        value = 'n/a' if fraction is None else f'{fraction:.2%}'
        lines.append(f"| {result['as_of']} | {result['visible_versions']} | {s['records']} | "
                     f"{s['known_records']} | {value} | {', '.join(e['event_id'] for e in result['events']) or 'none'} |")
    comparison = report['comparison']
    correct = comparison['as_of_summary']['observed_fraction_among_known']
    naive = comparison['naive_latest_summary']['observed_fraction_among_known']
    lines += ['', '## Why arrival time matters', '',
              f"At 10:00 UTC, the available records produce {correct:.2%}. Resolving the history at 12:00 "
              f"and using those latest records retroactively produces {naive:.2%}, a difference of "
              f"{100 * comparison['absolute_fraction_difference']:.2f} percentage points.", '',
              'The late record was observed at 09:10 but arrived at 11:00. The first revision was authored at '
              '10:15 and arrived at 10:30; the second arrived at 12:00. None was available at 10:00. '
              'A not_recorded slot remains unknown and is excluded from the known-status denominator.', '',
              'The as-of result describes what the recorded system could know then; it does not claim that the '
              'earlier observation was ultimately true. No ML model or clinical outcome is evaluated.', '',
              '## Reproduce', '', '```bash',
              'python3 benchmarks/history_replay.py --output build/history-replay', '```', '',
              'Use a new output directory. `results.json` contains the selected records, complete lineage, '
              'counts, and hashes of the input and source files. Compare it byte-for-byte across reruns with '
              'unchanged sources. See [history contract](../../HISTORY.md) for cutoff and error policies.', '']
    return '\n'.join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('output already exists; choose a new directory')
    report = build_report()
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'results.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    (args.output / 'REPORT.md').write_text(render(report))
    print(f'Wrote six synthetic snapshots and comparison to {args.output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
