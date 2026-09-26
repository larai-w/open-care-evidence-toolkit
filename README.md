# Open Care Evidence Toolkit

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Topics](https://img.shields.io/badge/topics-care%20data--quality%20%7C%20synthetic%20data%20%7C%20python-blue)](https://github.com/larai-w/open-care-evidence-toolkit)
[![CI](https://github.com/larai-w/open-care-evidence-toolkit/actions/workflows/test.yml/badge.svg)](https://github.com/larai-w/open-care-evidence-toolkit/actions/workflows/test.yml)
[![Releases](https://img.shields.io/github/v/release/larai-w/open-care-evidence-toolkit)](https://github.com/larai-w/open-care-evidence-toolkit/releases)
[![GitHub stars](https://img.shields.io/github/stars/larai-w/open-care-evidence-toolkit?style=social)](https://github.com/larai-w/open-care-evidence-toolkit/stargazers)

English | [日本語](README.ja.md)

An offline Python toolkit for checking the quality of synthetic care observation records. It reads JSON or CSV and produces a deterministic report of missing fields, timestamp issues, provenance gaps, and inconsistent missingness labels.

Use it to explore data validation before building an analytics or machine learning pipeline. The repository contains a rule-based validator, synthetic fixtures, automated checks, and a standalone browser demo. It does not train or evaluate a machine learning model, and it does not provide medical judgments or diagnoses.

## Evaluate the validator

The [controlled benchmark](benchmarks/README.md) goes beyond valid/invalid examples: it injects six kinds of synthetic data problems and measures detection, false alarms, retained data, and changes to a simple aggregate.

```bash
python3 benchmarks/quality_benchmark.py --output build/benchmark
```

The default run produces 72 paired cases and a clean control, with replayable edits and source/data hashes. Read the [example results](examples/benchmark-v1/REPORT.md), including missed problems and cases where rejecting records worsens aggregate bias. This is a synthetic data-quality experiment, not an ML performance evaluation.

## Replay history at a cutoff

The [history resolver](HISTORY.md) distinguishes observation time, revision authoring time, and arrival time. It selects only versions available at the requested cutoff and retains correction lineage.

```bash
python3 care_history.py fixtures/history.json --as-of 2026-01-01T10:00:00Z
python3 benchmarks/history_replay.py --output build/history-replay
```

Read the [synthetic replay results](examples/history-v1/REPORT.md): using later arrivals retroactively changes the example aggregate from 100% to 50%. This illustrates temporal leakage in a toy aggregation; no learned model is evaluated. Ambiguous branches, cycles, unavailable predecessors, and impossible time ordering are rejected explicitly.

## Connect a downstream consumer

The [synthetic integration](INTEGRATION.md) exports as-of summaries with quality decisions and provenance to [abstain-har](https://github.com/larai-w/abstain-har). The consumer verifies feature values, availability cutoffs, and subject-disjoint input splits. Six synthetic samples produce four eligible rows and two explicit exclusions.

```bash
python3 care_export.py fixtures/integration-request.json --output build/care-bundle.json
```

The feature set is a three-value synthetic indicator summary. It is not a HAR sensor representation, and this path performs no model training or prediction.

Current source-hashed regression snapshots are in [field-contract-v1](examples/field-contract-v1/README.md). Earlier benchmark, history, and integration examples remain unchanged as historical evidence.

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
| `required_fields` | Requires all ten keys, a nonblank string event ID, and numeric schema version 1. |
| `timestamp_timezone` | Checks the documented timestamp grammar, calendar date, offset, and nonblank timezone string. |
| `observation_interpretation` | Requires text fields to be strings; flags selected speculative phrases and missing observed content. |
| `provenance` | Requires nonblank strings for source and recorder role. |
| `missingness_status` | Checks the status vocabulary and rejects observation or interpretation text for `not_recorded`. |
| `correction_reference` | Requires a nonblank string ID or an array of nonblank string IDs; accepts `[]`. |

The distinction between `not_recorded` and `not_occurring` is deliberate: absence of a record is not evidence that an event did not happen.

## Input contract

JSON input can be a single event, a non-empty array of event objects, or an object with a non-empty `events` array. CSV input uses the same field names as column headers. Both entry points reject malformed containers before producing a report. See the [CLI/browser compatibility contract](docs/input-compatibility.md) for supported CSV syntax, regression cases, and field-level rules and migration notes.

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
| `schema_version` | Numeric value 1 (booleans and JSON strings are invalid). |

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

The CLI and browser share synthetic container and field-contract fixtures, including exact ordered rule IDs. See the [compatibility contract](docs/input-compatibility.md) for timestamp grammar, CSV conversion, migration changes, and test limits.

## Scope and limitations

- Use synthetic data only. The repository is an exploratory data-quality MVP, with no clinical validation or production-readiness claim.
- The checks are deterministic heuristics, not a learned model or a complete schema validator.
- Generic event checks do not verify IANA timezone membership, detect duplicate IDs, or resolve correction targets. History replay has its own stricter graph and temporal contract.
- The observation/interpretation check matches a small set of phrases; it does not establish whether a statement is factually correct.
- No model performance, clinical outcomes, or real-world deployment results are demonstrated here.

## Project resources

[One-minute guide](examples/ONE_MINUTE.md) · [Releases](https://github.com/larai-w/open-care-evidence-toolkit/releases) · [Changelog](CHANGELOG.md) · [Citation](CITATION.md)

Some supporting documents remain in Japanese: [Contributing](CONTRIBUTING.md), [Security](SECURITY.md), [Roadmap](ROADMAP.md), [Code of Conduct](CODE_OF_CONDUCT.md), and [Support](SUPPORT.md).

Licensed under the [MIT License](LICENSE).
