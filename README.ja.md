# Open Care Evidence Toolkit

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Topics](https://img.shields.io/badge/topics-care%20data--quality%20%7C%20synthetic%20data%20%7C%20python-blue)](https://github.com/larai-w/open-care-evidence-toolkit)
[![CI](https://github.com/larai-w/open-care-evidence-toolkit/actions/workflows/test.yml/badge.svg)](https://github.com/larai-w/open-care-evidence-toolkit/actions/workflows/test.yml)
[![Releases](https://img.shields.io/github/v/release/larai-w/open-care-evidence-toolkit)](https://github.com/larai-w/open-care-evidence-toolkit/releases)
[![GitHub stars](https://img.shields.io/github/stars/larai-w/open-care-evidence-toolkit?style=social)](https://github.com/larai-w/open-care-evidence-toolkit/stargazers)

合成データの観察記録を、**外部送信なし**で品質チェックするローカルツールです。
対象は研究・PoC・運用前の検証用途です。医療判断・診断・個人データの保存は扱いません。
[English](README.md) | 日本語

対象利用者:
- 介護データ品質を社内でレビューしたい開発者
- 外部APIなしで観察記録の検証を試したい研究者
- CSV/JSONデータの品質チェックを自動化したい開発チーム

関連情報: [SCHEMA.md](SCHEMA.md) / [SECURITY.md](SECURITY.md) / [CONTRIBUTING.md](CONTRIBUTING.md)
ルールの定義は [rules.json](rules.json)。CLI・ブラウザデモ共通です（`severity`を含む `high/medium/low`）。

## 検査の性能と限界を測る

[合成データの評価手順（英語）](benchmarks/README.md)では、6種類の問題を注入し、検出率・誤検出・残ったデータ量・集計の偏りを測れます。

```bash
python3 benchmarks/quality_benchmark.py --output build/benchmark
```

既定では72条件と正常対照を評価し、変更履歴と再現用ハッシュも保存します。[実測レポート](examples/benchmark-v1/REPORT.md)には見逃しや、除外によって偏りが悪化するケースも含みます。合成データ上の検証であり、ML精度や臨床的有効性の評価ではありません。

## 指定時点で分かっていた情報を再現する

[履歴処理の仕様（英語）](HISTORY.md)では観察・訂正作成・到着の時刻を区別します。指定時点で未到着の記録は使わず、訂正のつながりも出力します。

```bash
python3 care_history.py fixtures/history.json --as-of 2026-01-01T10:00:00Z
```

[合成データの再現例](examples/history-v1/REPORT.md)では、後から届いた情報を過去に持ち込むと集計が100%から50%に変わります。学習モデルの評価ではありません。訂正の分岐・循環・未到着の訂正元・時刻の矛盾はエラーにします。

## abstain-harとの合成データ連携

[接続仕様（英語）](INTEGRATION.md)に沿って履歴・品質検査後の3つの集計値を渡し、受信側で時刻・来歴・対象者の分割を確認します。合成6サンプルから4件を入力候補とし、情報不足1件・品質問題1件を区別して除外します。HARセンサー特徴量への変換、学習、モデルによる回答保留はまだ行いません。

```bash
python3 care_export.py fixtures/integration-request.json --output build/care-bundle.json
```

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

### 1分で再現したいとき

- [1分で始める手順](examples/ONE_MINUTE.md)

## 使い方（CLI）

```bash
python3 care_evidence.py fixtures/complete.json
python3 care_evidence.py fixtures/missing.json --format json
python3 care_evidence.py fixtures/complete.csv
```

JSONまたはCSVを入力できます。デフォルト出力は英語のMarkdownです。`--lang ja` で日本語を選べます。`--format json`では機械処理しやすい結果を出します。
CIでは `--format json --fail-on-issues` を使うと、品質問題がある場合は終了コード1、入力エラーは2になります。`--fail-on-issues` なしでは品質問題があっても従来どおり0です。入力エラー時は標準エラーに説明を出し、標準出力にはレポートを出しません。空データ、JSON内のオブジェクトでないイベント、CSVの重複・空ヘッダーや列数の不一致は入力エラーです。

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

このMVPはローカルのJSON/CSVを読み、ネットワーク・クラウド・アカウントを使いません。入力には実在の介護記録を入れず、合成データで試してください。

## GitHubでの進め方

- [最新リリース](https://github.com/larai-w/open-care-evidence-toolkit/releases)
- [変更履歴](CHANGELOG.md)
- [スター](https://github.com/larai-w/open-care-evidence-toolkit/stargazers)
- [引用情報](CITATION.md)
- [問題を報告する](https://github.com/larai-w/open-care-evidence-toolkit/issues/new)
- [issueテンプレート](https://github.com/larai-w/open-care-evidence-toolkit/issues/new/choose)
- [プルリクエスト](https://github.com/larai-w/open-care-evidence-toolkit/pulls)
- [開発ロードマップ](ROADMAP.md)
- [行動規範](CODE_OF_CONDUCT.md)
- [サポート窓口](SUPPORT.md)
