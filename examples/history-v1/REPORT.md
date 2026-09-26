# Synthetic history replay

A fixed example of delayed arrival and two revisions. All records are generated synthetic data.

| Cutoff (UTC) | Visible versions | Selected logical records | Known statuses | Observed fraction | Selected event IDs |
| --- | ---: | ---: | ---: | ---: | --- |
| 2026-01-01T09:00:00+00:00 | 0 | 0 | 0 | n/a | none |
| 2026-01-01T10:00:00+00:00 | 2 | 2 | 1 | 100.00% | synthetic-a, synthetic-c |
| 2026-01-01T10:20:00+00:00 | 2 | 2 | 1 | 100.00% | synthetic-a, synthetic-c |
| 2026-01-01T10:30:00+00:00 | 3 | 2 | 1 | 0.00% | synthetic-a-r1, synthetic-c |
| 2026-01-01T11:00:00+00:00 | 4 | 3 | 2 | 0.00% | synthetic-a-r1, synthetic-b, synthetic-c |
| 2026-01-01T12:00:00+00:00 | 5 | 3 | 2 | 50.00% | synthetic-a-r2, synthetic-b, synthetic-c |

## Why arrival time matters

At 10:00 UTC, the available records produce 100.00%. Resolving the history at 12:00 and using those latest records retroactively produces 50.00%, a difference of 50.00 percentage points.

The late record was observed at 09:10 but arrived at 11:00. The first revision was authored at 10:15 and arrived at 10:30; the second arrived at 12:00. None was available at 10:00. A not_recorded slot remains unknown and is excluded from the known-status denominator.

The as-of result describes what the recorded system could know then; it does not claim that the earlier observation was ultimately true. No ML model or clinical outcome is evaluated.

## Reproduce

```bash
python3 benchmarks/history_replay.py --output build/history-replay
```

Use a new output directory. `results.json` contains the selected records, complete lineage, counts, and hashes of the input and source files. Compare it byte-for-byte across reruns with unchanged sources. See [history contract](../../HISTORY.md) for cutoff and error policies.
