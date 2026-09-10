# Open Care Evidence Toolkit (local MVP)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Topics](https://img.shields.io/badge/topics-care%20data--quality%20%7C%20synthetic%20data%20%7C%20python-blue)](https://github.com/larai-w/open-care-evidence-toolkit)
[![Releases](https://img.shields.io/github/v/release/larai-w/open-care-evidence-toolkit)](https://github.com/larai-w/open-care-evidence-toolkit/releases)

合成データの観察記録を、**外部送信なし**で品質チェックするローカルツールです。  
対象は研究・PoC・運用前の検証用途です。医療判断・診断・個人データの保存は扱いません。  
[English version](README.en.md)

対象利用者:  
- 介護データ品質を社内でレビューしたい開発者
- 外部APIなしで観察記録の検証を試したい研究者
- CSV/JSONデータの品質チェックを自動化したい開発チーム

関連情報: [SCHEMA.md](SCHEMA.md) / [SECURITY.md](SECURITY.md) / [CONTRIBUTING.md](CONTRIBUTING.md)  
ルールの定義は [rules.json](rules.json)。CLI・ブラウザデモ共通です（`severity`を含む `high/medium/low`）。

## まずここを読む

1. 合成データのサンプルで実行する
2. `--format json` でCI向けに結果を取得する
3. `demo.html` で直感的に結果を確認する

## 目次

1. [クイックスタート](#クイックスタート)
2. [使い方（CLI）](#使い方cli)
3. [ブラウザで試す](#ブラウザで試す)
4. [出力の見方](#出力の見方)
5. [最小スキーマ](#最小スキーマ)

## クイックスタート

```bash
git clone https://github.com/larai-w/open-care-evidence-toolkit
cd open-care-evidence-toolkit
python3 care_evidence.py fixtures/complete.json
```

## 使い方（CLI）

```bash
python3 care_evidence.py fixtures/complete.json
python3 care_evidence.py fixtures/missing.json --format json
python3 care_evidence.py fixtures/complete.csv
```

JSONまたはCSVを入力できます。デフォルト出力は人が読むためのMarkdownです。`--format json`では機械処理しやすい結果を出します。  
CIや自動化では、`--format json` のみを想定してください。

```bash
python3 care_evidence.py fixtures/complete.json --format json
```

## 出力の見方

### CSV対応（実データ取込前チェック）

実データ取り込み前のPoC向けに、現実的なCSVエッジケースを確認します。

- UTF-8 BOMの除去
- ダブルクォート内のカンマ
- ダブルクォート内改行
- 空行のスキップ

## 品質ルール

`rules.json` にはルールIDと説明だけでなく、運用で使いやすい以下のメタ情報も含まれます。

- `severity`: 高/中/低を示す優先度
- `area`: 判定カテゴリ
- `machine_readable`: 自動処理連携可否の明示

## ブラウザで試す

`demo.html`をブラウザで開き、JSON/CSVを選択してください。「合成サンプルを表示」でも動作を確認できます。デモは依存・サーバー・外部送信を使いません。

## 最小スキーマ

`event_id`, `observed_at`, `timezone`, `source`, `recorder_role`, `observation`, `interpretation`, `status`, `corrects`, `schema_version` を使います。`status` は `observed`（観察あり）、`not_recorded`（記録なし）、`not_occurring`（起きていないことを確認）のいずれかです。

このMVPはローカルのJSONだけを読み、ネットワーク・クラウド・アカウントを使いません。入力には実在の介護記録を入れず、合成データで試してください。

## GitHubでの進め方

- [最新リリース](https://github.com/larai-w/open-care-evidence-toolkit/releases)
- [問題を報告する](https://github.com/larai-w/open-care-evidence-toolkit/issues/new)
- [プルリクエスト](https://github.com/larai-w/open-care-evidence-toolkit/pulls)
