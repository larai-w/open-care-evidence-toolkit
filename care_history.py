#!/usr/bin/env python3
"""Resolve append-only synthetic observation history at an arrival-time cutoff."""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from care_evidence import REQUIRED, STATUSES


def timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str) or 'T' not in value:
        raise ValueError(f'{field} must be an ISO 8601 timestamp with an offset')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise ValueError(f'{field} must be an ISO 8601 timestamp with an offset') from None
    if parsed.tzinfo is None:
        raise ValueError(f'{field} requires a timezone offset')
    try:
        return parsed.astimezone(timezone.utc)
    except OverflowError:
        raise ValueError(f'{field} is outside the supported UTC date range') from None


def predecessor(value: object) -> str | None:
    if value == []:
        return None
    if isinstance(value, str) and value:
        return value
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], str) and value[0]:
        return value[0]
    raise ValueError('corrects must be [] or exactly one non-empty predecessor ID')


def summarise(events: list[dict]) -> dict:
    counts = Counter(event['status'] for event in events)
    known = counts['observed'] + counts['not_occurring']
    return {'records': len(events), 'observed': counts['observed'],
            'not_occurring': counts['not_occurring'], 'not_recorded': counts['not_recorded'],
            'known_records': known,
            'observed_fraction_among_known': counts['observed'] / known if known else None}


def snapshot(payload: dict, as_of: str) -> dict:
    """Only received_at is read before visibility filtering; never alter input."""
    cutoff = timestamp(as_of, 'as_of')
    if not isinstance(payload, dict) or type(payload.get('history_schema_version')) is not int or payload['history_schema_version'] != 1:
        raise ValueError('history_schema_version must be integer 1')
    events = payload.get('events')
    if not isinstance(events, list):
        raise ValueError('events must be an array')
    visible = {}
    excluded = 0
    for row, event in enumerate(events):
        if not isinstance(event, dict):
            raise ValueError(f'row {row} must be an object with received_at')
        received = timestamp(event.get('received_at'), f'row {row} received_at')
        if received > cutoff:
            excluded += 1
            continue
        missing = [field for field in (*REQUIRED, 'corrected_at') if field not in event]
        if missing:
            raise ValueError(f'row {row} missing fields: {", ".join(missing)}')
        event_id = event['event_id']
        if not isinstance(event_id, str) or not event_id:
            raise ValueError(f'row {row} requires a non-empty event_id')
        if event_id in visible:
            raise ValueError(f'duplicate visible event_id: {event_id}')
        if type(event['schema_version']) is not int or event['schema_version'] != 1:
            raise ValueError(f'{event_id}: only observation schema_version 1 is supported')
        for field in ('timezone', 'source', 'recorder_role'):
            if not isinstance(event[field], str) or not event[field].strip():
                raise ValueError(f'{event_id}: {field} must be a non-empty string')
        if any(not isinstance(event[field], str) for field in ('observation', 'interpretation')):
            raise ValueError(f'{event_id}: observation and interpretation must be strings')
        status = event['status']
        if not isinstance(status, str) or status not in STATUSES:
            raise ValueError(f'{event_id}: invalid status')
        if status == 'observed' and not event['observation'].strip():
            raise ValueError(f'{event_id}: observed requires observation text')
        if status == 'not_recorded' and (event['observation'].strip() or event['interpretation'].strip()):
            raise ValueError(f'{event_id}: not_recorded requires empty observation and interpretation')
        observed = timestamp(event['observed_at'], f'{event_id} observed_at')
        if observed > received:
            raise ValueError(f'{event_id}: observation cannot occur after receipt')
        parent = predecessor(event['corrects'])
        corrected = None
        if parent is None:
            if event['corrected_at'] is not None:
                raise ValueError(f'{event_id}: original records require corrected_at null')
        else:
            corrected = timestamp(event['corrected_at'], f'{event_id} corrected_at')
            if not observed <= corrected <= received:
                raise ValueError(f'{event_id}: corrected_at must fall between observation and receipt')
        visible[event_id] = {'event': deepcopy(event), 'received': received,
                             'observed': observed, 'corrected': corrected, 'parent': parent}

    children = {}
    for event_id, row in visible.items():
        parent_id = row['parent']
        if parent_id is None:
            continue
        if parent_id not in visible:
            raise ValueError(f'{event_id}: predecessor is not available at this cutoff: {parent_id}')
        parent = visible[parent_id]
        if row['observed'] != parent['observed']:
            raise ValueError(f'{event_id}: a correction must preserve the observation instant')
        if row['corrected'] < parent['received']:
            raise ValueError(f'{event_id}: correction predates receipt of its predecessor')
        if parent_id in children:
            raise ValueError(f'ambiguous correction branch from {parent_id}')
        children[parent_id] = event_id

    # Iterative traversal handles arbitrarily long chains without recursion limits.
    roots = sorted((key for key, row in visible.items() if row['parent'] is None),
                   key=lambda key: (visible[key]['observed'], key))
    selected, lineage, visited, superseded = [], [], set(), []
    for root in roots:
        chain, current = [], root
        while True:
            if current in visited:
                raise ValueError('correction history contains a cycle')
            visited.add(current)
            chain.append(current)
            if current not in children:
                break
            current = children[current]
        selected.append(visible[current]['event'])
        superseded.extend(chain[:-1])
        lineage.append({'root_event_id': root, 'selected_event_id': current, 'chain': chain})
    if len(visited) != len(visible):
        raise ValueError('correction history contains a cycle')
    return {'history_schema_version': 1, 'as_of': cutoff.isoformat(),
            'visible_versions': len(visible), 'excluded_after_cutoff': excluded,
            'superseded_event_ids': sorted(superseded), 'events': selected,
            'lineage': lineage, 'summary': summarise(selected)}


def render_markdown(result: dict) -> str:
    s = result['summary']
    fraction = s['observed_fraction_among_known']
    value = 'n/a' if fraction is None else f'{fraction:.2%}'
    lines = ['# As-of observation history', '', f"Cutoff (UTC): {result['as_of']}",
             f"Visible versions: {result['visible_versions']}; selected records: {s['records']}; "
             f"excluded after cutoff: {result['excluded_after_cutoff']}.", '',
             f"Observed: {s['observed']}; not occurring: {s['not_occurring']}; "
             f"not recorded: {s['not_recorded']}; fraction among known: {value}.", '',
             '```text']
    lines.extend(' -> '.join(item['chain']) for item in result['lineage'])
    lines += ['```', '', 'Synthetic history only. The fraction is a descriptive toy aggregate, not a medical or ML prediction.', '']
    return '\n'.join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--as-of', required=True, help='inclusive ISO 8601 arrival cutoff with timezone offset')
    parser.add_argument('--format', choices=('json', 'markdown'), default='json')
    args = parser.parse_args()
    try:
        result = snapshot(json.loads(args.input.read_text(encoding='utf-8-sig')), args.as_of)
    except (OSError, ValueError) as error:
        print(f'History error: {error}', file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False) if args.format == 'json' else render_markdown(result), end='\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
