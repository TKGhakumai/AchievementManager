# Achievement Manager v0.8 第2段階：実績エディター（単体プレビュー）

## 起動
Windows PowerShellでプロジェクトのルートに移動し、以下を実行します。

```powershell
python -m pip install PyQt5
python achievement_editor.py
```

`achievement_editor.py` は第1段階の `achievement_core/store.py` を使用します。
保存先は新規作成される `v08_editor_demo.sqlite3` です。既存のv0.7のDBには触れません。

## できること
- Twitch共通の4テンプレートから作成
- 実績名、説明、ランク、回数、キーワード編集
- 折り畳み式詳細設定、2条件までのAND/OR
- 入力検証、保存済み実績の一覧・再編集・無効化

## 制限・今後
- まだ `main.py` と統合されていません。解除判定・OBS通知には反映されません。
- 画面上で設定できるのは最大2条件です（ストアは最大5条件）。
- 編集画面は `twitch_template` / `tkg_template` を追加するUIではなく、一般Twitchイベントの `custom` のみ扱います。
- 無効化は論理削除です。履歴保護のためDBから物理削除しません。
- v0.7本体へ統合する前に、既存 `main.py` の構造とDB保存先を確認してください。
