# Achievement Manager v0.8 — Stage 7（開発・検証版）

## 今回の変更
- 「設定・接続」に「TKG接続」「TKG切断」ボタンを追加。起動時は未接続、再起動しても自動接続しません。
- 接続した場合に限り `127.0.0.1:8767` で既存の認証付きHTTPイベント受信APIを起動。切断すると停止します。
- `GET /api/status`（`X-Achievement-Key` ヘッダー必須）を追加。protocol_version=1、対応イベント種別、接続状態をJSONで返します。
- イベント受信 `POST /api/event` の既存仕様を維持。受信後は既存の進捗・解除・通知処理を使用します。
- アプリ終了・再起動時に接続を停止するよう修正。

## 更新
1. Achievement Managerを終了し、`%LOCALAPPDATA%\AchievementManager\achievements.db` をバックアップ。
2. ZIP内の `main.py`、`achievement_editor.py`、`achievement_core/` をdevelop-v0.8へ上書き。
3. `python main.py` を実行し、「設定・接続」の「TKG接続」を押して待機表示を確認。「TKG切断」で停止することを確認。
4. OBSブラウザソースURLは従来どおり `http://127.0.0.1:8766/`。

## 重要な制限
- この段階は **Achievement Manager側の手動連携受信口** です。TKG本体の送信機能を変更していないため、ボタンだけで既存のTKGが自動的にイベント送信するわけではありません。
- 接続方式は既存のローカルHTTP API（8767番）であり、WebSocket 8765番ではありません。両アプリを接続するにはTKG側に対応した送信実装が必要です。
- TKGのコードや素材は同梱しません。旧31実績のTKG関連項目は後方互換のため残ります。
- TwitchユーザーID解決には、従来どおりTwitchチャット接続で認証情報を得る必要があります。
- Windows実機でのGUI・TKG間疎通・OBS表示は未検証です。公開リリース前に確認してください。
