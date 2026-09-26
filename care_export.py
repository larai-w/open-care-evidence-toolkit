#!/usr/bin/env python3
"""Export synthetic as-of summaries for a separate experiment-input consumer."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from care_evidence import check_event
from care_history import snapshot

ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / 'contracts/care-bundle-v1.json'
CONTRACT = json.loads(CONTRACT_PATH.read_text())


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def export_bundle(request: dict) -> dict:
    if not isinstance(request, dict) or request.get('dataset_kind') != 'synthetic':
        raise ValueError('only explicitly synthetic requests are supported')
    samples = request.get('samples')
    if not isinstance(samples, list) or not samples:
        raise ValueError('samples must be a non-empty array')
    rows, seen = [], set()
    for sample in samples:
        if not isinstance(sample, dict):
            raise ValueError('each sample must be an object')
        for field in ('sample_id', 'subject_id'):
            if not isinstance(sample.get(field), str) or not sample[field].strip():
                raise ValueError(f'{field} must be a non-empty string')
        if sample['sample_id'] in seen:
            raise ValueError('duplicate sample_id')
        seen.add(sample['sample_id'])
        state = snapshot(sample.get('history'), sample.get('as_of'))
        issues = [{'event_id': event['event_id'], 'rule': issue['rule']}
                  for event in state['events'] for issue in check_event(event)]
        summary = state['summary']
        decision = 'quality_rejected' if issues else 'insufficient_data' if not summary['known_records'] else 'eligible'
        features = None if decision != 'eligible' else {
            'observed_fraction': summary['observed_fraction_among_known'],
            'known_count': summary['known_records'], 'unknown_count': summary['not_recorded'],
        }
        rows.append({'sample_id': sample['sample_id'], 'subject_id': sample['subject_id'],
                     'as_of': state['as_of'], 'decision': decision, 'features': features,
                     'quality_issues': issues,
                     'audit': {'history_sha256': digest(sample['history']),
                               'selected_versions': [{key: event[key] for key in
                                   ('event_id', 'observed_at', 'received_at', 'status')} for event in state['events']],
                               'lineage': state['lineage']}})
    return {key: CONTRACT[key] for key in ('contract_version', 'dataset_kind', 'feature_set', 'feature_names')} | {
        'contract_sha256': hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest(),
        'rows': sorted(rows, key=lambda row: row['sample_id']),
        'audit': {'request_sha256': digest(request), 'producer': 'open-care-evidence-toolkit',
                  'source_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                      for name in ('care_export.py', 'care_history.py', 'care_evidence.py', 'rules.json')}}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('output already exists; choose a new file')
    try:
        bundle = export_bundle(json.loads(args.input.read_text(encoding='utf-8-sig')))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8') as output:
            output.write(json.dumps(bundle, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    except (OSError, ValueError) as error:
        print(f'Export error: {error}', file=sys.stderr)
        return 2
    print(f'Exported {len(bundle["rows"])} synthetic samples to {args.output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
