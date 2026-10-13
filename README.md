# Achievement Manager v0.8.0-beta.2 — 配布用ソース

**Stage 8の解除済み実績の強調表示、★並び替え、実績編集、TKG任意接続を維持した公開候補版です。**

## v0.7のTwitch自動ログインを復元
「設定・接続」→「Twitchでログイン（自動取得）」で、初回はブラウザ認証（OAuth Authorization Code + PKCE）を行います。
アクセストークンの手入力は不要です。トークンはWindowsの資格情報保管庫（keyring）に保存し、次回ログインボタンを押したとき再利用・期限切れなら更新します。
Twitch Client Secretは使用・配布しません。公開Client IDは`app_config.json`に収録済みです。

**Twitch開発者コンソールで、Client IDに対応するアプリのリダイレクトURL `http://localhost:3000/` が登録されていることを確認してください。**
ポート3000が使用中だと初回認証できません。

## 公開向けUI
ダッシュボードのテストイベント送信欄・テストチャット入力欄を削除しました。
`test_user_001`等の既存テストデータがユーザーのDBに残っている場合、データ保護のため自動削除しません。

## GitHub ActionsでWindowsインストーラーを生成
1. `develop-v0.8`ブランチにZIPの**中身**をアップロード（`.github/workflows/windows-build.yml`を含む）。
2. GitHub → Actions → `Windows v0.8 Beta installer` → Run workflow → `develop-v0.8`。
3. Artifactsから `AchievementManager-Setup-v0.8.0-beta.2` を取得。
4. Windowsで新規インストール、v0.7からの上書き、Twitch認証、チャット進捗、OBS、解除済み強調表示を検証。
5. 合格後、GitHub Releasesにタグ `v0.8.0-beta.2` で **Pre-release** としてインストーラーを添付。

このZIPには完成済みWindows EXEは含まれません。インストーラー公開は実機検証後に行ってください。

## ローカルビルド
Windows + Python 3.12 + Inno Setup 6:
```powershell
./build/build_windows.ps1
& 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' 'installer\setup.iss'
```

## 注意
- DB保存先: `%LOCALAPPDATA%\AchievementManager\achievements.db`。アップグレード前にバックアップしてください。
- 既存31実績のうち配信者固有のものやTKG専用のものは、今回の更新では除外していません。**一般向け公開前に初期実績の構成を確認してください。**
- TKG本体・秘密鍵・ユーザーDBは同梱しません。TKGイベント送信側の実装は別途必要です。
- GitHub ActionsのWindowsビルド、実際のTwitch認証、OBS通知はこの環境では未検証です。
- アプリ内自動アップデートはまだ実装していません。
