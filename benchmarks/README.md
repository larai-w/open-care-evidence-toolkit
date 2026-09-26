# Controlled data-quality benchmark

This benchmark asks two questions:

1. Which deliberately injected problems does the current validator flag, and which does it miss?
2. What happens to a simple aggregate when every flagged record is dropped?

It generates synthetic indicator observations locally. No downloaded datasets, accounts, API calls, or training runs are involved. The generator and injection truth do not consult the validator.

## Reproduce

From the repository root, using Python 3.11 or later:

```bash
python3 benchmarks/quality_benchmark.py --output build/benchmark
```

The default run evaluates **72 paired cases**: six scenarios × three injection rates × two placement patterns × two seeds, plus a clean control. Each case starts from the same 120-record baseline; cases are not successive modifications of one dataset.

The output directory must not exist. To reproduce again, choose another path:

```bash
python3 benchmarks/quality_benchmark.py --output build/benchmark-repeat
```

The two runs' `metrics.json`, `evidence.json`, and `REPORT.md` should be byte-identical for identical source files and parameters. `run.json` contains environment, revision, dirty-tree state, and elapsed time, so it intentionally differs. Source file hashes in `metrics.json` identify the evaluated code even when the working tree was dirty.

Custom configuration:

```bash
python3 benchmarks/quality_benchmark.py --size 240 --rates 0 0.1 0.5 1 --seeds 7 19 31 --output build/benchmark-custom
```

## Synthetic data specification

There is one event per minute, starting from a fixed UTC timestamp. An eight-record cycle has four `observed` signals, three `not_occurring` signals, and one `not_recorded` slot. Unrecorded slots are excluded from the known-status denominator.

Some observed records quote the exact word **"maybe"** shown on a synthetic display. Under this benchmark's specification, that is a valid observation, not the recorder's speculation. These controls deliberately challenge the validator's simple phrase matching. This specification is a test oracle, not independent real-world annotation.

Injections target only `observed` records, excluding the first record (the ID-collision anchor). The rate denominator is this **eligible subset**, not all rows. The number changed is `floor(eligible_rows × requested_rate)`. At small sizes, a non-zero requested rate can change zero rows; counts and undefined metrics expose this explicitly.

- **Scattered:** rank eligible row indexes by a hash of seed and index.
- **Block:** select a consecutive slice of eligible observations. Intervening non-eligible records stay unchanged; this is not a simulation of a complete device outage.
- A seed changes placement only. It does not generate a new independent population. Results across seeds are sensitivity checks, not confidence intervals.

## Scenarios

| Scenario | Injection | What it probes |
| --- | --- | --- |
| `missing_source` | Empty the source field. | Provenance checking. |
| `naive_timestamp` | Remove the timestamp offset. | Temporal contract checking. |
| `missingness_contradiction` | Change status to `not_recorded`, retaining observation text. | Missingness consistency. |
| `duplicate_id` | Reuse the anchor's ID on another row. | Dataset-level identity checking, absent from the current row validator. |
| `invalid_timezone` | Insert a nonexistent timezone name. | A gap between non-empty text and a valid IANA name. |
| `false_non_occurrence` | Change an observed signal to `not_occurring`, erasing text. | A semantic error that a schema-valid row alone generally cannot reveal. |

The injection log is the evaluator's ground truth. It is never passed to `check_event`. Evaluation uses **row indexes**, because event IDs are deliberately corrupted in one scenario.

## Metrics and limitations

A row is flagged if the validator returns any issue. TP/FP/FN/TN compare flagged indexes to injected indexes. Recall measures how many changed rows were flagged, **not whether the correct cause was identified**. Precision and false-positive rate depend on this artificial mixture of cases.

An existing false alarm can incidentally flag a subsequently corrupted row. `incremental_detection` therefore separates newly flagged injected rows from injected rows that were already flagged in the clean control. Read these counts alongside recall; the evidence records the exact rule IDs.

Undefined ratios use JSON `null` and Markdown `n/a`. Zero predictions do not imply perfect precision; zero injected rows do not imply perfect recall. The clean control provides a separate false-alarm measurement.

The downstream probe is:

```text
observed fraction = observed / (observed + not_occurring)
```

Both raw and retained results are compared to the same clean-baseline fraction. Error is an absolute percentage-point difference. Dropping flagged rows is an intentionally simple policy, not a recommended data repair. Because injections target positives, rejection can worsen selection bias even when detection is correct. Denominators and retained status counts are included.

This experiment does not evaluate a learned model, clinical outcomes, real-world frequencies, or production scale. Six authored transformations and a fixed baseline cannot establish general detection performance. Overlapping corruptions, missing entire rows, clock drift, and valid corrections are not modelled in this first version.

## Inspect the evidence

| File | Contents |
| --- | --- |
| `REPORT.md` | Human-readable results and interpretation. |
| `metrics.json` | Per-case confusion counts, rates, aggregate errors, configuration, and hashes. |
| `evidence.json` | Baseline, row-indexed before/after patches, and all flagged rule IDs. |
| `run.json` | Environment and single-run generation/evaluation time, kept separate from deterministic results. |

Reconstruct a case by copying the baseline, applying its `after` patches to the given row indexes, and comparing its canonical JSON hash to `input_sha256`. Canonical JSON uses sorted keys, UTF-8, compact separators, and no NaN values (see `digest`). `before` values allow every edit to be audited.

See the [checked-in example report](../examples/benchmark-v1/REPORT.md). These are measured synthetic results, including failures; no pass threshold or leaderboard score is assigned.

The regression suite independently checks confusion-matrix arithmetic, undefined metrics, input immutability, edit replay, known false alarms/misses, selection-bias effects, deterministic output, and refusal to overwrite prior runs:

```bash
python3 -m unittest discover -s tests -p 'test_quality_benchmark.py' -v
```
