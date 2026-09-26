# CLI and browser input compatibility

The event CLI and offline browser demo share the container contract below. The field profile below has shared, ordered rule-ID expectations in both implementations. This remains a small validator, not a full JSON Schema or clinical validator.

## Accepted containers

- JSON: one event object, a non-empty array of objects, or a wrapper with a non-empty `events` array. An existing `events` key never falls back to the outer object when its value is null or false.
- A leading UTF-8 BOM is accepted for JSON and CSV.
- CSV requires nonblank, unique header names and at least one record. Names are case sensitive and not trimmed. Every record must match the header's column count.
- CSV supports quoted commas and CR/LF, doubled quotes, CRLF record endings, and a missing final newline. Quotes inside unquoted fields are literal, matching Python's CSV reader. Unclosed quotes and text after closing quotes are rejected.
- Physical blank lines after the header are ignored. Empty-cell records (`,`) and quoted empty fields (`""`) remain records. A blank first line is an invalid header.
- Missing schema columns stay missing. The parser does not manufacture `corrects` or `schema_version`. Present CSV correction references split on semicolons, omitting empty segments; CSV versions matching `0*1` convert to numeric 1. Other version text stays text and is flagged, including `1.0`, Unicode digits, and trailing whitespace.

## Errors and recovery

Container errors produce CLI exit status 2, stderr diagnostics, and no stdout report. The browser clears prior results and displays an error that survives language changes. A subsequent valid input replaces it with new results. Missing event fields remain quality findings; the optional CLI `--fail-on-issues` gate is separate.

The browser translates the error prefix; parser detail text may remain English.

## Regression evidence

`fixtures/input-contract.json` contains 31 synthetic cases. `tests/test_demo_smoke.mjs` sends each to the actual CLI and browser script, comparing acceptance and event counts. Rejected cases also exercise a successful report followed by an error and language toggles. Before the fix, 25 cases failed at least one assertion; all 31 pass after it. CSV tests separately check quoted field contents and absence of fabricated columns.

```sh
node tests/test_demo_csv.mjs
node tests/test_demo_smoke.mjs
python3 -m unittest discover -s tests -v
```

The smoke runner uses `python3`, or the executable named by `PYTHON`. Browser tests use Node VM and a minimal DOM stub. They do not verify actual browsers, file-picker behavior, assistive technology, or mobile devices. They use temporary synthetic files and no network services.

## Shared field profile

| Rule | Contract |
| --- | --- |
| `required_fields` | One finding for missing keys. One additional finding if a supplied `event_id` is not a nonblank string or a supplied `schema_version` is not numeric 1. JSON `1.0` is numerically 1 and accepted; booleans and string `"1"` are rejected. |
| `timestamp_timezone` | One finding for an invalid timestamp and one for a missing/non-string/blank timezone. The grammar below is explicit. IANA membership is not checked. |
| `observation_interpretation` | One finding if observation or interpretation is not a string; content checks are skipped in that case. Otherwise flag selected speculative phrases, empty content for `observed`, and an additional interpretation-without-observation finding. |
| `provenance` | One finding if source or recorder role is not a nonblank string. |
| `missingness_status` | One finding for an unknown/non-string status. A `not_recorded` event containing nonblank observation or interpretation text gets another finding. |
| `correction_reference` | A supplied value must be a nonblank string or an array containing only nonblank strings. `[]` means no correction. Null, empty string, blank elements, numbers, and objects are flagged. An absent key gets only the required-fields finding for that absence. Target existence and uniqueness are not checked. |

No type coercion turns null, arrays, or booleans into observation text. Missing text keys use empty strings for content checks as well as producing a required-fields finding. The six existing rule IDs are retained; consumers should not assume one finding per rule.

Blankness uses the same explicit character set in both implementations: U+0009–000D, U+0020, U+0085, U+00A0, U+1680, U+2000–200A, U+2028–2029, U+202F, U+205F, U+3000, and U+FEFF. Values are checked without rewriting source text.

### Timestamp grammar

Use `YYYY-MM-DDTHH:MM:SS`, optionally followed by a dot and 1–6 fractional digits, then uppercase `Z` or `+HH:MM` / `-HH:MM`. All digits are ASCII. Years are 0001–9999; month/day must exist in the Gregorian calendar, including century leap-year rules. Hours are 00–23 and minutes/seconds 00–59. Offset hours are 00–23 and offset minutes 00–59, matching the supported Python offset range. `-00:00` is accepted syntactically without interpreting its special semantics.

Reject lowercase separators, spaces instead of `T`, week/basic dates, absent seconds, comma fractions, excess precision, leap seconds, hour 24, normalized invalid dates, and trailing whitespace. This is a deliberately narrow input profile, not support for every ISO 8601 representation. These checks do not normalize to UTC or reconcile the offset with the timezone name.

### Migration and regression evidence

This tightens acceptance within observation schema version 1. Rule IDs and CLI exit codes remain stable, but previously accepted malformed events can now produce findings and fail `--fail-on-issues`. Export also uses these checks, so malformed visible events may now become `quality_rejected`.

- Replace JSON null correction references with `[]` only when the record actually means no correction; repair missing/blank IDs at the source.
- Supply text fields as strings and use numeric schema version 1. JSON `1.0` is accepted by numeric value; history's separate wrapper still requires its own integer representation.
- Serialize timestamps using the documented grammar. Do not guess a missing offset or calendar date.

`fixtures/field-contract.json` defines 111 independently specified event cases. Python and browser tests check exact ordered rule IDs in both languages; Python had 94 failing subtests before the change (47 cases across two languages). `fixtures/field-csv-contract.json` adds 11 end-to-end CLI/browser cases for version conversion, correction IDs, timestamps, and quality-gate exit codes. The existing 31 container cases still pass.

Current snapshots are in [field-contract-v1](../examples/field-contract-v1/README.md). Historical snapshots are retained byte-for-byte. Tests check both current source hashes and equality of historical versus current metrics, predictions, history results, and feature decisions after excluding only source hashes. These unchanged synthetic results do not imply that arbitrary malformed inputs retain old behavior.

### Limits

Node VM checks are not real-browser or mobile validation. Exact parity is asserted for the shared corpus, not every Unicode case or parser extension (such as Python's nonstandard JSON NaN support). Unknown keys are allowed. Generic checks do not enforce IANA membership, ID uniqueness, or correction graph integrity. History replay retains its separate timestamp parser and stricter version, ordering, and predecessor contract; this change does not unify that parser with the generic event profile.
