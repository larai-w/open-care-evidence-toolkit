# Contributing

小さく再現可能な改善を歓迎します。現在は公開前のローカルMVPです。

## 提案の範囲

- 合成fixture、スキーマ説明、検査規則、アクセシビリティ、決定的なテストを優先します。
- 医療判断、診断、個人データ、施設を特定できる情報、外部送信を追加しないでください。
- 1つの変更を小さく保ち、入力・期待結果・検証コマンドを説明してください。

## ローカル確認

```bash
python3 -m unittest discover -s tests -v
python3 care_evidence.py fixtures/complete.json
```

ブラウザデモは `demo.html` を直接開いて確認できます。公開後のIssue/PR導線は、リポジトリ作成時に設定します。
