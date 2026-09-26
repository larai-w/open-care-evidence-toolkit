# Field-contract regression snapshots

These snapshots record the validator after CLI/browser field alignment. The directory name identifies this regression set; the event and bundle schema versions remain 1.

- `benchmark-metrics.json`: same configuration as `../benchmark-v1/metrics.json`; evidence remains `../benchmark-v1/evidence.json` and its digest is checked.
- `history-results.json`: the six-cutoff report from `benchmarks.history_replay.build_report()`.
- `bundle.json`: `care_export.export_bundle()` applied to `fixtures/integration-request.json`.

The Python suite checks these complete snapshots against current source hashes. It also compares them with the historical snapshots after excluding only source-hash dictionaries. Metrics, row decisions, features, selected history, and evidence must remain identical for these fixtures. Historical files are not overwritten.

All data is synthetic. Unchanged benchmark results do not establish clinical validity or model performance. See [the compatibility contract](../../docs/input-compatibility.md) for newly rejected malformed inputs.
