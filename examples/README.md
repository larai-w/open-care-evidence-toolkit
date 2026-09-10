# 1分で試す

この例はすべて合成データです。リポジトリのルートから実行します。

## 問題のない記録

```bash
python3 care_evidence.py fixtures/complete.json
```

```text
# データ品質サマリー

- イベント数: 1
- 問題数: 0

## evt-demo-001
✅ 6規則を通過
```

## 欠測を「問題なし」と解釈した記録

```bash
python3 care_evidence.py fixtures/missing.json
```

```text
# データ品質サマリー

- イベント数: 1
- 問題数: 4

## evt-demo-002
- ⚠️ 時刻とタイムゾーン: timezone がありません
- ⚠️ 出典と記録者: source と recorder_role を記録してください
- ⚠️ 欠測と非発生の区別: not_recorded に観察・解釈を入れないでください
- ⚠️ 訂正履歴: corrects は元イベントIDまたはID配列です
```

この出力は診断やリスク判定ではありません。どの項目が不足し、どの境界を曖昧にしたかを示すだけです。
