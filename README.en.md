# Open Care Evidence Toolkit (local MVP)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Topics](https://img.shields.io/badge/topics-care%20data--quality%20%7C%20synthetic%20data%20%7C%20python-blue)](https://github.com/larai-w/open-care-evidence-toolkit)
[![Releases](https://img.shields.io/github/v/release/larai-w/open-care-evidence-toolkit)](https://github.com/larai-w/open-care-evidence-toolkit/releases)
[![GitHub stars](https://img.shields.io/github/stars/larai-w/open-care-evidence-toolkit?style=social)](https://github.com/larai-w/open-care-evidence-toolkit/stargazers)

A tiny offline checker for synthetic observation records. It validates data quality without sending files anywhere. It does not make medical judgments, diagnoses, or store personal data.

Intended for research pilots, internal QA, and pre-production validation.  
[Japanese version](README.md)

Target users:

- developers validating care-data quality workflows
- researchers prototyping event schema and QA rules
- teams who want offline CSV/JSON validation before integrating into a platform

Reference docs: [SCHEMA.md](SCHEMA.md) / [SECURITY.md](SECURITY.md) / [CONTRIBUTING.md](CONTRIBUTING.md)  
Rule definitions are in [rules.json](rules.json) and shared by CLI + browser demo (including machine-readable `severity` as `high/medium/low`).

## Start here

```bash
git clone https://github.com/larai-w/open-care-evidence-toolkit
cd open-care-evidence-toolkit
python3 care_evidence.py fixtures/complete.json
```

### 1-minute quick start

- [1-minute quick start guide](examples/ONE_MINUTE.md)

## How to run (CLI)

```bash
python3 care_evidence.py fixtures/complete.json
python3 care_evidence.py fixtures/missing.json --format json
python3 care_evidence.py fixtures/complete.csv
```

JSON and CSV are supported. Default output is human-readable Markdown. Use `--format json` for machine-friendly CI outputs.

```bash
python3 care_evidence.py fixtures/complete.json --format json
```

### CSV coverage

The parser is tuned for realistic export edges before production.

CSV parsing is designed for practical care exports:

- UTF-8 BOM handling
- quoted commas
- embedded newlines inside quoted fields
- blank line skip

## Rule metadata

`rules.json` includes metadata fields for automation:

- `severity`: priority (`high`, `medium`, `low`)
- `area`: quality domain
- `machine_readable`: structured automation flag

## What it checks
- Required fields and schema version
- ISO 8601 timestamps with an explicit timezone offset
- Separation of observation from interpretation
- Source and recorder role provenance
- The difference between `not_recorded` and `not_occurring`
- Correction references to earlier event IDs

Use synthetic data only. The tool does not infer that an unrecorded event did not happen, and it does not provide clinical or emergency guidance.

## Contributing on GitHub

- [Latest release](https://github.com/larai-w/open-care-evidence-toolkit/releases)
- [Changelog](CHANGELOG.md)
- [Citation](CITATION.md)
- [Star this repository](https://github.com/larai-w/open-care-evidence-toolkit/stargazers)
- [Open an issue](https://github.com/larai-w/open-care-evidence-toolkit/issues/new)
- [Choose issue template](https://github.com/larai-w/open-care-evidence-toolkit/issues/new/choose)
- [Send a pull request](https://github.com/larai-w/open-care-evidence-toolkit/pulls)
- [Roadmap](ROADMAP.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Support](SUPPORT.md)
