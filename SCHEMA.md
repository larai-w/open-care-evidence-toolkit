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
| `schema_version` | integer | yes | 入力契約のバージョン |

## 6つの検査規則

| 規則ID | 検査 | 問題にする条件 |
|---|---|---|
| `required_fields` | 必須フィールド | 列またはキーが欠けている |
| `timestamp_timezone` | 時刻とタイムゾーン | ISO 8601でない、時刻にオフセットがない、または`timezone`が空 |
| `observation_interpretation` | 観察と解釈の分離 | 観察欄に推測表現がある、または`observed`なのに観察が空 |
| `provenance` | 出典と記録者 | `source`または`recorder_role`が空 |
| `missingness_status` | 欠測と非発生 | 未定義の状態、または`not_recorded`に内容がある |
| `correction_reference` | 訂正履歴 | `corrects`がIDまたはID配列でない |

検査は計算や診断を行いません。「記録がない」ことから、出来事が起きていないとは推定しません。
