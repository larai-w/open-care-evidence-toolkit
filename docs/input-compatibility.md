# CLI and browser input compatibility

The event CLI and offline browser demo share the container contract below. This is not a full schema validator or a claim that every event-level finding is identical.

## Accepted containers

- JSON: one event object, a non-empty array of objects, or a wrapper with a non-empty `events` array. An existing `events` key never falls back to the outer object when its value is null or false.
- A leading UTF-8 BOM is accepted for JSON and CSV.
- CSV requires nonblank, unique header names and at least one record. Names are case sensitive and not trimmed. Every record must match the header's column count.
- CSV supports quoted commas and CR/LF, doubled quotes, CRLF record endings, and a missing final newline. Quotes inside unquoted fields are literal, matching Python's CSV reader. Unclosed quotes and text after closing quotes are rejected.
- Physical blank lines after the header are ignored. Empty-cell records (`,`) and quoted empty fields (`""`) remain records. A blank first line is an invalid header.
- Missing schema columns stay missing. The parser does not manufacture `corrects` or `schema_version`. Present CSV correction references split on semicolons, omitting empty segments; ordinary ASCII digit versions convert to numbers.

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

## Remaining field-level differences

| Area | Limitation |
| --- | --- |
| Timestamps | Python `datetime.fromisoformat` and JavaScript `Date` differ in accepted formats and calendar edge cases. |
| Blank/non-string fields | Truthiness and string conversion differ, including whitespace-only provenance and null observation values. |
| Corrections | The CLI accepts null without a correction-type finding; the browser flags null or absent references. Neither generic checker validates every list element or reference target. |
| Interpretation only | The CLI can emit an additional finding for an observed event with interpretation but no observation. |
| Versions | Generic checks require the key but do not enforce integer version 1. Unicode digits and JavaScript numeric precision are outside the tested CSV profile. |
| Names and IDs | Generic checks do not validate IANA timezone membership, unique IDs, or correction graphs. |

History replay and feature export use separate, stricter contracts for supported versions, IDs, ordering, and correction relationships. This change does not weaken those checks or regenerate benchmark outputs. Further field-level alignment should define accepted types and timestamp grammar and add shared rule-ID expectations before changing behavior.
