# Open Care Evidence Toolkit

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Topics](https://img.shields.io/badge/topics-care%20data--quality%20%7C%20synthetic%20data%20%7C%20python-blue)](https://github.com/larai-w/open-care-evidence-toolkit)
[![CI](https://github.com/larai-w/open-care-evidence-toolkit/actions/workflows/test.yml/badge.svg)](https://github.com/larai-w/open-care-evidence-toolkit/actions/workflows/test.yml)
[![Releases](https://img.shields.io/github/v/release/larai-w/open-care-evidence-toolkit)](https://github.com/larai-w/open-care-evidence-toolkit/releases)
[![GitHub stars](https://img.shields.io/github/stars/larai-w/open-care-evidence-toolkit?style=social)](https://github.com/larai-w/open-care-evidence-toolkit/stargazers)

English | [日本語](README.ja.md)

An offline Python toolkit for checking the quality of synthetic care observation records. It reads JSON or CSV and produces a deterministic report of missing fields, timestamp issues, provenance gaps, and inconsistent missingness labels.

Use it to explore data validation before building an analytics or machine learning pipeline. The repository contains a rule-based validator, synthetic fixtures, automated checks, and a standalone browser demo. It does not train or evaluate a machine learning model, and it does not provide medical judgments or diagnoses.

## Quick start

Use Python 3.11 or later; CI covers Python 3.11, 3.12, and 3.13. The CLI uses the Python standard library and requires no API keys or third-party packages.

```bash
git clone https://github.com/larai-w/open-care-evidence-toolkit.git
cd open-care-evidence-toolkit
python3 care_evidence.py fixtures/complete.json --format json
```

The complete fixture produces `"issues": 0`. Compare it with a deliberately incomplete fixture:

```bash
python3 care_evidence.py fixtures/missing.json --format json
python3 care_evidence.py fixtures/complete.csv --format json
```

The JSON report contains `events`, a total `issues` count, and per-event `results` with rule IDs and diagnostic messages. Rule IDs and JSON keys stay the same across languages. Diagnostics and Markdown output default to English; use `--lang ja` for Japanese. Input-error details from the parser may remain in English.

### Use as a CI quality gate

```bash
python3 care_evidence.py fixtures/complete.json --format json --fail-on-issues
python3 care_evidence.py fixtures/missing.json --format json --fail-on-issues
python3 care_evidence.py fixtures/missing.json --lang ja
```

The second command deliberately returns exit code **1** while still printing the complete JSON report.

| Exit code | Meaning |
| --- | --- |
| `0` | Input was inspected; with `--fail-on-issues`, no quality issues were found. |
| `1` | Quality issues were found and `--fail-on-issues` was enabled. |
| `2` | Input could not be read or parsed, its container structure was invalid, or CLI arguments were invalid. |

Without `--fail-on-issues`, findings remain report-only for compatibility. Input errors go to stderr and produce no report on stdout. Empty datasets, non-object events, duplicate/blank CSV headers, and CSV row-width mismatches are rejected instead of being reported as clean data.

## Why these checks matter

Observation data can lose meaning before it reaches a model. An absent record can be mistaken for a negative example, an interpretation can be stored as an observation, or a timestamp can lose its timezone context. This toolkit makes a small set of those assumptions explicit and inspectable.

| Rule | Current check |
| --- | --- |
| `required_fields` | Checks that all ten schema keys are present. |
| `timestamp_timezone` | Parses the observation timestamp, requires an offset, and checks that the timezone field is non-empty. |
| `observation_interpretation` | Flags selected speculative phrases and an empty observation when the status is `observed`. |
| `provenance` | Requires a non-empty source and recorder role. |
| `missingness_status` | Checks the status vocabulary and rejects observation or interpretation text for `not_recorded`. |
| `correction_reference` | Checks the outer type of a supplied correction reference. |

The distinction between `not_recorded` and `not_occurring` is deliberate: absence of a record is not evidence that an event did not happen.

## Input contract

JSON input can be a single event, an array of events, or an object with an `events` array. CSV input uses the same field names as column headers.

| Field | Intended meaning |
| --- | --- |
| `event_id` | Event identifier. |
| `observed_at` | ISO 8601 observation timestamp with an explicit offset. |
| `timezone` | IANA timezone name, such as `Pacific/Auckland`. |
| `source` | Origin of the synthetic record. |
| `recorder_role` | Recorder role, without a person's name. |
| `observation` | What was observed. |
| `interpretation` | What the observation may mean; an empty string means no interpretation. |
| `status` | `observed`, `not_recorded`, or `not_occurring`. |
| `corrects` | Earlier event ID or a list of IDs; use `[]` when there is no correction. |
| `schema_version` | Input schema version. |

For CSV, separate multiple correction IDs with semicolons. See the [synthetic fixtures](fixtures/) for runnable examples and [schema notes in Japanese](SCHEMA.md) for further context.

## Review the implementation

- [Python validator](care_evidence.py): parsing, individual checks, and Markdown/JSON report generation.
- [Rule catalogue](rules.json): rule IDs, English/Japanese labels, severity, quality area, and automation metadata. The CLI report references rule IDs; it does not embed all catalogue metadata in every issue.
- [Tests](tests/): validator behaviour, synthetic inputs, browser CSV parsing, and browser smoke checks.
- [CI workflow](.github/workflows/test.yml): Python version matrix, browser checks, and a public-content boundary check.

To run the existing checks locally, install Python and Node.js, then run:

```bash
python3 -m unittest discover -s tests -v
node tests/test_demo_csv.mjs
node tests/test_demo_smoke.mjs
python3 scripts/check_public_repo.py
```

## Browser demo

Open [demo.html](demo.html) locally in a browser. Select a synthetic JSON/CSV file or click **合成サンプルを表示** (Show synthetic sample). Click **English** to switch the interface and results to English. The demo runs without a server, external dependencies, or file uploads.

The CLI and browser have checks for UTF-8 BOMs, quoted commas, quoted newlines, and blank lines. The CLI additionally rejects malformed input containers and ambiguous CSV shapes. Full parser and validation parity between the two interfaces is not yet guaranteed.

## Scope and limitations

- Use synthetic data only. The repository is an exploratory data-quality MVP, with no clinical validation or production-readiness claim.
- The checks are deterministic heuristics, not a learned model or a complete schema validator.
- The current implementation does not verify IANA timezone names, enforce schema-version values, detect duplicate event IDs, or resolve correction IDs against earlier events. Correction-list element types are not fully validated.
- The observation/interpretation check matches a small set of phrases; it does not establish whether a statement is factually correct.
- No model performance, clinical outcomes, or real-world deployment results are demonstrated here.

## Project resources

[One-minute guide](examples/ONE_MINUTE.md) · [Releases](https://github.com/larai-w/open-care-evidence-toolkit/releases) · [Changelog](CHANGELOG.md) · [Citation](CITATION.md)

Some supporting documents remain in Japanese: [Contributing](CONTRIBUTING.md), [Security](SECURITY.md), [Roadmap](ROADMAP.md), [Code of Conduct](CODE_OF_CONDUCT.md), and [Support](SUPPORT.md).

Licensed under the [MIT License](LICENSE).
