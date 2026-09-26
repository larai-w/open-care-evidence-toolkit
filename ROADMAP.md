# Roadmap

## Implemented

- Offline JSON/CSV CLI checker with six rule categories and synthetic fixtures
- English/Japanese CLI diagnostics and a bilingual local browser demo
- Opt-in CLI quality gate with distinct finding and input-error exit codes
- CLI input-shape validation and BOM-aware CSV/JSON loading
- Regression tests for CSV quoting, malformed inputs, and missingness semantics
- English default README with a separate Japanese guide
- Python 3.11–3.13 CI, browser checks, and public-content checks
- Controlled synthetic data-quality benchmark with replayable injections, false-alarm measurements, and aggregate-bias comparisons

## Next candidates

1. Define observation, arrival, and correction time semantics; reproduce the information available at a chosen cutoff.
2. Specify stronger field types and schema-version checks, then implement them consistently in the CLI and browser.
3. Validate event-ID uniqueness and correction references across a dataset, with an explicit policy for references outside the supplied file.
4. Expand shared synthetic fixtures to measure CLI/browser agreement and document intentional differences.
5. Add batch reports and comparisons against an earlier report once the single-file contract is stable.

These are candidates, not implemented features or delivery commitments. Scope remains offline validation of synthetic records; model training and clinical evaluation are outside the current implementation.
