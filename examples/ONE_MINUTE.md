# 1-minute quick start

## 1. Clone

```bash
 git clone https://github.com/larai-w/open-care-evidence-toolkit
 cd open-care-evidence-toolkit
```

## 2. Run CLI against a synthetic sample

```bash
python3 care_evidence.py fixtures/complete.json
```

Expected: no issues and output indicates all rules passed.

## 3. Check one synthetic problem case

```bash
python3 care_evidence.py fixtures/missing.json --format json
```

Expected: clear JSON list of issues (`timestamp_timezone`, `provenance`, `missingness_status`, etc.).

## 4. Run parser smoke tests for CSV edge cases

```bash
node tests/test_demo_csv.mjs
```

Expected: `browser CSV parser: quoted comma, BOM, and blank line PASS`

## 5. Try the browser demo

Open `demo.html` in a browser and click `合成サンプルを表示`.
You should see:

- summary line: `1イベント / 0件の問題` (or `1 event(s) / 0 issue(s)`)
- output line containing passed status
