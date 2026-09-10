# Open Care Evidence Toolkit (local MVP)

合成データの観察記録を、外部送信なしで検査する小さな試作です。医療判断・診断・個人データの保存は扱いません。 [English version](README.en.md)


現在は公開前のローカルMVPです。仕様は [SCHEMA.md](SCHEMA.md)、安全境界は [SECURITY.md](SECURITY.md)、貢献方法は [CONTRIBUTING.md](CONTRIBUTING.md) を参照してください。

検査規則のID・日英説明・修正ヒントは [rules.json](rules.json) を正本とし、CLIとブラウザデモで共有します。

公開準備の判断材料は [PUBLIC_LAUNCH_DRAFT.md](PUBLIC_LAUNCH_DRAFT.md) にあります（未公開）。

公開候補ファイルの一覧は [public-files.txt](public-files.txt) で管理します。`python3 export_public.py <空の出力先>` を実行すると、許可したファイルだけを別フォルダへコピーできます。

## 実行

```bash
python3 care_evidence.py fixtures/complete.json
python3 care_evidence.py fixtures/missing.json --format json
python3 care_evidence.py fixtures/complete.csv
python3 -m unittest discover -s tests -v
node tests/test_demo_csv.mjs
node tests/test_demo_smoke.mjs
```

JSONまたはCSVを入力できます。デフォルト出力は人が読むためのMarkdownです。`--format json`では機械処理しやすい結果を出します。

## ブラウザで試す

`demo.html`をブラウザで開き、JSON/CSVを選択してください。「合成サンプルを表示」でも動作を確認できます。デモは依存・サーバー・外部送信を使いません。

## 最小スキーマ

`event_id`, `observed_at`, `timezone`, `source`, `recorder_role`, `observation`, `interpretation`, `status`, `corrects`, `schema_version` を使います。`status` は `observed`（観察あり）、`not_recorded`（記録なし）、`not_occurring`（起きていないことを確認）のいずれかです。

このMVPはローカルのJSONだけを読み、ネットワーク・クラウド・アカウントを使いません。入力には実在の介護記録を入れず、合成データで試してください。
