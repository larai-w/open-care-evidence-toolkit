# Changelog

## Unreleased

### Added

- Opt-in JSON history resolver with arrival-time cutoffs, immutable input handling, correction lineage, and explicit errors for ambiguous or incomplete visible histories.
- Synthetic six-cutoff replay report demonstrating the difference between as-of data and retroactive use of later arrivals, with source/input hashes and temporal-boundary regression tests.

- Controlled synthetic benchmark: six injection scenarios, scattered/block placement, configurable rates and seeds, a clean challenge control, and replayable evidence.
- Detection/false-alarm metrics and a paired aggregate comparison showing how rejection can introduce selection bias; undefined metrics remain null.

- English CLI diagnostics by default and `--lang ja` for Japanese output.
- Opt-in `--fail-on-issues` quality gate: exit 1 for findings, exit 2 for invalid input, with JSON output preserved for quality findings.
- Temporary-input regression coverage for language-independent findings, quality gates, malformed JSON/CSV, and BOM-prefixed CSV with quoted newlines.

### Fixed

- Reject empty datasets, non-object events, duplicate/blank CSV headers, and row-width mismatches with a concise error instead of a traceback or a misleading clean report.
- Accept UTF-8 BOMs in JSON and CSV inputs.
- Report a non-string status as a quality issue instead of crashing on unhashable values.

### Changed

- English is now the default README; Japanese documentation is preserved in `README.ja.md`.
- Default human-readable CLI output and JSON diagnostic messages are now English. JSON keys and rule IDs remain unchanged. Use `--lang ja` to retain Japanese diagnostics.

## 2026-09-10

### Added

- Added machine-readable rule metadata fields (`severity`, `area`, `machine_readable`) to `rules.json`.
- Added a11y-focused result-region semantics improvements in `demo.html`.
- Added stronger CSV parser edge-case coverage tests.
- Improved repository onboarding: badges, usage flow, and contribution links in READMEs.

### Changed

- Added GitHub issue and PR templates to support external contribution.
- Added project governance docs (`CODE_OF_CONDUCT.md`, `SUPPORT.md`) for clearer community expectations.

### Released

- `v0.1.1` — follow-on improvements on parser coverage, accessibility, and rule metadata.
