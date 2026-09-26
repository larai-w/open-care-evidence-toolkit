# Roadmap

## Implemented

- Offline JSON/CSV CLI checker with six rule categories and synthetic fixtures
- English/Japanese CLI diagnostics and a bilingual local browser demo
- Opt-in CLI quality gate with distinct finding and input-error exit codes
- CLI input-shape validation and BOM-aware CSV/JSON loading
- Regression tests for CSV quoting, malformed inputs, and missingness semantics
- English default README with a separate Japanese guide
- Python 3.11–3.13 CI, browser checks, and public-content checks

## Next candidates

1. Specify stronger field types and schema-version checks, then implement them consistently in the CLI and browser.
2. Validate event-ID uniqueness and correction references across a dataset, with an explicit policy for references outside the supplied file.
3. Expand shared synthetic fixtures to measure CLI/browser agreement and document intentional differences.
4. Add batch reports and comparisons against an earlier report once the single-file contract is stable.

These are candidates, not implemented features or delivery commitments. Scope remains offline validation of synthetic records; model training and clinical evaluation are outside the current implementation.
