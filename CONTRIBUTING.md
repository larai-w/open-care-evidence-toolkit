# Contributing

小さく再現可能な改善を歓迎します。公開されているMVPとして、改善提案と検証を中心に進めます。

## 提案の範囲

- 合成fixture、スキーマ説明、検査規則、アクセシビリティ、決定的なテストを優先します。
- 医療判断、診断、個人データ、施設を特定できる情報、外部送信を追加しないでください。
- 1回のPRは小さく保ち、背景、再現手順、期待結果、検証コマンドを明記してください。

## ローカル確認

```bash
python3 -m unittest discover -s tests -v
python3 care_evidence.py fixtures/complete.json
python3 scripts/check_public_repo.py
```

コミット前に同じ確認を自動で走らせるには、クローンごとに一度だけ次を実行してください（`scripts/check_public_repo.py --staged` と、入っていれば gitleaks が走ります）。

```bash
git config core.hooksPath .githooks
```

ブラウザデモは `demo.html` を直接開いて確認できます。公開用の変更では、実行前に `python3 scripts/check_public_repo.py` を実行してください。内部用の下書き・秘密鍵形式・既知のトークン形式が混入していないかを確認します。

## すぐに寄与しやすい改善

公開性を上げるため、まずは以下の小さな改善から着手しやすいです。

- 問題の最小再現サンプルを追加
- ルール定義の説明を明確化
- 追加検証ケースをテストに入れる
