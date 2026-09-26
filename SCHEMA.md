# 最小イベントスキーマ

このMVPの入力契約です。値は合成データを前提にしています。

| フィールド | 型 | 必須 | 意味 |
|---|---|---:|---|
| `event_id` | string | yes | イベントを一意に識別するID |
| `observed_at` | ISO 8601 datetime | yes | 観察した時刻。タイムゾーンオフセット必須 |
| `timezone` | IANA timezone string | yes | 例: `Asia/Tokyo` |
| `source` | string | yes | 記録の出所。例: `synthetic-care-log` |
| `recorder_role` | string | yes | 記録者の役割。個人名は入れない |
| `observation` | string | yes | 見聞きした事実。推測を書かない |
| `interpretation` | string | yes | 解釈。空文字は解釈なしを表す |
| `status` | enum | yes | `observed` / `not_recorded` / `not_occurring` |
| `corrects` | string or string[] | yes | 訂正元イベントID。なければ `[]` |
| `schema_version` | number | yes | 値は1。真偽値・文字列は不可 |

## 6つの検査規則

| 規則ID | 検査 | 問題にする条件 |
|---|---|---|
| `required_fields` | 必須フィールド | 列またはキーが欠けている、IDが空または文字列でない、バージョンが数値1でない |
| `timestamp_timezone` | 時刻とタイムゾーン | 対応書式・実在する日時でない、オフセットが不正、または`timezone`が空・文字列でない |
| `observation_interpretation` | 観察と解釈の分離 | 文字列型でない、観察欄に推測表現がある、または`observed`なのに観察が空 |
| `provenance` | 出典と記録者 | `source`または`recorder_role`が空・文字列でない |
| `missingness_status` | 欠測と非発生 | 未定義の状態、または`not_recorded`に内容がある |
| `correction_reference` | 訂正履歴 | `corrects`が空でない文字列IDまたはその配列でない |

検査は計算や診断を行いません。「記録がない」ことから、出来事が起きていないとは推定しません。

## 履歴再現用の拡張

`care_history.py` は別の明示的な `history_schema_version: 1` ラッパーで、各イベントに `received_at`（到着時刻）と `corrected_at`（訂正作成時刻、元記録はnull）を要求します。既存CLI/ブラウザはこの履歴処理を行いません。訂正は単一の直前バージョンを参照し、観察時刻を維持します。詳細な検証・可視性・分岐の方針は [HISTORY.md](HISTORY.md) を参照してください。

## CLI・ブラウザの共通フィールド検査

両入口で、文字列欄の型、空でないevent_id、数値1のschema_version、correctsの各要素を検査します。訂正なしは`[]`です。nullや空文字のcorrectsは品質問題です。必須キー・ID・バージョンは既存のrequired_fields規則にまとめ、規則IDは6種類のままです。

日時は`YYYY-MM-DDTHH:MM:SS`＋任意の小数1〜6桁＋`Z`または`±HH:MM`に限定し、実在する日付を確認します。従来通った不正値が品質ゲートで拒否される変更です。JSONの1.0は数値1として受理します。IANA名や訂正先の存在は一般イベント検査では確認しません。詳細と移行方法は[英語の互換性仕様](docs/input-compatibility.md)を参照してください。履歴処理の日時パーサー・厳格な整数指定は別契約です。
