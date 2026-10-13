# Achievement Manager v0.8 — Stage 3 (UI integration preview)

- v0.7の既存タブと配色を残し、「実績管理（v0.8）」タブを追加しました。
- 実績エディターは既存アプリのQTabWidget内に表示され、アプリのテーマを継承します。
- 実績の作成・編集・無効化は `%LOCALAPPDATA%\AchievementManager\achievements_v08_preview.db` に保存します。
- **重要:** v0.7の固定実績31件、進捗、解除判定、TKG既存連携はまだ置換していません。実績エディターで作った実績は実際には解除されません。
- v0.7のインストーラーを置き換えず、開発用に動作確認してください。

## 手順
1. `develop-v0.8` ブランチで `main.py` と `achievement_editor.py` をこのZIPのものに更新し、`achievement_core/` を維持します。
2. Windowsで `python -m pip install -r requirements.txt` を実行します。
3. `python main.py` で起動し、「実績管理（v0.8）」タブを確認します。
4. 保存→再起動→実績一覧に残ること、既存タブが動くことを確認します。

## 注意
- v0.7の旧TKG受信処理は引き続き自動起動します。手動WebSocket接続への変更は次段階です。
- v0.7のデフォルト実績（TKG関連含む）はまだ残ります。公開前に汎用テンプレートへ移行します。
- v0.8用データベースは試験専用です。本番DBへの移行は別途実装します。
