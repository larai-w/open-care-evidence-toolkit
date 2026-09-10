# Open Care Evidence Toolkit (local MVP)

A tiny offline checker for synthetic observation records. It checks data quality without making medical judgments, diagnoses, or storing personal data.

This is currently a local MVP. See [SCHEMA.md](SCHEMA.md) for the input contract, [SECURITY.md](SECURITY.md) for the safety boundary, and [CONTRIBUTING.md](CONTRIBUTING.md) for contribution rules. Rule IDs, Japanese/English labels, and repair hints live in [rules.json](rules.json) and are shared by the CLI and browser demo.

## Run it

```bash
python3 care_evidence.py fixtures/complete.json
python3 care_evidence.py fixtures/missing.json --format json
python3 care_evidence.py fixtures/complete.csv
python3 -m unittest discover -s tests -v
```

The default output is human-readable Markdown. Use `--format json` for machine-readable output. The browser-only demo is [demo.html](demo.html): choose a JSON/CSV file or click the synthetic sample button. No server, account, dependency, or network request is required.

## What it checks

- Required fields and schema version
- ISO 8601 timestamps with an explicit timezone offset
- Separation of observation from interpretation
- Source and recorder role provenance
- The difference between `not_recorded` and `not_occurring`
- Correction references to earlier event IDs

Use synthetic data only. The tool does not infer that an unrecorded event did not happen, and it does not provide clinical or emergency guidance.
