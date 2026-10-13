# Achievement Manager v0.8.0-beta.5

## 変更
- ダッシュボードの実績解除ログはアプリ起動時に空。起動後のイベントだけ最大50件表示。
- 「ログをクリア」ボタンを追加。DBのイベント履歴・実績進捗・解除状態は一切削除しない。
- 個人実績カードの実績名に、解除から12時間未満だけ「NEW」を表示。
- 30秒ごとに表示更新し、期限切れを自動反映。再起動しても解除日時に基づき判定。
- 解除済みの背景強調・並び替えは従来どおり。

## 配布
`develop-v0.8` にZIPの中身を反映し、GitHub Actionsでビルド。
`AchievementManager-Setup-v0.8.0-beta.5.exe` のWindows動作確認後、タグ `v0.8.0-beta.5` をPre-releaseとして作成してください。
既存のbeta.4は残し、リリースのAssetsはbeta.5のEXEにします。

## 注意
Python構文とロジックは確認済みですが、WindowsのPyQt5画面とEXEは未検証です。
