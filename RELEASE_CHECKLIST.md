# v0.8.0-beta.2 公開前チェック

- [ ] GitHub ActionsのWindows EXE/インストーラー生成が成功
- [ ] `http://localhost:3000/` がTwitchアプリのOAuth Redirect URIに登録済み
- [ ] 初回「Twitchでログイン」でブラウザ認証→接続
- [ ] 再起動後のログインボタンで保存トークンを再利用
- [ ] 「Twitch認証情報を削除」で認証情報を消去
- [ ] コメント・スタンプ・キーワードで進捗／解除が反映
- [ ] OBS通知が表示される
- [ ] 個人実績カードの解除済み強調表示、★昇順降順
- [ ] v0.7からの上書きで既存DB・解除履歴が保持
- [ ] ダッシュボードにテストイベントUIがない
- [ ] 一般公開向けの初期実績（TKG固有31実績など）を見直し済み
- [ ] Client Secret・DB・トークン・TKG本体の機密素材がリポジトリにない
- [ ] Windows Defender/SmartScreen、新規インストール、アンインストールを確認
- [ ] Releasesで`v0.8.0-beta.2`をPre-releaseにして配布
