# Achievement Manager v0.7.0-beta.2 — GitHub公開準備版

## 今回の更新

- 手動アクセストークン・ログイン名入力欄を削除
- 「Twitchでログイン」「再接続」「切断」「ログアウト」を実装
- ログイン中のアカウント名を表示
- 特定スタンプ名の設定・保存、31種類の実績、OBS通知は維持
- 公開Client IDを `app_config.json` に設定済み（Client Secretは含まれません）

**ログイン**はブラウザ認可を開始します。**再接続**は保存済みの認証情報を再利用し、期限切れの場合は更新を試みます。**切断**はチャットのみ切断し、**ログアウト**はWindows資格情報ストアの保存情報も削除します。Twitch側の認可取り消しはTwitchの設定から別途行ってください。

## ソース版の起動

Windowsで `start.bat` を実行するか、ターミナルから以下を実行します。

```powershell
python -m pip install -r requirements.txt
python main.py
```

## GitHub Actionsでインストーラー作成

1. GitHubで新規リポジトリを作成（まずPrivate推奨）。
2. **このフォルダの中身**をリポジトリ直下にアップロード。秘密情報や個人用DBがないか確認。
3. GitHubの **Actions → Windows beta build → Run workflow** を実行。
4. 成功したら **Artifacts** から `AchievementManager-Setup-v0.7.0-beta.2` を取得。
5. Windows PCでインストール、ログイン、再接続、ログアウト、スタンプ、OBS通知を検証。
6. **Releases → Draft a new release** で `v0.7.0-beta.2` をタグに指定し、インストーラーを添付。**Pre-release** を選んで公開。

ビルドにはPyInstallerとInno Setupを使用します。GitHub Actionsのビルドはこの環境では実行できていません。

## 既知の制限

- アプリ内自動更新とReleasesへの自動アップロードは未実装。
- IRC接続中にトークンが失効した場合の完全自動再接続は未実装。「再接続」で更新できます。
- OAuthコールバックの `http://localhost:3000/` はTwitch Developer Consoleの設定と一致が必要。ポート3000が使用中だとログインできません。
- TKG連携は任意の補助スクリプトです。他の配信者の環境で動作する保証はありません。
- 特定スタンプはIRC emotesタグに含まれるTwitchエモートのみ対象。第三者エモートには非対応。
- 配布用EXEは未署名のためWindows SmartScreenで警告が出る場合があります。
- ユーザーデータは `%LOCALAPPDATA%\AchievementManager\` に保存されます。アンインストール時も保持されます。
- ライセンスファイルは未確定です。Publicリポジトリにする前に利用許諾を決めてください。

## v0.8予定

実績の追加・変更・削除、判定条件・ランク・アイコン設定、削除前の確認と解除履歴保護。

---

## v0.7 Beta：特定スタンプの設定

「設定・接続」→「特定スタンプ実績の設定」から「グットゲーム！！」の対象スタンプ名を変更し、「対象スタンプ名を保存」を押します。初期値は `shirat43Gg` です。設定はQSettingsに保存され、次回起動時にも復元されます。Twitch接続中でも保存後のチャットから新設定を使用します。

実績解除はTwitch IRCの`emotes`タグに記載されたスタンプの文字範囲と、設定名が一致したときのみ行います。名前を単にテキストで送っただけでは解除されません。累計スタンプ実績は引き続き全Twitchエモートが対象です。Twitchが`emotes`タグに含めない第三者スタンプなどは対象外です。画像の変更・選択UIは今回の範囲に含みません。

判定の単体テスト: `python test_emote_matching.py`。

