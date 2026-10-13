# Achievement Manager v0.8 — Stage 5（開発版）

## 変更点
- 「実績一覧」と「個人実績カード」に★ランク昇順・降順セレクターを追加。
- それぞれの「★ ランク」列見出しをクリックしても昇順・降順を切り替えられます。
- 初期表示は★1→★5。同じランクでは元の並びを維持します。
- 新規追加・編集保存後の画面更新時も現在選択中の並び順を維持して再配置します。
- 並び替えは表示上のみ。SQLiteの実績ID・解除履歴・進捗は変更しません。

## Twitch連携の現状
- Stage 4から引き継いだIRCチャット受信・コメント／スタンプ／キーワード判定を保持。
- チャネポのTwitch EventSub自動受信は未実装です。TKG手動接続も未実装です。
- 本ZIPはライブ配信に接続しての実機試験をしていません。Windows上で接続・カウント・解除通知の動作確認が必要です。

## 更新方法
1. アプリを終了し `%LOCALAPPDATA%\AchievementManager\achievements.db` をバックアップ。
2. `develop-v0.8` の `main.py`、`achievement_editor.py`、`achievement_core/` をこのZIPで更新。
3. Windowsで `python main.py` を実行。
4. 新規追加・★ランク編集・昇順／降順の切替・個人実績カードの表示を確認。

## 確認事項
- 本環境で構文チェックと並び替えロジックの自動テストを実施。
- PyQt5のWindows画面操作とTwitchライブ接続は未検証。
